from src.graph.state import State
from src.utils.vector_store import get_vector_store


def retrieve(state: State) -> dict:
    """Exercício 1: busca os 3 chunks mais próximos (apenas o manual)."""
    docs = get_vector_store(("manual_operacoes.txt",)).similarity_search(
        state["pergunta"], k=3
    )
    return {"contextos": docs}
