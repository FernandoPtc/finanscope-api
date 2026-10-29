"""Rotas de importação, consulta, orçamento e relatórios financeiros."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_session
from app.enums import TipoLancamento
from app.models import Lancamento, Orcamento
from app.schemas import (
    LancamentoPage,
    LancamentoRead,
    OrcamentoCreate,
    OrcamentoRead,
    RelatorioMensal,
    ResumoImportacao,
    TendenciaMensal,
)
from app.services.csv_importer import CsvInvalido, importar_csv, normalizar_categoria
from app.services.reporting import relatorio_mensal, tendencia_mensal


router = APIRouter(prefix="/api/v1", tags=["Finanças"])
SessionDep = Annotated[Session, Depends(get_session)]
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.post("/importacoes/csv", response_model=ResumoImportacao)
def importar_lancamentos_csv(
    session: SessionDep,
    file: Annotated[UploadFile, File(description="Arquivo CSV em UTF-8")],
) -> dict:
    if not file.filename or not file.filename.casefold().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Envie um arquivo com extensão .csv.")
    conteudo = file.file.read(MAX_UPLOAD_BYTES + 1)
    try:
        return importar_csv(conteudo, session)
    except CsvInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="A importação coincidiu com outra gravação. Tente enviar o arquivo novamente.",
        ) from exc


@router.get("/lancamentos", response_model=LancamentoPage)
def listar_lancamentos(
    session: SessionDep,
    tipo: TipoLancamento | None = None,
    categoria: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    data_de: date | None = None,
    data_ate: date | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LancamentoPage:
    if data_de and data_ate and data_de > data_ate:
        raise HTTPException(status_code=422, detail="data_de não pode ser posterior a data_ate.")

    filtros = []
    if tipo is not None:
        filtros.append(Lancamento.tipo == tipo)
    if categoria:
        try:
            categoria_normalizada = normalizar_categoria(categoria)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Categoria inválida.") from exc
        filtros.append(Lancamento.categoria == categoria_normalizada)
    if q:
        termo = f"%{q.strip()}%"
        filtros.append(or_(Lancamento.descricao.ilike(termo), Lancamento.categoria.ilike(termo)))
    if data_de is not None:
        filtros.append(Lancamento.data >= data_de)
    if data_ate is not None:
        filtros.append(Lancamento.data <= data_ate)

    total = session.scalar(
        select(func.count()).select_from(Lancamento).where(*filtros)
    ) or 0
    consulta = (
        select(Lancamento)
        .where(*filtros)
        .order_by(Lancamento.data.desc(), Lancamento.id.desc())
        .offset(offset)
        .limit(limit)
    )
    items = list(session.scalars(consulta).all())
    return LancamentoPage(items=items, total=total, offset=offset, limit=limit)


@router.get("/lancamentos/{lancamento_id}", response_model=LancamentoRead)
def obter_lancamento(lancamento_id: int, session: SessionDep) -> Lancamento:
    lancamento = session.get(Lancamento, lancamento_id)
    if lancamento is None:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado.")
    return lancamento


@router.put("/orcamentos", response_model=OrcamentoRead)
def salvar_orcamento(payload: OrcamentoCreate, session: SessionDep) -> Orcamento:
    try:
        categoria = normalizar_categoria(payload.categoria)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Categoria inválida.") from exc
    orcamento = session.scalar(
        select(Orcamento).where(
            Orcamento.ano == payload.ano,
            Orcamento.mes == payload.mes,
            Orcamento.categoria == categoria,
        )
    )
    if orcamento is None:
        orcamento = Orcamento(
            ano=payload.ano,
            mes=payload.mes,
            categoria=categoria,
            limite=payload.limite,
        )
        session.add(orcamento)
    else:
        orcamento.limite = payload.limite
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="Não foi possível salvar esse orçamento.") from exc
    session.refresh(orcamento)
    return orcamento


@router.get("/orcamentos", response_model=list[OrcamentoRead])
def listar_orcamentos(
    session: SessionDep,
    ano: Annotated[int, Query(ge=2000, le=2100)],
    mes: Annotated[int, Query(ge=1, le=12)],
) -> list[Orcamento]:
    consulta = (
        select(Orcamento)
        .where(Orcamento.ano == ano, Orcamento.mes == mes)
        .order_by(Orcamento.categoria)
    )
    return list(session.scalars(consulta).all())


@router.get("/relatorios/mensal", response_model=RelatorioMensal)
def obter_relatorio_mensal(
    session: SessionDep,
    ano: Annotated[int, Query(ge=2000, le=2100)],
    mes: Annotated[int, Query(ge=1, le=12)],
) -> dict:
    return relatorio_mensal(session, ano, mes)


@router.get("/relatorios/tendencia", response_model=list[TendenciaMensal])
def obter_tendencia_mensal(
    session: SessionDep,
    meses: Annotated[int, Query(ge=1, le=24)] = 6,
) -> list[dict]:
    return tendencia_mensal(session, meses)
