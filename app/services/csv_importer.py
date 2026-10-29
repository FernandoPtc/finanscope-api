"""Leitura, validação, normalização e deduplicação dos CSVs financeiros."""

import csv
import hashlib
import io
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import TipoLancamento
from app.models import Lancamento


CENTAVO = Decimal("0.01")
CAMPOS_OBRIGATORIOS = {"data", "descricao", "valor", "tipo", "categoria"}
TAMANHO_MAXIMO = 5 * 1024 * 1024
LINHAS_MAXIMAS = 10_000
TAMANHO_LOTE_HASH = 500


class CsvInvalido(ValueError):
    """Indica um CSV que não pode ser processado como arquivo de lançamentos."""


def normalizar_texto(valor: str) -> str:
    texto = unicodedata.normalize("NFKC", valor)
    return " ".join(texto.strip().split())


def normalizar_categoria(valor: str) -> str:
    texto = normalizar_texto(valor)
    if not texto:
        raise ValueError("categoria vazia")
    return texto.title()


def _chave_fingerprint(valor: str) -> str:
    return normalizar_texto(valor).casefold()


def _ler_valor(valor: str) -> Decimal:
    texto = valor.strip().replace("R$", "").replace(" ", "")
    if not texto:
        raise ValueError("valor vazio")
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        numero = Decimal(texto)
    except InvalidOperation as exc:
        raise ValueError("valor não é um número válido") from exc
    if not numero.is_finite() or numero <= 0:
        raise ValueError("valor deve ser positivo")
    if numero > Decimal("9999999999.99"):
        raise ValueError("valor excede o máximo aceito de 9.999.999.999,99")
    try:
        return numero.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    except InvalidOperation as exc:
        raise ValueError("valor excede o limite de precisão aceito") from exc


def _fingerprint(
    dia: date,
    descricao: str,
    valor: Decimal,
    tipo: TipoLancamento,
    categoria: str,
) -> str:
    partes = (
        dia.isoformat(),
        _chave_fingerprint(descricao),
        format(valor, ".2f"),
        tipo.value,
        _chave_fingerprint(categoria),
    )
    conteudo = "|".join(partes).encode("utf-8")
    return hashlib.sha256(conteudo).hexdigest()


def _parse_linha(row: dict[str, str | None]) -> tuple[dict, str]:
    try:
        dia = date.fromisoformat((row.get("data") or "").strip())
    except ValueError as exc:
        raise ValueError("data inválida; use AAAA-MM-DD") from exc

    descricao = normalizar_texto(row.get("descricao") or "")
    if not descricao or len(descricao) > 180:
        raise ValueError("descrição deve ter entre 1 e 180 caracteres")

    try:
        tipo = TipoLancamento((row.get("tipo") or "").strip().casefold())
    except ValueError as exc:
        raise ValueError("tipo deve ser 'despesa' ou 'receita'") from exc

    categoria = normalizar_categoria(row.get("categoria") or "")
    if len(categoria) > 80:
        raise ValueError("categoria deve ter no máximo 80 caracteres")

    valor = _ler_valor(row.get("valor") or "")
    fingerprint = _fingerprint(dia, descricao, valor, tipo, categoria)
    dados = {
        "data": dia,
        "descricao": descricao,
        "valor": valor,
        "tipo": tipo,
        "categoria": categoria,
        "fingerprint": fingerprint,
    }
    return dados, fingerprint


def importar_csv(conteudo: bytes, session: Session) -> dict:
    if len(conteudo) > TAMANHO_MAXIMO:
        raise CsvInvalido("o arquivo excede o limite de 5 MB")
    try:
        texto = conteudo.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvInvalido("salve o CSV com codificação UTF-8") from exc

    amostra = texto[:4096]
    try:
        delimitador = csv.Sniffer().sniff(amostra, delimiters=",;").delimiter
    except csv.Error:
        delimitador = ","

    leitor = csv.DictReader(io.StringIO(texto), delimiter=delimitador)
    if not leitor.fieldnames:
        raise CsvInvalido("o arquivo não possui cabeçalho")
    leitor.fieldnames = [campo.strip().casefold() for campo in leitor.fieldnames]
    faltando = CAMPOS_OBRIGATORIOS - set(leitor.fieldnames)
    if faltando:
        nomes = ", ".join(sorted(faltando))
        raise CsvInvalido(f"faltam colunas obrigatórias: {nomes}")

    registros: list[dict] = []
    fingerprints_no_arquivo: set[str] = set()
    erros: list[dict[str, int | str]] = []
    erros_total = 0
    duplicados_no_arquivo = 0
    linhas_lidas = 0

    for linha, row in enumerate(leitor, start=2):
        if not row or not any(valor and valor.strip() for valor in row.values() if isinstance(valor, str)):
            continue
        linhas_lidas += 1
        if linhas_lidas > LINHAS_MAXIMAS:
            raise CsvInvalido(f"o arquivo excede o limite de {LINHAS_MAXIMAS} linhas")
        try:
            dados, fingerprint = _parse_linha(row)
        except ValueError as exc:
            erros_total += 1
            if len(erros) < 100:
                erros.append({"linha": linha, "mensagem": str(exc)})
            continue

        if fingerprint in fingerprints_no_arquivo:
            duplicados_no_arquivo += 1
            continue
        fingerprints_no_arquivo.add(fingerprint)
        registros.append(dados)

    if linhas_lidas == 0:
        raise CsvInvalido("o CSV não contém linhas de dados")

    fingerprints = [registro["fingerprint"] for registro in registros]
    existentes: set[str] = set()
    for inicio in range(0, len(fingerprints), TAMANHO_LOTE_HASH):
        lote = fingerprints[inicio:inicio + TAMANHO_LOTE_HASH]
        if lote:
            encontrados = session.scalars(
                select(Lancamento.fingerprint).where(Lancamento.fingerprint.in_(lote))
            ).all()
            existentes.update(encontrados)

    novos = [
        Lancamento(**registro)
        for registro in registros
        if registro["fingerprint"] not in existentes
    ]
    session.add_all(novos)
    session.commit()

    duplicados_banco = len(registros) - len(novos)
    return {
        "linhas_lidas": linhas_lidas,
        "importados": len(novos),
        "duplicados": duplicados_no_arquivo + duplicados_banco,
        "rejeitados": erros_total,
        "erros": erros,
        "erros_omitidos": max(0, erros_total - len(erros)),
    }
