"""Guardrails do exercício 2 da semana 3 (G1 a G9).

Camadas:
  entrada.py     G1  — normaliza e reconhece injeção antes do modelo
  recuperacao.py G3  G4 — só entra no contexto o que está no manifesto e
                          sem padrão de injeção; o texto vai envelopado
  saida.py       G5  G6 G7 — extração, argumentos das tools e resposta
                          final conferidos em Python
  nos.py         nós do grafo (`guard_*`, `blocked`) e a auditoria (G8)

Regra mestra: o que muda a decisão é validado em código.
"""
