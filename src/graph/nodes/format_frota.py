import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.graph.state import State

# Marcadores "[doc#secao]" que os tools MCP colocam no início de cada trecho.
_PADRAO_FONTE = re.compile(r"\[([^\]#]+#[^\]]+)\]")


def _texto(conteudo: Any) -> str:
    if isinstance(conteudo, list):
        return " ".join(
            bloco.get("text", "") if isinstance(bloco, dict) else str(bloco)
            for bloco in conteudo
        )
    return str(conteudo)


def _resposta_final(state: State) -> str:
    resultados = [
        f"{mensagem.name}: {_texto(mensagem.content)}"
        for mensagem in state.get("messages", [])
        if mensagem.type == "tool"
    ]
    if not resultados:
        raise RuntimeError(
            "O agente MCP terminou sem resposta textual nem resultados de ferramentas."
        )

    from src.utils.llm_adapter import get_llm

    resultados_texto = "\n".join(resultados)
    resposta = get_llm().invoke(
        [
            SystemMessage(
                content=(
                    "Responda em português à pergunta usando somente os resultados "
                    "das ferramentas. Não chame ferramentas nem exponha raciocínio "
                    "interno. Para perguntas sobre chegada/ETA, compare todas as "
                    "rotas possíveis; em tempestade, respeite o limite seguro de "
                    "cada rota e escolha o menor ETA válido. Exclua navios com "
                    "combustível abaixo da reserva. Se os dados não bastarem, diga "
                    "isso claramente."
                )
            ),
            HumanMessage(
                content=(
                    f"Pergunta: {state['pergunta']}\n\n"
                    f"Resultados das ferramentas:\n{resultados_texto}"
                )
            ),
        ]
    ).content
    if not isinstance(resposta, str) or not resposta.strip():
        raise RuntimeError(
            "O modelo não produziu uma resposta textual após a tentativa final."
        )
    return resposta.strip()


def format_frota(state: State) -> dict[str, str]:
    # No caminho MCP as fontes vêm dentro do conteúdo das tool messages.
    fontes = list(state.get("fontes") or [])
    for mensagem in state.get("messages", []):
        if mensagem.type != "tool":
            continue
        fontes.extend(_PADRAO_FONTE.findall(_texto(mensagem.content)))
    fontes = list(dict.fromkeys(fontes))
    # G7: `resposta` é a versão já conferida pelo guard_output; o restante é
    # o comportamento antigo, mantido para quem chama este nó sem o grafo.
    resposta = (state.get("resposta") or "").strip()
    if not resposta:
        mensagens = state.get("messages", [])
        resposta = _texto(mensagens[-1].content).strip() if mensagens else ""
    if not resposta:
        resposta = _resposta_final(state)
    return {"resultado": f"{resposta}\nFontes: {', '.join(fontes)}"}
