import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


_ENV_SERVIDOR = {
    **os.environ,
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
}


def _parametros_stdio():
    from mcp import StdioServerParameters

    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
        cwd=str(RAIZ),
        env=_ENV_SERVIDOR,
    )


@asynccontextmanager
async def sessao_mcp():
    """Abre (e mantém aberta) uma sessão MCP com o servidor 'porto-alfa'."""
    transporte = os.getenv("MCP_TRANSPORT", "stdio").lower()

    if transporte == "http":
        from mcp.client.streamable_http import streamablehttp_client

        url = os.getenv("MCP_URL", "http://127.0.0.1:8765/mcp")
        async with streamablehttp_client(url) as (read, write, _):
            session = _nova_sessao(read, write)
            async with session:
                await session.initialize()
                yield session
    else:
        from mcp.client.stdio import stdio_client

        async with stdio_client(_parametros_stdio()) as (read, write):
            session = _nova_sessao(read, write)
            async with session:
                await session.initialize()
                yield session


def _nova_sessao(read, write):
    from mcp import ClientSession

    return ClientSession(read, write)


async def ferramentas_mcp(session) -> list:
    """Converte as tools MCP da sessão em tools do LangChain."""
    from langchain_mcp_adapters.tools import load_mcp_tools

    return await load_mcp_tools(session, server_name="porto")
