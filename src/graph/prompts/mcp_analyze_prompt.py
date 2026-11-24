from langchain_core.prompts import ChatPromptTemplate

MCP_ANALYZE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você é um despachante de porto com ferramentas MCP do servidor 'porto-alfa':\n"
            "- consultar_frota(pergunta): busca dados atuais dos navios no relatório\n"
            "- consultar_manual(pergunta): busca regras no manual de operações\n"
            "- calcular_eta_horas, velocidade_efetiva e reserva_ok: cálculos\n\n"
            "Use as ferramentas para QUALQUER consulta ou cálculo. Consulte a frota E as "
            "regras antes de responder; nunca use conhecimento prévio nem calcule de "
            "cabeça. Passe a limite_tempestade_kn exatamente como está no manual. "
            "No fim, responda à pergunta do operador, liste o ETA dos navios elegíveis "
            "e os navios bloqueados com o motivo.",
        ),
        ("human", "Pergunta: {pergunta}"),
    ]
)
