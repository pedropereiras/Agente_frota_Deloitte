from pydantic import BaseModel

from src.graph.prompts.grade_prompt import GRADE_PROMPT
from src.graph.state import State
from src.utils.llm_adapter import get_llm


class Relevancia(BaseModel):
    suficiente: bool


def grade(state: State) -> dict:
    contexto = "\n\n".join(d.page_content for d in state["contextos"])
    chain = GRADE_PROMPT | get_llm().with_structured_output(Relevancia)
    r = chain.invoke({"contexto": contexto, "pergunta": state["pergunta"]})
    return {"suficiente": r.suficiente}
