from pydantic import BaseModel

from src.guardrails.recuperacao import envelopar
from src.graph.prompts.extract_prompt import EXTRACT_PROMPT
from src.graph.state import State
from src.utils.llm_adapter import get_llm
from src.utils.vector_store import fonte


class NavioRelatorio(BaseModel):
    id: str
    destino: str
    distancia_nm: float
    velocidade_kn: float
    combustivel_t: float
    reserva_t: float
    em_tempestade: bool


class Frota(BaseModel):
    navios: list[NavioRelatorio]


def extract_frota(state: State) -> dict:
    # G4: o relatório chega ao modelo como DADO, entre tags, e não como ordem.
    relatorio = envelopar(
        [(fonte(d), d.page_content) for d in state["contextos"]],
        "relatorio_frota",
    )
    chain = EXTRACT_PROMPT | get_llm().with_structured_output(Frota)
    frota = chain.invoke({"relatorio": relatorio})
    return {"frota": [n.model_dump() for n in frota.navios]}
