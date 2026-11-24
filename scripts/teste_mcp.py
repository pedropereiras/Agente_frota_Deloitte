"""Smoke test do servidor MCP: lista as tools e chama duas delas.

Rodar na raiz:  python -m scripts.teste_mcp
"""

import asyncio
import time

from src.utils.mcp_client import ferramentas_mcp, sessao_mcp


def como_texto(resultado) -> str:
    """O adaptador MCP devolve blocos de conteúdo; normaliza para texto."""
    if isinstance(resultado, str):
        return resultado
    partes = []
    for bloco in resultado:
        if isinstance(bloco, dict):
            partes.append(bloco.get("text", str(bloco)))
        else:
            partes.append(getattr(bloco, "text", str(bloco)))
    return "\n".join(partes)


async def main() -> None:
    async with sessao_mcp() as session:
        inicio = time.perf_counter()
        tools = await ferramentas_mcp(session)
        print(f"Tools ({len(tools)}): {', '.join(t.name for t in tools)}")
        print(f"Conexão + listagem: {time.perf_counter() - inicio:.1f}s\n")

        manual = next(t for t in tools if t.name == "consultar_manual")
        inicio = time.perf_counter()
        resultado = await manual.ainvoke({"pergunta": "limite de velocidade em tempestade"})
        print(f"consultar_manual (1a): {time.perf_counter() - inicio:.2f}s")
        print(como_texto(resultado)[:300] + "\n")

        inicio = time.perf_counter()
        await manual.ainvoke({"pergunta": "reserva mínima de combustível"})
        print(f"consultar_manual (2a): {time.perf_counter() - inicio:.2f}s\n")

        eta = next(t for t in tools if t.name == "calcular_eta_horas")
        valor = await eta.ainvoke({"distancia_nm": 680, "velocidade_kn": 12})
        print(f"calcular_eta_horas(680, 12) = {valor}")


if __name__ == "__main__":
    asyncio.run(main())
