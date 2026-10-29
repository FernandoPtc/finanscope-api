"""Agregações financeiras por mês e por categoria."""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import TipoLancamento
from app.models import Lancamento, Orcamento


ZERO = Decimal("0.00")


def limites_mes(ano: int, mes: int) -> tuple[date, date]:
    inicio = date(ano, mes, 1)
    if mes == 12:
        fim = date(ano + 1, 1, 1)
    else:
        fim = date(ano, mes + 1, 1)
    return inicio, fim


def relatorio_mensal(session: Session, ano: int, mes: int) -> dict:
    inicio, fim = limites_mes(ano, mes)
    lancamentos = session.scalars(
        select(Lancamento).where(Lancamento.data >= inicio, Lancamento.data < fim)
    ).all()
    orcamentos = session.scalars(
        select(Orcamento).where(Orcamento.ano == ano, Orcamento.mes == mes)
    ).all()

    receitas = sum(
        (item.valor for item in lancamentos if item.tipo == TipoLancamento.RECEITA), ZERO
    )
    despesas = sum(
        (item.valor for item in lancamentos if item.tipo == TipoLancamento.DESPESA), ZERO
    )
    despesas_categoria: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for item in lancamentos:
        if item.tipo == TipoLancamento.DESPESA:
            despesas_categoria[item.categoria] += item.valor

    limites = {item.categoria: item.limite for item in orcamentos}
    categorias = sorted(
        set(despesas_categoria) | set(limites),
        key=lambda nome: despesas_categoria[nome],
        reverse=True,
    )
    por_categoria = []
    for categoria in categorias:
        gasto = despesas_categoria[categoria]
        limite = limites.get(categoria)
        restante = limite - gasto if limite is not None else None
        percentual = (gasto / limite * Decimal("100")).quantize(Decimal("0.01")) if limite else None
        por_categoria.append(
            {
                "categoria": categoria,
                "despesas": gasto,
                "orcamento": limite,
                "restante": restante,
                "percentual_usado": percentual,
            }
        )

    return {
        "ano": ano,
        "mes": mes,
        "receitas": receitas,
        "despesas": despesas,
        "saldo": receitas - despesas,
        "por_categoria": por_categoria,
    }


def adicionar_meses(mes_atual: date, deslocamento: int) -> date:
    indice = mes_atual.year * 12 + (mes_atual.month - 1) + deslocamento
    ano, mes_zero = divmod(indice, 12)
    return date(ano, mes_zero + 1, 1)


def tendencia_mensal(session: Session, quantidade: int) -> list[dict]:
    mes_corrente = date.today().replace(day=1)
    inicio = adicionar_meses(mes_corrente, -(quantidade - 1))
    fim = adicionar_meses(mes_corrente, 1)
    lancamentos = session.scalars(
        select(Lancamento).where(Lancamento.data >= inicio, Lancamento.data < fim)
    ).all()

    totais: dict[tuple[int, int], list[Decimal]] = defaultdict(lambda: [ZERO, ZERO])
    for item in lancamentos:
        valores = totais[(item.data.year, item.data.month)]
        indice = 0 if item.tipo == TipoLancamento.RECEITA else 1
        valores[indice] += item.valor

    resultado = []
    for deslocamento in range(quantidade):
        periodo = adicionar_meses(inicio, deslocamento)
        receitas, despesas = totais[(periodo.year, periodo.month)]
        resultado.append(
            {
                "ano": periodo.year,
                "mes": periodo.month,
                "receitas": receitas,
                "despesas": despesas,
                "saldo": receitas - despesas,
            }
        )
    return resultado
