"""Schemas Pydantic para entrada e saída da API."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.enums import TipoLancamento


class LancamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data: date
    descricao: str
    valor: Decimal
    tipo: TipoLancamento
    categoria: str
    criado_em: datetime


class LancamentoPage(BaseModel):
    items: list[LancamentoRead]
    total: int
    offset: int
    limit: int


class ErroImportacao(BaseModel):
    linha: int
    mensagem: str


class ResumoImportacao(BaseModel):
    linhas_lidas: int
    importados: int
    duplicados: int
    rejeitados: int
    erros: list[ErroImportacao]
    erros_omitidos: int


class OrcamentoCreate(BaseModel):
    ano: int = Field(ge=2000, le=2100)
    mes: int = Field(ge=1, le=12)
    categoria: str = Field(min_length=2, max_length=80)
    limite: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class OrcamentoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ano: int
    mes: int
    categoria: str
    limite: Decimal
    criado_em: datetime


class CategoriaMensal(BaseModel):
    categoria: str
    despesas: Decimal
    orcamento: Decimal | None
    restante: Decimal | None
    percentual_usado: Decimal | None


class RelatorioMensal(BaseModel):
    ano: int
    mes: int
    receitas: Decimal
    despesas: Decimal
    saldo: Decimal
    por_categoria: list[CategoriaMensal]


class TendenciaMensal(BaseModel):
    ano: int
    mes: int
    receitas: Decimal
    despesas: Decimal
    saldo: Decimal
