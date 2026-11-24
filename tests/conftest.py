"""G9 — a suíte inteira roda sem rede: qualquer conexão sai da máquina e falha.

`src.utils.egress.instalar_guarda` troca `socket.connect` por uma guarda que
levanta `EgressBloqueado`. Um teste que tente falar com a internet morre
barulhento em vez de depender de chave de API ou de conexão disponível.
"""

import os

# Sem traço remoto durante os testes: langsmith/langfuse não têm para onde ir.
os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")
os.environ.setdefault("LANGFUSE_TRACING", "false")

import pytest

from src.utils.egress import instalar_guarda


@pytest.fixture(autouse=True)
def sem_rede():
    """Nenhum teste desta suíte pode abrir conexão externa."""
    restaurar = instalar_guarda(permitidos=set())
    try:
        yield
    finally:
        restaurar()
