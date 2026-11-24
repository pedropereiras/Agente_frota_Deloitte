import json

from src.graph.prompts.analyze_prompt import ANALYZE_PROMPT
from src.graph.state import State
from src.guardrails.recuperacao import envelopar
from src.guardrails.saida import definir_contexto_manual


def prepare(state: State) -> dict:
    # G6: o manual recuperado fica à mão para o `velocidade_efetiva` ancorar
    # o `limite_tempestade_kn` no que foi buscado, não em constante de código.
    definir_contexto_manual(state.get("contexto_regras", ""))
    # G4: as regras recuperadas entram como dado, entre tags, no prompt do analyze.
    regras = envelopar(
        [("manual_operacoes", state.get("contexto_regras", ""))],
        "manual_operacoes",
    )
    mensagens = ANALYZE_PROMPT.format_messages(
        regras=regras,
        frota=json.dumps(state["frota"], ensure_ascii=False),
        pergunta=state["pergunta"],
    )
    return {"messages": mensagens}
