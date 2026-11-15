# AURORA — Earth System Intelligence Model
## Reporte científico (borrador V1)

NASA Space Apps Challenge 2026 · Equipo AURORA (Local Event Guadalajara)
Región: Querétaro · Variable: NDVI · Período: 2001–2025 · Fuente: MODIS/061/MOD13Q1

> **Estado:** resultados reales de MODIS incluidos (sección 7). Quedan [PENDIENTE] la validación de 3 píxeles y la
> evaluación predictiva. Los TIFF sintéticos anteriores NO son evidencia científica y no aparecen aquí.
> Las afirmaciones marcadas [VERIFICAR] (Sofia).necesitan una fuente antes de enviarse.

---

## 1. Introducción
El sistema Tierra cambia de forma continua. Cuando el cambio sigue una dirección sostenida
(sube o baja) se le llama **tendencia**, y las variables medidas desde el espacio la reflejan.
Una misma variable puede aumentar en una región y disminuir en otra, incluso si el proceso
que la causa es el mismo; por eso no basta con mirar promedios globales: hay que analizar
**dónde** ocurre el cambio.

AURORA es un modelo científico reproducible que, a partir de imágenes satelitales, responde
cuatro preguntas: **qué** cambia, **dónde**, **cuánto** y **si el cambio es estadísticamente
significativo**. El caso de estudio es el NDVI (índice de vegetación) en Querétaro, México.

## 2. Problemática
- Hay cientos de variables de misiones y modelos de la NASA, y no es evidente cuáles muestran
  tendencias ni en qué zonas.
- Las tendencias suelen ser regionales y a veces de signo opuesto en zonas vecinas.
- Un mapa de tendencias sin prueba estadística puede confundir ruido con cambio. Al evaluar
  miles de píxeles a la vez, además, algunos resultan "significativos" solo por azar, así que
  se necesita corrección por pruebas múltiples.
- Querétaro combina zonas semiáridas, agrícolas y urbanas en crecimiento [VERIFICAR con fuente
  oficial, p. ej. INEGI/CONABIO], lo que la hace un caso útil para detectar cambios de
  vegetación diferentes en una misma región.

## 3. Objetivos
**General.** Detectar y cuantificar tendencias de NDVI en Querétaro entre 2001 y 2025, y
evaluar su significancia estadística con un procedimiento reproducible.

**Específicos.**
1. Construir una serie mensual de NDVI por píxel a partir de MODIS/061/MOD13Q1 con control de calidad.
2. Estimar por píxel la pendiente (NDVI/año), el cambio total estimado y su significancia
   corregida por pruebas múltiples.
3. Visualizar pendiente, magnitud, significancia y cobertura de datos en mapas.
4. Validar de forma independiente los cálculos en píxeles seleccionados.
5. (Complementario) Predecir el NDVI del mes siguiente y comparar contra referencias simples.

## 4. NDVI: qué es y cómo se interpreta
El **NDVI** (Normalized Difference Vegetation Index) se calcula con la luz roja y la
infrarroja cercana que refleja la superficie:

    NDVI = (NIR − Rojo) / (NIR + Rojo)

La vegetación sana absorbe mucha luz roja y refleja mucha infrarroja, por lo que da valores altos.

| Valor aproximado | Superficie típica |
|---|---|
| Cercano a 0 o negativo | Agua, nubes, suelo desnudo o construcciones |
| Bajo–moderado | Vegetación escasa, pastizal seco, cultivo en etapa temprana |
| Alto | Vegetación densa y activa |

[VERIFICAR rangos con Huete et al., 2002 / documentación del producto.]

**Cómo leer una tendencia.** Pendiente positiva = el verdor aumenta con los años; negativa =
disminuye. Un NDVI más alto no siempre es "mejor": puede reflejar riego, cambio de cultivo o
un año lluvioso, y uno más bajo puede deberse a sequía, cosecha o urbanización. El NDVI mide
cambios de la señal de vegetación, no explica por sí solo la causa.

