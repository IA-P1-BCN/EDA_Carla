"""Pipeline reproducible: carga -> limpia -> enriquece -> guarda.

Un solo comando desde la raiz del repo:

    python pipeline.py

Lo que hace:
1. Descarga (solo si no esta cacheado) los datos COVID Tracking + poblacion Census.
2. Limpia con las funciones de src/limpieza.py (las mismas que usan los notebooks).
3. Calcula tasas por 100k, calidad de datos y el resumen por estado.
4. Guarda:
   - data/processed/covid_limpio.csv        (limpieza basica, nivel medio)
   - data/processed/covid_avanzado.csv       (con poblacion, region y tasas)
   - data/processed/informe_calidad.json     (automatico: que habia, que se hizo)

Idempotente: se puede ejecutar tantas veces como se quiera; siempre produce
los mismos resultados. Salida 0 = exito (para CI/automatizacion).
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.limpieza import (  # noqa: E402
    URL_POBLACION,
    cargar_crudo,
    cargar_poblacion,
    clasificar_ola,
    comprobar_calidad,
    integrar_poblacion,
    leer_o_descargar,
    limpiar,
)

RAW = Path("data/raw")
PROCESSED = Path("data/processed")


def ejecutar() -> dict:
    """Ejecuta el pipeline completo y devuelve un resumen en forma de dict."""
    print("=" * 60)
    print("PIPELINE COVID-19 EDA")
    print("=" * 60)

    # 1) Carga (con cache local)
    print("\n[1/4] Cargando datos...")
    crudo = cargar_crudo(RAW / "covid_tracking.csv")
    leer_o_descargar(URL_POBLACION, RAW / "poblacion_census.csv")
    poblacion = cargar_poblacion(RAW / "poblacion_census.csv")
    print(f"  datos crudos: {crudo.shape} | poblacion: {poblacion.shape}")

    # 2) Limpieza
    print("\n[2/4] Limpiando...")
    limpio = limpiar(crudo)
    print(f"  {crudo.shape[1]} columnas -> {limpio.shape[1]} analizables")

    # 3) Enriquecimiento + calidad
    print("\n[3/4] Enriqueciendo y auditando calidad...")
    completo = integrar_poblacion(limpio, crudo, poblacion)
    completo["ola"] = completo["date"].map(clasificar_ola)

    problemas = comprobar_calidad(completo)
    calidad = {
        "filas": int(len(completo)),
        "columnas_finales": int(completo.shape[1]),
        "estados_sin_poblacion": sorted(
            completo.loc[completo["poblacion"].isna(), "state"].unique().tolist()
        ),
        "nulos_restantes": {
            k: int(v) for k, v in completo.isna().sum().items() if v > 0
        },
        "acumulados_que_bajan": {
            k: int(v) for k, v in problemas["resumen_acumulados_que_bajan"].items()
        },
        "uci_mayor_que_hospitalizados": int(len(problemas["uci_mayor_que_hospitalizados"])),
        "respirador_mayor_que_uci": int(len(problemas["respirador_mayor_que_uci"])),
        "estados_con_descuadre_reconciliacion": int(
            len(problemas["reconciliacion_positivos"])
        ),
        "positividad_pct_media": round(float(completo["positividad_pct"].mean()), 1),
        "olas": completo["ola"].value_counts().to_dict(),
    }

    # 4) Guardar
    print("\n[4/4] Guardando resultados...")
    PROCESSED.mkdir(parents=True, exist_ok=True)
    limpio.to_csv(PROCESSED / "covid_limpio.csv", index=False)
    completo.to_csv(PROCESSED / "covid_avanzado.csv", index=False)
    (PROCESSED / "informe_calidad.json").write_text(
        json.dumps(calidad, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    for f in ["covid_limpio.csv", "covid_avanzado.csv", "informe_calidad.json"]:
        p = PROCESSED / f
        print(f"  {p} ({p.stat().st_size / 1024:.0f} KB)")

    print("\nPipeline terminado sin errores.")
    return calidad


if __name__ == "__main__":
    ejecutar()
