from src.graph.state import State
from src.guardrails.recuperacao import filtrar_chunks
from src.utils.vector_store import buscar, fonte


def retrieve_frota(state: State) -> dict:
    # k alto de propósito: a pergunta compara todos os navios, então todas as seções entram
    docs, descartes = filtrar_chunks(
        buscar(state["pergunta"], "relatorio_frota", k=10)
    )
    return {
        "contextos": docs,
        "fontes": [fonte(d) for d in docs],
        "alertas": descartes,
    }