## 5. Fuentes de datos
| Elemento | Detalle |
|---|---|
| Producto | MODIS/061/MOD13Q1 (Terra), índices de vegetación cada 16 días, 250 m |
| Bandas | NDVI (factor de escala 0.0001) y SummaryQA |
| Acceso | Google Earth Engine (catálogo oficial del producto) |
| Filtro de calidad | SummaryQA == 0 y rango físico documentado |
| Agregación temporal | Mediana mensual de observaciones válidas (mes calendario UTC) |
| Rejilla | EPSG:32614, 1000 m, extensión y transformada fijas |
| Faltantes | Se registran; nunca se rellenan con cero |
| Formato | GeoTIFF Float32, una banda, nodata = −9999 |

Citas completas en la sección 10. Las licencias y condiciones de uso de los datos
[PENDIENTE: confirmar en el catálogo de Earth Engine y el LP DAAC].

## 6. Metodología
**6.1 Preparación.** Cubo espacio-temporal `[T, H, W, C]` con máscara de validez.
**6.2 Serie anual.** Media anual por píxel, solo si el año tiene al menos 9 meses válidos.
Se exigen al menos 15 años válidos por píxel.
**6.3 Tendencia (método primario).** Regresión lineal por mínimos cuadrados (OLS) de la media
anual contra el año real. Salidas: pendiente (NDVI/año), valor p y cambio estimado
(pendiente × intervalo observado).
**6.4 Métodos de respaldo.** Pendiente de Theil–Sen (robusta a valores atípicos) y una
sensibilidad con errores estándar HAC (Newey–West) para considerar autocorrelación de los residuos.
**6.5 Significancia.** Corrección por pruebas múltiples de Benjamini–Hochberg (control de la
tasa de falsos descubrimientos); se declara significativo con **q < 0.05**.
**6.6 Cómo leer p y q.** El valor p es la probabilidad de observar una pendiente tan extrema
como la medida si en realidad no hubiera tendencia. **No** es la probabilidad de que el cambio
sea real. La q es la p ajustada por la cantidad de píxeles probados.
**6.7 Predicción (complementaria).** Objetivo: NDVI del mes siguiente con 12 meses de historia.
Partición por fecha objetivo: entrenamiento 2002–2018, validación 2019–2021, prueba 2022–2025.
Referencias: persistencia, climatología mensual y OLS estacional. Modelos: XGBoost y ConvLSTM.
Métricas: MAE, RMSE y R², sobre los mismos pares válidos. El conjunto de prueba no se usa para elegir modelo.
**6.7b Serie regional.** Media no ponderada de los píxeles por mes; solo se usan meses con cobertura regional ≥ 70 %;
media anual y regresión OLS con IC 95 %.
**6.8 Validación independiente.** Tres píxeles documentados, recalculados con
`scipy.stats.linregress` y comparados contra la referencia OLS (tolerancia propuesta 1e-6 NDVI/año).
**6.9 Reproducibilidad.** Se registran versiones, semilla, período y commit en `run_metadata.json`.

## 7. Resultados
> Datos: MODIS/061/MOD13Q1 real, entregados por Ian (paquete con `package_manifest.json`; los 15 archivos
> coinciden con sus SHA-256). Región: 11 511 píxeles de 1 km² dentro de Querétaro. Las cifras de esta sección
> salen de `metrics.json`, `regional_trend.json` y de los mapas; revisarlas contra la corrida final antes de enviar.

**7.1 Tendencia por píxel (OLS, q < 0.05)**

| Categoría | Píxeles | % de probados |
|---|---|---|
| Aumento significativo | 2 010 | 17.8 % |
| Disminución significativa | 505 | 4.5 % |
| Sin evidencia significativa | 8 773 | 77.7 % |
| **Probados (≥ 15 años válidos)** | **11 288** | 100 % |
| No probados (< 15 años válidos) | 223 | — |

