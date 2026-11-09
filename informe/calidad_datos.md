# 📋 Informe de calidad de datos

**Dataset:** COVID Tracking Project — registros diarios por estado (13/01/2020 – 07/03/2021)
**Auditoría:** automática (`python pipeline.py` → `data/processed/informe_calidad.json`) + revisión manual en los notebooks
**Fecha de la revisión:** noviembre 2026

---

## 1. Estado inicial del dataset

| Métrica | Valor |
|---|---|
| Filas × columnas | 20.780 × 56 |
| Duplicados por clave `(date, state)` | **0** |
| Columnas con >80% de nulos | **15** |
| Columnas constantes o vacías | **7** (5 siempre a 0, 2 al 100% vacías) |
| Tipo de fecha | Entero `20200313` → convertido a `datetime` |

---

## 2. Qué faltaba (y qué se hizo)

| Problema | Volumen | Decisión | Justificación |
|---|---|---|---|
| Columnas con >80% de nulos | 15 columnas (tests antígeno/anticuerpo, UCI acumulada, `pending`...) | **Eliminadas** | Sus valores no existen: no hay nada que analizar |
| Columnas constantes / vacías | 7 (`score`, `grade`, `dataQualityGrade`...) | **Eliminadas** | No varían → no explican nada |
| Nulos al inicio de acumulados (`positive`, `death`, `totalTestResults`) | 188 / 850 / 166 filas, **todos previos** al primer reporte | **Rellenados con 0** | Comprobado por código: 0 huecos interiores. «Aún no había registros» es cierto para un acumulado |
| Huecos **interiores** de hospitalización/UCI/respirador | 117 / 409 / 222 filas | **Rellenados con el último valor conocido** (ffill dentro del estado) | Un paciente no desaparece de un día para otro |
| Nulos **iniciales/finales** de hospitalización | 2.995 / 329 (hosp.) y equivalentes en UCI | **Se dejaron vacíos** | El estado no reportaba: rellenar sería inventar pacientes |
| Fechas como entero | 100% de las filas | **Convertidas** | Sin fecha real no hay análisis temporal |

**Nota metodológica sobre la mediana:** *no* se usó para imputar. Es una serie temporal:
la mediana anual aplastaría las olas (pocos ingresos en julio, muchísimos en enero) y
planificaría sobre una realidad que no existió.

---

## 3. Datos de calidad dudosa encontrados (y tratados)

Estos son datos **presentes pero «imposibles»**. Decisión transversal: **no se borran**
(borrarlos inflaría los totales u ocultaría correcciones), se documentan y se mitigan
con medias de 7 días donde procede.

| Hallazgo | Volumen real | Tratamiento |
|---|---|---|
| **Acumulados que retroceden**: `death` baja en 73 días, `positive` en 24, `totalTestResults` en 49 | 146 días-estado | Conservados: son correcciones de registros duplicados por los estados |
| **Valores negativos diarios** (`deathIncrease` mínimo −201, `positiveIncrease` −7.757...) | 24–88 por columna (<0,5%) | Conservados + documentados; suavizados con media móvil de 7 días en gráficos |
| **UCI > hospitalizados** (imposible anatómicamente) | 39 días-estado (casi todos en territorios con 1-2 pacientes) | Conservados y marcados; sin impacto en conclusiones |
| **Respirador > UCI** (posible fuera de UCI, según práctica de algunos estados) | 102 días-estado | Conservados; además estas columnas (44-56% nulos) no se usan en el informe |
| **Descuadre reconciliación** (suma de incrementos ≠ acumulado final) | 17 estados; máximo 53 de 3,5 M en California (0,002%) | Ignorado: ruido de redondeo y correcciones; no altera ninguna conclusión |
| **Ratio de positividad imposible** (positivos > pruebas el mismo día, por desfases de reporte) | Recortado al 100% | `positividad_pct` solo se calcula con incrementos positivos y `clip(upper=100)` |
| **Cobertura desigual** | WA desde 13/01/2020 (420 días) vs. territorios desde 16/03/2020 (357 días) | Nunca se comparan totales crudos; se usan tasas y periodos comunes |

---

## 4. Qué quedó pendiente (y por qué)

| Pendiente | Motivo |
|---|---|
| **4 territorios sin tasas per cápita** (AS, GU, MP, VI) | El fichero del Census Bureau no incluye su población. No se divide lo que no se conoce → `inner join` deliberado, documentado en el notebook 03 |
| **Puerto Rico fuera del mapa coroplético** | `plotly` con `scope="usa"` no lo dibuja; sus datos sí están en tablas y CSV |
| **Población usada: estimación 2020 del Census** | La serie diaria ideal (población día a día) no existe de forma pública comparable; la estimación anual es el estándar aceptado |
| **Muertes desglosadas en «confirmadas/probables»** | >50% de nulos y sin criterio común entre estados → no se analiza el desglose |
| **`recovered` (recuperados) no se analiza** | 42% de nulos; muchos estados dejaron de reportarlo y sin criterio único no es comparable |
| **Sin normalización por edad/riesgo** | Saldría del alcance: requiere pirámides de población por estado y grupo de edad |

---

## 5. Cómo reproducir esta auditoría

```bash
pip install -r requirements.txt
python pipeline.py                      # genera los CSVs + informe_calidad.json
python -m pytest tests/ -v              # 26 tests de las funciones de limpieza
```

Los notebooks `01`, `02` y `03` muestran el razonamiento paso a paso con markdown;
`informe_calidad.json` se regenera en cada ejecución del pipeline y es la fuente
de las cifras de este documento.
