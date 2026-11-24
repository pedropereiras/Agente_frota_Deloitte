"""G5, G6 e G7 — validação determinística da extração, das tools e da saída.

Sem rede e sem LLM: só Python.
"""

import unittest
from contextvars import copy_context

from langchain_core.documents import Document

from src.guardrails.saida import (
    GuardrailErro,
    VELOCIDADE_MAX_KN,
    afirma_liberado,
    conferir,
    definir_contexto_manual,
    divergente,
    exigir,
    ganhador_declarado,
    limite_ancorado,
    limite_rota_direta,
    plano_de_voo,
    resposta_calculada,
    validar_extracao,
    validar_velocidade,
    varrer_segredos,
)


def _navio(**campos) -> dict:
    base = {
        "id": "S1-FAROL",
        "destino": "Porto Norte",
        "distancia_nm": 700,
        "velocidade_kn": 14,
        "combustivel_t": 30,
        "reserva_t": 33,
        "em_tempestade": False,
    }
    base.update(campos)
    return base


def _secao(texto: str, secao: str = "S1-FAROL", doc: str = "relatorio_frota"):
    return Document(page_content=texto, metadata={"doc": doc, "secao": secao})


class ExtracaoTests(unittest.TestCase):
    def test_extraicao_confere_com_o_relatorio(self):
        relatorio = _secao(
            "Navio: S1-FAROL. Destino: Porto Norte. Distância: 700 nm. "
            "Velocidade: 14 nós. Combustível: 30 t. Reserva: 33 t."
        )
        self.assertEqual(validar_extracao([_navio()], [relatorio]), [])

    def test_navio_fora_do_relatorio_e_rejeitado(self):
        relatorio = _secao("Navio: S2-MARE. Destino: Porto Leste.", secao="S2-MARE")
        alertas = validar_extracao([_navio()], [relatorio])
        self.assertEqual(len(alertas), 1)
        self.assertTrue(alertas[0].startswith("EXTRACAO_INCONSISTENTE:"))
        self.assertIn("NAVIO_FORA_DO_RELATORIO:S1-FAROL", alertas[0])

    def test_numero_que_nao_esta_na_secao_e_rejeitado(self):
        relatorio = _secao(
            "Navio: S1-FAROL. Destino: Porto Norte. Combustível: 30 t. Reserva: 33 t."
        )
        alertas = validar_extracao([_navio(distancia_nm=9999)], [relatorio])
        self.assertIn(
            "NUMERO_NAO_ENCONTRADO:S1-FAROL.distancia_nm", alertas[0]
        )

    def test_destino_inventado_e_rejeitado(self):
        relatorio = _secao("Navio: S1-FAROL. Destino: Porto Sul. Combustível: 30 t.")
        alertas = validar_extracao([_navio(destino="Marte")], [relatorio])
        self.assertIn("DESTINO_NAO_ENCONTRADO:S1-FAROL", alertas[0])


