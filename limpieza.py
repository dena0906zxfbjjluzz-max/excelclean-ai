import io
import re

import pandas as pd

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
    "stock",
    "cajas",
    "unidades",
    "peso",
    "kg",
)
ERRORES_EXCEL = (
    "#n/a",
    "#na",
    "#ref!",
    "#value!",
    "#div/0!",
    "#name?",
    "#null!",
    "#num!",
    "#getting_data",
)
FILAS_TOTAL = re.compile(
    r"^\s*(total|subtotal|suma|totales|subtotales)\b",
    re.IGNORECASE,
)
CARACTERES_TEXTO = r"[^a-zA-Z0-9\sñÑáéíóúÁÉÍÓÚüÜ]"
MAX_MB = 25


def es_columna_numero(nombre: str) -> bool:
    n = str(nombre).lower()
    return any(k in n for k in PALABRAS_NUMERO)


def es_columna_fecha(nombre: str) -> bool:
    n = str(nombre).lower()
    return "fecha" in n or "date" in n


def es_columna_id(nombre: str) -> bool:
    n = str(nombre).lower()
    return any(k in n for k in ("id", "codigo", "código", "sscc", "ean", "sku"))


def normalizar_nombre_columna(nombre) -> str:
    texto = str(nombre).strip()
    texto = re.sub(r"\s+", " ", texto)
    if texto.lower().startswith("unnamed") or texto in ("", "nan", "None"):
        return ""
    return texto


def a_numero(serie: pd.Series) -> pd.Series:
    texto = serie.astype(str).str.strip()
    texto = texto.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA, "NaT": pd.NA})
    con_coma = texto.str.contains(",", na=False)
    texto = texto.where(
        ~con_coma,
        texto.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
    )
    texto = texto.str.replace(r"[^\d.\-]", "", regex=True)
    texto = texto.replace({"": pd.NA})
    return pd.to_numeric(texto, errors="coerce")


def ids_a_texto(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if not es_columna_id(col):
            continue

        def _celda(v):
            if pd.isna(v):
                return ""
            if isinstance(v, float) and v.is_integer():
                return str(int(v))
            s = str(v).strip()
            if "e+" in s.lower() or "e-" in s.lower():
                try:
                    return str(int(float(s)))
                except ValueError:
                    return s
            if s.endswith(".0"):
                return s[:-2]
            return s

        out[col] = out[col].map(_celda)
    return out


def leer_hoja(datos: bytes, hoja: str) -> pd.DataFrame:
    tabla = pd.read_excel(io.BytesIO(datos), sheet_name=hoja, engine="openpyxl")
    return ids_a_texto(tabla)


def parece_columna_numerica(serie: pd.Series) -> bool:
    muestra = serie.dropna().astype(str).str.strip()
    muestra = muestra[~muestra.str.lower().isin(("nan", "none", "", "-", "n/a"))]
    if len(muestra) < 4:
        return False
    convertidos = a_numero(muestra)
    ok = convertidos.notna().mean()
    return ok >= 0.7


def limpiar_celdas_texto(serie: pd.Series) -> pd.Series:
    out = serie.astype(object)
    mask = out.notna()
    if not mask.any():
        return out
    texto = out.loc[mask].astype(str)
    texto = texto.str.replace("\u00a0", " ", regex=False)
    texto = texto.str.replace(r"[\u200b\u200c\u200d\ufeff]", "", regex=True)
    texto = texto.str.replace(r"[\r\n]+", " ", regex=True)
    texto = texto.str.strip()
    texto = texto.replace({"nan": None, "NaT": None, "None": None, "": None, "-": None})
    vacios = texto.isna() | texto.astype(str).str.lower().isin(ERRORES_EXCEL)
    texto = texto.mask(vacios, None)
    out.loc[mask] = texto
    return out


def _es_vacio(v) -> bool:
    if v is None:
        return True
    try:
        return bool(pd.isna(v))
    except (ValueError, TypeError):
        return False


def columnas_compatibles(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = [str(c) for c in out.columns]
    for col in out.columns:
        serie = out[col]
        if pd.api.types.is_datetime64_any_dtype(serie):
            out[col] = pd.to_datetime(serie, errors="coerce").dt.strftime("%Y-%m-%d")
            continue
        if pd.api.types.is_numeric_dtype(serie):
            out[col] = pd.to_numeric(serie, errors="coerce")
            continue
        out[col] = [None if _es_vacio(v) else v for v in serie.tolist()]
    return out.reset_index(drop=True)


def es_fila_total(fila: pd.Series) -> bool:
    for val in fila.tolist():
        if pd.isna(val):
            continue
        if FILAS_TOTAL.match(str(val).strip()):
            return True
    return False


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
    quitar_errores_excel: bool,
    quitar_filas_total: bool,
    rellenar_hacia_abajo: bool,
) -> tuple[pd.DataFrame, dict]:
    df_limpio = df.copy()
    stats = {
        "filas_antes": int(df.shape[0]),
        "cols_antes": int(df.shape[1]),
        "duplicados": 0,
        "filas_vacias": 0,
        "cols_vacias": 0,
        "filas_total": 0,
        "errores_excel": 0,
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

    if quitar_errores_excel or limpiar_espacios:
        for col in df_limpio.columns:
            if pd.api.types.is_datetime64_any_dtype(df_limpio[col]):
                continue
            if pd.api.types.is_numeric_dtype(df_limpio[col]):
                continue
            if df_limpio[col].dtype == "object" or pd.api.types.is_string_dtype(df_limpio[col]):
                antes_na = df_limpio[col].isna().sum()
                df_limpio[col] = limpiar_celdas_texto(df_limpio[col])
                stats["errores_excel"] += int(df_limpio[col].isna().sum() - antes_na)

    if quitar_filas_total and not df_limpio.empty:
        mask_total = df_limpio.apply(es_fila_total, axis=1)
        stats["filas_total"] = int(mask_total.sum())
        df_limpio = df_limpio.loc[~mask_total]

    if rellenar_hacia_abajo:
        df_limpio = df_limpio.ffill()

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
        numero = es_columna_numero(col) or (
            corregir_numeros and not es_columna_id(col) and not fecha and parece_columna_numerica(serie)
        )

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
                df_limpio.loc[mask, col]
                .astype(str)
                .str.replace(CARACTERES_TEXTO, "", regex=True)
            )

        if corregir_numeros and numero:
            df_limpio[col] = a_numero(df_limpio[col])

        if corregir_fechas and fecha:
            df_limpio[col] = pd.to_datetime(
                df_limpio[col], errors="coerce", dayfirst=True
            ).dt.strftime("%Y-%m-%d")

    if rellenar_na:
        df_limpio = df_limpio.fillna("N/A")

    df_limpio = columnas_compatibles(df_limpio)
    stats["filas_despues"] = int(df_limpio.shape[0])
    stats["cols_despues"] = int(df_limpio.shape[1])
    return df_limpio, stats
