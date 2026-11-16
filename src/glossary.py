"""Glosario de negocio: traduce cómo pregunta un equipo de negocio al vocabulario de la norma.

Es la misma idea de un glosario de gobierno de datos: términos de negocio enlazados a términos técnicos.
Se construyó mirando los fallos del conjunto de desarrollo (eval/preguntas.jsonl) y se mide aparte en un
conjunto de prueba que no se usó para construirlo (eval/preguntas_prueba.jsonl).
"""
from __future__ import annotations

import re
import unicodedata

GLOSARIO: dict[str, str] = {
    # Solo términos que salieron de los fallos del conjunto de desarrollo.
    r"\b(borr\w*|elimin\w*)\b": "supresión cancelación",
    r"\b(llevar\w*|formato|otro banco)\b": "portabilidad",
    r"\bmulta\w*\b": "sanción multa unidades impositivas tributarias UIT",
    r"\bsensibles?\b": "datos sensibles definiciones",
    r"\b(prospect\w*|llamar|ofrec\w*|publicidad|marketing)\b": "publicidad prospección comercial",
    r"\b(no responde|reclam\w*)\b": "tutela reclamación",
    r"\b(reduc\w*|atenu\w*)\b": "atenuantes",
    r"\b(hacke\w*|brecha|ataque)\b": "incidente de seguridad notificación",
    r"\b(nube|proveedor\w*|subcontrat\w*)\b": "encargado del tratamiento tercerizados subcontratación",
    r"\b(algoritmo\w*|automátic\w*)\b": "tratamiento objetivo automatizado",
    r"\b(otro país|extranjero|exterior)\b": "flujo transfronterizo",
    r"\bcliente\w*\b": "titular de datos personales",
    r"\b(antes de recopilar|informar)\b": "derecho de información",
    r"\bgrupo\b": "grupo empresarial",
    r"\b(autoridad|supervisa\w*)\b": "Autoridad Nacional de Protección de Datos Personales funciones",
    r"\b(cuántos días|plazo)\b": "plazos de respuesta",
}


def expandir(pregunta: str) -> str:
    """Agrega a la pregunta los términos de la norma que corresponden a sus palabras de negocio."""
    p = pregunta.lower()
    extra = [termino for patron, termino in GLOSARIO.items() if re.search(patron, p)]
    return pregunta + (" " + " ".join(extra) if extra else "")
