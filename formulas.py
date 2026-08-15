import re
from datetime import date

import pandas as pd

from limpieza import a_numero

PLANTILLAS = {
    "(elige función)": "",
    "SUMA": "=SUMA(Kilos)",
    "PROMEDIO": "=PROMEDIO(Kilos)",
    "MEDIANA": "=MEDIANA(Kilos)",
    "MAX": "=MAX(Kilos)",
    "MIN": "=MIN(Kilos)",
    "CONTAR": "=CONTAR(Kilos)",
    "CONTARA": "=CONTARA(Cliente)",
    "PRODUCTO": "=PRODUCTO(Kilos)",
    "SUMAR.SI": '=SUMAR.SI(Estado,"Pagado en efectivo",Monto S/)',
    "CONTAR.SI": '=CONTAR.SI(Estado,"Pagado en efectivo")',
    "PROMEDIO.SI": '=PROMEDIO.SI(Estado,"Pagado en efectivo",Monto S/)',
    "SI": "=SI(Kilos>=10,Alto,Bajo)",
    "CONCATENAR": "=CONCATENAR(Cliente,Estado)",
    "MAYUSC": "=MAYUSC(Cliente)",
    "MINUSC": "=MINUSC(Cliente)",
    "ESPACIOS": "=ESPACIOS(Cliente)",
    "REDONDEAR": "=REDONDEAR(Precio S/,2)",
    "ABS": "=ABS(Monto S/)",
    "VALOR": "=VALOR(Kilos)",
    "LARGO": "=LARGO(Cliente)",
    "HOY": "=HOY()",
}


def _columna(df: pd.DataFrame, nombre: str) -> str:
    pedido = str(nombre).strip().strip('"').strip("'")
    for col in df.columns:
        if str(col).strip().lower() == pedido.lower():
            return col
    raise ValueError(f"No existe la columna `{pedido}`.")


def _args(cuerpo: str) -> list[str]:
    partes = []
    actual = []
    comilla = None
    for ch in cuerpo:
        if comilla:
            actual.append(ch)
            if ch == comilla:
                comilla = None
            continue
        if ch in ('"', "'"):
            comilla = ch
            actual.append(ch)
            continue
        if ch == ",":
            partes.append("".join(actual).strip())
            actual = []
            continue
        actual.append(ch)
    if actual or partes:
        partes.append("".join(actual).strip())
    return [p for p in partes if p != ""]


def _lit(texto: str):
    t = str(texto).strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in ('"', "'"):
        return t[1:-1]
    return t


def _nums(serie: pd.Series, excluir: int | None) -> pd.Series:
    if excluir is not None and 0 <= excluir < len(serie):
        serie = serie.drop(serie.index[excluir])
    return a_numero(serie)


def _criterio(serie: pd.Series, criterio: str) -> pd.Series:
    c = str(criterio).strip()
    vals = serie.astype(str)
    m = re.match(r"^(>=|<=|<>|!=|>|<|=)?\s*(.*)$", c)
    op = m.group(1) or "="
    der = m.group(2).strip().strip('"').strip("'")
    if op in (">=", "<=", ">", "<"):
        nums = a_numero(serie)
        ref = pd.to_numeric(pd.Series([der]), errors="coerce").iloc[0]
        if pd.isna(ref):
            return pd.Series(False, index=serie.index)
        if op == ">=":
            return nums >= ref
        if op == "<=":
            return nums <= ref
        if op == ">":
            return nums > ref
        return nums < ref
    if op in ("<>", "!="):
        return vals.str.strip().str.lower() != der.lower()
    return vals.str.strip().str.lower() == der.lower()


def _si_filas(df: pd.DataFrame, cond: str, si_verdad, si_falso) -> pd.Series:
    m = re.match(r"^(.+?)(>=|<=|<>|!=|=|>|<)(.+)$", cond.strip())
    if not m:
        raise ValueError("En SI usa así: =SI(Kilos>=10,Alto,Bajo)")
    col = _columna(df, m.group(1))
    op = m.group(2)
    der = m.group(3).strip().strip('"').strip("'")
    izq_txt = df[col].astype(str).str.strip()
    izq_num = a_numero(df[col])
    der_num = pd.to_numeric(pd.Series([der]), errors="coerce").iloc[0]
    if op == "=":
        ok = izq_txt.str.lower() == der.lower()
        if not pd.isna(der_num):
            ok = ok | (izq_num == der_num)
    elif op in ("<>", "!="):
        ok = izq_txt.str.lower() != der.lower()
    elif op == ">=":
        ok = izq_num >= der_num
    elif op == "<=":
        ok = izq_num <= der_num
    elif op == ">":
        ok = izq_num > der_num
    else:
        ok = izq_num < der_num
    out = pd.Series([si_falso] * len(df), index=df.index, dtype=object)
    out.loc[ok.fillna(False)] = si_verdad
    return out


def _entero(valor):
    if pd.isna(valor):
        return valor
    if isinstance(valor, (int, float)) and float(valor).is_integer():
        return int(valor)
    if isinstance(valor, float):
        return round(valor, 4)
    return valor


