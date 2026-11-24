from langchain_core.prompts import ChatPromptTemplate

from src.guardrails.recuperacao import INSTRUCAO_DADOS

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você responde perguntas sobre o manual de operações do porto. "
            "Use SOMENTE o contexto fornecido. Se a resposta não estiver no contexto, "
            "responda exatamente: Não encontrado no manual de operações.\n\n"
            + INSTRUCAO_DADOS,
        ),
        ("human", "Contexto:\n{contexto}\n\nPergunta: {pergunta}"),
    ]
)
