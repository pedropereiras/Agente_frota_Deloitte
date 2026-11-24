"""G9 — ambiente: segredos fora do repositório, egress restrito, testes sem
rede e teto de tokens.

Sem rede: este arquivo depende do bloqueio automático de `tests/conftest.py`.
"""

import os
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

from src.utils.egress import (
    EgressBloqueado,
    _IPS_AUTORIZADOS,
    _host_de,
    conexao_liberada,
    hosts_permitidos,
    host_permitido,
    instalar_egress_da_app,
    instalar_guarda,
)
from src.utils.llm_adapter import (
    MAX_TOKENS_PADRAO,
    MAX_TOKENS_TETO,
    _max_tokens,
    get_llm,
)

RAIZ = Path(__file__).resolve().parents[1]


class SegredosTests(unittest.TestCase):
    def test_gitignore_guarda_o_env(self):
        linhas = {
            linha.strip()
            for linha in (RAIZ / ".gitignore").read_text(encoding="utf-8").splitlines()
        }
        self.assertIn(".env", linhas)

    def test_ci_tem_varredura_de_segredos_e_testes(self):
        workflows = sorted((RAIZ / ".github" / "workflows").glob("*.y*ml"))
        self.assertTrue(workflows, "CI ausente: sem workflow em .github/workflows")
        texto = "\n".join(w.read_text(encoding="utf-8") for w in workflows).lower()
        self.assertIn("gitleaks", texto)
        self.assertIn("pytest", texto)


class EgressTests(unittest.TestCase):
    def _ambiente(self):
        return patch.dict(
            os.environ,
            {
                "LLM_PROVIDER": "groq",
                "EMBEDDINGS_PROVIDER": "huggingface",
                "LANGFUSE_BASE_URL": "https://cloud.langfuse.com",
            },
        )

    def test_allowlist_e_so_modelo_e_langfuse(self):
        with self._ambiente():
            self.assertTrue(host_permitido("api.groq.com"))
            self.assertTrue(host_permitido("cdn-lfs.huggingface.co"))
            self.assertTrue(host_permitido("cloud.langfuse.com"))
            self.assertFalse(host_permitido("evil.example.com"))
            self.assertFalse(host_permitido("pastebin.com"))
            self.assertFalse(host_permitido("api.groq.com.evil.example.com"))

    def test_provedor_fora_do_catalogo_nao_entra_na_allowlist(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "provedor-inexistente"}):
            hosts = hosts_permitidos()
        self.assertNotIn("provedor-inexistente", hosts)

    def test_conexao_fora_da_allowlist_levanta_erro(self):
        restaurar = instalar_guarda(permitidos={"api.groq.com"})
        try:
            with self.assertRaises(EgressBloqueado) as captura:
                socket.create_connection(("evil.example.com", 443), timeout=1)
            self.assertIn("EGRESS_BLOQUEADO", str(captura.exception))
        finally:
            restaurar()

    def test_conexao_para_host_permitido_passa_pela_guarda(self):
        restaurar = instalar_guarda(permitidos={"api.groq.com"})
        try:
            # Só a checagem: sem abrir socket de verdade para não depender de rede.
            self.assertTrue(host_permitido("api.groq.com"))
            with self.assertRaises(EgressBloqueado):
                socket.create_connection(("pastebin.com", 443), timeout=1)
        finally:
            restaurar()

    def test_suite_integra_roda_sem_rede(self):
        """G9: nenhum teste desta suíte pode falar com a internet."""
        for destino in (("example.com", 443), ("api.groq.com", 443)):
            with self.subTest(destino=destino), self.assertRaises(EgressBloqueado):
                socket.create_connection(destino, timeout=1)


