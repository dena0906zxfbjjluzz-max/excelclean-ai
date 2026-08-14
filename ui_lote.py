import html

import pandas as pd
import streamlit as st

from limpieza import es_columna_id, filtrar_revision


def borrar_editores() -> None:
    for k in list(st.session_state.keys()):
        if str(k).startswith("editor_"):
            del st.session_state[k]


def config_columnas(df: pd.DataFrame) -> dict:
    cfg = {}
    for col in df.columns:
        if es_columna_id(col):
            cfg[col] = st.column_config.TextColumn(str(col), width="medium")
    return cfg


def editor_excel(df: pd.DataFrame, clave: str, altura: int = 520, filas="dynamic") -> pd.DataFrame:
    return st.data_editor(
        df,
        num_rows=filas,
        use_container_width=True,
        height=altura,
        key=clave,
        hide_index=True,
        column_config=config_columnas(df),
    )


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
                df = df.copy()
                df[nombre] = ""
                guardar(df)
                st.session_state.editor_ver = st.session_state.get("editor_ver", 0) + 1
                borrar_editores()
                st.rerun()
    with c3:
        if len(df.columns):
            borrar = st.selectbox(
                "Quitar columna",
                ["(ninguna)"] + list(map(str, df.columns)),
                key=f"{prefijo}_del_col",
            )
            if borrar != "(ninguna)" and st.button("Quitar", key=f"{prefijo}_del_btn"):
                df = df.drop(columns=[borrar])
                guardar(df)
                st.session_state.editor_ver = st.session_state.get("editor_ver", 0) + 1
                borrar_editores()
                st.rerun()
    return df


def cuadro_filtro_validador(df: pd.DataFrame, clave: str) -> pd.DataFrame:
    st.markdown(
        '<p class="vx-filter-title">Revisión de lote</p>'
        '<p class="vx-filter-heading">Buscar y filtrar (Validador)</p>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        busqueda = st.text_input(
            "Búsqueda global (lote / producto / almacén)",
            key=f"{clave}_busq",
        )
    with c2:
        columna = st.selectbox(
            "Filtrar por columna",
            ["(todas)"] + list(map(str, df.columns)),
            key=f"{clave}_col",
        )
    with c3:
        if columna != "(todas)" and columna in df.columns:
            unicos = (
                df[columna]
                .dropna()
                .astype(str)
                .replace({"": pd.NA})
                .dropna()
                .unique()
                .tolist()
            )
            unicos = sorted(unicos)[:400]
            valor = st.selectbox("Valor", ["TODOS"] + unicos, key=f"{clave}_val")
        else:
            valor = "TODOS"
            st.selectbox("Valor", ["TODOS"], key=f"{clave}_val_off", disabled=True)
    vista = filtrar_revision(df, busqueda, columna, valor)
    st.caption(f"Mostrando **{len(vista):,}** de **{len(df):,}** filas")
    return vista


def editar_en_cuadro(df: pd.DataFrame, hoja: str, prefijo: str, guardar) -> pd.DataFrame:
    hoja_txt = html.escape(str(hoja))
    with st.container(border=True):
        st.markdown(
            f'<p class="sb-card-title">Excel · almacén / packing</p>'
            f'<p class="sb-card-heading">{hoja_txt}</p>',
            unsafe_allow_html=True,
        )
        df = herramientas_columnas(df, prefijo, guardar)
        vista = cuadro_filtro_validador(df, f"filtro_{prefijo}")
        filas = "fixed" if len(vista) != len(df) else "dynamic"
        editado_vista = editor_excel(vista, f"editor_{prefijo}", filas=filas)
        if len(vista) == len(df):
            guardar(editado_vista)
            return editado_vista
        base = df.copy()
        comunes = editado_vista.index.intersection(base.index)
        for col in editado_vista.columns:
            if col in base.columns:
                base.loc[comunes, col] = editado_vista.loc[comunes, col]
        guardar(base)
        return base
