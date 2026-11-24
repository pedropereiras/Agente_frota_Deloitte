from src.utils.vector_store import DADOS, carregar_chunks

chunks = carregar_chunks(DADOS / "manual_operacoes.txt")

print(f"Quantidade de chunks: {len(chunks)}\n")

for chunk in chunks:
    print(chunk.metadata)
    print(chunk.page_content[:120].replace("\n", " "), "...\n")
