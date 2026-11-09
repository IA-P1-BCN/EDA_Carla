"""Dashboard interactivo para el CEO: filtra y explora sin tocar código.

Ejecutar desde la raiz del repo:

    streamlit run dashboard/app.py

Requiere haber ejecutado antes `python pipeline.py` (o un notebook) para tener
data/processed/covid_avanzado.csv; si no existe, el dashboard lo genera solo.
"""

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.limpieza import clasificar_ola  # noqa: E402

DATA = ROOT / "data" / "processed" / "covid_avanzado.csv"

st.set_page_config(
    page_title="COVID-19 EE. UU. — Panel ejecutivo",
    page_icon="🦠",
    layout="wide",
)


@st.cache_data
def cargar() -> pd.DataFrame:
    """Carga el dataset enriquecido; si no existe, lo genera con el pipeline."""
    if not DATA.exists():
        from pipeline import ejecutar

        ejecutar()
    df = pd.read_csv(DATA, parse_dates=["date"])
    if "ola" not in df.columns:
        df["ola"] = df["date"].map(clasificar_ola)
    return df


df = cargar()

# ---------------------------------------------------------------------------
# Filtros del CEO (sidebar)
# ---------------------------------------------------------------------------
st.sidebar.header("🎛️ Filtros")

regiones = sorted(df["region"].dropna().unique())
region_sel = st.sidebar.multiselect(
    "Región", regiones, default=regiones,
    help="Regiones oficiales del Census Bureau: Noreste, Medio Oeste, Sur y Oeste.",
)

estados_disp = (
    df[df["region"].isin(region_sel)]["state"].unique() if region_sel else []
)
estado_sel = st.sidebar.multiselect(
    "Estado (concreto)", sorted(estados_disp), default=[],
    help="Vacío = todos los estados de las regiones seleccionadas.",
)

olas = sorted(df["ola"].dropna().unique())
ola_sel = st.sidebar.multiselect(
    "Ola / periodo", olas, default=olas,
    help="primavera_2020 = primera ola (NY); invierno_2020 = la gran ola.",
)

fecha_min, fecha_max = df["date"].min(), df["date"].max()
rango = st.sidebar.slider(
    "Rango de fechas", fecha_min.date(), fecha_max.date(),
    (fecha_min.date(), fecha_max.date()), format="DD/MM/YYYY",
)

if st.sidebar.button("🔄 Vaciar caché y recargar"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------------------------
# Aplicar filtros
# ---------------------------------------------------------------------------
m = (
    df["region"].isin(region_sel)
    & df["ola"].isin(ola_sel)
    & (df["date"].dt.date >= rango[0])
    & (df["date"].dt.date <= rango[1])
)
if estado_sel:
    m &= df["state"].isin(estado_sel)

datos = df[m]

if datos.empty:
    st.warning("Los filtros actuales no dejan pasar ningún dato. Amplía la selección.")
    st.stop()

# ---------------------------------------------------------------------------
# Título + KPIs
# ---------------------------------------------------------------------------
st.title("🦠 COVID-19 en Estados Unidos — Panel ejecutivo")
st.caption(
    f"Fuente: COVID Tracking Project (hasta 07/03/2021) + población US Census Bureau · "
    f"{len(datos):,} registros con los filtros actuales"
)

con_pob = datos.dropna(subset=["poblacion"])
ultimo = datos.groupby("state").last()
pob_ultima = ultimo["poblacion"].sum() or 0

k1, k2, k3, k4 = st.columns(4)
k1.metric("Muertes registradas", f"{datos['death'].sum() / 1_000:,.0f}".replace(",", ".") + " K"
          if datos["death"].sum() >= 1_000 else f"{datos['death'].sum():,.0f}")
k2.metric("Casos positivos", f"{datos['positive'].sum() / 1_000:,.0f}".replace(",", ".") + " K"
          if datos["positive"].sum() >= 1_000 else f"{datos['positive'].sum():,.0f}")
pos = datos["positiveIncrease"].sum()
tot = datos["totalTestResultsIncrease"].sum()
k3.metric("Positividad", f"{pos / tot * 100:.1f} %" if tot else "—",
          help="% de pruebas que dieron positivas en el periodo filtrado")
k4.metric("Pico de hospitalizados",
          f"{datos.groupby('date')['hospitalizedCurrently'].sum().max():,.0f}")

# ---------------------------------------------------------------------------
# 1) Evolución temporal (media 7 días)
# ---------------------------------------------------------------------------
st.subheader("📈 Evolución: la pandemia en el tiempo")

serie = (
    datos.groupby("date")
    .agg(casos=("positiveIncrease", "sum"),
         muertes=("deathIncrease", "sum"),
         hospitales=("hospitalizedCurrently", "sum"))
    .sort_index()
)
for c in serie.columns:
    serie[f"{c}_7d"] = serie[c].rolling(7).mean()

fig = px.line(
    serie.reset_index(),
    x="date",
    y=["casos_7d", "muertes_7d"],
    labels={"value": "Diario (media 7 días)", "date": "Fecha", "variable": "Métrica"},
    title="Casos y muertes diarios (media móvil de 7 días)",
)
fig.update_layout(legend_title_text="")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 2) Ranking por estado: total vs. tasa (la lección de justicia)
# ---------------------------------------------------------------------------
st.subheader("⚖️ ¿Quién lo vivió peor? Total vs. tasa justa")

