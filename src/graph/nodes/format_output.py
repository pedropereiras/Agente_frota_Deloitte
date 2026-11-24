from src.graph.state import State


def format_output(state: State) -> dict:
    fontes = state.get("fontes") or [
        f"{d.metadata['doc']}#{d.metadata.get('secao', '-')}"
        for d in state.get("contextos", [])
    ]
    texto = (
        f"Pergunta: {state['pergunta']}\n"
        f"Resposta: {state['resposta']}\n"
        f"Fontes: {', '.join(fontes)}"
    )
    sem_base = state.get("afirmacoes_sem_base") or []
    if sem_base:
        texto += "\n⚠️  Sem base no contexto: " + "; ".join(sem_base)
    return {"resultado": texto}
