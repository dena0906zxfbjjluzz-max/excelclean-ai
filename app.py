import io
import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ExcelClean AI", page_icon="📊", layout="wide")

PALABRAS_NUMERO = (
    "monto",
    "precio",
    "total",
    "cantidad",
    "valor",
    "costo",
    "importe",
    "pago",
    "saldo",
)
CARACTERES_TEXTO = r"[^a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚüÜ]"
MAX_MB = 25


def es_columna_numero(nombre: str) -> bool:
    n = str(nombre).lower()
    return any(k in n for k in PALABRAS_NUMERO)


def es_columna_fecha(nombre: str) -> bool:
    n = str(nombre).lower()
    return "fecha" in n or "date" in n


def normalizar_nombre_columna(nombre) -> str:
    texto = str(nombre).strip()
    texto = re.sub(r"\s+", " ", texto)
    if texto.lower().startswith("unnamed") or texto in ("", "nan", "None"):
        return ""
    return texto


def a_numero(serie: pd.Series) -> pd.Series:
    texto = serie.astype(str).str.strip()
    texto = texto.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaT": pd.NA})
    # 1.234,56 → 1234.56  |  1234.56 se deja
    con_coma = texto.str.contains(",", na=False)
    texto = texto.where(~con_coma, texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    texto = texto.str.replace(r"[^\d.\-]", "", regex=True)
    texto = texto.replace({"": pd.NA})
    return pd.to_numeric(texto, errors="coerce")


def leer_hoja(datos: bytes, hoja: str) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(datos), sheet_name=hoja, engine="openpyxl")


def limpiar_dataframe(
    df: pd.DataFrame,
    *,
    eliminar_duplicados: bool,
    eliminar_filas_vacias: bool,
    eliminar_columnas_vacias: bool,
    rellenar_na: bool,
    limpiar_espacios: bool,
    espacios_internos: bool,
    modo_texto: str,
    remover_especiales: bool,
    corregir_numeros: bool,
    corregir_fechas: bool,
    normalizar_encabezados: bool,
) -> tuple[pd.DataFrame, dict]:
    df_limpio = df.copy()
    stats = {
        "filas_antes": int(df.shape[0]),
        "cols_antes": int(df.shape[1]),
        "duplicados": 0,
        "filas_vacias": 0,
        "cols_vacias": 0,
    }

    if normalizar_encabezados:
        nuevos = [normalizar_nombre_columna(c) for c in df_limpio.columns]
        usados = {}
        finales = []
        for i, nombre in enumerate(nuevos):
            base = nombre or f"columna_{i + 1}"
            if base in usados:
                usados[base] += 1
                base = f"{base}_{usados[base]}"
            else:
                usados[base] = 1
            finales.append(base)
        df_limpio.columns = finales

    if eliminar_filas_vacias:
        antes = len(df_limpio)
        df_limpio = df_limpio.dropna(how="all")
        stats["filas_vacias"] = antes - len(df_limpio)

    if eliminar_columnas_vacias:
        antes = df_limpio.shape[1]
        df_limpio = df_limpio.dropna(axis=1, how="all")
        stats["cols_vacias"] = antes - df_limpio.shape[1]

    if eliminar_duplicados:
        antes = len(df_limpio)
        df_limpio = df_limpio.drop_duplicates()
        stats["duplicados"] = antes - len(df_limpio)

    for col in df_limpio.columns:
        serie = df_limpio[col]
        es_texto = serie.dtype == "object" or pd.api.types.is_string_dtype(serie)
        fecha = es_columna_fecha(col)
        numero = es_columna_numero(col)

        if es_texto and limpiar_espacios:
            mask = serie.notna()
            df_limpio.loc[mask, col] = serie.loc[mask].astype(str).str.strip()
            serie = df_limpio[col]

        if es_texto and espacios_internos:
            mask = df_limpio[col].notna()
            df_limpio.loc[mask, col] = (
                df_limpio.loc[mask, col].astype(str).str.replace(r"\s+", " ", regex=True)
            )

        if es_texto and modo_texto != "dejar" and not fecha:
            mask = df_limpio[col].notna()
            s = df_limpio.loc[mask, col].astype(str)
            if modo_texto == "MAYÚSCULAS":
                df_limpio.loc[mask, col] = s.str.upper()
            elif modo_texto == "minúsculas":
                df_limpio.loc[mask, col] = s.str.lower()
            elif modo_texto == "Título":
                df_limpio.loc[mask, col] = s.str.title()

        if es_texto and remover_especiales and not fecha and not numero:
            mask = df_limpio[col].notna()
            df_limpio.loc[mask, col] = (
                df_limpio.loc[mask, col].astype(str).str.replace(CARACTERES_TEXTO, "", regex=True)
            )

        if corregir_numeros and numero:
            df_limpio[col] = a_numero(df_limpio[col])

        if corregir_fechas and fecha:
            df_limpio[col] = pd.to_datetime(df_limpio[col], errors="coerce", dayfirst=True).dt.strftime(
                "%Y-%m-%d"
            )

    if rellenar_na:
        df_limpio = df_limpio.fillna("N/A")

    stats["filas_despues"] = int(df_limpio.shape[0])
    stats["cols_despues"] = int(df_limpio.shape[1])
    return df_limpio, stats


