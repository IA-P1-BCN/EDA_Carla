"""Funciones de limpieza y preparación del dataset COVID Tracking Project.

Este módulo concentra TODO el código de limpieza que antes vivía repartido en los
notebooks, para poder reutilizarlo (notebook 03, dashboard, tests...) sin copiar
y pegar. Cada función hace una cosa y está documentada con la justificación
de su decisión.

Uso típico (desde un notebook en notebooks/):

    import sys; sys.path.append("..")
    from src.limpieza import cargar_crudo, limpiar, integrar_poblacion
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Fuentes de datos
# ---------------------------------------------------------------------------
URL_COVID = "https://api.covidtracking.com/v1/states/daily.json"
# Población por estado y región - US Census Bureau (fuente oficial de EE. UU.)
URL_POBLACION = (
    "https://www2.census.gov/programs-surveys/popest/datasets/"
    "2020-2023/state/totals/NST-EST2023-ALLDATA.csv"
)

# Las 13 columnas que responden las preguntas del análisis (decisiones
# documentadas en el notebook 02: >80% nulos, constantes, redundantes,
# metadatos e inconsistencias entre estados).
COLUMNAS_MANTENER = [
    "date", "state",
    "positive", "totalTestResults", "death",                     # acumulados clave
    "hospitalizedCumulative", "hospitalizedCurrently",
    "inIcuCurrently", "onVentilatorCurrently",                    # presion hospitalaria
    "positiveIncrease", "totalTestResultsIncrease",
    "deathIncrease", "hospitalizedIncrease",                      # incrementos diarios
]

ACUMULADOS = ["positive", "death", "totalTestResults"]
INSTANTANEOS = ["hospitalizedCurrently", "inIcuCurrently", "onVentilatorCurrently"]

REGIONES = {1: "Noreste", 2: "Medio Oeste", 3: "Sur", 4: "Oeste"}


# ---------------------------------------------------------------------------
# Carga con cache local
# ---------------------------------------------------------------------------
def leer_o_descargar(url: str, ruta: Path) -> pd.DataFrame:
    """Devuelve el DataFrame de `url`, cacheado en `ruta` (solo se descarga una vez)."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if ruta.exists():
        print(f"Leyendo cache local: {ruta}")
        return pd.read_csv(ruta)

    import io

    import requests  # import perezoso: solo hace falta en la primera ejecución

    print(f"Descargando {url} ...")
    r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content))
    df.to_csv(ruta, index=False)
    print(f"Guardado en {ruta}")
    return df


