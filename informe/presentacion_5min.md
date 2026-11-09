# 🎤 Presentación de 5 minutos — El hallazgo

> Guion para contar el proyecto a público no técnico. Tiempos orientativos.
> **Halla­zgo principal en una frase:** *«Comparar por totales crudos te dice dónde hay
> más personas; comparar por tasas te dice dónde hay más riesgo. Y la diferencia entre
> una cosa y otra cambia las decisiones.»*

---

## 1. ENGANCHE (0:00 – 0:45) — La pregunta de las dos California

**[Diapositiva: dos barras — California y Nueva Jersey]**

> «California registró 54.124 muertes. Nueva Jersey, 23.574: menos de la mitad.
> Si tuviera que decidir dónde estuvo la tragedia, por estos números diría
> *California, claro*.
>
> **Pero California tiene 39,5 millones de habitantes y Nueva Jersey 9,3 millones.**
> Si contamos muertes *por cada 100.000 habitantes*:
> California 137... **Nueva Jersey 254**. Casi el doble.
>
> Los dos números son ciertos. **Solo uno sirve para decidir.** Esto es de lo que
> va este proyecto.»

---

## 2. CONTEXTO (0:45 – 1:30) — Qué había en la caja

**[Diapositiva: foto de la "caja de datos" — 20.780 filas, 56 columnas]**

> «El cliente nos entregó el mayor registro público de la pandemia en EE. UU.:
> **20.780 filas**, una por estado y día, durante 13 meses. Nadie lo había mirado
> con calma.
>
> Lo primero que hicimos **no fue analizar: fue mirar**. Y encontramos:
> 15 columnas casi vacías, una fecha que no era fecha (era un número),
> muertes «negativas» y estados que empezaron a medir meses después que otros.
>
> Si alguien hubiera usado esos datos tal cual, habría sacado conclusiones falsas.»

---

## 3. LA LIMPIEZA (1:30 – 2:30) — «No borramos: explicamos»

**[Diapositiva: tabla de decisiones con iconos ✂️ y 📌]**

> «Cada decisión de limpieza tiene una razón escrita. Las tres más importantes:
>
> 1️⃣ **Las muertes negativas no eran errores**: eran estados corrigiendo registros
> duplicados. No las borramos — habría mentido sobre los totales — pero sí usamos
> medias de 7 días para que la foto no salga borrosa por el fin de semana
> (spoiler: los hospitales reportan poco los domingos y mucho los miércoles).
>
> 2️⃣ **Los huecos de hospitalizados no se rellenan a lo loco**: si ayer había
> pacientes y hoy no se reportó, seguimos con los de ayer (no desaparecen). Pero
> si un estado *nunca* reportó, dejamos vacío: no inventamos pacientes.
>
> 3️⃣ **Usamos la mediana solo donde NO hace falta.** Sí, han leído bien:
> en series temporales la mediana *estropea* los datos — convertiría las olas de
> invierno en una línea plana que nunca existió.
>
> Y lo comprobamos: **26 tests automatizados** validan esta limpieza. Si mañana
> alguien la toca sin querer, el sistema avisa.»

---

## 4. EL HALLAZGO (2:30 – 4:00) — La historia de los tres relojes

**[Diapositiva: gráfico `medio_tendencia_nacional.png` — tres olas]**

> «La pandemia de EE. UU. **no fue una ola: fueron tres**, y cada región vivió la
> suya en su momento:
>
> 🗽 **Primavera 2020**: el Noreste. Nueva York colapsa mientras el resto del país
> está casi tranquilo.
> ☀️ **Verano 2020**: el Sur. Texas, Florida, Arizona.
> ❄️ **Invierno 2020-21**: la gran ola, casi todos a la vez — **11 de enero de 2021:
> 247.000 casos en un solo día**.
>
> **[Diapositiva: las tres curvas desfasadas]**
>
> Y hay un detalle bonito: los tres picos — casos, hospitalizados y muertes —
> llegan **con días de diferencia**. Primero te infectas, luego ingresas, luego
> se complica. Los datos cuentan la enfermedad sin decir una palabra sobre ella.»

**[Diapositiva: positividad mensual vs. línea del 5% — `medio_positividad_mensual.png`]**

> «Y encontramos el **indicador más barato que existe**. Cuando las pruebas
> superan el 5% de positividad — como en abril de 2020 (15,9%) o en el invierno
> (11,3%) — los hospitales se llenan **dos a cuatro semanas después**.
> Es mirar el reloj antes de que suene la alarma.»

**[Diapositiva: mapa interactivo coroplético]**

> «Al normalizar por población, el mapa cambia: **el Noreste fue la zona más
> castigada en términos relativos** (Nueva Jersey 254 muertes por 100k, frente a
> 137 de California). California no entra ni en el top-8 de gravedad real.»

---

## 5. CIERRE (4:00 – 5:00) — Qué se lleva el cliente

**[Diapositiva: 3 iconos]**

> «Tres cosas:
>
> 1. **Datos limpios y auditables**: de 56 columnas a 13 que responden preguntas,
>    cada decisión justificada, 26 tests y un pipeline que se ejecuta con un
>    comando: `python pipeline.py`.
> 2. **Un panel para explorar sin tocar código**: filtros por región, estado,
>    periodo y fechas — el mapa y los rankings, a un clic.
> 3. **La lección**: *antes de comparar, normaliza*. Totales crudos → decides
>    donde hay más gente. Tasas → decides donde hay más riesgo.
>
> Pregunta para el cliente: **¿sobre qué números están decidiendo hoy ustedes?**
>
> — Fin (4:55)」

---

### 📦 Recursos para la sesión

| Momento | Recurso |
|---|---|
| Diapositiva 1 | `assets/avanzado_total_vs_tasa.png` |
| Diapositiva 3 | Tabla del notebook 02 (`decisiones`) |
| Diapositiva 4 | `assets/medio_tendencia_nacional.png`, `assets/medio_positividad_mensual.png` |
| Demo en vivo | `streamlit run dashboard/app.py` (mapa + filtros) |
| Si preguntan por calidad | `informe/calidad_datos.md` |
