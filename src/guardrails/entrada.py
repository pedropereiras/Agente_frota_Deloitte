"""G1 — entrada: normaliza, limita o tamanho e reconhece tentativa de injeção.

Determinístico: **não** chama LLM e roda antes de `classify`, então uma
pergunta bloqueada nunca chega ao modelo (critério de aceite do exercício).

Falso positivo existe e é aceito: "Posso ignorar as regras de tempestade?"
é legítima e seria bloqueada. Em produção, casos ambíguos viram `alerta` +
revisão humana em vez de bloqueio seco.
"""

from __future__ import annotations

import re
import unicodedata
from typing import NamedTuple

LIMITE_CARACTERES = 500

# Caracteres invisíveis: escondem texto de quem lê o log e do modelo.
INVISIVEIS = (
    "\u00ad\u061c\u115f\u1160\u17b4\u17b5\u180e"
    "\u200b\u200c\u200d\u200e\u200f\u2028\u2029"
    "\u202a\u202b\u202c\u202d\u202e\u2060\u2061"
    "\u2062\u2063\u2064\u2066\u2067\u2068\u2069"
    "\ufeff\ufff9\ufffa\ufffb"
)
_TABELA_INVISIVEIS = dict.fromkeys(map(ord, INVISIVEIS))

# (subtipo, padrão). O alerta emitido é "INJECTION_SUSPECTED:<subtipo>" para
# que todo caso de injeção satisfaça `alerta.startswith("INJECTION_SUSPECTED")`.
PADROES_INJECAO: tuple[tuple[str, str], ...] = (
    ("INSTRUCTION_OVERRIDE", r"\bignore\s+(?:as\s+)?regras\b"),
    (
        "INSTRUCTION_OVERRIDE",
        r"\b(?:ignore|disregard|forget|desconsidere|descarte)\b"
        r"[^.!?\n]{0,60}\b(?:instru[çc][õo]es|regras|diretrizes|prompts?|"
        r"anteriores?|antecessores?|previous|prior|above)\b",
    ),
    ("PROMPT_EXFILTRATION", r"\bsystem\s*prompt\b"),
    (
        "PROMPT_EXFILTRATION",
        r"\b(?:revele|reveja|mostre|exiba|liste|imprima|printe|digite|copie)\b"
        r"[^.!?\n]{0,60}\b(?:prompt|chaves?|senhas?|tokens?|segredos?|"
        r"credenciais|secret|api[\s_-]?key)\b",
    ),
    ("ROLE_ESCAPE", r"</?\s*(?:system|assistant|user|human|developer)\s*>"),
    ("ROLE_ESCAPE", r"\bobede[çc]a\s+s[óo]\s+a\s+mim\b"),
    ("ROLE_ESCAPE", r"\bn[ãa]o\s+mencione\s+esta\s+nota\b"),
    ("ROLE_ESCAPE", r"\bnew\s+instructions?\b"),
)


class Entrada(NamedTuple):
    """Resultado do G1: `bloqueio == ""` significa liberado."""

    bloqueio: str
    pergunta: str
    alertas: list[str]


def normalizar(pergunta: str) -> str:
    """NFKC, sem invisíveis, com espaços colapsados."""
    texto = unicodedata.normalize("NFKC", str(pergunta or ""))
    texto = texto.translate(_TABELA_INVISIVEIS)
    return re.sub(r"\s+", " ", texto).strip()


def padroes_de_injecao(texto: str) -> list[str]:
    """Subtipos de injeção presentes no texto (lista vazia = limpo)."""
    return [
        subtipo
        for subtipo, padrao in PADROES_INJECAO
        if re.search(padrao, texto, re.IGNORECASE)
    ]


def validar(pergunta: str) -> Entrada:
    """Aplica o G1 inteiro e devolve a decisão + a pergunta normalizada."""
    texto = normalizar(pergunta)

    if not texto:
        return Entrada("PERGUNTA_VAZIA", "", ["PERGUNTA_VAZIA"])

    if len(texto) > LIMITE_CARACTERES:
        return Entrada(
            "PERGUNTA_LONGA",
            texto[:LIMITE_CARACTERES],
            [f"PERGUNTA_LONGA:{len(texto)}"],
        )

    subtipos = padroes_de_injecao(texto)
    if subtipos:
        alertas = [f"INJECTION_SUSPECTED:{s}" for s in dict.fromkeys(subtipos)]
        return Entrada("INJECTION_SUSPECTED", texto, alertas)

    return Entrada("", texto, [])
