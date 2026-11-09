"""Tests de las funciones de limpieza — escritos ANTES que las funciones (TDD).

Sección A: tests de `clasificar_ola`, función que AÚN NO EXISTE en src/limpieza.py.
Ejecutar ahora debe dar ROJO (falla); el rojo es la especificación de la función.

Sección B: tests de las funciones ya existentes, con mini-DataFrames sintéticos
(no tocamos el dataset real: los tests deben ser rápidos y no depender de red).

Ejecutar:  python -m pytest tests/ -v
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# src/ es importable desde la raíz del repo
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.limpieza import (  # noqa: E402
    anadir_variables,
    comprobar_calidad,
    eliminar_columnas,
    integrar_poblacion,
    rellenar_nulos,
)


# ---------------------------------------------------------------------------
# A) TDD: la función NO existe todavía -> este test tiene que fallar primero
# ---------------------------------------------------------------------------
class TestClasificarOla:
    """`clasificar_ola(fecha)` debe devolver el nombre de la ola/pandemia
    en la que cae una fecha, para poder segmentar el dashboard:

    - primavera_2020: hasta el 30/06/2020
    - verano_2020:    01/07/2020 - 30/09/2020
    - otono_2020:     01/10/2020 - 30/11/2020
    - invierno_2020:  01/12/2020 - 28/02/2021  (la gran ola)
    - resto:          todo lo demás (antes del inicio y el final de la serie)
    """

    @pytest.mark.parametrize(
        "fecha,esperado",
        [
            ("2020-04-05", "primavera_2020"),   # peor día de NY
            ("2020-06-30", "primavera_2020"),   # limite incluido
            ("2020-07-01", "verano_2020"),      # limite excluido
            ("2020-08-15", "verano_2020"),
            ("2020-09-30", "verano_2020"),
            ("2020-10-01", "otono_2020"),
            ("2020-11-30", "otono_2020"),
            ("2020-12-01", "invierno_2020"),
            ("2021-01-11", "invierno_2020"),    # pico de casos nacional
            ("2021-02-28", "invierno_2020"),
            ("2021-03-07", "resto"),            # fin de la serie
            ("2020-01-13", "resto"),            # antes de la pandemia
        ],
    )
    def test_fecha_conocida(self, fecha, esperado):
        from src.limpieza import clasificar_ola

        assert clasificar_ola(pd.Timestamp(fecha)) == esperado

    def test_acepta_datetime_y_string(self):
        from src.limpieza import clasificar_ola

        assert clasificar_ola("2021-01-11") == clasificar_ola(pd.Timestamp("2021-01-11"))


# ---------------------------------------------------------------------------
# B) Funciones existentes: mini-DataFrames sintéticos
# ---------------------------------------------------------------------------
def _df_mini() -> pd.DataFrame:
    """Mini-DataFrame con las 13 columnas analizables, 2 estados x 3 dias.

    - AK: hospitalizados con un HUECO INTERIOR (valor, nan, valor).
    - AS: nulos INICIALES en death e UCI (nunca los reporto al principio).
    """
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2020-03-06", "2020-03-07", "2020-03-08",   # AK
                 "2020-03-09", "2020-03-10", "2020-03-11"]   # AS
            ),
            "state": ["AK", "AK", "AK", "AS", "AS", "AS"],
            "positive": [10.0, 11.0, 12.0, np.nan, 5.0, 6.0],
            "totalTestResults": [100.0, 120.0, 140.0, np.nan, 40.0, 48.0],
            "death": [0.0, 1.0, 2.0, np.nan, 0.0, 0.0],
            "hospitalizedCumulative": [5.0, 6.0, 7.0, 1.0, 1.0, 1.0],
            # AK: hueco INTERIOR (dia 2 sin reporte, con valor antes y despues)
            "hospitalizedCurrently": [3.0, np.nan, 2.0, 1.0, 1.0, 1.0],
            # AS: nunca reporto UCI/ventilador -> nulos (iniciales y todo el grupo)
            "inIcuCurrently": [1.0, 1.0, 1.0, np.nan, np.nan, np.nan],
            "onVentilatorCurrently": [1.0, 1.0, 1.0, np.nan, np.nan, np.nan],
            "positiveIncrease": [3, 1, 1, 0, 2, 1],
            "totalTestResultsIncrease": [20, 20, 20, 0, 10, 8],
            "deathIncrease": [0, 1, 1, 0, 0, 0],
            "hospitalizedIncrease": [1, 0, 0, 0, 0, 0],
        }
    )


class TestEliminarColumnas:
    def test_conserva_solo_las_13_analizables(self):
        df = _df_mini()
        out = eliminar_columnas(df)
        assert out.shape[1] == 13
        assert "date" in out.columns and "state" in out.columns

    def test_no_modifica_el_original(self):
        df = _df_mini()
        eliminar_columnas(df)
        assert df.shape[1] == 13  # el original sigue intacto


class TestRellenarNulos:
    def test_acumulados_se_vuelven_cero(self):
        out = rellenar_nulos(eliminar_columnas(_df_mini()))
        assert out["positive"].isna().sum() == 0
        assert out["death"].isna().sum() == 0
        assert out["totalTestResults"].isna().sum() == 0
        # el nulo inicial de death (AS) = 0: aun no habia registros
        assert out.loc[3, "death"] == 0

    def test_hueco_interior_de_hospitalizados_usa_ultimo_valor(self):
        out = rellenar_nulos(eliminar_columnas(_df_mini()))
        # AK dia 2: hueco interior -> toma el valor del dia anterior (3)
        assert out.loc[1, "hospitalizedCurrently"] == 3.0

    def test_nulo_inicial_de_uci_se_respeta(self):
        out = rellenar_nulos(eliminar_columnas(_df_mini()))
        # AS nunca reporto UCI (filas 3-5): NO se inventa (no hay valor previo)
        assert np.isnan(out.loc[3, "inIcuCurrently"])
        assert np.isnan(out.loc[5, "inIcuCurrently"])
        # AK si tiene UCI rellena sin problemas
        assert out.loc[1, "inIcuCurrently"] == 1.0

    def test_lanza_error_si_hay_hueco_interior_en_acumulado(self):
        # AK con positivos en el primer y ultimo dia, pero NULO en el intermedio:
        # eso es un hueco real en un acumulado -> la funcion debe negarse a rellenar
        mini = eliminar_columnas(
            pd.DataFrame(
                {
                    "date": pd.to_datetime(["2020-03-06"] * 3),
                    "state": ["AK"] * 3,
                    "positive": [10.0, np.nan, 12.0],
                    "death": [0.0, 0.0, 0.0],
                    "totalTestResults": [1.0, 1.0, 1.0],
                    "hospitalizedCumulative": [1.0, 1.0, 1.0],
                    "hospitalizedCurrently": [1.0, 1.0, 1.0],
                    "inIcuCurrently": [1.0, 1.0, 1.0],
                    "onVentilatorCurrently": [1.0, 1.0, 1.0],
                    "positiveIncrease": [1, 0, 1],
                    "totalTestResultsIncrease": [1, 1, 1],
                    "deathIncrease": [0, 0, 0],
                    "hospitalizedIncrease": [0, 0, 0],
                }
            )
        )
        with pytest.raises(ValueError, match="interior"):
            rellenar_nulos(mini)


class TestAnadirVariables:
    def test_crea_mes_y_dia_y_positividad(self):
        out = anadir_variables(rellenar_nulos(eliminar_columnas(_df_mini())))
        assert {"mes", "dia_semana", "positividad_pct"} <= set(out.columns)
        assert out.loc[0, "mes"] == "2020-03"
        assert out.loc[0, "dia_semana"] == "Friday"  # 2020-03-06 fue viernes

    def test_positividad_acotada_al_100(self):
        df = eliminar_columnas(_df_mini())
        # un "ratio imposible": mas positivos que pruebas
        df.loc[0, "positiveIncrease"] = 50
        df.loc[0, "totalTestResultsIncrease"] = 10
        out = anadir_variables(rellenar_nulos(df))
        assert out.loc[0, "positividad_pct"] <= 100

    def test_dias_sin_pruebas_no_generan_ratio(self):
        out = anadir_variables(rellenar_nulos(eliminar_columnas(_df_mini())))
        # sin incrementos >0 no hay tasa: no se inventa
        assert out["positividad_pct"].isna().sum() > 0


class TestComprobarCalidad:
    def test_detecta_acumulado_que_baja(self):
        df = eliminar_columnas(_df_mini())
        df.loc[0, "death"] = 5.0  # AK pasa de 5.0 -> 1.0: el acumulado RETROCEDE
        out = comprobar_calidad(df)
        assert out["resumen_acumulados_que_bajan"]["death_baja"] >= 1

    def test_detecta_uci_mayor_que_hospitalizados(self):
        df = eliminar_columnas(_df_mini())
        df.loc[0, "hospitalizedCurrently"] = 1.0
        df.loc[0, "inIcuCurrently"] = 5.0  # imposible
        out = comprobar_calidad(df)
        assert len(out["uci_mayor_que_hospitalizados"]) == 1

    def test_devuelve_los_cuatro_problemas(self):
        out = comprobar_calidad(rellenar_nulos(eliminar_columnas(_df_mini())))
        assert set(out) == {
            "resumen_acumulados_que_bajan",
            "uci_mayor_que_hospitalizados",
            "respirador_mayor_que_uci",
            "reconciliacion_positivos",
        }


class TestIntegrarPoblacion:
    def test_merge_por_fips_y_tasas(self):
        crudo = pd.DataFrame(
            {"state": ["AK", "AS"], "fips": [2, 60]}
        )
        df = eliminar_columnas(_df_mini())  # solo AK/AS, con death>0
        df = rellenar_nulos(df)
        poblacion = pd.DataFrame(
            {
                "fips": [2],
                "estado_nombre": ["Alaska"],
                "region": ["Oeste"],
                "poblacion": [100],
            }
        )
        out = integrar_poblacion(df, crudo, poblacion)
        # AK tiene poblacion y tasa calculada
        ak = out[out["state"] == "AK"]
        assert ak["poblacion"].notna().all()
        assert ak["muertes_100k"].notna().all()
        # AS (territorio sin dato) queda sin tasa: no se divide lo que no se conoce
        assert out.loc[out["state"] == "AS", "muertes_100k"].isna().all()
