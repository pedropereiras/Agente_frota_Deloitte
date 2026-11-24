from pydantic import BaseModel

from src.graph.prompts.grounding_prompt import GROUNDING_PROMPT
from src.graph.state import State
from src.utils.llm_adapter import get_llm

NAO_ENCONTRADO = "Não encontrado no manual de operações."


class Afirmacao(BaseModel):
    texto: str
    suportada: bool


class Verificacao(BaseModel):
    afirmacoes: list[Afirmacao]


def verify_grounding(state: State) -> dict:

    resposta = state.get("resposta", "").strip()
    if not resposta or resposta.startswith(NAO_ENCONTRADO):
        # Resposta de "não encontrado" não precisa de verificação.
        return {"afirmacoes_sem_base": []}

    contexto = "\n\n".join(d.page_content for d in state.get("contextos", []))
    chain = GROUNDING_PROMPT | get_llm().with_structured_output(Verificacao)
    verificacao = chain.invoke({"contexto": contexto, "resposta": resposta})
    sem_base = [a.texto for a in verificacao.afirmacoes if not a.suportada]
    return {"afirmacoes_sem_base": sem_base}

    """Confere se cada afirmação da resposta tem base literal no contexto recuperado.

    É a camada de defesa contra alucinação: o RAG informa, mas só o código
    consegue provar que a informação veio mesmo dos chunks.
    """