class EnderecoResolvidoTests(unittest.TestCase):
    """G9: valida o **nome** do host; o IP só passa se veio de resolução permitida.

    Reproduz o que `socket.create_connection` e o asyncio fazem — resolvem o
    nome e depois chamam `connect` com o endereço já em IP. Sem esta regra,
    um destino permitido pela allowlist era bloqueado depois do DNS e a
    chamada legítima da aplicação morria.
    """

    def test_connect_com_ip_resolvido_de_host_permitido_e_liberado(self):
        with patch.object(socket.socket, "connect") as conexao_real:
            restaurar = instalar_guarda(permitidos={"api.groq.com"})
            try:
                _IPS_AUTORIZADOS.add("203.0.113.10")  # veio do getaddrinfo
                socket.socket().connect(("203.0.113.10", 443))
                conexao_real.assert_called_once()
            finally:
                restaurar()

    def test_connect_com_ip_sem_resolucao_autorizada_e_bloqueado(self):
        """Fechar o bypass: conectar direto no IP sem passar pelo nome."""
        with patch.object(socket.socket, "connect") as conexao_real:
            restaurar = instalar_guarda(permitidos={"api.groq.com"})
            try:
                with self.assertRaises(EgressBloqueado):
                    socket.socket().connect(("198.51.100.7", 443))
                conexao_real.assert_not_called()
            finally:
                restaurar()

    def test_connect_com_nome_permitido_e_liberado(self):
        with patch.object(socket.socket, "connect") as conexao_real:
            restaurar = instalar_guarda(permitidos={"api.groq.com"})
            try:
                socket.socket().connect(("api.groq.com", 443))
                conexao_real.assert_called_once()
            finally:
                restaurar()

    def test_formato_do_getaddrinfo_e_lido_pelo_ip(self):
        """O `connect` recebe `(family, type, proto, canonname, (ip, port))`."""
        resolvido = (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 443))
        self.assertEqual(_host_de(resolvido), "203.0.113.10")
        self.assertEqual(_host_de(("api.groq.com", 443)), "api.groq.com")

    def test_resolucao_valida_o_nome_e_registra_os_ips(self):
        resposta = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 443))
        ]
        with patch("socket.getaddrinfo", return_value=resposta) as dns:
            restaurar = instalar_guarda(permitidos={"api.groq.com"})
            try:
                socket.getaddrinfo("api.groq.com", 443)
                dns.assert_called_once_with("api.groq.com", 443)
                self.assertIn("203.0.113.10", _IPS_AUTORIZADOS)
            finally:
                restaurar()

    def test_resolucao_de_host_fora_da_allowlist_nem_chama_o_dns(self):
        with patch("socket.getaddrinfo") as dns:
            restaurar = instalar_guarda(permitidos={"api.groq.com"})
            try:
                with self.assertRaises(EgressBloqueado):
                    socket.getaddrinfo("evil.example.com", 443)
                dns.assert_not_called()
            finally:
                restaurar()

    def test_create_connection_de_host_permitido_passa_ponta_a_ponta(self):
        """Caminho real de uma chamada legítima: resolver → conectar pelo IP."""
        resolvido = [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("203.0.113.10", 443))
        ]
        with patch("socket.getaddrinfo", return_value=resolvido) as dns, \
                patch.object(socket.socket, "connect") as conexao_real:
            restaurar = instalar_guarda(permitidos={"api.groq.com"})
            try:
                sock = socket.create_connection(("api.groq.com", 443))
                sock.close()
                dns.assert_called_once_with("api.groq.com", 443, 0, socket.SOCK_STREAM)
                conexao_real.assert_called_once()
                self.assertIn("203.0.113.10", _IPS_AUTORIZADOS)
            finally:
                restaurar()

    def test_gethostbyname_valida_o_nome_e_registra_o_ip(self):
        with patch("socket.gethostbyname", return_value="203.0.113.10") as dns:
            restaurar = instalar_guarda(permitidos={"api.groq.com"})
            try:
                self.assertEqual(socket.gethostbyname("api.groq.com"), "203.0.113.10")
                dns.assert_called_once_with("api.groq.com")
                self.assertIn("203.0.113.10", _IPS_AUTORIZADOS)
                with self.assertRaises(EgressBloqueado):
                    socket.gethostbyname("evil.example.com")
                dns.assert_called_once()  # o proibido nem chega ao resolver
            finally:
                restaurar()

    def test_regra_unica_de_liberacao(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "groq"}):
            _IPS_AUTORIZADOS.add("203.0.113.10")
            try:
                self.assertTrue(conexao_liberada("api.groq.com"))
                self.assertTrue(conexao_liberada("203.0.113.10"))  # resolvido
                self.assertTrue(conexao_liberada(""))  # sem destino
                self.assertFalse(conexao_liberada("198.51.100.7"))  # IP direto
                self.assertFalse(conexao_liberada("evil.example.com"))
            finally:
                _IPS_AUTORIZADOS.discard("203.0.113.10")