class FerramentasTests(unittest.TestCase):
    def test_exigir_levanta_guardrail_erro(self):
        with self.assertRaises(GuardrailErro):
            exigir(False, "inválido")

    def test_velocidade_zero_ou_negativa_e_rejeitada(self):
        for valor in (0, -1, "-3"):
            with self.subTest(valor=valor), self.assertRaises(GuardrailErro):
                validar_velocidade(valor)

    def test_velocidade_acima_do_teto_e_rejeitada(self):
        with self.assertRaises(GuardrailErro):
            validar_velocidade(VELOCIDADE_MAX_KN + 0.1)

    def test_velocidade_invalida_e_rejeitada(self):
        with self.assertRaises(GuardrailErro):
            validar_velocidade("rápido")

    def test_limite_ancorado_no_manual_recuperado(self):
        definir_contexto_manual(
            "Velocidade segura em tempestade na rota direta: 12 nós."
        )
        limite_ancorado(12)  # não levanta

    def test_limite_fora_do_manual_e_rejeitado(self):
        definir_contexto_manual(
            "Velocidade segura em tempestade na rota direta: 12 nós."
        )
        with self.assertRaises(GuardrailErro) as captura:
            limite_ancorado(17)
        self.assertIn("LIMITE_NAO_ANCORADO", str(captura.exception))

    def test_sem_manual_recuperado_nada_e_ancorado(self):
        definir_contexto_manual("")
        with self.assertRaises(GuardrailErro) as captura:
            limite_ancorado(12)
        self.assertIn("LIMITE_NAO_ANCORADO", str(captura.exception))

    def test_limite_nao_numerico_e_rejeitado(self):
        definir_contexto_manual("limite: 12 nós")
        with self.assertRaises(GuardrailErro):
            limite_ancorado("doze")

    def test_ferramentas_do_grafo_rejeitam_valores_ruins(self):
        from src.graph.tools import calcular_eta_horas, reserva_ok, velocidade_efetiva

        definir_contexto_manual("")  # sem manual recuperado: nada é ancorado
        with self.assertRaises(GuardrailErro):
            calcular_eta_horas.func(100, 0)
        with self.assertRaises(GuardrailErro):
            calcular_eta_horas.func(-100, 12)
        with self.assertRaises(GuardrailErro):
            velocidade_efetiva.func(14, True, 12)  # limite não ancorado: sem manual
        with self.assertRaises(GuardrailErro):
            reserva_ok.func(-1, 10)

    def test_limite_ancorado_funciona_no_contexto_da_chamada(self):
        """ContextVar: o manual definido em `prepare` vale na tool, não global."""
        from src.graph.tools import velocidade_efetiva

        ctx = copy_context()
        ctx.run(definir_contexto_manual, "tempestade: limite de 12 nós")
        self.assertEqual(ctx.run(velocidade_efetiva.func, 14, True, 12), 12)
        with self.assertRaises(GuardrailErro):
            ctx.run(velocidade_efetiva.func, 14, True, 16)


class SaidaTests(unittest.TestCase):
    def test_varredura_de_segredos(self):
        self.assertEqual(varrer_segredos("A resposta é 12 nós."), [])
        self.assertEqual(
            varrer_segredos("chave: pk-lf-abcdefghijklmnop"), ["SAIDA_COM_SEGREDO"]
        )

    def test_limite_da_rota_direta_vem_do_manual(self):
        self.assertEqual(
            limite_rota_direta("Velocidade segura em tempestade: 12 nós"), 12.0
        )
        self.assertEqual(limite_rota_direta(""), 12.0)

    def test_plano_de_voo_calcula_eta_e_bloqueio(self):
        planos = plano_de_voo([_navio(em_tempestade=True)], limite_kn=12)
        self.assertEqual(planos[0]["velocidade_efetiva_kn"], 12)
        self.assertEqual(planos[0]["eta_h"], 58.33)
        self.assertTrue(planos[0]["bloqueado"])  # 30 t < 33 t

    def test_plano_ignora_navio_sem_campos_numericos(self):
        self.assertEqual(plano_de_voo([{"id": "X"}], limite_kn=12), [])

    def test_resposta_calculada_descreve_os_planos(self):
        texto = resposta_calculada(plano_de_voo([_navio()], limite_kn=12))
        self.assertIn("S1-FAROL está impedido de zarpar", texto)
        self.assertIn("Resposta recalculada em Python", texto)


