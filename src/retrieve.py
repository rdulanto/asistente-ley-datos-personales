"""Búsqueda de artículos relevantes con BM25 (léxica, sin costo y explicable)."""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import snowballstemmer
from rank_bm25 import BM25Okapi

from glossary import expandir

DATA = Path(__file__).resolve().parents[1] / "data"
_stem = snowballstemmer.stemmer("spanish")

STOP = set("""a al algo algun alguna algunas alguno algunos ante antes como con contra cual cuales cuando cuanto
cuantos cuantas de del desde donde dos el ella ellas ellos en entre era es esa esas ese eso esos esta estas este esto
estos fue ha han hasta hay la las le les lo los mas me mi mis mucho muy no nos o otra otro para pero poco por porque
puede pueden puedo que quien se segun ser si sin sobre su sus tambien tan tanto te tener tengo tiene toda todo todos
tu un una uno unos y ya yo debo debe deben hacer hago cuales cual""".split())


def _sin_tildes(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def tokens(texto: str, stem: bool = True) -> list[str]:
    palabras = re.findall(r"[a-zñ0-9]+", _sin_tildes(texto.lower()))
    if not stem:
        return palabras
    return [_stem.stemWord(p) for p in palabras if p not in STOP and len(p) > 1]


@lru_cache(maxsize=1)
def articulos() -> list[dict]:
    with open(DATA / "articulos.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


class Buscador:
    """BM25 sobre título + texto de cada artículo.

    stem=True usa raíces en español y quita palabras vacías; glosario=True traduce la pregunta
    al vocabulario de la norma antes de buscar (ver glossary.py).
    """

    def __init__(self, stem: bool = False, peso_titulo: int = 1, glosario: bool = True):
        self.stem = stem
        self.glosario = glosario
        self.docs = articulos()
        corpus = [tokens((a["titulo"] + " ") * peso_titulo + a["texto"], stem) for a in self.docs]
        self.bm25 = BM25Okapi(corpus)

    def buscar(self, pregunta: str, k: int = 5) -> list[tuple[dict, float]]:
        consulta = expandir(pregunta) if self.glosario else pregunta
        puntajes = self.bm25.get_scores(tokens(consulta, self.stem))
        orden = sorted(range(len(self.docs)), key=lambda i: puntajes[i], reverse=True)[:k]
        return [(self.docs[i], float(puntajes[i])) for i in orden]