class EgressDaAppTests(unittest.TestCase):
    """A porta de entrada da aplicação: só instala com allowlist fechada.

    A restauração fica por conta do teardown de `sem_rede` (`tests/conftest.py`),
    que devolve o estado capturado antes do teste.
    """

    def test_instala_com_provedor_conhecido_e_guarda_o_nome(self):
        ambiente = {
            "LLM_PROVIDER": "groq",
            "EMBEDDINGS_PROVIDER": "huggingface",
            "EGRESS_STRICT": "1",
        }
        with patch.dict(os.environ, ambiente), \
                patch.object(socket.socket, "connect") as conexao:
            self.assertTrue(instalar_egress_da_app())
            socket.socket().connect(("api.groq.com", 443))  # permitido
            conexao.assert_called_once()
            with self.assertRaises(EgressBloqueado):
                socket.socket().connect(("evil.example.com", 443))  # proibido
            self.assertEqual(conexao.call_count, 1)

    def test_escape_de_manutencao_desliga_a_guarda(self):
        with patch.dict(os.environ, {"EGRESS_STRICT": "0"}), \
                patch("src.utils.egress.instalar_guarda") as instalar:
            self.assertFalse(instalar_egress_da_app())
            instalar.assert_not_called()

    def test_provedor_desconhecido_nao_instala(self):
        ambiente = {
            "LLM_PROVIDER": "provedor-x",
            "EMBEDDINGS_PROVIDER": "provedor-y",
            "EGRESS_STRICT": "1",
        }
        with patch.dict(os.environ, ambiente), \
                patch("src.utils.egress.instalar_guarda") as instalar, \
                self.assertLogs("egress", level="WARNING") as logs:
            self.assertFalse(instalar_egress_da_app())
            instalar.assert_not_called()
            self.assertIn("EGRESS_SEM_ALLOWLIST", logs.output[0])


class MaxTokensTests(unittest.TestCase):
    def test_padrao_quando_nao_ha_variavel(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("MAX_TOKENS", None)
            self.assertEqual(_max_tokens(), MAX_TOKENS_PADRAO)

    def test_variavel_baixa_o_teto_e_o_teto_duro_nao_passa(self):
        with patch.dict(os.environ, {"MAX_TOKENS": "512"}):
            self.assertEqual(_max_tokens(), 512)
        with patch.dict(os.environ, {"MAX_TOKENS": str(MAX_TOKENS_TETO * 10)}):
            self.assertEqual(_max_tokens(), MAX_TOKENS_TETO)
        with patch.dict(os.environ, {"MAX_TOKENS": "0"}):
            self.assertEqual(_max_tokens(), MAX_TOKENS_PADRAO)
        with patch.dict(os.environ, {"MAX_TOKENS": "muito"}):
            self.assertEqual(_max_tokens(), MAX_TOKENS_PADRAO)

    def test_get_llm_envia_max_tokens_para_o_provedor(self):
        with patch.dict(
            os.environ,
            {"LLM_MODEL": "modelo-teste", "LLM_PROVIDER": "groq", "MAX_TOKENS": "777"},
        ), patch("src.utils.llm_adapter.init_chat_model") as init:
            get_llm()
        kwargs = init.call_args.kwargs
        self.assertEqual(kwargs["max_tokens"], 777)
        self.assertEqual(kwargs["model"], "modelo-teste")
        self.assertEqual(kwargs["model_provider"], "groq")


class RecursionLimitTests(unittest.TestCase):
    def test_apps_limitam_o_laco_do_grafo(self):
        """G9: `recursion_limit` corta laço `analyze <-> tools` na aplicação."""
        for nome in ("main.py", "mcp_main.py", "streamlit_app.py"):
            with self.subTest(app=nome):
                texto = (RAIZ / "src" / "app" / nome).read_text(encoding="utf-8")
                self.assertIn("recursion_limit", texto)
                self.assertIn("25", texto)


if __name__ == "__main__":
    unittest.main()
