import json

from src.graph.builder import build_graph
from src.utils.langfuse_client import flush, run_config
from src.utils.vector_store import DADOS


def normalizar(texto: str) -> str:
    """Minúsculas e sem espaços, para '15 %', '15%' e '15\u202f%' valerem igual."""
    return "".join(texto.lower().split())


def main() -> None:
    graph = build_graph()
    casos = json.loads((DADOS / "avaliacao.json").read_text(encoding="utf-8"))
    acertos = 0
    for caso in casos:
        saida = graph.invoke(
            {"pergunta": caso["pergunta"]},
            config=run_config(
                run_name=f"avaliacao-{caso['id']}",
                tags=("avaliacao", "semana-3"),
                recursion_limit=25,
            ),
        )
        texto = normalizar(saida["resultado"])
        ok = all(normalizar(esperado) in texto for esperado in caso["esperado"])
        acertos += ok
        print(caso["id"], "OK" if ok else "FALHOU")
    print(f"Acertos: {acertos}/{len(casos)}")
    flush()


if __name__ == "__main__":
    main()
