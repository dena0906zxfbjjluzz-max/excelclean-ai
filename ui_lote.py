import pandas as pd
import streamlit as st

from limpieza import columnas_compatibles, es_columna_id


def borrar_editores() -> None:
    for k in list(st.session_state.keys()):
        if not str(k).startswith("editor_"):
            continue
        try:
            st.session_state.pop(k, None)
        except KeyError:
            pass


def _refrescar(df: pd.DataFrame, guardar) -> None:
    guardar(df.reset_index(drop=True))
    st.session_state.editor_ver = st.session_state.get("editor_ver", 0) + 1
    borrar_editores()
    st.rerun()


def config_columnas(df: pd.DataFrame) -> dict:
    cfg = {}
    for col in df.columns:
        if es_columna_id(col):
            cfg[col] = st.column_config.TextColumn(str(col), width="medium")
    return cfg


def editor_excel(df: pd.DataFrame, clave: str) -> pd.DataFrame:
    vista = columnas_compatibles(df).copy()
    n = max(int(vista.shape[0]), 1)
    editado = st.data_editor(
        vista,
        num_rows="fixed",
        use_container_width=True,
        height=int(min(520, 42 + n * 35)),
        key=clave,
        hide_index=True,
        column_config=config_columnas(vista),
    )
    return editado.reset_index(drop=True)


def herramientas_columnas(df: pd.DataFrame, prefijo: str, guardar) -> pd.DataFrame:
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        nueva = st.text_input(
            "Nueva columna",
            placeholder="Ej: OBSERVACION",
            key=f"{prefijo}_nueva_col",
        )
    with c2:
        st.write("")
        st.write("")
        if st.button("Agregar", key=f"{prefijo}_add_col") and nueva.strip():
            nombre = nueva.strip()
            if nombre not in df.columns:
                extra = df.copy()
                extra[nombre] = ""
                _refrescar(extra, guardar)
    with c3:
        quitar = st.text_input(
            "Quitar columna",
            placeholder="Escribe el nombre exacto",
            key=f"{prefijo}_del_col",
        )
        if quitar.strip() and st.button("Quitar", key=f"{prefijo}_del_btn"):
            destino = None
            pedido = quitar.strip().lower()
            for col in df.columns:
                if str(col).strip().lower() == pedido:
                    destino = col
                    break
            if destino is not None:
                _refrescar(df.drop(columns=[destino]), guardar)
    return df


def editar_tabla(df: pd.DataFrame, prefijo: str, guardar) -> pd.DataFrame:
    df = herramientas_columnas(df, prefijo, guardar)
    editado = editor_excel(df, f"editor_{prefijo}")
    guardar(editado)
    return editado