def cargar_crudo(ruta: Path = Path("../data/raw/covid_tracking.csv")) -> pd.DataFrame:
    """Carga los datos COVID, convierte `date` a fecha real y ordena por estado y fecha."""
    df = pd.read_csv(ruta)
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%Y%m%d")
    return df.sort_values(["state", "date"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------
def eliminar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Conserva solo las 13 columnas analizables; el resto se eliminan (ver notebook 02)."""
    return df[COLUMNAS_MANTENER].copy()


def rellenar_nulos(df: pd.DataFrame) -> pd.DataFrame:
    """Trata los nulos según el tipo de serie (ninguno es aleatorio):

    - Acumulados (`positive`, `death`, `totalTestResults`): sus nulos son SOLO
      previos al primer reporte de cada estado -> 0 significa «aún no había registros».
      Se comprueba antes; si apareciera un hueco interior, se lanzaría un error.
    - Instantáneos (hospitalizados, UCI, respirador): un nulo no es 0, es «no reportado».
      Se rellenan SOLO los huecos internos con el último valor conocido (ffill dentro
      del estado) y se respetan los nulos iniciales y finales: no inventamos pacientes.
    """
    df = df.copy()

    for col in ACUMULADOS:
        interiores = _nulos_interiores(df, col)
        if interiores:
            raise ValueError(f"{col} tiene {interiores} huecos interiores; decidir caso a caso")
        df[col] = df[col].fillna(0)

    for col in INSTANTANEOS:
        previo = df.groupby("state")[col].ffill()
        futuro = df.groupby("state")[col].bfill()
        df[col] = previo.where(futuro.notna(), np.nan)

    return df


def _nulos_interiores(df: pd.DataFrame, col: str) -> int:
    """Cuenta nulos que caen ENTRE el primer y el último valor reportado por un estado."""
    total = 0
    for _, g in df.groupby("state"):
        s = g[col]
        fv, lv = s.first_valid_index(), s.last_valid_index()
        if fv is None or lv is None:
            continue
        fi, li = g.index.get_loc(fv), g.index.get_loc(lv)
        total += int(s.iloc[fi:li + 1].isna().sum())
    return total


def anadir_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Crea las variables derivadas: partes de la fecha, ratio de positividad
    (recortado a 100% y solo con incrementos positivos: los días negativos son
    correcciones, no tasas)."""
    df = df.copy()
    df["mes"] = df["date"].dt.to_period("M").astype(str)
    df["dia_semana"] = df["date"].dt.day_name()

    valido = (df["positiveIncrease"] > 0) & (df["totalTestResultsIncrease"] > 0)
    df["positividad_pct"] = np.where(
        valido,
        (df["positiveIncrease"] / df["totalTestResultsIncrease"] * 100).clip(upper=100),
        np.nan,
    )
    return df


def limpiar(df_crudo: pd.DataFrame) -> pd.DataFrame:
    """Pipeline completo: elimina columnas inútiles, rellena nulos y añade variables."""
    return anadir_variables(rellenar_nulos(eliminar_columnas(df_crudo)))


# ---------------------------------------------------------------------------
# Segunda fuente: población (Census Bureau) y normalización
# ---------------------------------------------------------------------------
def mapeo_fips(df_crudo: pd.DataFrame) -> pd.DataFrame:
    """Extrae del dataset crudo la correspondencia estado -> código FIPS,
    que es la llave con la que el Census Bureau identifica los estados."""
    return df_crudo[["state", "fips"]].drop_duplicates().reset_index(drop=True)


def cargar_poblacion(ruta: Path = Path("../data/raw/poblacion_census.csv")) -> pd.DataFrame:
    """Carga población por estado del Census Bureau (SUMLEV 40 = estados/DC,
    incluye Puerto Rico; no incluye los territorios menores)."""
    df = pd.read_csv(ruta)
    df = df[df["SUMLEV"] == 40][
        ["NAME", "STATE", "REGION", "DIVISION", "POPESTIMATE2020"]
    ].copy()
    # REGION viene como texto ('1'..'4'; 'X' en PR) -> mapear a nombre legible
    df["region"] = (
        pd.to_numeric(df["REGION"], errors="coerce").map(REGIONES)
        .fillna("Sin región (territorio)")
    )
    df["poblacion"] = df["POPESTIMATE2020"]
    return df.rename(columns={"NAME": "estado_nombre", "STATE": "fips"})[
        ["fips", "estado_nombre", "region", "poblacion"]
    ]


def integrar_poblacion(df: pd.DataFrame, df_crudo: pd.DataFrame,
                       poblacion: pd.DataFrame) -> pd.DataFrame:
    """Une población al dataset limpio (merge por FIPS) y crea tasas por 100.000 hab.

    Los territorios sin dato de población (AS, GU, MP, VI) quedan fuera de las
    tasas: no se puede dividir lo que no se conoce. Es un `inner join` deliberado.
    """
    mapa = mapeo_fips(df_crudo)
    out = df.merge(mapa, on="state", how="left").merge(poblacion, on="fips", how="left")

    out["muertes_100k"] = out["death"] / out["poblacion"] * 100_000
    out["casos_100k"] = out["positive"] / out["poblacion"] * 100_000
    return out


# ---------------------------------------------------------------------------
# Control de calidad
# ---------------------------------------------------------------------------
def comprobar_calidad(df: pd.DataFrame) -> dict:
    """Detecta datos de calidad dudosa y devuelve {nombre_problema: DataFrame}.

    - Acumulados que BAJAN (una muerte no desaparece): correcciones de registro.
    - UCI > hospitalizados: imposible anatómicamente (inconsistencia de reporte).
    - Respirador > UCI: posible (algunos estados reportan respiradores fuera de UCI),
      se cuenta para saber cuántos casos hay.
    - Reconciliación: suma de incrementos diarios vs. acumulado final.
    """
    problemas = {}

    # 1) Acumulados que bajan
    bajadas = {}
    for col in ACUMULADOS:
        baja = df.groupby("state")[col].diff() < 0
        bajadas[f"{col}_baja"] = int(baja.sum())
    problemas["resumen_acumulados_que_bajan"] = pd.Series(bajadas, name="n_dias")

    # 2) Inconsistencias entre columnas actuales
    mask_uci = (df["inIcuCurrently"] > df["hospitalizedCurrently"]).fillna(False)
    mask_resp = (df["onVentilatorCurrently"] > df["inIcuCurrently"]).fillna(False)
    problemas["uci_mayor_que_hospitalizados"] = df.loc[
        mask_uci, ["date", "state", "hospitalizedCurrently", "inIcuCurrently"]
    ]
    problemas["respirador_mayor_que_uci"] = df.loc[
        mask_resp, ["date", "state", "inIcuCurrently", "onVentilatorCurrently"]
    ]

    # 3) Reconciliación incrementos vs. acumulado
    fin = df.groupby("state").agg(
        positivos_acum=("positive", "max"),
        suma_incrementos=("positiveIncrease", "sum"),
    )
    fin["diferencia"] = fin["suma_incrementos"] - fin["positivos_acum"]
    problemas["reconciliacion_positivos"] = fin[fin["diferencia"] != 0]

    return problemas
