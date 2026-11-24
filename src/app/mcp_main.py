"""Agente híbrido: RAG local (regras) + ferramentas MCP (frota e cálculo).

Rodar na raiz do projeto:

    python -m src.app.mcp_main

Por padrão o cliente MCP sobe o servidor automaticamente (stdio) e mantém a
sessão aberta durante toda a execução. Para usar um servidor externo, rode
`python -m mcp_server.server --http` em outro terminal e defina
MCP_TRANSPORT=http no .env.
"""

import asyncio
import sys

from src.graph.builder_hibrido import build_graph_hibrido
from src.utils.egress import instalar_egress_da_app
from src.utils.langfuse_client import flush, run_config
from src.utils.mcp_client import ferramentas_mcp, sessao_mcp


async def main() -> None:
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure:
        reconfigure(errors="replace")
    instalar_egress_da_app()  # G9: só modelo e Langfuse saem da máquina
    async with sessao_mcp() as session:
        tools = await ferramentas_mcp(session)
        print(f"Conectado ao servidor MCP 'porto-alfa'.")
        print(f"Tools MCP: {', '.join(t.name for t in tools)}\n")

        graph = build_graph_hibrido(tools)
        pergunta = input("Pergunta: ").strip()
        try:
            saida = await graph.ainvoke(
                {"pergunta": pergunta},
                config=run_config(
                    trace_name="porto-alfa-hibrido",
                    tags=("porto-alfa", "hibrido"),
                    recursion_limit=25,
                ),
            )
            print(saida["resultado"])
        finally:
            flush()


if __name__ == "__main__":
    asyncio.run(main())
