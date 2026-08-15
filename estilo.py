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
        <div style="padding:0 0 0.85rem 0;margin-bottom:0.5rem;border-bottom:1px solid rgba(28,36,31,0.14)">
          <p style="margin:0;font-size:0.68rem;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#2F6F5E">Herramienta</p>
          <p style="margin:0.2rem 0 0 0;font-size:1.05rem;font-weight:700;color:#152018">ExcelClean AI</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cabecera() -> None:
    st.markdown(
        """
        <div class="hero">
          <p class="hero-kicker">#ExcelClean</p>
          <h1>ExcelClean<br>AI</h1>
          <p>Sube un Excel, aplica filtros y descarga la tabla lista para enviar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
