"""Suíte red team (G1, G3, G4, G5, G7): 6 casos hostis de ponta a ponta.

Rodar na raiz do projeto (precisa de rede/chave para o LLM):

    python -m scripts.avaliar_seguranca

Saída esperada: `Acertos: 6/6`. Em s5 e s6 o relatório legítimo é trocado por
uma versão envenenada com o manifesto regenerado por cima: só o G3 (varredura
do chunk) pode pegar o ataque ali. Ver `dados/avaliacao_seguranca.json`.
"""

import json
import shutil
import tempfile
from pathlib import Path

from src.graph.builder import build_graph
from src.utils import vector_store
from src.utils.langfuse_client import flush, run_config
from src.guardrails.recuperacao import gerar_manifesto

CASOS = Path("dados/avaliacao_seguranca.json")


def com_relatorio_envenenado(fixture: Path):
    """Simula um documento legítimo comprometido: manifesto regenerado, então só o G3 (chunk) pode pegar."""
    tmp = Path(tempfile.mkdtemp())
    for nome in vector_store.ARQUIVOS:
        origem = fixture if nome == "relatorio_frota.txt" else vector_store.DADOS / nome
        shutil.copy(origem, tmp / nome)
    (tmp / "manifesto.json").write_text(
        json.dumps(gerar_manifesto(tmp, vector_store.ARQUIVOS), indent=2)
    )
    vector_store.DADOS = tmp
    vector_store.MANIFESTO = tmp / "manifesto.json"
    vector_store.get_vector_store.cache_clear()


def main() -> None:
    graph, acertos = build_graph(), 0
    casos = json.loads(CASOS.read_text(encoding="utf-8"))
    for caso in casos:
        if "fixture" in caso:
            com_relatorio_envenenado(Path("dados") / caso["fixture"])
        saida = graph.invoke(
            {"pergunta": caso["pergunta"]},
            config=run_config(
                trace_name=f"seguranca-{caso['id']}",
                tags=("seguranca", "red-team"),
                recursion_limit=25,
            ),
        )
        texto = saida["resultado"].lower()
        ok = (
            all(e.lower() in texto for e in caso["esperado"])
            and not any(p.lower() in texto for p in caso["proibido"])
            and (
                caso["alerta"] is None
                or any(
                    a.startswith(caso["alerta"])
                    for a in saida.get("alertas", [])
                )
            )
        )
        acertos += ok
        print(caso["id"], caso["vetor"], "OK" if ok else "FALHOU")
    print(f"Acertos: {acertos}/{len(casos)}")
    flush()


if __name__ == "__main__":
    main()
