from pathlib import Path

import streamlit as st

RAIZ = Path(__file__).resolve().parent
CSS_PATH = RAIZ / "assets" / "estilo.css"


def aplicar_estilo() -> None:
    css = CSS_PATH.read_text(encoding="utf-8") if CSS_PATH.exists() else ""
    css = css.replace(
        "__FONDO__",
        "https://raw.githubusercontent.com/dena0906zxfbjjluzz-max/excelclean-ai/master/assets/fondo.png",
    )
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def marca_sidebar() -> None:
    st.sidebar.markdown(
        """
        <div class="sb-brand">
          <p class="sb-kicker">ExcelClean AI</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cabecera() -> None:
    st.markdown(
        """
        <div class="hero">
          <h1>ExcelClean AI</h1>
          <p>Sube, limpia y descarga el Excel.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
