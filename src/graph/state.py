import operator
from typing import Annotated, TypedDict

from langchain_core.documents import Document
from langgraph.graph.message import add_messages


class State(TypedDict, total=False):
    pergunta: str
    intent: str
    contextos: list[Document]
    suficiente: bool
    resposta: str
    frota: list[dict]
    contexto_regras: str
    messages: Annotated[list, add_messages]
    fontes: Annotated[list[str], operator.add]
    afirmacoes_sem_base: list[str]
    resultado: str
    bloqueio: str
    alertas: Annotated[list[str], operator.add]