def excel_en_memoria(hojas: dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for nombre, tabla in hojas.items():
            hoja = re.sub(r"[\\/*?:\[\]]", "_", str(nombre))[:31] or "limpio"
            tabla.to_excel(writer, index=False, sheet_name=hoja)
    return buffer.getvalue()


def borrar_editores() -> None:
    for k in list(st.session_state.keys()):
        if str(k).startswith("editor_"):
            del st.session_state[k]


def editor_excel(df: pd.DataFrame, clave: str, altura: int = 480) -> pd.DataFrame:
    return st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        height=altura,
        key=clave,
        hide_index=True,
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


st.title("📊 ExcelClean AI")
st.write("Como Excel, pero aquí: editas celdas, agregas filas y luego limpias o descargas.")

archivo = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if archivo is None:
    for k in ("resultado", "archivo_nombre", "hojas_elegidas", "edit_src", "editor_ver"):
        st.session_state.pop(k, None)
    borrar_editores()
    st.info("Arrastra un `.xlsx`. Sin contraseña: cada quien sube su archivo.")
    st.stop()

peso_mb = len(archivo.getvalue()) / (1024 * 1024)
if peso_mb > MAX_MB:
    st.error(f"El archivo pesa {peso_mb:.1f} MB. El máximo es {MAX_MB} MB.")
    st.stop()

if st.session_state.get("archivo_nombre") != archivo.name:
    st.session_state.archivo_nombre = archivo.name
    st.session_state.pop("resultado", None)
    st.session_state.pop("edit_src", None)
    st.session_state.editor_ver = 0
    borrar_editores()

datos = archivo.getvalue()

try:
    xls = pd.ExcelFile(io.BytesIO(datos), engine="openpyxl")
    hojas = xls.sheet_names
except Exception as e:
    st.error(f"Error al leer el Excel: {e}")
    st.stop()

st.sidebar.header("Hojas")
if len(hojas) == 1:
    hojas_elegidas = hojas
    st.sidebar.caption(f"Una hoja: **{hojas[0]}**")
else:
    todas = st.sidebar.checkbox("Limpiar todas las hojas", value=False)
    if todas:
        hojas_elegidas = hojas
    else:
        hojas_elegidas = st.sidebar.multiselect(
            "Hojas a tabular", hojas, default=[hojas[0]]
        )
    if not hojas_elegidas:
        st.warning("Elige al menos una hoja.")
        st.stop()

if st.session_state.get("hojas_elegidas") != hojas_elegidas:
    st.session_state.hojas_elegidas = hojas_elegidas
    st.session_state.pop("resultado", None)

try:
    tablas = {h: leer_hoja(datos, h) for h in hojas_elegidas}
except Exception as e:
    st.error(f"Error al leer la hoja: {e}")
    st.stop()

if "edit_src" not in st.session_state:
    st.session_state.edit_src = {}
for h, tabla in tablas.items():
    if h not in st.session_state.edit_src:
        st.session_state.edit_src[h] = tabla.copy()

st.sidebar.header("Filtros")

st.sidebar.subheader("1. Filas y columnas")
eliminar_duplicados = st.sidebar.checkbox("Eliminar filas 100% idénticas", value=True)
eliminar_filas_vacias = st.sidebar.checkbox(
    "Eliminar filas completamente vacías", value=True
)
eliminar_columnas_vacias = st.sidebar.checkbox(
    "Eliminar columnas completamente vacías", value=True
)
normalizar_encabezados = st.sidebar.checkbox(
    "Limpiar nombres de columnas", value=True
)
rellenar_na = st.sidebar.checkbox("Rellenar celdas vacías sueltas con N/A")

st.sidebar.subheader("2. Texto")
limpiar_espacios = st.sidebar.checkbox("Quitar espacios al inicio/final", value=True)
espacios_internos = st.sidebar.checkbox("Dejar un solo espacio entre palabras", value=True)
modo_texto = st.sidebar.selectbox(
    "Mayúsculas / minúsculas",
    ["dejar", "MAYÚSCULAS", "minúsculas", "Título"],
)
remover_especiales = st.sidebar.checkbox("Quitar caracteres raros (#, $, %, @)")

st.sidebar.subheader("3. Números y fechas")
corregir_numeros = st.sidebar.checkbox(
    "Forzar números (monto, precio, total, importe)", value=True
)
corregir_fechas = st.sidebar.checkbox(
    "Normalizar fechas a YYYY-MM-DD (día primero)", value=True
)

if st.sidebar.button("Limpiar ahora", use_container_width=True, type="primary"):
    with st.spinner("Tabulando y limpiando..."):
        resultado = {}
        for nombre in hojas_elegidas:
            tabla = st.session_state.edit_src.get(nombre, tablas[nombre])
            limpio, stats = limpiar_dataframe(
                tabla,
                eliminar_duplicados=eliminar_duplicados,
                eliminar_filas_vacias=eliminar_filas_vacias,
                eliminar_columnas_vacias=eliminar_columnas_vacias,
                rellenar_na=rellenar_na,
                limpiar_espacios=limpiar_espacios,
                espacios_internos=espacios_internos,
                modo_texto=modo_texto,
                remover_especiales=remover_especiales,
                corregir_numeros=corregir_numeros,
                corregir_fechas=corregir_fechas,
                normalizar_encabezados=normalizar_encabezados,
            )
            resultado[nombre] = {"original": tabla, "limpio": limpio, "stats": stats}
        st.session_state.resultado = resultado
        st.session_state.editor_ver = st.session_state.get("editor_ver", 0) + 1
        borrar_editores()

resultado = st.session_state.get("resultado")
ver = st.session_state.get("editor_ver", 0)

st.subheader("Tabla (editable)")
st.caption("Haz clic en una celda para escribir. Abajo a la derecha puedes agregar o borrar filas.")
hoja_vista = (
    hojas_elegidas[0]
    if len(hojas_elegidas) == 1
    else st.selectbox("Ver hoja", hojas_elegidas)
)

if resultado is None:
    df = st.session_state.edit_src[hoja_vista]
    c1, c2, c3 = st.columns(3)
    c1.metric("Filas", f"{df.shape[0]:,}")
    c2.metric("Columnas", f"{df.shape[1]:,}")
    c3.metric("Hojas", len(hojas_elegidas))
    df = herramientas_columnas(
        df,
        f"src_{hoja_vista}_{ver}",
        lambda t: st.session_state.edit_src.__setitem__(hoja_vista, t),
    )
    editado = editor_excel(df, f"editor_src_{hoja_vista}_{ver}")
    st.session_state.edit_src[hoja_vista] = editado
    st.info("Edita aquí como en Excel, o pulsa **Limpiar ahora**.")
    st.download_button(
        label="Descargar esta hoja",
        data=excel_en_memoria({hoja_vista: editado}),
        file_name=f"{Path(archivo.name).stem}_{hoja_vista}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    st.stop()

item = resultado[hoja_vista]
stats = item["stats"]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Filas listas", f"{item['limpio'].shape[0]:,}", delta=-(stats["filas_antes"] - item["limpio"].shape[0]))
m2.metric("Duplicados quitados", stats["duplicados"])
m3.metric("Filas vacías quitadas", stats["filas_vacias"])
m4.metric("Columnas vacías quitadas", stats["cols_vacias"])

antes, despues = st.tabs(["Original (editable)", "Limpio (editable)"])
with antes:
    orig = herramientas_columnas(
        item["original"],
        f"orig_{hoja_vista}_{ver}",
        lambda t: st.session_state.resultado[hoja_vista].__setitem__("original", t),
    )
    orig = editor_excel(orig, f"editor_orig_{hoja_vista}_{ver}")
    st.session_state.resultado[hoja_vista]["original"] = orig
    st.session_state.edit_src[hoja_vista] = orig
with despues:
    limpio = herramientas_columnas(
        item["limpio"],
        f"limpio_{hoja_vista}_{ver}",
        lambda t: st.session_state.resultado[hoja_vista].__setitem__("limpio", t),
    )
    limpio = editor_excel(limpio, f"editor_limpio_{hoja_vista}_{ver}")
    st.session_state.resultado[hoja_vista]["limpio"] = limpio

nombre_salida = f"{Path(archivo.name).stem}_limpio.xlsx"
st.download_button(
    label="Descargar Excel limpio",
    data=excel_en_memoria({n: r["limpio"] for n, r in st.session_state.resultado.items()}),
    file_name=nombre_salida,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
