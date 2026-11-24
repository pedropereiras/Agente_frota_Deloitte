"""Interface Streamlit do agente Porto Alfa — tema "ponte de comando".

Execute a partir da raiz do projeto:

    streamlit run src/app/streamlit_app.py
    .\.venv\Scripts\python.exe -m streamlit run src\app\streamlit_app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Garante que "src.*" seja importável mesmo rodando de outro diretório.
RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st

from src.app.theme import (
    aplicar_tema,
    cabecalho,
    linha_fontes,
    marca_lateral,
    painel_lateral,
    rodape_lateral,
    rotulo_exemplos,
)
from src.graph.builder import build_graph
from src.utils.egress import instalar_egress_da_app
from src.utils.langfuse_client import flush, run_config

# G9: só o provedor do modelo e o Langfuse podem sair da máquina.
# Instalação idempotente — o Streamlit reexecuta este módulo a cada rerun.
instalar_egress_da_app()

st.set_page_config(
    page_title="Porto Alfa — Agente RAG",
    page_icon="🧭",
    layout="wide",
)
aplicar_tema()

EXEMPLOS = (
    "Qual é a distância da rota direta do S4-ATLAS?",
    "Qual a reserva mínima de combustível do S3-CORAL?",
    "Qual é a velocidade segura em tempestade na rota protegida?",
)


@st.cache_resource(show_spinner="Compilando o grafo do agente...")
def carregar_grafo():
    """Compila o grafo uma única vez e reaproveita entre execuções."""
    return build_graph()


@st.cache_resource(show_spinner="Indexando os documentos...")
def aquecer_indice():
    """Força a indexação na primeira carga para o chat responder rápido."""
    from src.utils.vector_store import get_vector_store

    return get_vector_store()


def desmontar(texto: str) -> tuple[str, list[str], list[str]]:
    """Quebra o formato ``Pergunta/Resposta/Fontes`` do ``format_output``.

    Devolve (corpo da resposta, fontes, avisos de afirmação sem base).
    O caminho MCP (``format_frota``) só tem a linha final de fontes.
    """
    linhas = (texto or "").strip().splitlines()
    if not linhas:
        return "", [], []

    fontes: list[str] = []
    avisos: list[str] = []

    # A linha "Fontes:" é sempre a última do formato montado pelo grafo.
    for indice in range(len(linhas) - 1, -1, -1):
        if linhas[indice].startswith("Fontes:"):
            fontes = [
                fonte.strip()
                for fonte in linhas[indice][len("Fontes:"):].split(",")
                if fonte.strip()
            ]
            linhas.pop(indice)
            break

    corpo: list[str] = []
    for linha in linhas:
        if "Sem base no contexto" in linha:
            aviso = linha.split("Sem base no contexto:", 1)[-1].strip()
            avisos.append(aviso or linha.strip())
            continue
        if not corpo and linha.startswith("Pergunta:"):
            continue
        if not corpo and linha.startswith("Resposta:"):
            linha = linha[len("Resposta:"):].lstrip()
        corpo.append(linha)

    return "\n".join(corpo).strip(), fontes, avisos


def registrar(pergunta: str, saida: dict) -> dict:
    """Guarda a pergunta e o resultado no histórico e devolve o item."""
    corpo, fontes, avisos = desmontar(saida.get("resultado") or "")
    item = {
        "pergunta": pergunta,
        "corpo": corpo or "_O agente não devolveu resultado._",
        "intent": saida.get("intent"),
        "suficiente": saida.get("suficiente"),
        # O estado carrega as fontes mesmo quando o texto não as menciona.
        "fontes": list(dict.fromkeys(saida.get("fontes") or fontes)),
        "avisos": avisos,
    }
    st.session_state.historico.append(item)
    return item


def mostrar_resposta(item: dict) -> None:
    """Desenha uma resposta: bolha, instrumentos, fontes e alertas."""
    if item["corpo"].lower().startswith("não encontrado"):
        st.warning(item["corpo"])
    else:
        st.markdown(item["corpo"])

    st.markdown("---")

    col_intencao, col_contexto, col_fontes = st.columns(3)
    col_intencao.metric("Intenção", item.get("intent") or "—")
    col_contexto.metric("Contexto", _sim_nao(item.get("suficiente")))
    col_fontes.metric("Fontes", len(item["fontes"]))

    if item["fontes"]:
        st.html(linha_fontes(item["fontes"]))

    for aviso in item["avisos"]:
        st.warning(f"Sem base no contexto: {aviso}")


def _sim_nao(valor) -> str:
    if valor is None:
        return "—"
    return "Sim" if valor else "Não"


def sidebar() -> None:
    with st.sidebar:
        marca_lateral()

        if st.button(
            "Limpar conversa",
            width="stretch",
            icon=":material/delete_sweep:",
        ):
            st.session_state.historico = []
            st.rerun()

        painel_lateral(
            modelo=os.getenv("LLM_MODEL", "não definido"),
            embeddings=os.getenv("EMBEDDINGS_MODEL", "não definido"),
        )

        if os.getenv("LANGFUSE_PUBLIC_KEY"):
            st.link_button(
                "Ver traces no Langfuse",
                os.getenv("LANGFUSE_BASE_URL")
                or os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                width="stretch",
                icon=":material/monitoring:",
            )

        rodape_lateral()


def exemplos() -> str | None:
    """Linha de sugestões quando a conversa ainda está vazia."""
    if st.session_state.historico:
        return None

    st.html(rotulo_exemplos())
    escolhido = None
    for coluna, texto in zip(st.columns(len(EXEMPLOS)), EXEMPLOS):
        if coluna.button(texto, key=f"exemplo::{texto}", width="stretch", wrap=True):
            escolhido = texto
    return escolhido


def executar(grafo, pergunta: str) -> None:
    """Roda o grafo e desenha a troca completa na mesma execução."""
    with st.chat_message("user"):
        st.markdown(pergunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando o agente..."):
            try:
                saida = grafo.invoke(
                    {"pergunta": pergunta},
                    config=run_config(
                        trace_name="porto-alfa-streamlit",
                        tags=("porto-alfa", "streamlit"),
                        recursion_limit=25,
                    ),
                )
            except Exception as erro:  # noqa: BLE001 - erro de API vira aviso na tela
                st.error(f"Falha ao consultar o agente: {erro}")
                return
            finally:
                flush()

        mostrar_resposta(registrar(pergunta, saida))


def main() -> None:
    sidebar()
    cabecalho()

    if "historico" not in st.session_state:
        st.session_state.historico = []

    grafo = carregar_grafo()
    try:
        aquecer_indice()
    except Exception as erro:  # noqa: BLE001 - queremos avisar e seguir
        st.warning(f"Não foi possível indexar os documentos agora: {erro}")

    escolhido = exemplos()

    for item in st.session_state.historico:
        with st.chat_message("user"):
            st.markdown(item["pergunta"])
        with st.chat_message("assistant"):
            mostrar_resposta(item)

    pergunta = st.chat_input(
        "Ex.: qual é a reserva mínima de combustível do S3-CORAL?"
    ) or escolhido

    if pergunta:
        executar(grafo, pergunta)


if __name__ == "__main__":
    main()
