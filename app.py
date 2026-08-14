import io

import pandas as pd
import streamlit as st

st.set_page_config(page_title="ExcelClean AI", page_icon="📊", layout="wide")

PALABRAS_NUMERO = ("monto", "precio", "total", "cantidad", "valor", "costo")
CARACTERES_TEXTO = r"[^a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚüÜ]"


def es_columna_numero(nombre: str) -> bool:
    n = str(nombre).lower()
    return any(k in n for k in PALABRAS_NUMERO)


def es_columna_fecha(nombre: str) -> bool:
    n = str(nombre).lower()
    return "fecha" in n or "date" in n


def leer_excel(datos: bytes, hoja):
    return pd.read_excel(io.BytesIO(datos), sheet_name=hoja, engine="openpyxl")


def limpiar_dataframe(
    df: pd.DataFrame,
    *,
    eliminar_duplicados: bool,
    eliminar_filas_vacias: bool,
    rellenar_na: bool,
    limpiar_espacios: bool,
    texto_mayusculas: bool,
    remover_especiales: bool,
    corregir_numeros: bool,
    corregir_fechas: bool,
) -> pd.DataFrame:
    df_limpio = df.copy()

    if eliminar_duplicados:
        df_limpio = df_limpio.drop_duplicates()

    if eliminar_filas_vacias:
        df_limpio = df_limpio.dropna(how="all")

    for col in df_limpio.columns:
        serie = df_limpio[col]
        es_texto = serie.dtype == "object" or pd.api.types.is_string_dtype(serie)

        if es_texto and limpiar_espacios:
            mask = serie.notna()
            df_limpio.loc[mask, col] = serie.loc[mask].astype(str).str.strip()

        if es_texto and texto_mayusculas:
            mask = df_limpio[col].notna()
            df_limpio.loc[mask, col] = df_limpio.loc[mask, col].astype(str).str.upper()

        if es_texto and remover_especiales and not es_columna_fecha(col):
            mask = df_limpio[col].notna()
            df_limpio.loc[mask, col] = df_limpio.loc[mask, col].astype(str).str.replace(
                CARACTERES_TEXTO, "", regex=True
            )

        if corregir_numeros and es_columna_numero(col):
            df_limpio[col] = (
                df_limpio[col]
                .astype(str)
                .str.replace(r"[^\d.\-]", "", regex=True)
                .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
            )
            df_limpio[col] = pd.to_numeric(df_limpio[col], errors="coerce")

        if corregir_fechas and es_columna_fecha(col):
            df_limpio[col] = pd.to_datetime(df_limpio[col], errors="coerce").dt.strftime(
                "%Y-%m-%d"
            )

    if rellenar_na:
        df_limpio = df_limpio.fillna("N/A")

    return df_limpio


def excel_en_memoria(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="limpio")
    return buffer.getvalue()


st.title("📊 ExcelClean AI")
st.write("Sube un Excel, elige la hoja y limpia la tabla en un clic.")

archivo = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"])

if archivo is None:
    st.session_state.pop("df_original", None)
    st.session_state.pop("df_limpio", None)
    st.session_state.pop("archivo_nombre", None)
    st.stop()

if st.session_state.get("archivo_nombre") != archivo.name:
    st.session_state.archivo_nombre = archivo.name
    st.session_state.pop("df_limpio", None)

datos = archivo.getvalue()

try:
    xls = pd.ExcelFile(io.BytesIO(datos), engine="openpyxl")
    hojas = xls.sheet_names
except Exception as e:
    st.error(f"Error al leer el Excel: {e}")
    st.stop()

hoja = hojas[0] if len(hojas) == 1 else st.selectbox("Hoja a tabular", hojas)

try:
    df = leer_excel(datos, hoja)
except Exception as e:
    st.error(f"Error al leer la hoja: {e}")
    st.stop()

st.session_state.df_original = df

st.subheader("Vista previa")
st.write(f"**{df.shape[0]} filas** · **{df.shape[1]} columnas** · hoja `{hoja}`")
st.dataframe(df.head(20), use_container_width=True)

st.sidebar.header("Filtros")

st.sidebar.subheader("1. Filas")
eliminar_duplicados = st.sidebar.checkbox("Eliminar filas 100% idénticas", value=True)
eliminar_filas_vacias = st.sidebar.checkbox(
    "Eliminar filas completamente vacías", value=True
)
rellenar_na = st.sidebar.checkbox("Rellenar celdas vacías sueltas con N/A")

st.sidebar.subheader("2. Texto")
limpiar_espacios = st.sidebar.checkbox(
    "Quitar espacios al inicio/final", value=True
)
texto_mayusculas = st.sidebar.checkbox("Convertir texto a MAYÚSCULAS")
remover_especiales = st.sidebar.checkbox("Quitar caracteres raros (#, $, %, @)")

st.sidebar.subheader("3. Números y fechas")
corregir_numeros = st.sidebar.checkbox(
    "Forzar números en monto/precio/total", value=True
)
corregir_fechas = st.sidebar.checkbox("Normalizar columnas de fecha a YYYY-MM-DD")

if st.sidebar.button("Limpiar ahora", use_container_width=True, type="primary"):
    with st.spinner("Tabulando y limpiando..."):
        st.session_state.df_limpio = limpiar_dataframe(
            df,
            eliminar_duplicados=eliminar_duplicados,
            eliminar_filas_vacias=eliminar_filas_vacias,
            rellenar_na=rellenar_na,
            limpiar_espacios=limpiar_espacios,
            texto_mayusculas=texto_mayusculas,
            remover_especiales=remover_especiales,
            corregir_numeros=corregir_numeros,
            corregir_fechas=corregir_fechas,
        )

df_limpio = st.session_state.get("df_limpio")
if df_limpio is None:
    st.info("Ajusta los filtros y pulsa **Limpiar ahora**.")
    st.stop()

filas_menos = df.shape[0] - df_limpio.shape[0]
st.success("Tabla lista.")
st.write(
    f"**{df_limpio.shape[0]} filas** · **{df_limpio.shape[1]} columnas**"
    + (f" · se quitaron **{filas_menos}** filas" if filas_menos else "")
)
st.dataframe(df_limpio.head(20), use_container_width=True)

st.download_button(
    label="Descargar Excel limpio",
    data=excel_en_memoria(df_limpio),
    file_name="datos_limpiados.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