def aplicar_formula(df: pd.DataFrame, texto: str, excluir_fila: int | None = None):
    """Devuelve ('celda', valor) o ('columna', Series)."""
    t = str(texto).strip()
    if t.startswith("="):
        t = t[1:]
    m = re.fullmatch(r"([A-Za-zÁÉÍÓÚáéíóú.]+)\s*\(\s*(.*)\s*\)", t, flags=re.DOTALL)
    if not m:
        raise ValueError("Escribe una fórmula tipo =SUMA(Kilos) o =SI(Kilos>=10,Alto,Bajo).")
    nombre = m.group(1).lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    args = _args(m.group(2)) if m.group(2).strip() else []

    alias = {
        "sum": "suma",
        "average": "promedio",
        "avg": "promedio",
        "maximo": "max",
        "minimo": "min",
        "count": "contar",
        "counta": "contara",
        "countif": "contar.si",
        "sumif": "sumar.si",
        "averageif": "promedio.si",
        "if": "si",
        "concatenate": "concatenar",
        "upper": "mayusc",
        "lower": "minusc",
        "trim": "espacios",
        "round": "redondear",
        "value": "valor",
        "len": "largo",
        "today": "hoy",
        "product": "producto",
        "median": "mediana",
    }
    fn = alias.get(nombre, nombre)

    def col_num(i=0):
        if len(args) <= i:
            raise ValueError("Faltan argumentos en la fórmula.")
        return _nums(df[_columna(df, args[i])], excluir_fila)

    if fn == "hoy":
        return "columna", pd.Series([date.today().isoformat()] * len(df), index=df.index)

    if fn in {"suma", "promedio", "mediana", "max", "min", "contar", "contara", "producto"}:
        if fn == "contara":
            serie = df[_columna(df, args[0])]
            if excluir_fila is not None and 0 <= excluir_fila < len(serie):
                serie = serie.drop(serie.index[excluir_fila])
            val = int(serie.astype(str).str.strip().replace("", pd.NA).notna().sum())
            return "celda", val
        nums = col_num(0)
        if fn == "suma":
            return "celda", _entero(float(nums.sum(skipna=True)))
        if fn == "promedio":
            return "celda", _entero(float(nums.mean(skipna=True)))
        if fn == "mediana":
            return "celda", _entero(float(nums.median(skipna=True)))
        if fn == "max":
            return "celda", _entero(float(nums.max(skipna=True)))
        if fn == "min":
            return "celda", _entero(float(nums.min(skipna=True)))
        if fn == "producto":
            return "celda", _entero(float(nums.dropna().prod()))
        return "celda", int(nums.notna().sum())

    if fn in {"sumar.si", "contar.si", "promedio.si"}:
        if len(args) < 2:
            raise ValueError("Usa =CONTAR.SI(Columna,criterio) o =SUMAR.SI(Columna,criterio,ColumnaSuma).")
        col_c = df[_columna(df, args[0])]
        mask = _criterio(col_c, _lit(args[1]))
        if fn == "contar.si":
            return "celda", int(mask.sum())
        col_v = df[_columna(df, args[2] if len(args) > 2 else args[0])]
        nums = a_numero(col_v).where(mask)
        if fn == "sumar.si":
            return "celda", _entero(float(nums.sum(skipna=True)))
        return "celda", _entero(float(nums.mean(skipna=True)))

    if fn == "si":
        if len(args) < 3:
            raise ValueError("Usa =SI(Kilos>=10,Alto,Bajo)")
        return "columna", _si_filas(df, args[0], _lit(args[1]), _lit(args[2]))

    if fn == "concatenar":
        if len(args) < 2:
            raise ValueError("Usa =CONCATENAR(Col1,Col2)")
        a = df[_columna(df, args[0])].astype(str).replace("nan", "")
        b = df[_columna(df, args[1])].astype(str).replace("nan", "")
        return "columna", (a + " " + b).str.strip()

    if fn in {"mayusc", "minusc", "espacios", "abs", "valor", "largo", "redondear"}:
        col = df[_columna(df, args[0])]
        if fn == "mayusc":
            return "columna", col.astype(str).str.upper()
        if fn == "minusc":
            return "columna", col.astype(str).str.lower()
        if fn == "espacios":
            return "columna", col.astype(str).str.strip().str.replace(r"\s+", " ", regex=True)
        if fn == "largo":
            return "columna", col.astype(str).str.len()
        nums = a_numero(col)
        if fn == "abs":
            return "columna", nums.abs()
        if fn == "valor":
            return "columna", nums
        dec = int(float(_lit(args[1]))) if len(args) > 1 else 0
        return "columna", nums.round(dec)

    raise ValueError(
        "Función no disponible aquí. Usa el listado fx: SUMA, PROMEDIO, SI, SUMAR.SI, CONCATENAR, MAYUSC…"
    )


def evaluar_formula(df: pd.DataFrame, texto: str, excluir_fila: int | None = None):
    modo, val = aplicar_formula(df, texto, excluir_fila=excluir_fila)
    if modo != "celda":
        raise ValueError("Esa fórmula se aplica a toda la columna. Pulsa Calcular igual: llena la columna destino.")
    return val


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
