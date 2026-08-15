import re

import pandas as pd

from limpieza import a_numero

_FUNCIONES = {
    "suma": "sum",
    "sum": "sum",
    "promedio": "mean",
    "average": "mean",
    "avg": "mean",
    "max": "max",
    "maximo": "max",
    "máximo": "max",
    "min": "min",
    "minimo": "min",
    "mínimo": "min",
    "contar": "count",
    "count": "count",
    "contara": "counta",
    "counta": "counta",
}


def _columna(df: pd.DataFrame, nombre: str) -> str:
    pedido = str(nombre).strip().strip('"').strip("'")
    for col in df.columns:
        if str(col).strip().lower() == pedido.lower():
            return col
    raise ValueError(f"No existe la columna `{pedido}`.")


def evaluar_formula(df: pd.DataFrame, texto: str, excluir_fila: int | None = None) -> float | int:
    t = str(texto).strip()
    if t.startswith("="):
        t = t[1:]
    m = re.fullmatch(r"([A-Za-zÁÉÍÓÚáéíóú]+)\s*\(\s*(.+?)\s*\)", t)
    if not m:
        raise ValueError("Escribe =SUMA(Columna), =PROMEDIO(Columna), =MAX(Columna), =MIN(Columna) o =CONTAR(Columna).")
    fn = _FUNCIONES.get(m.group(1).lower())
    if not fn:
        raise ValueError("Función no reconocida. Prueba SUMA, PROMEDIO, MAX, MIN o CONTAR.")
    col = _columna(df, m.group(2))
    serie = df[col]
    if excluir_fila is not None and 0 <= excluir_fila < len(serie):
        serie = serie.drop(serie.index[excluir_fila])
    if fn == "counta":
        return int(serie.astype(str).str.strip().replace("", pd.NA).notna().sum())
    nums = a_numero(serie)
    if fn == "sum":
        return float(nums.sum(skipna=True))
    if fn == "mean":
        return float(nums.mean(skipna=True))
    if fn == "max":
        return float(nums.max(skipna=True))
    if fn == "min":
        return float(nums.min(skipna=True))
    return int(nums.notna().sum())


def fila_totales(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or df.shape[1] < 1:
        return df
    out = df.copy()
    mask = out.iloc[:, 0].astype(str).str.strip().str.upper().eq("TOTAL")
    if mask.any():
        out = out.loc[~mask].reset_index(drop=True)
    total = []
    for i, col in enumerate(out.columns):
        if i == 0:
            total.append("TOTAL")
            continue
        nums = a_numero(out[col])
        if nums.notna().sum() >= 1:
            val = float(nums.sum(skipna=True))
            total.append(int(val) if val.is_integer() else round(val, 2))
        else:
            total.append("")
    return pd.concat([out, pd.DataFrame([total], columns=out.columns)], ignore_index=True)
