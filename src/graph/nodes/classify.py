from typing import Literal

from pydantic import BaseModel

from src.graph.prompts.classify_prompt import CLASSIFY_PROMPT
from src.graph.state import State
from src.utils.llm_adapter import get_llm


class Intencao(BaseModel):
    intent: Literal["regra", "frota", "fora_escopo"]


def classify(state: State) -> dict:
    """G2: a intenção é enum fechado e a falha de parsing cai em `fora_escopo`.

    O fallback é fechado de propósito: não existe quarta intenção, então um
    erro do modelo não pode virar caminho novo no grafo.
    """
    chain = CLASSIFY_PROMPT | get_llm().with_structured_output(Intencao)
    try:
        return {"intent": chain.invoke({"pergunta": state["pergunta"]}).intent}
    except Exception:
        return {"intent": "fora_escopo", "alertas": ["CLASSIFY_FALHOU"]}
