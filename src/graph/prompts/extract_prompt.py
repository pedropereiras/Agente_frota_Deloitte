from langchain_core.prompts import ChatPromptTemplate

from src.guardrails.recuperacao import INSTRUCAO_DADOS

EXTRACT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Extraia os navios do relatório abaixo. Copie os valores exatamente como estão "
            "no texto e não invente nenhum dado. Ignore a seção 'Sobre este documento'.\n\n"
            + INSTRUCAO_DADOS,
        ),
        ("human", "{relatorio}"),
    ]
)
