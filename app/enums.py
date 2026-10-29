"""Tipos de movimentação financeira aceitos pelo projeto."""

from enum import Enum


class TipoLancamento(str, Enum):
    DESPESA = "despesa"
    RECEITA = "receita"