- Pendiente media por píxel: **+0.00083 NDVI/año**. Rango de pendientes: de −0.0170 a +0.0110 NDVI/año;
  cambio estimado por píxel: de −0.39 a +0.26 NDVI en el intervalo observado.
- Cobertura temporal media: **94.7 %** de los meses con dato válido.
- Patrón espacial (ver `map_significance.png`): los aumentos significativos se agrupan sobre todo en el centro-este
  y el noreste de la región; las disminuciones, en el suroeste. Los patrones espaciales se describen aquí;
  **sus causas no se afirman** (ver 7.4).

**7.2 Serie regional (media no ponderada de píxeles, `series_regional.png`)**
- Pendiente: **+0.00116 NDVI/año** (+0.0116 por década); cambio estimado 2001–2025: **+0.028 NDVI**.
- p = **0.066**, R² = 0.14, IC 95 % de la pendiente: [−0.00008, +0.00241].
  **A nivel regional la tendencia no alcanza significancia al 5 %**: el intervalo incluye el cero.
- Se excluyen 10 de 300 meses con cobertura regional < 70 %. Los 10 caen entre junio y octubre (época de lluvias, más nubes).

**7.3 Sensibilidad (errores HAC, `map_significance_hac.png`)**
- Con HAC se probaron 10 053 píxeles y 1 965 resultaron significativos (19.5 %). Entre los píxeles probados con HAC,
  1 690 son significativos con ambos métodos (≈ 80 % de los 2 123 significativos con el método primario).
- HAC es exploratorio y no garantiza calibración (advertencia en `run_metadata.json`).
- HAC solo se calcula en píxeles con serie anual completa (25 años) y excluye series constantes; los 1 235 píxeles
  con 15–24 años solo se evalúan con el método primario. La comparación entre métodos se hace sobre los 10 053 píxeles comunes.

**7.4 Interpretación prudente**
- Que haya muchos píxeles con aumento y una tendencia regional no significativa no es contradictorio: la prueba
  por píxel y la regional responden preguntas distintas, y los cambios de signo opuesto se compensan en la media.
- Posibles explicaciones (**hipótesis, no verificadas**): cambios en riego y cultivos, lluvia anual, expansión urbana
  y cambios de uso de suelo. Contrastarlas requiere datos adicionales (p. ej. precipitación o uso de suelo).
- Un píxel de 1 km² promedia vegetación, cultivos y construcciones.

**7.5 Predicción del NDVI del mes siguiente (complementaria)**
Evaluación en el período de prueba 2022–2025, sobre 489 633 pares comparables pixel-mes [CONFIRMAR cifra con Ian]:

| Modelo | R² | MAE | RMSE |
|---|---|---|---|
| XGBoost | 0.884433 | 0.042175 | 0.063527 |
| ConvLSTM | 0.884137 | 0.044379 | 0.063608 |
| Persistencia, climatología mensual, OLS estacional | [PENDIENTE: Ian] | [PENDIENTE] | [PENDIENTE] |

Los dos modelos tienen un desempeño prácticamente igual; XGBoost tiene un MAE algo menor. Sin las referencias de
comparación no se puede afirmar cuánto aportan sobre métodos simples, porque el NDVI tiene un ciclo estacional fuerte.
No se afirma generalización a otras regiones.

## 8. Incertidumbre y validación
Resumen de `docs/validation_report.md` (17 de 17 comprobaciones de coherencia correctas en esta entrega):
- Los conteos por categoría de `metrics.json` coinciden con los mapas.
- La q recalculada con Benjamini–Hochberg desde p coincide con `trend_q.tif` (dif. máx. 6.6e-8, precisión Float32).
- La serie regional recalculada con `scipy.stats.linregress` reproduce pendiente, p, R² e IC de `regional_trend.json`.
- Tres píxeles (aumento, disminución, sin evidencia) recalculados con `scipy.stats.linregress` desde los 300 TIFF mensuales
  reproducen la pendiente y el p del modelo (diferencia máxima 7.4e-11 NDVI/año; tolerancia 1e-6).

