"""Configuração do banco de dados e sessões SQLAlchemy."""

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finanscope.db")
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Base declarativa compartilhada pelos modelos."""


def get_session() -> Generator[Session, None, None]:
    """Fornece uma sessão por requisição e garante seu fechamento."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
