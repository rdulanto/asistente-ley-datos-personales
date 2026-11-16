import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from glossary import expandir  # noqa: E402
from ingest import dividir  # noqa: E402
from retrieve import Buscador, tokens  # noqa: E402

FUENTE = {"id": "ley", "norma": "Ley de prueba", "corta": "Ley X", "url": "", "pagina": ""}


def test_dividir_quita_cabeceras_y_reubica_parrafos_desordenados():
    texto = "\n".join([
        "Artículo 1. Objeto",
        "1.1 La ley protege los datos personales.",
        "Sábado 30 de noviembre de 2024 /",
        "El Peruano",
        "2.2 Segundo párrafo que el PDF puso antes de su encabezado.",
        "Artículo 2. Definiciones",
        "2.1 Primer párrafo del artículo dos.",
    ])
    arts = {a["articulo"]: a for a in dividir(texto, FUENTE)}
    assert set(arts) == {1, 2}
    assert "Peruano" not in arts[1]["texto"] and "2024" not in arts[1]["texto"]
    assert "Segundo párrafo" in arts[2]["texto"]
    assert arts[2]["titulo"] == "Definiciones"


def test_tokens_ignora_tildes_y_reduce_a_raices():
    assert tokens("Supresión de datos", stem=False) == ["supresion", "de", "datos"]
    assert "de" not in tokens("Supresión de datos", stem=True)
    assert tokens("sanciones", stem=True) == tokens("sanción", stem=True)


def test_glosario_traduce_lenguaje_de_negocio():
    assert "incidente de seguridad" in expandir("¿Qué hago si nos hackean?")
    assert expandir("pregunta sin términos del glosario") == "pregunta sin términos del glosario"


def test_bm25_encuentra_el_articulo_de_incidentes():
    ids = [a["id"] for a, _ in Buscador(stem=True, glosario=True).buscar(
        "¿En cuántas horas debo avisar a la autoridad si hackean mi base de clientes?", k=5)]
    assert "reglamento-34" in ids
