"""Modelos SQLAlchemy de lançamentos e orçamentos."""

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum as SqlEnum, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.enums import TipoLancamento


def _enum_values(enum_type: type) -> list[str]:
    return [item.value for item in enum_type]


class Lancamento(Base):
    __tablename__ = "lancamentos"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    data: Mapped[date] = mapped_column(Date, index=True)
    descricao: Mapped[str] = mapped_column(String(180))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tipo: Mapped[TipoLancamento] = mapped_column(
        SqlEnum(
            TipoLancamento,
            values_callable=_enum_values,
            native_enum=False,
            length=10,
        ),
        index=True,
    )
    categoria: Mapped[str] = mapped_column(String(80), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class Orcamento(Base):
    __tablename__ = "orcamentos"
    __table_args__ = (
        UniqueConstraint("ano", "mes", "categoria", name="uq_orcamento_periodo_categoria"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    ano: Mapped[int] = mapped_column(Integer, index=True)
    mes: Mapped[int] = mapped_column(Integer, index=True)
    categoria: Mapped[str] = mapped_column(String(80))
    limite: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
