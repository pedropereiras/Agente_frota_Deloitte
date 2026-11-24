"""
Rodar (stdio, o cliente sobe o processo automaticamente):

    python -m mcp_server.server

Rodar (streamable HTTP, processo único e mais rápido por chamada):

    python -m mcp_server.server --http

"""

import sys
from pathlib import Path

# Garante que 'src' seja importável mesmo quando o processo é um subprocesso MCP.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("porto-alfa", host="127.0.0.1", port=8765)


def _aquecer() -> None:
    """Importa e indexa ANTES de começar a servir.

    Por quê: carregar extensões pesadas (numpy/torch) ou o modelo de embeddings
    no MEIO de uma chamada, com o event loop do servidor já rodando, travava o
    processo neste ambiente (Windows + venv dentro do OneDrive). Na inicialização
    o mesmo import leva ~1s e roda limpo.
    """
    from src.utils.vector_store import get_vector_store

    get_vector_store()  # indexa manual + relatório uma única vez


def _formatar(docs) -> str:
    if not docs:
        return "Nenhum trecho encontrado."
    from src.utils.vector_store import fonte

    return "\n\n".join(f"[{fonte(d)}]\n{d.page_content}" for d in docs)


@mcp.tool()
def consultar_manual(pergunta: str, k: int = 3) -> str:
    """RAG sobre o manual de operações: retorna os k trechos mais relevantes com a
    seção de origem. Use para regras, limites, valores, prazos e procedimentos."""
    from src.utils.vector_store import buscar

    return _formatar(buscar(pergunta, "manual_operacoes", k=k))


@mcp.tool()
def consultar_frota(pergunta: str, k: int = 10) -> str:
    """RAG sobre o relatório da frota: retorna os k trechos mais relevantes com a
    seção de origem. Use para dados atuais dos navios (distância, velocidade,
    combustível, reserva, tempestade). k alto porque perguntas comparativas
    precisam de todos os navios."""
    from src.utils.vector_store import buscar

    return _formatar(buscar(pergunta, "relatorio_frota", k=k))


@mcp.tool()
def calcular_eta_horas(distancia_nm: float, velocidade_kn: float) -> float:
    """Calcula o ETA em horas: distancia_nm dividida por velocidade_kn."""
    return round(distancia_nm / velocidade_kn, 2)


@mcp.tool()
def velocidade_efetiva(
    velocidade_kn: float, em_tempestade: bool, limite_tempestade_kn: float
) -> float:
    """Velocidade efetiva do navio. Em tempestade é limitada a limite_tempestade_kn
    (valor que deve vir do manual de operações, não de cabeça)."""
    return min(velocidade_kn, limite_tempestade_kn) if em_tempestade else velocidade_kn


@mcp.tool()
def reserva_ok(combustivel_t: float, reserva_t: float) -> bool:
    """True se o combustível a bordo cobre a reserva mínima (navio pode zarpar)."""
    return combustivel_t >= reserva_t


if __name__ == "__main__":
    if "--no-warm" not in sys.argv:
        _aquecer()
    if "--http" in sys.argv:
        mcp.run(transport="streamable-http")
    else:
        mcp.run()  # stdio
