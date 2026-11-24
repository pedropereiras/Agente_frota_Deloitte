"""G9 — egress restrito: só o provedor do modelo e o Langfuse saem da máquina.

O bloqueio é um monkeypatch de `socket.socket.connect`,
`socket.create_connection`, `socket.getaddrinfo` e `socket.gethostbyname`:
qualquer destino fora da allowlist levanta `EgressBloqueado` em vez de abrir
a conexão. `tests/conftest.py` instala a guarda sem host nenhum (testes rodam
offline) e os testes do G9 conferem que a allowlist só contém modelo,
embeddings e Langfuse.

**O que se valida é o NOME do host, nunca o IP.** Depois do `getaddrinfo` o
endereço chega ao `connect` já resolvido (`(AF_INET, ..., ('93.184.216.34',
443))`); validar esse valor bloquearia até um destino permitido. Por isso:

* nome fora da allowlist → bloqueado, inclusive na resolução (`getaddrinfo`);
* nome dentro da allowlist → liberado, e os IPs que ele devolveu são
  registrados em `_IPS_AUTORIZADOS`;
* IP literal → liberado só se for local ou se veio de uma resolução
  autorizada neste processo (fecha o bypass "pular o hostname e conectar
  direto no IP").
"""

from __future__ import annotations

import ipaddress
import logging
import os
import socket
from typing import Callable, Iterable
from urllib.parse import urlparse

# Hosts fixos por provedor; a allowlist é `PROVEDORES[LLM_PROVIDER]` +
# `PROVEDORES[EMBEDDINGS_PROVIDER]` + as URLs explícitas do ambiente.
PROVEDORES: dict[str, tuple[str, ...]] = {
    "openai": ("api.openai.com",),
    "groq": ("api.groq.com",),
    "anthropic": ("api.anthropic.com",),
    "deepseek": ("api.deepseek.com",),
    "mistralai": ("api.mistral.ai",),
    "google-genai": ("generativelanguage.googleapis.com",),
    "google_vertexai": ("aiplatform.googleapis.com",),
    "bedrock": ("amazonaws.com",),
    "together": ("api.together.xyz",),
    "huggingface": ("huggingface.co",),
    "ollama": ("localhost", "127.0.0.1"),
}

# O SDK do Langfuse cai na nuvem dele quando `LANGFUSE_BASE_URL` não está
# definido; os dois hosts da nuvem entram sempre na allowlist.
LANGFUSE_NUVEM = ("cloud.langfuse.com", "api.langfuse.com", "langfuse.com")

# Variáveis que trazem URL própria (proxy, self-hosted, Langfuse).
URLS_AMBIENTE = (
    "LANGFUSE_BASE_URL",
    "LANGFUSE_HOST",
    "OPENAI_BASE_URL",
    "GROQ_API_BASE",
    "ANTHROPIC_API_URL",
    "EMBEDDINGS_BASE_URL",
)

_LOCAIS = ("localhost", "127.0.0.1", "::1")

# IPs devolvidos por uma resolução de host permitido neste processo. É o que
# permite o `connect` que chega com o endereço já resolvido (create_connection,
# asyncio) sem perder a restrição por nome.
_IPS_AUTORIZADOS: set[str] = set()


def _eh_ip(host: str) -> bool:
    """True quando `host` já é endereço literal (IPv4/IPv6), não nome."""
    try:
        ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return False
    return True


def _desembrulhar(funcao, indice: int):
    """Função original por trás de uma guarda nossa (sem aninhar guards).

    Se `funcao` já é uma guarda do G9, devolve o original guardado nela;
    caso contrário devolve a própria função — que pode ser um mock nos testes.
    Lê o `__dict__` direto: `getattr` em mock criaria o atributo sozinho.
    """
    originais = getattr(funcao, "__dict__", {}).get("_egress_originais")
    return originais[indice] if originais else funcao


class EgressBloqueado(RuntimeError):
    """Conexão para host fora da allowlist do G9."""


def _host_de(address) -> str:
    """Extrai o host de qualquer formato de `connect`.

    Aceita `(host, port)`, o par de 5 posições devolvido pelo `getaddrinfo`
    (`(family, type, proto, canonname, (ip, port))`) e o caminho do AF_UNIX.
    """
    if isinstance(address, tuple) and address:
        if len(address) >= 5 and isinstance(address[4], tuple) and address[4]:
            return str(address[4][0])
        return str(address[0])
    texto = str(address)
    return texto.split("%")[0].split(":")[0] if texto else texto


def conexao_liberada(host: str, permitidos: Iterable[str] | None = None) -> bool:
    """Regra única do G9 para um endereço qualquer.

    * **nome** → precisa estar na allowlist (`permitidos=None` usa
      `hosts_permitidos()`);
    * **IP literal** → só se for local ou se veio de resolução de host
      permitido (`_IPS_AUTORIZADOS`);
    * vazio/`None` → não há destino remoto, deixa passar.
    """
    alvo = (host or "").strip().lower().rstrip(".")
    if not alvo:
        return True
    if _eh_ip(alvo):
        return alvo in _LOCAIS or alvo in _IPS_AUTORIZADOS
    if permitidos is None:
        return host_permitido(alvo)
    conjunto = {str(h).lower().rstrip(".") for h in permitidos}
    return (
        alvo in conjunto
        or alvo in _LOCAIS
        or any(alvo.endswith(f".{base}") for base in conjunto)
    )


def _hosts_de_url(url: str) -> list[str]:
    host = urlparse(url if "//" in url else f"//{url}").hostname
    return [host] if host else []


