from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.graph.nodes.analyze import analyze
from src.graph.nodes.classify import classify
from src.graph.nodes.extract_frota import extract_frota
from src.graph.nodes.format_frota import format_frota
from src.graph.nodes.format_output import format_output
from src.graph.nodes.generate import generate
from src.graph.nodes.grade import grade
from src.graph.nodes.nao_encontrado import nao_encontrado
from src.graph.nodes.prepare import prepare
from src.graph.nodes.refuse import refuse
from src.graph.nodes.retrieve_frota import retrieve_frota
from src.graph.nodes.retrieve_regras import retrieve_regras
from src.graph.nodes.retrieve_regras_calculo import retrieve_regras_calculo
from src.graph.routing import route_after_grade, route_by_intent
from src.graph.state import State
from src.graph.tools import TOOLS
from src.guardrails.nos import (
    blocked,
    guard_extracao,
    guard_input,
    guard_output,
    route_after_guard,
    route_after_output,
)
from src.guardrails.saida import definir_contexto_manual

# G6: sem `handle_tool_errors` a exceção da tool derruba o grafo em vez de
# voltar ao modelo como erro corrigível.
_TOOL_NODE = ToolNode(TOOLS, handle_tool_errors=True)


def tools(state: State, config) -> dict:
    """Nó `tools` com o manual ancorado no mesmo contexto da execução.

    G6: cada nó do LangGraph roda com um contexto de `ContextVar` próprio,
    então o `definir_contexto_manual` do `prepare` não chega aqui. Por isso o
    `contexto_regras` recuperado é reancorado antes de delegar ao `ToolNode` —
    é ele que lê `limite_tempestade_kn` em `velocidade_efetiva`.
    """
    definir_contexto_manual(state.get("contexto_regras", ""))
    return _TOOL_NODE.invoke(state, config)


def build_graph():
    """Grafo do exercício 2 com os guardrails G1, G2, G5 e G7 como nós.

    Os demais entram dentro de nós existentes: G3/G4 na recuperação e nos
    prompts, G6 nas tools, G8 na auditoria e G9 no ambiente.
    """
    graph = StateGraph(State)
    for nome, funcao in {
        "guard_input": guard_input,
        "blocked": blocked,
        "classify": classify,
        "retrieve_regras": retrieve_regras,
        "grade": grade,
        "generate": generate,
        "guard_output": guard_output,
        "format_output": format_output,
        "nao_encontrado": nao_encontrado,
        "retrieve_frota": retrieve_frota,
        "retrieve_regras_calculo": retrieve_regras_calculo,
        "extract_frota": extract_frota,
        "guard_extracao": guard_extracao,
        "prepare": prepare,
        "analyze": analyze,
        "format_frota": format_frota,
        "refuse": refuse,
    }.items():
        graph.add_node(nome, funcao)
    # G6: o wrapper `tools` ancora o manual no contexto antes de executar as
    # ferramentas; `handle_tool_errors` faz a exceção virar ToolMessage de erro.
    graph.add_node("tools", tools)

    graph.add_edge(START, "guard_input")
    graph.add_conditional_edges(
        "guard_input",
        route_after_guard,
        {"ok": "classify", "bloqueado": "blocked"},
    )
    graph.add_conditional_edges(
        "classify",
        route_by_intent,
        {"regra": "retrieve_regras", "frota": "retrieve_frota", "fora_escopo": "refuse"},
    )
    graph.add_edge("retrieve_regras", "grade")
    graph.add_conditional_edges(
        "grade", route_after_grade, {"suficiente": "generate", "insuficiente": "nao_encontrado"}
    )
    graph.add_edge("generate", "guard_output")
    graph.add_edge("retrieve_frota", "retrieve_regras_calculo")
    graph.add_edge("retrieve_regras_calculo", "extract_frota")
    graph.add_edge("extract_frota", "guard_extracao")
    graph.add_conditional_edges(
        "guard_extracao",
        route_after_guard,
        {"ok": "prepare", "bloqueado": "blocked"},
    )
    graph.add_edge("prepare", "analyze")
    graph.add_conditional_edges(
        "analyze", tools_condition, {"tools": "tools", END: "guard_output"}
    )
    graph.add_edge("tools", "analyze")
    graph.add_conditional_edges(
        "guard_output",
        route_after_output,
        {"regra": "format_output", "frota": "format_frota"},
    )
    for terminal in (
        "format_output",
        "nao_encontrado",
        "format_frota",
        "refuse",
        "blocked",
    ):
        graph.add_edge(terminal, END)
    return graph.compile()
