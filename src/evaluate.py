"""Evalúa la búsqueda con 30 preguntas de cumplimiento y sus artículos correctos (eval/preguntas.jsonl)."""
from __future__ import annotations

import json
from pathlib import Path

from retrieve import Buscador
from semantic import E5, BuscadorHibrido, BuscadorSemantico

EVAL = Path(__file__).resolve().parents[1] / "eval"


def cargar() -> list[dict]:
    with open(EVAL / "preguntas.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def evaluar(buscador: Buscador, preguntas: list[dict]) -> dict:
    hit1 = hit3 = hit5 = rr = 0.0
    fallos = []
    for q in preguntas:
        ids = [a["id"] for a, _ in buscador.buscar(q["pregunta"], k=10)]
        pos = next((i for i, x in enumerate(ids) if x in q["relevantes"]), None)
        hit1 += pos == 0
        hit3 += pos is not None and pos < 3
        hit5 += pos is not None and pos < 5
        rr += 0 if pos is None else 1 / (pos + 1)
        if pos is None or pos >= 3:
            fallos.append({"pregunta": q["pregunta"], "esperado": q["relevantes"][:3], "top3": ids[:3]})
    n = len(preguntas)
    return {"acierto@1": hit1 / n, "acierto@3": hit3 / n, "acierto@5": hit5 / n, "MRR": rr / n, "n": n, "fallos": fallos}


CONFIGS = {
    "1. BM25 palabras exactas": lambda: Buscador(stem=False, glosario=False),
    "2. BM25 + raíces en español": lambda: Buscador(stem=True, glosario=False),
    "3. BM25 + raíces + glosario de negocio": lambda: Buscador(stem=True, glosario=True),
    "4. Embeddings multilingual-e5-large": lambda: BuscadorSemantico(**E5),
    "5. Híbrido (3 + 4, fusión de rankings)": lambda: BuscadorHibrido(**E5),
}


def cargar_archivo(nombre: str) -> list[dict]:
    with open(EVAL / nombre, encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def main() -> None:
    conjuntos = {"desarrollo": cargar_archivo("preguntas.jsonl"), "prueba": cargar_archivo("preguntas_prueba.jsonl")}
    resultados = {}
    for nombre, crear in CONFIGS.items():
        b = crear()
        resultados[nombre] = {c: evaluar(b, qs) for c, qs in conjuntos.items()}
        for c, r in resultados[nombre].items():
            print(f"{nombre:42s} [{c:10s}] " + ", ".join(f"{k}={v:.2f}" for k, v in r.items() if k not in ("fallos", "n")))
    with open(EVAL / "resultados.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    for c in conjuntos:
        for x in resultados["5. Híbrido (3 + 4, fusión de rankings)"][c]["fallos"]:
            print(f"  FALLO [{c}]:", x)


if __name__ == "__main__":
    main()
