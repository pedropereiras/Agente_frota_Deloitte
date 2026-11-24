from src.graph.state import State
from src.guardrails.recuperacao import filtrar_chunks
from src.utils.vector_store import buscar, fonte


def retrieve_regras(state: State) -> dict:
    docs, descartes = filtrar_chunks(
        buscar(state["pergunta"], "manual_operacoes", k=3)
    )
    return {
        "contextos": docs,
        "fontes": [fonte(d) for d in docs],
        "alertas": descartes,
    }
