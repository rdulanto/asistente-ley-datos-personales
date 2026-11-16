"""Búsqueda semántica con un modelo de embeddings abierto (se ejecuta local, sin API key)."""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

import numpy as np

from retrieve import Buscador, articulos

# Modelo elegido tras comparar con paraphrase-multilingual-mpnet-base-v2 (ver README).
E5 = dict(modelo="intfloat/multilingual-e5-large", prefijo_pregunta="query: ", prefijo_doc="passage: ")
CACHE = Path(__file__).resolve().parents[1] / "data" / "embeddings"


@lru_cache(maxsize=2)
def _modelo(nombre: str):
    from fastembed import TextEmbedding
    return TextEmbedding(nombre, cache_dir=str(CACHE / "modelos"), threads=2)


class BuscadorSemantico:
    def __init__(self, modelo: str = E5["modelo"],
                 prefijo_pregunta: str = E5["prefijo_pregunta"], prefijo_doc: str = E5["prefijo_doc"]):
        self.docs = articulos()
        self.m = _modelo(modelo)
        self.pq = prefijo_pregunta
        textos = [f"{prefijo_doc}{a['titulo']}. {a['texto'][:2000]}" for a in self.docs]
        # La huella de los textos invalida la caché si se vuelve a ejecutar la ingesta.
        huella = hashlib.sha256("\n".join(textos).encode()).hexdigest()[:10]
        archivo = CACHE / f"{modelo.replace('/', '__')}-{huella}.npy"
        if archivo.exists():
            self.E = np.load(archivo)
        else:
            self.E = np.array(list(self.m.embed(textos, batch_size=4)), dtype=np.float32)
            self.E /= np.linalg.norm(self.E, axis=1, keepdims=True)
            archivo.parent.mkdir(parents=True, exist_ok=True)
            np.save(archivo, self.E)

    def puntajes(self, pregunta: str) -> np.ndarray:
        q = np.array(next(iter(self.m.embed([self.pq + pregunta]))), dtype=np.float32)
        return self.E @ (q / np.linalg.norm(q))

    def buscar(self, pregunta: str, k: int = 5):
        s = self.puntajes(pregunta)
        orden = np.argsort(-s)[:k]
        return [(self.docs[i], float(s[i])) for i in orden]


class BuscadorHibrido:
    """Combina BM25 (+ raíces + glosario) y embeddings con Reciprocal Rank Fusion."""

    def __init__(self, k_rrf: int = 60, **kw):
        self.lex = Buscador(stem=True, glosario=True)
        self.sem = BuscadorSemantico(**kw)
        self.docs = self.lex.docs
        self.k = k_rrf

    def buscar(self, pregunta: str, k: int = 5):
        n = len(self.docs)
        r_lex = [a["id"] for a, _ in self.lex.buscar(pregunta, k=n)]
        r_sem = [a["id"] for a, _ in self.sem.buscar(pregunta, k=n)]
        score: dict[str, float] = {}
        for ranking in (r_lex, r_sem):
            for pos, i in enumerate(ranking):
                score[i] = score.get(i, 0) + 1 / (self.k + pos + 1)
        por_id = {a["id"]: a for a in self.docs}
        top = sorted(score, key=score.get, reverse=True)[:k]
        return [(por_id[i], score[i]) for i in top]
