from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.graph.nodes.analyze_hibrido import make_analyze
from src.graph.nodes.classify import classify
from src.graph.nodes.format_frota import format_frota
from src.graph.nodes.format_output import format_output
from src.graph.nodes.generate import generate
from src.graph.nodes.grade import grade
from src.graph.nodes.nao_encontrado import nao_encontrado
from src.graph.nodes.prepare_hibrido import prepare_hibrido
from src.graph.nodes.refuse import refuse
from src.graph.nodes.retrieve_regras import retrieve_regras
from src.graph.nodes.verify_grounding import verify_grounding
from src.graph.routing import route_after_grade, route_by_intent
from src.graph.state import State


def build_graph_hibrido(mcp_tools: list[BaseTool]):
    """Grafo HÍBRIDO: RAG local para regras, ferramentas MCP para frota e cálculo.

    Contraste com o grafo do exercício 2:
      - exercício 2: os nós `retrieve_*` decidem O QUE buscar (pipeline fixo);
      - híbrido: o modelo decide QUAL ferramenta MCP chamar (RAG como ferramenta).
    """
    graph = StateGraph(State)
    for nome, funcao in {
        "classify": classify,
        # caminho regra → RAG local (barato, sem hop de rede)
        "retrieve_regras": retrieve_regras,
        "grade": grade,
        "generate": generate,
        "verify_grounding": verify_grounding,
        "format_output": format_output,
        "nao_encontrado": nao_encontrado,
        # caminho frota → tudo via MCP, decidido pelo modelo
        "prepare_hibrido": prepare_hibrido,
        "analyze": make_analyze(mcp_tools),
        "format_frota": format_frota,
        # fora de escopo
        "refuse": refuse,
    }.items():
        graph.add_node(nome, funcao)
    graph.add_node("tools", ToolNode(mcp_tools))

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        {"regra": "retrieve_regras", "frota": "prepare_hibrido", "fora_escopo": "refuse"},
    )
    # caminho regra: RAG local + verificação de alucinação
    graph.add_edge("retrieve_regras", "grade")
    graph.add_conditional_edges(
        "grade", route_after_grade, {"suficiente": "generate", "insuficiente": "nao_encontrado"}
    )
    graph.add_edge("generate", "verify_grounding")
    graph.add_edge("verify_grounding", "format_output")
    # caminho frota: o modelo chama as tools MCP quando quiser
    graph.add_edge("prepare_hibrido", "analyze")
    graph.add_conditional_edges(
        "analyze", tools_condition, {"tools": "tools", END: "format_frota"}
    )
    graph.add_edge("tools", "analyze")
    for terminal in ("format_output", "nao_encontrado", "format_frota", "refuse"):
        graph.add_edge(terminal, END)
    return graph.compile()
