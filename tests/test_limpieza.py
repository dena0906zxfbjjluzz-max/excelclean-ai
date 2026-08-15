import pandas as pd

from limpieza import limpiar_celdas_texto, limpiar_dataframe


def _limpiar(df, **extra):
    opts = dict(
        eliminar_duplicados=True,
        eliminar_filas_vacias=True,
        eliminar_columnas_vacias=True,
        rellenar_na=False,
        limpiar_espacios=True,
        espacios_internos=True,
        modo_texto="dejar",
        remover_especiales=False,
        corregir_numeros=True,
        corregir_fechas=True,
        normalizar_encabezados=True,
        quitar_errores_excel=True,
        quitar_filas_total=True,
        rellenar_hacia_abajo=False,
    )
    opts.update(extra)
    return limpiar_dataframe(df, **opts)


def test_unicode_invisibles_no_revienta():
    s = pd.Series(["abc\u200bdef", "ok"])
    out = limpiar_celdas_texto(s)
    assert "abc" in str(out.iloc[0])


def test_errores_excel_a_vacio():
    s = pd.Series(["#REF!", "dato", "#N/A"])
    out = limpiar_celdas_texto(s)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1] == "dato"
    assert pd.isna(out.iloc[2])


def test_packing_ids_y_totales():
    df = pd.DataFrame(
        {
            "ALMACEN": ["Almacén P", "Almacén P", "TOTAL"],
            "IDPRODUCTO": [210100103.0, 210100200.0, None],
            "STOCK": ["1", "35", "36"],
            "CAJAS": [1, 35, 36],
        }
    )
    limpio, stats = _limpiar(df)
    assert stats["filas_total"] == 1
    assert len(limpio) == 2
    assert str(limpio.loc[0, "IDPRODUCTO"]) == "210100103"


def test_porcentaje_y_nulos():
    df = pd.DataFrame({"a": ["12%", "n/a", "3"], "b": ["x", "NULL", "y"]})
    limpio, _ = _limpiar(df, convertir_pct=True, quitar_nulos_texto=True)
    vals_a = [float(v) for v in limpio["a"].tolist() if not pd.isna(v)]
    assert 12.0 in vals_a
    assert all(str(v).lower() != "null" for v in limpio["b"].tolist())


def test_columnas_duplicadas():
    df = pd.DataFrame({"a": [1, 2], "b": [1, 2], "c": [9, 8]})
    limpio, stats = _limpiar(df, quitar_columnas_duplicadas=True)
    assert stats["cols_dup"] >= 1
    assert "c" in limpio.columns


def test_promueve_encabezado_si_hay_titulo():
    from limpieza import promover_encabezado_real

    df = pd.DataFrame(
        [
            ["Hoja del Lunes", None, None],
            ["Cliente", "Kilos", "Precio S/"],
            ["Pollería El Corralito", 48, 2.86],
        ]
    )
    df.columns = ["Unnamed: 0", "Unnamed: 1", "Unnamed: 2"]
    out = promover_encabezado_real(df)
    assert "Cliente" in list(out.columns)
    assert "Kilos" in list(out.columns)
    assert out.iloc[0, 0] == "Pollería El Corralito"
