import base64
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
CSS_PATH = RAIZ / "assets" / "estilo.css"
FONDO_PATH = RAIZ / "assets" / "fondo.jpg"


def aplicar_estilo() -> None:
    css = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""
    if FONDO_PATH.exists():
        foto = base64.b64encode(FONDO_PATH.read_bytes()).decode("ascii")
        css = css.replace("__FONDO__", foto)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def marca_sidebar() -> None:
    st.sidebar.markdown(
        """
        <div style="padding:0 0 0.85rem 0;margin-bottom:0.5rem;border-bottom:1px solid #1e2a3d">
          <p style="margin:0;font-size:0.68rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#2bb8a8">Herramienta</p>
          <p style="margin:0.2rem 0 0 0;font-size:1rem;font-weight:700;color:#e8eef6">ExcelClean AI</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cabecera() -> None:
    st.markdown(
        """
        <div class="hero">
          <p class="hero-kicker">Limpieza de datos</p>
          <h1>ExcelClean AI</h1>
          <p>Sube un Excel, aplica filtros y descarga la tabla lista para enviar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