class ConferenciaTests(unittest.TestCase):
    def setUp(self):
        # S1-FAROL bloqueado (30 < 33); S3-CORAL elegível com 680/12 = 56.67 h.
        self.planos = plano_de_voo(
            [
                _navio(),
                _navio(
                    id="S3-CORAL",
                    destino="Porto Sul",
                    distancia_nm=680,
                    velocidade_kn=12,
                    combustivel_t=115,
                    reserva_t=51,
                ),
            ],
            limite_kn=12,
        )

    def test_resposta_correta_nao_gera_alerta(self):
        texto = "S3-CORAL chega primeiro com 56.67 h. S1-FAROL está impedido de zarpar."
        alertas, substituta = conferir(texto, self.planos)
        self.assertEqual(alertas, [])
        self.assertIsNone(substituta)

    def test_eta_divergente_e_corrigido_por_codigo(self):
        # O vencedor real é S3-CORAL (56.67 h); a resposta declara S1-FAROL.
        texto = "S1-FAROL chega primeiro com 30 h."
        alertas, substituta = conferir(texto, self.planos)
        self.assertIn("ETA_DIVERGENTE", alertas)
        self.assertIsNotNone(substituta)
        self.assertIn("Resposta recalculada em Python", substituta)
        self.assertIn("S3-CORAL", substituta)

    def test_eta_numerico_errado_com_o_vencedor_certo(self):
        # O vencedor está certo, mas o número está errado: precisa alertar
        # e substituir — antes, este caso passava sem alerta nem correção.
        texto = "S3-CORAL chega primeiro com 30 h."
        alertas, substituta = conferir(texto, self.planos)
        self.assertIn("ETA_DIVERGENTE", alertas)
        self.assertIsNotNone(substituta)
        self.assertIn("Resposta recalculada em Python", substituta)
        self.assertIn("S3-CORAL", substituta)

    def test_eta_numerico_correto_com_virgula_decimal_passa(self):
        texto = "S3-CORAL chega primeiro com 56,67 horas."
        alertas, substituta = conferir(texto, self.planos)
        self.assertEqual(alertas, [])
        self.assertIsNone(substituta)

    def test_eta_de_qualquer_navio_e_conferido(self):
        # Sem frase de vencedor, o número declarado ainda precisa bater.
        texto = "O S1-FAROL levaria 99 h, mas está impedido de zarpar."
        alertas, substituta = conferir(texto, self.planos)
        self.assertIn("ETA_DIVERGENTE", alertas)
        self.assertIsNotNone(substituta)

    def test_texto_sem_hora_nao_vira_alerta(self):
        texto = "S3-CORAL chega primeiro; S1-FAROL está impedido de zarpar."
        alertas, substituta = conferir(texto, self.planos)
        self.assertEqual(alertas, [])
        self.assertIsNone(substituta)

    def test_bloqueado_com_eta_e_corrigido(self):
        texto = "S1-FAROL pode zarpar; S3-CORAL chega primeiro."
        alertas, substituta = conferir(texto, self.planos)
        self.assertIn("BLOQUEADO_COM_ETA", alertas)
        self.assertIsNotNone(substituta)
        self.assertIn("S1-FAROL está impedido de zarpar", substituta)

    def test_navio_desconhecido_so_sinaliza(self):
        texto = "O navio S9-TESTE chegou ontem. S3-CORAL chega primeiro."
        alertas, substituta = conferir(texto, self.planos)
        self.assertIn("NAVIO_DESCONHECIDO:s9-teste", alertas)
        self.assertFalse(divergente(alertas))
        self.assertIsNone(substituta)  # só sinaliza, não substitui

    def test_sem_planos_nao_faz_nada(self):
        self.assertEqual(conferir("qualquer", []), ([], None))
        self.assertEqual(conferir("", self.planos), ([], None))

    def test_ganhador_declarado_ignora_negacao(self):
        self.assertEqual(ganhador_declarado("S1-FAROL não chega primeiro."), None)
        self.assertEqual(ganhador_declarado("S3-CORAL chega primeiro."), "s3-coral")
        self.assertIsNone(ganhador_declarado("pergunta sem resposta"))

    def test_afirma_liberado_detecta_passada_de_pano(self):
        self.assertTrue(afirma_liberado("S1-FAROL pode zarpar amanhã.", "S1-FAROL"))
        self.assertFalse(
            afirma_liberado("S1-FAROL não pode zarpar; está bloqueado.", "S1-FAROL")
        )


class ContextoManualTests(unittest.TestCase):
    def test_contexto_manual_guarda_e_devolve(self):
        definir_contexto_manual("regra: 12 nós")
        from src.guardrails.saida import contexto_manual

        self.assertEqual(contexto_manual(), "regra: 12 nós")


if __name__ == "__main__":
    unittest.main()
