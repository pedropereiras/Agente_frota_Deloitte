from langchain_core.prompts import ChatPromptTemplate

GROUNDING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Você é um verificador de afirmações. Analise a RESPOSTA usando SOMENTE o "
            "CONTEXTO fornecido. Divida a resposta em afirmações verificáveis e diga, para "
            "cada uma, se ela é totalmente suportada pelo contexto (suportada=true) ou não "
            "(suportada=false). Não julgue se o fato é verdadeiro no mundo real; julgue "
            "apenas se ele está escrito no contexto.",
        ),
        (
            "human",
            "Contexto recuperado:\n{contexto}\n\nResposta a verificar:\n{resposta}",
        ),
    ]
)
