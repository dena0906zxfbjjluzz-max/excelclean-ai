import pandas as pd
import streamlit as st

from formulas import fila_totales
from limpieza import columnas_compatibles, es_columna_id


def borrar_editores() -> None:
    for k in list(st.session_state.keys()):
        if not str(k).startswith("editor_"):
            continue
        try:
            st.session_state.pop(k, None)
        except KeyError:
            pass


def _guardar_y_refrescar(df: pd.DataFrame, guardar) -> None:
    guardar(df.reset_index(drop=True))
    st.session_state.editor_ver = st.session_state.get("editor_ver", 0) + 1
    borrar_editores()
    st.rerun()


COL_SEL = "Sel"


def quitar_marca(df: pd.DataFrame) -> pd.DataFrame:
    if COL_SEL in df.columns:
        return df.drop(columns=[COL_SEL])
    return df


def config_columnas(df: pd.DataFrame) -> dict:
    cfg = {
        COL_SEL: st.column_config.CheckboxColumn(
            "Sel",
            help="Marca la fila y pulsa Eliminar filas marcadas",
            default=False,
            width="small",
        )
    }
    for col in df.columns:
        if col == COL_SEL:
            continue
        if es_columna_id(col):
            cfg[col] = st.column_config.TextColumn(str(col), width="medium")
    return cfg


def altura_tabla(df: pd.DataFrame) -> int:
    n = max(int(df.shape[0]), 1)
    return int(min(560, 42 + n * 35))


def editor_excel(df: pd.DataFrame, clave: str) -> tuple[pd.DataFrame, pd.Series]:
    vista = quitar_marca(columnas_compatibles(df)).copy()
    vista.insert(0, COL_SEL, False)
    vista.index = range(1, len(vista) + 1)
    editado = st.data_editor(
        vista,
        num_rows="fixed",
        use_container_width=True,
        height=altura_tabla(vista),
        key=clave,
        hide_index=False,
        column_config=config_columnas(vista),
    )
    marcas = (
        editado[COL_SEL].fillna(False).astype(bool)
        if COL_SEL in editado.columns
        else pd.Series(False, index=editado.index)
    )
    limpio = quitar_marca(editado).reset_index(drop=True)
    marcas = marcas.reset_index(drop=True)
    return limpio, marcas


def insertar_fila(df: pd.DataFrame, fila_1: int, abajo: bool) -> pd.DataFrame:
    if df.empty or not len(df.columns):
        return df
    pos = max(1, min(int(fila_1), len(df)))
    idx = pos if abajo else pos - 1
    idx = max(0, min(idx, len(df)))
    vacia = pd.DataFrame([[""] * len(df.columns)], columns=df.columns)
    return pd.concat([df.iloc[:idx], vacia, df.iloc[idx:]], ignore_index=True)


def barra_excel(df: pd.DataFrame, prefijo: str, guardar) -> pd.DataFrame:
    n = max(len(df), 1)
    cols = list(map(str, df.columns)) if len(df.columns) else ["(sin columnas)"]
    clave_fila = f"{prefijo}_fila"
    if clave_fila not in st.session_state:
        st.session_state[clave_fila] = n
    elif int(st.session_state[clave_fila]) > n:
        st.session_state[clave_fila] = n

    st.markdown('<div class="excel-bar">', unsafe_allow_html=True)
    r1, r2, r3, r4, r5, r6 = st.columns([1.1, 1, 1, 1, 1.2, 1.2])
    with r1:
        fila = st.number_input(
            "Fila",
            min_value=1,
            max_value=n,
            step=1,
            key=clave_fila,
        )
    with r2:
        st.write("")
        st.write("")
        if st.button("Fila arriba", key=f"{prefijo}_up") and len(df.columns):
            _guardar_y_refrescar(insertar_fila(df, int(fila), abajo=False), guardar)
    with r3:
        st.write("")
        st.write("")
        if st.button("Fila abajo", key=f"{prefijo}_down") and len(df.columns):
            _guardar_y_refrescar(insertar_fila(df, int(fila), abajo=True), guardar)
    with r4:
        st.write("")
        st.write("")
        if st.button("Borrar fila", key=f"{prefijo}_del_row") and len(df):
            pos = int(fila) - 1
            if 0 <= pos < len(df):
                _guardar_y_refrescar(df.drop(df.index[pos]).reset_index(drop=True), guardar)
    with r5:
        st.write("")
        st.write("")
        if st.button("Fila TOTAL", key=f"{prefijo}_total") and len(df.columns):
            _guardar_y_refrescar(fila_totales(df), guardar)
    with r6:
        st.write("")
        st.write("")
        if st.button("Fila al final", key=f"{prefijo}_add_row") and len(df.columns):
            extra = df.copy()
            extra.loc[len(extra)] = [""] * len(extra.columns)
            _guardar_y_refrescar(extra, guardar)

    st.markdown("</div>", unsafe_allow_html=True)

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
                _guardar_y_refrescar(extra, guardar)
    with c3:
        if len(df.columns):
            borrar = st.selectbox(
                "Quitar columna",
                ["(ninguna)"] + cols,
                key=f"{prefijo}_del_col",
            )
            if borrar != "(ninguna)" and st.button("Quitar", key=f"{prefijo}_del_btn"):
                _guardar_y_refrescar(df.drop(columns=[borrar]), guardar)
    return df


def editar_tabla(df: pd.DataFrame, prefijo: str, guardar) -> pd.DataFrame:
    df = barra_excel(quitar_marca(df), prefijo, guardar)
    editado, marcas = editor_excel(df, f"editor_{prefijo}")
    guardar(editado)
    if st.button("Eliminar filas marcadas", key=f"{prefijo}_del_sel", type="primary"):
        if marcas.any():
            _guardar_y_refrescar(editado.loc[~marcas.to_numpy()].reset_index(drop=True), guardar)
        else:
            st.warning("Marca la casilla Sel de la fila que quieres borrar.")
    return editado
