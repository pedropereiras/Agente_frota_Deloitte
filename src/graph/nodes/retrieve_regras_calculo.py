from src.graph.state import State
from src.guardrails.recuperacao import filtrar_chunks
from src.utils.vector_store import buscar, fonte

CONSULTA = "velocidade em tempestade, reserva de combustível e cálculo do ETA"


def retrieve_regras_calculo(state: State) -> dict:
    docs, descartes = filtrar_chunks(buscar(CONSULTA, "manual_operacoes", k=4))
    return {
        "contexto_regras": "\n\n".join(d.page_content for d in docs),
        "fontes": [fonte(d) for d in docs],
        "alertas": descartes,
    }
