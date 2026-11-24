from src.graph.prompts.rag_prompt import RAG_PROMPT
from src.graph.state import State
from src.guardrails.recuperacao import envelopar
from src.utils.llm_adapter import get_llm
from src.utils.vector_store import fonte


def generate(state: State) -> dict:
    # G4: o contexto recuperado chega ao modelo entre tags de dado, não como ordem.
    contexto = envelopar(
        [(fonte(d), d.page_content) for d in state["contextos"]],
        "manual_operacoes",
    )
    resposta = (RAG_PROMPT | get_llm()).invoke(
        {"contexto": contexto, "pergunta": state["pergunta"]}
    )
    return {"resposta": str(resposta.content)}
