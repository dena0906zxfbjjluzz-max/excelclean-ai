import base64
from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
FONDO_PATH = RAIZ / "assets" / "fondo.jpg"
CSS_PATH = RAIZ / "assets" / "estilo.css"


def aplicar_estilo() -> None:
    css = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""
    if FONDO_PATH.exists():
        foto = base64.b64encode(FONDO_PATH.read_bytes()).decode("ascii")
        css = css.replace("__FONDO__", foto)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def marca_sidebar() -> None:
    st.sidebar.markdown(
        """
        <div style="padding:0 0 0.7rem 0;margin-bottom:0.35rem;border-bottom:1px solid rgba(43,184,168,0.22)">
          <p style="margin:0;font-size:0.68rem;font-weight:700;letter-spacing:0.12em;text-transform:uppercase;color:#2BB8A8">Validador</p>
          <p style="margin:0.12rem 0 0 0;font-size:0.82rem;font-weight:600;color:#EAF0F6">ExcelClean AI</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cabecera() -> None:
    st.markdown(
        """
        <div class="hero">
          <p class="hero-kicker">Validador · packing y almacén</p>
          <h1>ExcelClean AI</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )
