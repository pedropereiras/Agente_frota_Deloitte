from langchain_core.tools import BaseTool

from src.graph.state import State
from src.utils.llm_adapter import get_llm, invocar_com_retry


def make_analyze(tools: list[BaseTool]):
    """Cria o nó analyze com as ferramentas MCP informadas.

    Assim o builder decide quais tools o modelo enxerga (MCP, locais, ou ambas).
    """

    def analyze(state: State) -> dict:
        llm = get_llm().bind_tools(tools)
        return {"messages": [invocar_com_retry(llm, state["messages"], tools)]}

    return analyze
