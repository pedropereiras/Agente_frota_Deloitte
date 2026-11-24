from src.graph.state import State
from src.graph.tools import TOOLS
from src.utils.llm_adapter import get_llm, invocar_com_retry


def analyze(state: State) -> dict:
    llm = get_llm().bind_tools(TOOLS)
    return {"messages": [invocar_com_retry(llm, state["messages"], TOOLS)]}
