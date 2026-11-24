from langchain_core.prompts import ChatPromptTemplate

CLASSIFY_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Classifique a pergunta de um operador de porto:\n"
            "- regra: dúvida sobre regras, limites, valores e procedimentos do manual\n"
            "- frota: pergunta sobre a situação atual dos navios (quem chega primeiro, "
            "ETA, quem está impedido de zarpar)\n"
            "- fora_escopo: qualquer outro assunto",
        ),
        ("human", "{pergunta}"),
    ]
)
