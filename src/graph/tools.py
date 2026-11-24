from langchain_core.tools import tool

from src.guardrails.saida import (
    VELOCIDADE_MAX_KN,
    exigir,
    limite_ancorado,
    validar_velocidade,
)


@tool
def calcular_eta_horas(distancia_nm: float, velocidade_kn: float) -> float:
    """Calcula o ETA em horas: distancia_nm dividida por velocidade_kn."""
    # G6: faixa válida antes de dividir — sem isso, 0 ou negativo vira ETA absurdo.
    exigir(distancia_nm > 0, "distancia_nm deve ser positiva")
    validar_velocidade(velocidade_kn)
    return round(distancia_nm / velocidade_kn, 2)


@tool
def velocidade_efetiva(
    velocidade_kn: float, em_tempestade: bool, limite_tempestade_kn: float
) -> float:
    """Velocidade efetiva. Em tempestade, é no máximo o limite de tempestade do manual."""
    validar_velocidade(velocidade_kn)
    exigir(
        0 < limite_tempestade_kn <= VELOCIDADE_MAX_KN,
        f"limite_tempestade_kn fora de (0, {VELOCIDADE_MAX_KN:g}]",
    )
    # G6: o limite não é constante de código — precisa estar no manual recuperado.
    limite_ancorado(limite_tempestade_kn)
    return min(velocidade_kn, limite_tempestade_kn) if em_tempestade else velocidade_kn


@tool
def reserva_ok(combustivel_t: float, reserva_t: float) -> bool:
    """True se o combustível a bordo cobre a reserva mínima (navio pode zarpar)."""
    exigir(combustivel_t >= 0, "combustivel_t não pode ser negativo")
    exigir(reserva_t >= 0, "reserva_t não pode ser negativa")
    return combustivel_t >= reserva_t


TOOLS = [calcular_eta_horas, velocidade_efetiva, reserva_ok]
