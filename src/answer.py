"""Genera una respuesta en lenguaje natural con Claude, citando los artículos recuperados.

Opcional: solo se usa si hay credenciales de Anthropic (ANTHROPIC_API_KEY). Sin ellas, la app muestra
los artículos encontrados, que ya son la respuesta verificable.
"""
from __future__ import annotations

import os

SISTEMA = (
    "Eres un asistente de cumplimiento en protección de datos personales en el Perú. "
    "Responde en español, en 3 a 6 oraciones, usando solo los artículos entregados como documentos. "
    "Cita cada afirmación. Si los documentos no bastan para responder, dilo y sugiere consultar a un abogado. "
    "No es asesoría legal."
)


def disponible() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def responder(pregunta: str, articulos: list[dict]) -> dict:
    """Devuelve {"texto": str, "citas": [(cita, articulo)], "estado": str}."""
    import anthropic

    client = anthropic.Anthropic()
    documentos = [
        {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": a["texto"]},
            "title": f"{a['corta']}, artículo {a['articulo']}: {a['titulo']}",
            "citations": {"enabled": True},
        }
        for a in articulos
    ]
    try:
        r = client.beta.messages.create(
            model="claude-opus-5-5",
            max_tokens=2000,
            system=SISTEMA,
            output_config={"effort": "low"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            messages=[{"role": "user", "content": [*documentos, {"type": "text", "text": pregunta}]}],
        )
    except anthropic.RateLimitError:
        return {"texto": "", "citas": [], "estado": "Límite de uso alcanzado; intenta en un minuto."}
    except anthropic.APIStatusError as e:
        return {"texto": "", "citas": [], "estado": f"Error del servicio ({e.status_code})."}
    except anthropic.APIConnectionError:
        return {"texto": "", "citas": [], "estado": "Sin conexión con el servicio."}

    if r.stop_reason == "refusal":
        return {"texto": "", "citas": [], "estado": "El modelo no respondió esta consulta."}
    texto, citas = [], []
    for b in r.content:
        if b.type == "text":
            texto.append(b.text)
            for c in getattr(b, "citations", None) or []:
                citas.append((c.cited_text, c.document_title))
    return {"texto": "".join(texto), "citas": citas, "estado": "ok"}