fin = datos.groupby("state").agg(
    muertes=("death", "max"),
    poblacion=("poblacion", "first"),
    region=("region", "first"),
).dropna(subset=["poblacion"])
fin["muertes_100k"] = (fin["muertes"] / fin["poblacion"] * 100_000).round(1)
fin = fin.reset_index()

c1, c2 = st.columns(2)
with c1:
    top_t = fin.nlargest(10, "muertes")
    fig1 = px.bar(top_t, x="state", y="muertes", color="region",
                  title="Por TOTALES (tamaño del estado)",
                  labels={"state": "Estado", "muertes": "Muertes", "region": "Región"})
    st.plotly_chart(fig1, use_container_width=True)
with c2:
    top_r = fin.nlargest(10, "muertes_100k")
    fig2 = px.bar(top_r, x="state", y="muertes_100k", color="region",
                  title="Por cada 100.000 habitantes (gravedad real)",
                  labels={"state": "Estado", "muertes_100k": "Muertes / 100k",
                          "region": "Región"})
    st.plotly_chart(fig2, use_container_width=True)

st.info(
    "💡 **Los dos gráficos no coinciden**: por totales mandan California, Texas y Nueva "
    "York (tamaño); por tasa suben Nueva Jersey, Massachusetts y Rhode Island (riesgo). "
    "Comparar sin normalizar lleva a decisiones equivocadas."
)

# ---------------------------------------------------------------------------
# 3) Mapa coroplético interactivo
# ---------------------------------------------------------------------------
st.subheader("🗺️ Mapa: muertes por cada 100.000 habitantes")

mapa = fin.copy()
fig_mapa = px.choropleth(
    mapa, locations="state", locationmode="USA-states", color="muertes_100k",
    scope="usa", color_continuous_scale="YlOrRd",
    hover_name="state",
    hover_data={"muertes_100k": ":.1f", "muertes": ":,.0f", "region": True},
    labels={"muertes_100k": "Muertes/100k", "muertes": "Muertes", "region": "Región"},
    title="Muertes por COVID-19 por cada 100.000 habitantes",
)
fig_mapa.update_layout(margin=dict(l=0, r=0, t=40, b=0))
st.plotly_chart(fig_mapa, use_container_width=True)

# ---------------------------------------------------------------------------
# 4) Comparación de segmentos: regiones
# ---------------------------------------------------------------------------
st.subheader("🏞️ Regiones del Census Bureau")

if con_pob["region"].notna().any():
    pob_region = (
        con_pob.groupby(["region", "state"])["poblacion"].first().groupby("region").sum()
    )
    tasa_reg = (
        con_pob.groupby("region")
        .agg(muertes=("death", "max"))
        .assign(poblacion=lambda t: t.index.map(pob_region))
    )
    # agregado por region a lo largo del tiempo (numerador/denominador ANTES de dividir)
    serie_reg = con_pob.groupby(["date", "region"], as_index=False).agg(
        muertes=("death", "sum")
    )
    serie_reg["poblacion"] = serie_reg["region"].map(pob_region)
    serie_reg["muertes_100k"] = serie_reg["muertes"] / serie_reg["poblacion"] * 100_000

    fig_reg = px.line(
        serie_reg, x="date", y="muertes_100k", color="region",
        labels={"date": "Fecha", "muertes_100k": "Muertes acumuladas / 100k",
                "region": "Región"},
        title="Evolución por región: el Noreste partió primero",
    )
    fig_reg.update_layout(hovermode="x unified")
    st.plotly_chart(fig_reg, use_container_width=True)

# ---------------------------------------------------------------------------
# 5) Calidad de datos (transparencia)
# ---------------------------------------------------------------------------
st.subheader("🔍 Calidad de los datos")
info_path = ROOT / "data" / "processed" / "informe_calidad.json"
if info_path.exists():
    calidad = json.loads(info_path.read_text(encoding="utf-8"))
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Acumulados que retroceden** (correcciones de los estados):")
        st.json(calidad.get("acumulados_que_bajan", {}))
    with c2:
        st.write("**Inconsistencias entre columnas:**")
        st.write(
            f"- UCI > hospitalizados: {calidad.get('uci_mayor_que_hospitalizados', 0)} días-estado\n"
            f"- Respirador > UCI: {calidad.get('respirador_mayor_que_uci', 0)} días-estado\n"
            f"- Descuadres de reconciliación: "
            f"{calidad.get('estados_con_descuadre_reconciliacion', 0)} estados"
        )
    st.caption(
        "Todos estos casos se conservaron y documentaron: son correcciones reales, "
        "no errores que se pudieran borrar sin mentir."
    )

st.sidebar.markdown("---")
st.sidebar.markdown(
    "📦 **Repo:** `ai_project_EDA` · Datos: COVID Tracking Project + US Census · "
    "Generado con `pipeline.py`"
)
