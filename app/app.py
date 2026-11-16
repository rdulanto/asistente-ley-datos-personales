"""Asistente de normativa: Ley 29733 de Protección de Datos Personales y su Reglamento."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
import answer  # noqa: E402
from semantic import BuscadorHibrido  # noqa: E402

ACCENT, INK, MUTED, SAND = "#0F5E6E", "#1F2933", "#5B6770", "#E9E4D8"

T = {
    "es": {
        "title": "¿Qué dice la ley peruana de datos personales sobre mi caso?",
        "sub": "Busca en los 174 artículos de la Ley 29733 y su Reglamento (DS 016-2024-JUS) y muestra los artículos que responden tu pregunta.",
        "tab1": "Preguntar", "tab2": "Cómo se evaluó",
        "ask": "Escribe tu pregunta", "ph": "Ej.: ¿en cuántas horas debo avisar a la autoridad si hackean mi base de clientes?",
        "examples": "Ejemplos",
        "found": "Artículos más relevantes",
        "ai": "Respuesta generada con IA (cita los artículos)",
        "noai": "La respuesta redactada con IA se activa al configurar una API key. Los artículos de abajo son la fuente verificable.",
        "disc": "Herramienta educativa. No es asesoría legal.",
        "h_eval": "Resultados de la búsqueda",
        "eval_d": "45 preguntas de cumplimiento escritas en lenguaje de negocio, con el artículo correcto marcado a mano. 30 se usaron para ajustar el sistema (desarrollo) y 15 solo para medir (prueba).",
        "find": "**Hallazgo:** el sistema híbrido acierta el artículo correcto en primer lugar en 60% de las preguntas nuevas, frente a 27% de la búsqueda por palabras exactas. El glosario de negocio ayuda mucho en desarrollo, pero generaliza menos que los embeddings: la brecha entre desarrollo y prueba es la señal de sobreajuste.",
        "metric": "Artículo correcto en primer lugar (prueba)",
    },
    "en": {
        "title": "What does Peru's data protection law say about my case?",
        "sub": "Searches the 174 articles of Law 29733 and its Regulation (DS 016-2024-JUS) and shows the articles that answer your question. Content is in Spanish.",
        "tab1": "Ask", "tab2": "How it was evaluated",
        "ask": "Type your question (Spanish works best)", "ph": "E.g.: ¿en cuántas horas debo avisar a la autoridad si hackean mi base de clientes?",
        "examples": "Examples",
        "found": "Most relevant articles",
        "ai": "AI-generated answer (cites the articles)",
        "noai": "The AI-written answer turns on when an API key is configured. The articles below are the verifiable source.",
        "disc": "Educational tool. Not legal advice.",
        "h_eval": "Search results",
        "eval_d": "45 compliance questions written in business language, with the correct article labeled by hand. 30 were used to tune the system (development) and 15 only to measure it (test).",
        "find": "**Finding:** the hybrid system ranks the correct article first for 60% of new questions, vs. 27% for exact-word search. The business glossary helps a lot in development but generalizes less than embeddings: the dev-test gap is the overfitting signal.",
        "metric": "Correct article ranked first (test)",
    },
}

EJEMPLOS = [
    "¿En cuántas horas debo avisar a la autoridad si hackean mi base de clientes?",
    "¿Puedo guardar los datos de mis clientes en un servidor en otro país?",
    "¿Cuándo es obligatorio nombrar un oficial de datos personales?",
    "¿Cuál es la multa máxima por una infracción muy grave?",
]

st.set_page_config(page_title="Asistente Ley 29733", page_icon="⚖️", layout="wide")
st.markdown("<style>.block-container{max-width:1000px;padding-top:2rem} h1{font-size:2rem!important;letter-spacing:-.02em}</style>",
            unsafe_allow_html=True)
lang = st.radio("Idioma / Language", ["es", "en"], horizontal=True, label_visibility="collapsed",
                format_func=lambda x: "Español" if x == "es" else "English")
t = T[lang]


@st.cache_resource
def buscador():
    return BuscadorHibrido()


st.title(t["title"])
st.caption(t["sub"])
tab1, tab2 = st.tabs([t["tab1"], t["tab2"]])

with tab1:
    if "q" not in st.session_state:
        st.session_state.q = EJEMPLOS[0]
    cols = st.columns(len(EJEMPLOS))
    for c, ej in zip(cols, EJEMPLOS):
        if c.button(ej[:42] + "…", width="stretch"):
            st.session_state.q = ej
    q = st.text_input(t["ask"], key="q", placeholder=t["ph"])
    if q:
        resultados = buscador().buscar(q, k=5)
        if answer.disponible():
            with st.spinner("…"):
                r = answer.responder(q, [a for a, _ in resultados])
            st.subheader(t["ai"])
            st.write(r["texto"] if r["estado"] == "ok" else r["estado"])
        else:
            st.info(t["noai"])
        st.subheader(t["found"])
        for i, (a, _) in enumerate(resultados):
            with st.expander(f"{a['corta']} · Art. {a['articulo']} · {a['titulo']}", expanded=i == 0):
                st.write(a["texto"])
                st.caption(f"[{a['norma']}]({a['fuente']})")
    st.caption(t["disc"])

with tab2:
    st.subheader(t["h_eval"])
    st.caption(t["eval_d"])
    st.markdown(t["find"])
    res = json.loads((RAIZ / "eval" / "resultados.json").read_text(encoding="utf-8"))
    filas = []
    for nombre, por_conj in res.items():
        for conj, m in por_conj.items():
            filas.append({"Sistema": nombre, "Conjunto": conj, **{k: round(v, 2) for k, v in m.items() if k not in ("fallos", "n")}})
    df = pd.DataFrame(filas)
    prueba = df[df["Conjunto"] == "prueba"]
    fig = go.Figure(go.Bar(y=prueba["Sistema"], x=prueba["acierto@1"], orientation="h",
                           marker_color=[ACCENT if s.startswith("5") else "#9AA5AE" for s in prueba["Sistema"]],
                           text=[f"{v:.0%}" for v in prueba["acierto@1"]], textposition="outside"))
    fig.update_layout(height=300, margin=dict(l=10, r=40, t=10, b=10), plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="Inter, sans-serif", color=INK), xaxis=dict(range=[0, 1], tickformat=".0%", gridcolor=SAND, title=t["metric"]),
                      yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig, width="stretch")
    st.dataframe(df, hide_index=True, width="stretch",
                 column_config={c: st.column_config.NumberColumn(format="%.2f") for c in ["acierto@1", "acierto@3", "acierto@5", "MRR"]})
