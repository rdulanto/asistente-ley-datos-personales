"""Descarga la Ley 29733 y su Reglamento (DS 016-2024-JUS) y los divide en artículos.

Salida: data/articulos.jsonl, un artículo por línea con su norma, número, título y texto.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
import unicodedata
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"

FUENTES = [
    {
        "id": "ley",
        "norma": "Ley N.º 29733, Ley de Protección de Datos Personales",
        "corta": "Ley 29733",
        "url": "https://cdn.www.gob.pe/uploads/document/file/2011398/Ley%20N%C2%BA%2029733%20-%20Ley%20de%20protecci%C3%B3n%20de%20datos%20personales.pdf.pdf?v=1683928275",
        "pagina": "https://www.gob.pe/institucion/anpd/normas-legales/2018427-29733-2011",
    },
    {
        "id": "reglamento",
        "norma": "Reglamento de la Ley N.º 29733 (Decreto Supremo N.º 016-2024-JUS)",
        "corta": "Reglamento DS 016-2024-JUS",
        "url": "https://cdn.www.gob.pe/uploads/document/file/7756037/6554453-reglamento-de-la-ley-n-29733.pdf?v=1743779969",
        "pagina": "https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus",
    },
]

ART = re.compile(r"^\s*Art[ií]culo\s+(\d+)[°º]?\s*\.?\s*[-–.]?\s*(.*)$")
# Títulos que el PDF parte en fragmentos justificados; verificados contra la extracción con -layout.
TITULOS_CORREGIDOS = {("reglamento", 116): "Resolución del procedimiento sancionador"}
# Cabeceras y pies de página del Diario Oficial: "NORMAS LEGALES", "Sábado 30 de noviembre de 2024 /",
# "El Peruano" y números de página sueltos.
RUIDO = re.compile(
    r"NORMAS LEGALES|El Peruano\s*/|^\s*\d{1,3}\s*$|^\s*El Peruano\s*$"
    r"|^\s*(Lunes|Martes|Miércoles|Jueves|Viernes|Sábado|Domingo)\s+\d{1,2}\s+de\s+\w+\s+de\s+\d{4}\s*/?\s*$"
)
PARRAFO = re.compile(r"^(\d+)\.(\d+)\.?\s")  # "18.1 El flujo..." pertenece al artículo 18

def _descargar(url: str, destino: Path, intentos: int = 4) -> None:
    """Descarga con reintentos: el CDN de gob.pe corta conexiones de vez en cuando."""
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                destino.write_bytes(r.read())
            return
        except OSError:
            if i == intentos - 1:
                raise
            time.sleep(2 ** i * 3)


def _texto_pdf(fuente: dict) -> str:
    pdf = DATA / "raw" / f"{fuente['id']}.pdf"
    if not pdf.exists():
        pdf.parent.mkdir(parents=True, exist_ok=True)
        _descargar(fuente["url"], pdf)
    # pdftotext (poppler) respeta mejor el orden de lectura en columnas que pypdf.
    return subprocess.run(["pdftotext", str(pdf), "-"], capture_output=True, text=True, check=True).stdout


def _limpiar(t: str) -> str:
    t = unicodedata.normalize("NFKC", t)  # ligaduras del PDF ("ﬁ" -> "fi")
    t = re.sub(r"-\n(\w)", r"\1", t)                 # palabras cortadas por guion
    t = re.sub(r"\n(?=[a-záéíóúñ,;])", " ", t)       # saltos dentro de una oración
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def dividir(texto: str, fuente: dict) -> list[dict]:
    """Divide en artículos.

    El Diario Oficial publica a dos columnas y la extracción a veces desordena bloques. Por eso cada
    párrafo numerado ("18.1 ...") se asigna al artículo de su número, no al último encabezado leído.
    """
    if fuente["id"] == "reglamento":
        # El PDF empieza con el decreto que aprueba el reglamento (sus propios artículos 1-4): se descarta.
        m = re.search(r"REGLAMENTO DE LA LEY N[°º.]*\s*29733", texto[2000:])
        if m:
            texto = texto[2000 + m.start():]
    lineas = [l.rstrip() for l in texto.splitlines()]
    lineas = [l for l in lineas if not RUIDO.search(l)]

    titulos: dict[int, str] = {}
    cuerpos: dict[int, list[str]] = {}
    pendientes: dict[int, list[str]] = {}
    actual = None
    i = 0
    while i < len(lineas):
        l = lineas[i]
        m = ART.match(l)
        if m and int(m.group(1)) not in titulos:
            n = int(m.group(1))
            titulo = [m.group(2).strip()]
            if not titulo[0] and i + 1 < len(lineas):  # "Artículo 116." con el título en la línea siguiente
                i += 1
                titulo = [lineas[i].strip()]
            # El título puede ocupar 1-2 líneas más en una columna angosta.
            while (i + 1 < len(lineas) and len(titulo) < 3 and lineas[i + 1].strip()
                   and not PARRAFO.match(lineas[i + 1]) and not ART.match(lineas[i + 1])
                   and (lineas[i + 1].strip()[0].islower()
                        or (len(lineas[i + 1].strip()) < 40 and len(titulo[-1]) >= 25))):
                i += 1
                titulo.append(lineas[i].strip())
            titulos[n] = " ".join(titulo).rstrip(".")
            cuerpos.setdefault(n, [])
            actual = n
        else:
            p = PARRAFO.match(l)
            if p and int(p.group(1)) in titulos:
                actual = int(p.group(1))
            elif p and actual is not None and (int(p.group(1)) > actual + 1
                                               or (int(p.group(1)) == actual + 1 and p.group(2) != "1")):
                # Párrafo de un artículo cuyo encabezado aparece más adelante (columnas desordenadas).
                actual = int(p.group(1))
                pendientes.setdefault(actual, [])
            elif p and actual is not None and int(p.group(1)) == actual + 1 and p.group(2) == "1":
                # Encabezado ilegible en el PDF, pero el párrafo "N.1" confirma que empieza el artículo N.
                actual = int(p.group(1))
                titulos[actual] = ""
                cuerpos[actual] = []
            if actual is not None:
                if actual in titulos:
                    cuerpos[actual].append(l)
                else:
                    pendientes.setdefault(actual, []).append(l)
        i += 1

    for n, ls in pendientes.items():
        if n in cuerpos:
            cuerpos[n] = ls + cuerpos[n]
    for (fid, n), t in TITULOS_CORREGIDOS.items():
        if fid == fuente["id"] and n in titulos:
            titulos[n] = t

    arts = []
    for n in sorted(titulos):
        cuerpo = _limpiar("\n".join(cuerpos[n]))
        if not cuerpo:
            continue  # artículo cuyo texto no pudo recuperarse del PDF; se reporta abajo
        arts.append({
            "id": f"{fuente['id']}-{n}",
            "norma": fuente["norma"],
            "corta": fuente["corta"],
            "articulo": n,
            "titulo": _limpiar(titulos[n]) or "(título no legible en el PDF)",
            "texto": cuerpo[:12000],
            "fuente": fuente["pagina"],
        })
    faltan = sorted(set(range(1, max(titulos) + 1)) - {a["articulo"] for a in arts})
    if faltan:
        print(f"  {fuente['corta']}: sin texto recuperable en artículos {faltan}")
    return arts


def main() -> None:
    DATA.mkdir(exist_ok=True)
    todos = []
    for f in FUENTES:
        arts = dividir(_texto_pdf(f), f)
        print(f"{f['corta']}: {len(arts)} artículos")
        todos += arts
    with open(DATA / "articulos.jsonl", "w", encoding="utf-8") as out:
        for a in todos:
            out.write(json.dumps(a, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