## 9. Limitaciones
- **Resolución:** se agrega a 1 km; zonas pequeñas (parcelas, parques urbanos) se mezclan.
- **Nubes y huecos:** MODIS tiene datos faltantes; los meses excluidos caen en la época de lluvias, cerca del máximo de NDVI, lo que puede sesgar la media anual; los píxeles con menos de 15 años válidos (223) no se prueban.
- **Dependencia espacial:** píxeles vecinos no son independientes; la corrección Benjamini–Hochberg puede ser imperfecta.
- **Serie regional:** media no ponderada; la composición espacial observada puede variar en el tiempo.
- **NDVI:** se satura en vegetación densa y responde al ciclo agrícola, la lluvia y el riego.
- **Tendencia lineal:** no capta cambios no lineales ni cambios bruscos; la estacionalidad se atenúa con medias anuales.
- **Autocorrelación y período corto:** con ~25 puntos anuales la prueba tiene poder limitado; HAC es solo sensibilidad.
- **Significancia ≠ importancia:** una tendencia puede ser significativa y pequeña, o grande y no significativa.
- **Sin causalidad:** el modelo detecta cambios, no explica por qué ocurren.
- **Generalización:** no se afirma que el modelo funcione en otras regiones sin una prueba independiente.
- **Datos de prueba:** las figuras generadas con datos sintéticos no son resultados científicos.
- **Posible sesgo estacional (no evaluado):** los 10 meses excluidos por baja cobertura caen entre junio y octubre,
  cerca del máximo de NDVI, y pueden sesgar a la baja las medias anuales de esos años.
- **Predicción:** métricas agrupadas por pixel-mes; sin referencias de comparación publicadas todavía.

## 10. Referencias
> Cita completa verificada en cada fuente antes del envío (año, páginas, DOI). Las escribí de memoria.

**Datos y plataforma**
- Didan, K. (2021). *MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061* [Data set]. NASA EOSDIS Land Processes DAAC. https://doi.org/10.5067/MODIS/MOD13Q1.061
- Catálogo de Earth Engine: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1
- Gorelick, N., et al. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. *Remote Sensing of Environment*, 202, 18–27.

**NDVI**
- Rouse, J. W., et al. (1974). Monitoring vegetation systems in the Great Plains with ERTS. *NASA SP-351*.
- Tucker, C. J. (1979). Red and photographic infrared linear combinations for monitoring vegetation. *Remote Sensing of Environment*, 8(2), 127–150.
- Huete, A., et al. (2002). Overview of the radiometric and biophysical performance of the MODIS vegetation indices. *Remote Sensing of Environment*, 83, 195–213.
- Pettorelli, N., et al. (2005). Using the satellite-derived NDVI to assess ecological responses to environmental change. *Trends in Ecology & Evolution*, 20(9), 503–510.

**Estadística**
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. *Journal of the American Statistical Association*, 63(324), 1379–1389.
- Mann, H. B. (1945). Nonparametric tests against trend. *Econometrica*, 13, 245–259.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. *Journal of the Royal Statistical Society B*, 57(1), 289–300.
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica*, 55(3), 703–708.
- Wasserstein, R. L., & Lazar, N. A. (2016). The ASA statement on p-values. *The American Statistician*, 70(2), 129–133.

**Modelos y software**
- Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. *Proc. KDD '16*.
- Shi, X., et al. (2015). Convolutional LSTM network. *Advances in Neural Information Processing Systems 28*.
- Virtanen, P., et al. (2020). SciPy 1.0. *Nature Methods*, 17, 261–272.
- Documentación: https://docs.scipy.org/ · https://xgboost.readthedocs.io/ · https://pytorch.org/
