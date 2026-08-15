import pandas as pd

from formulas import aplicar_formula, evaluar_formula, fila_totales


def test_suma_y_promedio():
    df = pd.DataFrame({"Kilos": [10, 20, 30], "x": ["a", "b", "c"]})
    assert evaluar_formula(df, "=SUMA(Kilos)") == 60
    assert evaluar_formula(df, "=PROMEDIO(Kilos)") == 20


def test_excluye_fila_destino():
    df = pd.DataFrame({"Kilos": [10, 20, 99]})
    assert evaluar_formula(df, "=SUM(Kilos)", excluir_fila=2) == 30


def test_sumar_si_y_si():
    df = pd.DataFrame(
        {
            "Estado": ["Pagado en efectivo", "Credito", "Pagado en efectivo"],
            "Monto S/": [10, 99, 5],
            "Kilos": [8, 20, 12],
        }
    )
    assert evaluar_formula(df, '=SUMAR.SI(Estado,"Pagado en efectivo",Monto S/)') == 15
    modo, serie = aplicar_formula(df, "=SI(Kilos>=10,Alto,Bajo)")
    assert modo == "columna"
    assert list(serie) == ["Bajo", "Alto", "Alto"]


def test_fila_totales():
    df = pd.DataFrame({"Cliente": ["A", "B"], "Kilos": [5, 7], "Nota": ["x", "y"]})
    out = fila_totales(df)
    assert str(out.iloc[-1, 0]) == "TOTAL"
    assert float(out.iloc[-1]["Kilos"]) == 12
