import io
from pathlib import Path

import pandas as pd
import streamlit as st

from estilo import aplicar_estilo, cabecera, marca_sidebar
from excel_validador import excel_en_memoria
from limpieza import MAX_MB, leer_hoja, limpiar_dataframe
from ui_lote import borrar_editores, editar_tabla

st.set_page_config(page_title="ExcelClean AI", page_icon="📊", layout="wide")
aplicar_estilo()
marca_sidebar()
cabecera()

archivo = st.file_uploader("Archivo Excel (.xlsx)", type=["xlsx"])

if archivo is None:
    for k in ("resultado", "archivo_nombre", "hojas_elegidas", "edit_src", "editor_ver"):
        st.session_state.pop(k, None)
    borrar_editores()
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
normalizar_encabezados = st.sidebar.checkbox("Limpiar nombres de columnas", value=True)
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

st.sidebar.subheader("4. Extra")
quitar_errores_excel = st.sidebar.checkbox(
    "Quitar errores de Excel (#REF!, #N/A, #VALUE!)", value=True
)
quitar_filas_total = st.sidebar.checkbox(
    "Quitar filas de Total / Subtotal", value=True
)
rellenar_hacia_abajo = st.sidebar.checkbox(
    "Rellenar celdas vacías con el valor de arriba"
)
quitar_nulos_texto = st.sidebar.checkbox(
    "Tratar NULL / n/a / sin dato como vacío", value=True
)
quitar_columnas_duplicadas = st.sidebar.checkbox(
    "Quitar columnas idénticas", value=True
)
convertir_pct = st.sidebar.checkbox("Convertir porcentajes (12% → 12)", value=True)
normalizar_si_no = st.sidebar.checkbox("Unificar SI / NO")

if st.sidebar.button("Limpiar ahora", use_container_width=True, type="primary"):
    with st.spinner("Tabulando y limpiando..."):
        resultado = {}
        for nombre in hojas_elegidas:
            tabla = st.session_state.edit_src.get(nombre, tablas[nombre])
            try:
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
                    quitar_errores_excel=quitar_errores_excel,
                    quitar_filas_total=quitar_filas_total,
                    rellenar_hacia_abajo=rellenar_hacia_abajo,
                    quitar_nulos_texto=quitar_nulos_texto,
                    quitar_columnas_duplicadas=quitar_columnas_duplicadas,
                    convertir_pct=convertir_pct,
                    normalizar_si_no=normalizar_si_no,
                )
            except Exception as e:
                st.error(f"No se pudo limpiar la hoja `{nombre}`: {e}")
                st.stop()
            resultado[nombre] = {"original": tabla, "limpio": limpio, "stats": stats}
        st.session_state.resultado = resultado
        st.session_state.editor_ver = st.session_state.get("editor_ver", 0) + 1
        borrar_editores()

resultado = st.session_state.get("resultado")
ver = st.session_state.get("editor_ver", 0)

st.subheader("Tabla")
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
    editado = editar_tabla(
        df,
        f"src_{hoja_vista}_{ver}",
        lambda t: st.session_state.edit_src.__setitem__(hoja_vista, t),
    )
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
m1.metric(
    "Filas listas",
    f"{item['limpio'].shape[0]:,}",
    delta=-(stats["filas_antes"] - item["limpio"].shape[0]),
)
m2.metric("Duplicados quitados", stats["duplicados"])
m3.metric("Filas vacías quitadas", stats["filas_vacias"])
m4.metric("Totales quitados", stats.get("filas_total", 0))

antes, despues = st.tabs(["Original", "Limpio"])
with antes:
    orig = editar_tabla(
        item["original"],
        f"orig_{hoja_vista}_{ver}",
        lambda t: st.session_state.resultado[hoja_vista].__setitem__("original", t),
    )
    st.session_state.edit_src[hoja_vista] = orig
with despues:
    editar_tabla(
        item["limpio"],
        f"limpio_{hoja_vista}_{ver}",
        lambda t: st.session_state.resultado[hoja_vista].__setitem__("limpio", t),
    )

nombre_salida = f"{Path(archivo.name).stem}_limpio.xlsx"
st.download_button(
    label="Descargar Excel limpio",
    data=excel_en_memoria({n: r["limpio"] for n, r in st.session_state.resultado.items()}),
    file_name=nombre_salida,
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True,
)