def hosts_permitidos() -> set[str]:
    """Allowlist do egress: modelo, embeddings e Langfuse (nada mais)."""
    hosts: set[str] = set(_LOCAIS) | set(LANGFUSE_NUVEM)
    for variavel in ("LLM_PROVIDER", "EMBEDDINGS_PROVIDER"):
        provedor = os.environ.get(variavel, "").strip().lower()
        hosts.update(PROVEDORES.get(provedor, ()))
    for variavel in URLS_AMBIENTE:
        valor = os.environ.get(variavel, "").strip()
        if valor:
            hosts.update(_hosts_de_url(valor))
    # Só se o rastreamento do LangChain estiver ligado explicitamente.
    if os.environ.get("LANGCHAIN_TRACING_V2", "").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        hosts.update(("api.langsmith.com", "smith.langchain.com"))
    return {h for h in hosts if h}


def hosts_de_modelo() -> set[str]:
    """Hosts do modelo e dos embeddings — sem eles a allowlist não fecha."""
    hosts: set[str] = set()
    for variavel in ("LLM_PROVIDER", "EMBEDDINGS_PROVIDER"):
        provedor = os.environ.get(variavel, "").strip().lower()
        hosts.update(PROVEDORES.get(provedor, ()))
    return hosts


def host_permitido(host: str) -> bool:
    """True para host exato, subdomínio de host permitido ou destino local."""
    alvo = (host or "").strip().lower().strip(".")
    if not alvo:
        return False
    if alvo in _LOCAIS:
        return True
    permitidos = hosts_permitidos()
    if alvo in permitidos:
        return True
    return any(alvo.endswith(f".{base}") for base in permitidos)


def instalar_guarda(
    permitidos: Iterable[str] | None = None,
) -> Callable[[], None]:
    """Bloqueia egress fora da allowlist. Devolve a função que restaura.

    `permitidos=None` usa `hosts_permitidos()`; `permitidos=set()` bloqueia
    qualquer host remoto (só `localhost` passa) — é o que os testes usam.

    A validação é sempre pelo **nome**: `create_connection` e `asyncio`
    resolvem o host antes de conectar, então o `connect` recebe o endereço já
    resolvido e só é liberado se aquele IP veio de resolução autorizada.
    """
    conjunto = None if permitidos is None else {h.lower() for h in permitidos}
    # O que está instalado agora (para devolver igual na restauração) e o que
    # está por trás (para delegar sem aninhar uma guarda dentro da outra).
    atuais = (
        socket.socket.connect,
        socket.create_connection,
        socket.getaddrinfo,
        socket.gethostbyname,
    )
    originais = tuple(
        _desembrulhar(funcao, i) for i, funcao in enumerate(atuais)
    )

    def _liberado(host: str) -> bool:
        return conexao_liberada(host, conjunto)

    def _registrar_ips(nome: str, resposta) -> None:
        """Guarda os IPs que um nome permitido devolveu, para o connect seguinte."""
        if not nome or _eh_ip(nome):
            return
        for item in resposta:
            try:
                ip = str(item[4][0])
            except (IndexError, TypeError):
                continue
            _IPS_AUTORIZADOS.add(ip)

    def getaddrinfo(host, *args, **kwargs):
        # O nome vive aqui: é neste ponto que ele é conferido contra a allowlist.
        nome = "" if host is None else str(host)
        if not _liberado(nome):
            raise EgressBloqueado(f"EGRESS_BLOQUEADO:{nome}")
        resposta = originais[2](host, *args, **kwargs)
        _registrar_ips(nome, resposta)
        return resposta

    def gethostbyname(host):
        nome = str(host)
        if not _liberado(nome):
            raise EgressBloqueado(f"EGRESS_BLOQUEADO:{nome}")
        ip = originais[3](host)
        if not _eh_ip(nome):
            _IPS_AUTORIZADOS.add(str(ip))
        return ip

    def conectar(self, address, *args, **kwargs):
        host = _host_de(address)
        if not _liberado(host):
            raise EgressBloqueado(f"EGRESS_BLOQUEADO:{host}")
        return originais[0](self, address, *args, **kwargs)

    def criar(address, *args, **kwargs):
        host = _host_de(address)
        if not _liberado(host):
            raise EgressBloqueado(f"EGRESS_BLOQUEADO:{host}")
        return originais[1](address, *args, **kwargs)

    socket.socket.connect = conectar
    socket.create_connection = criar
    socket.getaddrinfo = getaddrinfo
    socket.gethostbyname = gethostbyname

    # Marcador para uma reinstalação (rerun do Streamlit) reaproveitar os
    # originais em vez de aninhar uma guarda dentro da outra.
    for instalada in (conectar, criar, getaddrinfo, gethostbyname):
        instalada._egress_originais = originais

    def restaurar() -> None:
        (
            socket.socket.connect,
            socket.create_connection,
            socket.getaddrinfo,
            socket.gethostbyname,
        ) = atuais
        _IPS_AUTORIZADOS.clear()

    return restaurar


def instalar_egress_da_app() -> bool:
    """Instala a guarda no processo da aplicação (G9 em produção).

    Só instala quando a allowlist dá para fechar (provedor conhecido no
    `PROVEDORES`); provedor desconhecido não pode virar bloqueio acidental do
    app. `EGRESS_STRICT=0` desliga a guarda como escape de manutenção.
    """
    if os.environ.get("EGRESS_STRICT", "1").strip().lower() in (
        "0",
        "false",
        "off",
        "no",
    ):
        return False
    if not hosts_de_modelo():
        logging.getLogger("egress").warning(
            "EGRESS_SEM_ALLOWLIST: provedor de modelo desconhecido; "
            "guarda de egress não instalada"
        )
        return False
    instalar_guarda()
    return True

