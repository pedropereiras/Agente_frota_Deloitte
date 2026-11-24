"""G5, G6 e G7 — validação determinística do que o modelo pede e produz.

Aqui não há LLM: números, ids, limites e a resposta final são conferidos
contra os dados que o grafo recuperou.

* **G5** (`validar_extracao`): todo número extraído precisa existir na seção
  do **próprio** navio; id fora do relatório é rejeitado.
* **G6** (`exigir`, `validar_velocidade`, `limite_ancorado`): argumentos das
  tools com faixa válida e `limite_tempestade_kn` escrito no manual recuperado.
* **G7** (`conferir`, `resposta_calculada`): recalcula ETA e bloqueio em
  Python, varredura de segredos e **substitui** a resposta em divergência.
"""

from __future__ import annotations

import re
from contextvars import ContextVar
from typing import Any, Mapping, Sequence

VELOCIDADE_MAX_KN = 18.0
LIMITE_DIRETA_PADRAO_KN = 12.0


class GuardrailErro(ValueError):
    """Erro de guardrail. Com ``ToolNode(handle_tool_errors=True)`` ele vira
    ToolMessage de erro e volta ao modelo, em vez de derrubar o grafo."""


def exigir(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise GuardrailErro(mensagem)


# --------------------------------------------------------------- G6 (tool)


_CONTEXTO_MANUAL: ContextVar[str] = ContextVar("CONTEXTO_MANUAL", default="")


def definir_contexto_manual(texto: str) -> None:
    """Guarda o manual que o grafo recuperou, para ancorar o limite."""
    _CONTEXTO_MANUAL.set(texto or "")


def contexto_manual() -> str:
    return _CONTEXTO_MANUAL.get()


def _numero_escrito(valor: Any, texto: str) -> bool:
    """Confere se o número aparece literalmente no texto (12 casa com "12 nós")."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return False
    candidatos = {f"{numero:g}", str(numero)}
    if numero.is_integer():
        candidatos.add(str(int(numero)))
    return any(
        re.search(rf"(?<![\d.,]){re.escape(c)}(?![\d.,])", texto)
        for c in candidatos
    )


def validar_velocidade(velocidade_kn: Any) -> float:
    try:
        velocidade = float(velocidade_kn)
    except (TypeError, ValueError):
        raise GuardrailErro(f"velocidade_kn inválido: {velocidade_kn!r}") from None
    exigir(
        0 < velocidade <= VELOCIDADE_MAX_KN,
        f"velocidade_kn fora de (0, {VELOCIDADE_MAX_KN:g}]",
    )
    return velocidade


def limite_ancorado(limite_tempestade_kn: Any) -> None:
    """O limite precisa estar escrito no manual **recuperado**, não no código."""
    texto = contexto_manual()
    if not texto.strip():
        raise GuardrailErro("LIMITE_NAO_ANCORADO: manual recuperado indisponível")
    try:
        limite = float(limite_tempestade_kn)
    except (TypeError, ValueError):
        raise GuardrailErro(
            f"LIMITE_NAO_ANCORADO: valor inválido {limite_tempestade_kn!r}"
        ) from None
    if not _numero_escrito(limite, texto):
        raise GuardrailErro(
            f"LIMITE_NAO_ANCORADO: {limite:g} não está escrito no manual recuperado"
        )


# ------------------------------------------------------------------- G5


CAMPOS_NUMERICOS = ("distancia_nm", "velocidade_kn", "combustivel_t", "reserva_t")


def validar_extracao(
    frota: Sequence[Mapping[str, Any]],
    contextos: Sequence[Any],
) -> list[str]:
    """G5: id e número precisam existir na seção do próprio navio."""
    por_secao = {
        str(chunk.metadata.get("secao")): chunk.page_content for chunk in contextos
    }
    problemas: list[str] = []
    for navio in frota:
        identificador = str(navio.get("id") or "").strip()
        texto = por_secao.get(identificador)
        if texto is None:
            problemas.append(f"NAVIO_FORA_DO_RELATORIO:{identificador or '?'}")
            continue
        destino = str(navio.get("destino") or "").strip()
        if destino and destino.lower() not in texto.lower():
            problemas.append(f"DESTINO_NAO_ENCONTRADO:{identificador}")
        for campo in CAMPOS_NUMERICOS:
            if not _numero_escrito(navio.get(campo), texto):
                problemas.append(f"NUMERO_NAO_ENCONTRADO:{identificador}.{campo}")
                break
    if not problemas:
        return []
    return ["EXTRACAO_INCONSISTENTE:" + ";".join(problemas)]


# ------------------------------------------------------------------- G7


PADROES_SEGREDO: tuple[str, ...] = (
    r"\bpk-lf-[A-Za-z0-9]{8,}",
    r"\bsk-lf-[A-Za-z0-9]{8,}",
    r"\bgsk_[A-Za-z0-9]{12,}",
    r"\bhf_[A-Za-z0-9]{16,}",
    r"\bAKIA[0-9A-Z]{16}\b",
    r"\bBearer\s+[A-Za-z0-9._-]{16,}",
    r"\b(?:api[_-]?key|secret|token|senha|password|chave de acesso)"
    r"\s*[:=]\s*[\"']?[^\s\"']{8,}",
)

FRASES_VENCEDOR = (
    "chega primeiro",
    "primeiro a chegar",
    "chega antes",
    "menor eta",
    "é o primeiro",
    "será o primeiro",
)

PERMISSAO = (
    "pode zarpar",
    "liberado",
    "liberada",
    "elegível",
    "elegivel",
    "pode partir",
    "apta a zarpar",
    "está apto",
)

NEGA = (
    "não",
    "nao",
    "nunca",
    "jamais",
    "impedido",
    "bloqueado",
    "por último",
    "por ultimo",
    "abaixo da reserva",
)


def varrer_segredos(texto: str) -> list[str]:
    """G7: a resposta não pode devolver chave, token ou credencial."""
    if any(re.search(padrao, texto, re.IGNORECASE) for padrao in PADROES_SEGREDO):
        return ["SAIDA_COM_SEGREDO"]
    return []


def limite_rota_direta(texto: str, padrao: float = LIMITE_DIRETA_PADRAO_KN) -> float:
    """Lê da rota direta o limite escrito no manual recuperado."""
    if not texto:
        return padrao
    for padrao_regex in (
        r"rota direta\s*é? de\s*(\d+(?:[.,]\d+)?)",
        r"velocidade segura[^\n]{0,60}?(\d+(?:[.,]\d+)?)",
    ):
        achado = re.search(padrao_regex, texto, re.IGNORECASE)
        if achado:
            return float(achado.group(1).replace(",", "."))
    return padrao


def plano_de_voo(
    frota: Sequence[Mapping[str, Any]], limite_kn: float
) -> list[dict[str, Any]]:
    """Recálculo do G7: ETA e bloqueio feitos em Python, não pelo modelo."""
    planos: list[dict[str, Any]] = []
    for navio in frota:
        try:
            distancia = float(navio["distancia_nm"])
            velocidade = float(navio["velocidade_kn"])
            combustivel = float(navio["combustivel_t"])
            reserva = float(navio["reserva_t"])
        except (KeyError, TypeError, ValueError):
            continue
        efetiva = min(velocidade, limite_kn) if navio.get("em_tempestade") else velocidade
        eta = distancia / efetiva if efetiva > 0 else float("inf")
        planos.append(
            {
                **navio,
                "bloqueado": combustivel < reserva,
                "velocidade_efetiva_kn": efetiva,
                "eta_h": round(eta, 2),
            }
        )
    return planos


def _negado(trecho: str) -> bool:
    return any(marcador in trecho for marcador in NEGA)


def _ids_do(trecho: str) -> list[str]:
    return re.findall(r"\bs\d+-[a-z]+\b", trecho)


# "56.67 h", "56,67 horas", "em 57 h" — só número + unidade de hora.
_ETA_DECLARADA = re.compile(
    r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*(?:horas?|\bh\b)(?![a-z])",
    re.IGNORECASE,
)

# Tolerância do arredondamento: 2% do valor ou meia hora, o que for maior.
_TOLERANCIA_H = 0.5
_TOLERANCIA_REL = 0.02


def etas_declaradas(texto: str) -> list[float]:
    """ETAs em horas que o texto afirma, com vírgula decimal aceita."""
    return [
        float(m.group(1).replace(",", "."))
        for m in _ETA_DECLARADA.finditer(texto)
    ]


def eta_confere(declarado: float, planos: Sequence[Mapping[str, Any]]) -> bool:
    """O número declarado bate com algum ETA recalculado em Python?"""
    for plano in planos:
        eta = plano.get("eta_h")
        if eta is None or eta == float("inf"):
            continue
        if abs(declarado - float(eta)) <= max(
            _TOLERANCIA_H, _TOLERANCIA_REL * abs(float(eta))
        ):
            return True
    return False


def eta_confere_declarado(
    texto: str, planos: Sequence[Mapping[str, Any]]
) -> bool:
    """Todo ETA em horas do texto bate com o recálculo (sem número = True)."""
    declarados = etas_declaradas(texto)
    if not declarados:
        return True
    return all(eta_confere(d, planos) for d in declarados)


def ganhador_declarado(texto: str) -> str | None:
    """Qual navio a resposta afirma que chega primeiro (None = não declara)."""
    baixo = texto.lower()
    for frase in FRASES_VENCEDOR:
        for achado in re.finditer(re.escape(frase), baixo):
            inicio = max(0, achado.start() - 45)
            fim = min(len(baixo), achado.end() + 45)
            trecho = baixo[inicio:fim]
            if _negado(trecho):
                continue
            candidatos = [
                (abs(inicio + m.start() - achado.start()), m.group(0))
                for m in re.finditer(r"\bs\d+-[a-z]+\b", trecho)
            ]
            if candidatos:
                return min(candidatos)[1]
    return None


def afirma_liberado(texto: str, identificador: str) -> bool:
    """A resposta passa pano para um navio que o código diz estar bloqueado."""
    baixo = texto.lower()
    alvo = identificador.lower()
    inicio = baixo.find(alvo)
    while inicio != -1:
        janela = baixo[inicio : inicio + 90]
        if any(p in janela for p in PERMISSAO) and not _negado(janela):
            return True
        inicio = baixo.find(alvo, inicio + 1)
    return False


def resposta_calculada(planos: Sequence[Mapping[str, Any]]) -> str:
    """Substituta em código: o que o Python calculou, sem depender do modelo."""
    elegiveis = [p for p in planos if not p["bloqueado"]]
    bloqueados = [p for p in planos if p["bloqueado"]]
    partes: list[str] = []
    if elegiveis:
        vencedor = min(elegiveis, key=lambda p: p["eta_h"])
        partes.append(
            f"Menor ETA: {vencedor['id']} com {vencedor['eta_h']:g} h "
            f"({float(vencedor['distancia_nm']):g} nm / "
            f"{vencedor['velocidade_efetiva_kn']:g} nós)"
        )
    for navio in sorted(bloqueados, key=lambda p: str(p.get("id"))):
        partes.append(
            f"{navio['id']} está impedido de zarpar: "
            f"{float(navio['combustivel_t']):g} t abaixo da reserva mínima de "
            f"{float(navio['reserva_t']):g} t"
        )
    corpo = ". ".join(partes) if partes else "Nenhum navio elegível identificado."
    return (
        "Resposta recalculada em Python pelo guardrail de saída (G7). " + corpo + "."
    )


def conferir(
    texto: str, planos: Sequence[Mapping[str, Any]]
) -> tuple[list[str], str | None]:
    """G7: devolve (alertas, substituta | None). Nulo quando está tudo certo."""
    if not planos or not texto:
        return [], None

    alertas: list[str] = []

    conhecidos = {str(p.get("id", "")).lower() for p in planos}
    for sid in sorted(set(_ids_do(texto.lower()))):
        if sid not in conhecidos:
            alertas.append(f"NAVIO_DESCONHECIDO:{sid}")

    elegiveis = [p for p in planos if not p["bloqueado"]]
    if elegiveis:
        vencedor = min(elegiveis, key=lambda p: p["eta_h"])
        declarado = ganhador_declarado(texto)
        if declarado and declarado != str(vencedor["id"]).lower():
            alertas.append("ETA_DIVERGENTE")

    # G7: o vencedor até pode estar certo e o número errado — o ETAs declarado
    # precisa bater com algum ETA recalculado em Python.
    if not eta_confere_declarado(texto, planos) and "ETA_DIVERGENTE" not in alertas:
        alertas.append("ETA_DIVERGENTE")

    for navio in planos:
        if navio["bloqueado"] and afirma_liberado(texto, str(navio["id"])):
            alertas.append("BLOQUEADO_COM_ETA")
            break

    # Só a divergência de cálculo troca o texto; o resto é apenas sinalizado.
    if divergente(alertas):
        return alertas, resposta_calculada(planos)
    return alertas, None


def divergente(alertas: Sequence[str]) -> bool:
    """Há erro de cálculo na resposta (ETA errado ou bloqueio ignorado)?"""
    return any(
        a == "ETA_DIVERGENTE" or a == "BLOQUEADO_COM_ETA" for a in alertas
    )
