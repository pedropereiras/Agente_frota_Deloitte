"""Nós de guardrail do grafo e auditoria (G8).

Quatro nós novos: `guard_input` (G1), `guard_extracao` (G5),
`guard_output` (G7) e `blocked` (destino comum de qualquer bloqueio).
Os demais guardrails (G2, G3, G4, G6) moram dentro de nós já existentes.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

from src.graph.state import State
from src.guardrails.entrada import validar
from src.guardrails.saida import (
    conferir,
    limite_rota_direta,
    plano_de_voo,
    validar_extracao,
    varrer_segredos,
)

log = logging.getLogger("guardrails")


# --------------------------------------------------------------- roteamento


def route_after_guard(state: State) -> str:
    """G1 e G5: `bloqueio` presente => vai para `blocked`, sem tocar no LLM."""
    return "bloqueado" if state.get("bloqueio") else "ok"


def route_after_output(state: State) -> str:
    """G7 roda para os dois caminhos; a formatação final depende da intenção."""
    return "frota" if state.get("intent") == "frota" else "regra"


# -------------------------------------------------------------------- nós


def guard_input(state: State) -> dict:
    """G1 — normaliza e decide antes de qualquer chamada ao modelo."""
    entrada = validar(state.get("pergunta", ""))
    saida: dict[str, Any] = {"alertas": list(entrada.alertas)}
    if entrada.bloqueio:
        saida["bloqueio"] = entrada.bloqueio
    else:
        saida["pergunta"] = entrada.pergunta
    registrar(saida, state.get("pergunta", ""), no="guard_input")
    return saida


def blocked(state: State) -> dict:
    codigo = state.get("bloqueio") or "BLOQUEADO"
    return {
        "resultado": (
            f"Resposta bloqueada pelo guardrail ({codigo}). "
            "Nenhuma chamada ao modelo foi feita."
        )
    }


def guard_extracao(state: State) -> dict:
    """G5 — o que o LLM leu do relatório precisa existir no relatório."""
    alertas = validar_extracao(
        state.get("frota") or [], state.get("contextos") or []
    )
    saida: dict[str, Any] = {"alertas": alertas}
    if alertas:
        saida["bloqueio"] = "EXTRACAO_INCONSISTENTE"
    registrar(saida, state.get("pergunta", ""), no="guard_extracao")
    return saida


def _texto(conteudo: Any) -> str:
    if isinstance(conteudo, list):
        return " ".join(
            bloco.get("text", "") if isinstance(bloco, dict) else str(bloco)
            for bloco in conteudo
        )
    return str(conteudo or "")


def _resposta_atual(state: State) -> str:
    """No caminho `regra` a resposta vem de `generate`; no `frota`, do LLM."""
    resposta = (state.get("resposta") or "").strip()
    if resposta:
        return resposta
    for mensagem in reversed(state.get("messages") or []):
        if getattr(mensagem, "type", "") == "ai":
            conteudo = _texto(mensagem.content).strip()
            if conteudo:
                return conteudo
    return ""


def guard_output(state: State) -> dict:
    """G7 — recalcula em Python e troca a resposta em divergência; G7-também
    varre segredos em qualquer caminho."""
    resposta = _resposta_atual(state)
    alertas: list[str] = []

    if state.get("frota"):
        planos = plano_de_voo(
            state["frota"], limite_rota_direta(state.get("contexto_regras", ""))
        )
        novos, substituta = conferir(resposta, planos)
        alertas.extend(novos)
        if substituta:
            resposta = substituta

    if varrer_segredos(resposta):
        alertas.append("SAIDA_COM_SEGREDO")
        resposta = (
            "Resposta retida pelo guardrail de saída: o texto continha material "
            "sensível (SAIDA_COM_SEGREDO)."
        )

    saida: dict[str, Any] = {"resposta": resposta, "alertas": alertas}
    registrar(saida, state.get("pergunta", ""), no="guard_output")
    return saida


# ------------------------------------------------------------------- G8


class _FormatoAuditoria(logging.Formatter):
    """Só nó, código e hash: nunca a pergunta, o prompt ou a chave."""

    def format(self, record: logging.LogRecord) -> str:
        codigo = getattr(record, "codigo", "-")
        no = getattr(record, "no", "-")
        pergunta = getattr(record, "pergunta_sha256", "-")
        return (
            f"{record.levelname} guardrail no={no} codigo={codigo} "
            f"pergunta_sha256={pergunta}"
        )


def _garantir_handler() -> None:
    if log.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(_FormatoAuditoria())
    log.addHandler(handler)
    log.setLevel(logging.WARNING)


def registrar(saida: dict, pergunta: str, no: str = "-") -> None:
    """G8 — loga só nó, código do alerta e hash truncado da pergunta."""
    _garantir_handler()
    resumo = hashlib.sha256(pergunta.encode("utf-8")).hexdigest()[:12]
    for alerta in saida.get("alertas", []) or []:
        log.warning(
            "guardrail",
            extra={"codigo": alerta, "no": no, "pergunta_sha256": resumo},
        )
