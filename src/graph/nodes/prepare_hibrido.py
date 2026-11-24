from src.graph.prompts.mcp_analyze_prompt import MCP_ANALYZE_PROMPT
from src.graph.state import State


def prepare_hibrido(state: State) -> dict:
    """Monta as mensagens iniciais do caminho que consulta tudo via MCP."""
    mensagens = MCP_ANALYZE_PROMPT.format_messages(pergunta=state["pergunta"])
    return {"messages": mensagens}
