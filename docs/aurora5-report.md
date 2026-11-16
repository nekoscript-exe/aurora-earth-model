# AURORA 5.0 — Multivariate and Planetary Intelligence

Informe del 15 de noviembre de 2026. Desarrollo local en `feature/model-core`.
No se realizaron commits, push, merges, cambios de rama ni eliminación de datos.

## Estado inicial y arquitectura

Se inspeccionaron rama, estado local, contrato de cubos, entrenadores, evaluador,
inferencia y widgets antes de modificar archivos. El árbol de trabajo estaba
limpio. Estaban disponibles los dos cubos reales de Querétaro, NDVI y LST,
con 300 meses, enero de 2001 a diciembre de 2025, dimensiones 171×161 y
EPSG:32614. La rejilla tiene resolución de 1,000 m y 11,511 píxeles regionales.
La RTX 5070 Laptop, capacidad CUDA 12.0, funciona con el entorno existente.

La arquitectura previa separaba tendencias, variables, modelos, scripts y
widgets PySide6. Había referencias temporales y cortes correctos para NDVI,
pero ConvLSTM aplicaba `tanh` y la inferencia recortaba al rango NDVI. Las rutas
regionales se repetían en varios módulos y las observaciones del visor se
cargaban enteras. Las 72 pruebas iniciales aprobaron sus aserciones, aunque una
ejecución acabó con código 139 al cerrar Qt. La limpieza explícita de widgets en
las pruebas corrigió ese cierre: la ejecución final termina con código 0.

## Fase 1 — Predicción LST

Se añadió `aurora.models.forecasting`, reutilizando:

- `temporal_split`, `fit_climatology`, `predict_baselines` y métricas existentes.
- Las once características temporales de XGBoost, calculadas solo con los doce
  meses anteriores al objetivo, incluida la fase estacional conocida.
- El dataset espacial de parches y el entrenador enmascarado de ConvLSTM.

ConvLSTM ahora acepta una cabeza lineal opcional. Su constructor predeterminado
sigue aplicando `tanh`: los pesos y el comportamiento histórico NDVI siguen
siendo compatibles. El nuevo experimento multivariable emplea cabeza lineal y
normalización global por media/desviación de los objetivos observados de
**entrenamiento exclusivamente**. LST se restaura a Celsius antes de evaluar,
exportar o visualizar. No se recorta a −0.2..1 ni se fuerza una mejora artificial.
Los ceros de entrada de la red son marcadores computacionales acompañados por
un canal de validez; no se convierten en observaciones del cubo ni en objetivos.

Protocolo ejecutado:

| Partición de objetivos | Periodo | Meses |
| --- | --- | ---: |
| Entrenamiento | 2002-01 — 2018-12 | 204 |
| Validación | 2019-01 — 2021-12 | 36 |
| Prueba retenida | 2022-01 — 2025-12 | 48 |

Los doce meses de 2001 proporcionan contexto inicial. Cada objetivo usa los
12 meses anteriores y se requieren al menos nueve observados por píxel. La
evaluación es **rolling one-month-ahead**: para un objetivo posterior se pueden
usar observaciones anteriores ya disponibles dentro del periodo de prueba.
No es un pronóstico libre de 48 meses desde diciembre de 2021. La prueba no se
utilizó para entrenar, normalizar, elegir época ni elegir iteración.

La normalización LST entrenada tiene media **29.336734 °C** y desviación
**6.148776 °C**. XGBoost usa características en unidades físicas, sin necesitar
normalización. Se fijó semilla 42. XGBoost seleccionó iteración 75; ConvLSTM,
época 7. La red paró tras la época 10 con paciencia 3, dentro del máximo de 12.
Se ejecutaron realmente CUDA y BF16 en el entrenador de la red cuando compatible.

### Métricas reales de prueba

Población común de **507,583** pares píxel-mes, de 528,314 objetivos observados.
La misma máscara exige objetivo observado, historia suficiente y resultado
finito de las cinco referencias/modelos. Las métricas se agrupan sobre esos
pares; no son un promedio de R² mensuales ni una prueba de generalización espacial.

| Modelo | MAE (°C) | RMSE (°C) | R² |
| --- | ---: | ---: | ---: |
| Persistencia | 3.37079 | 4.27227 | 0.58868 |
| Persistencia estacional | 3.07098 | 4.07129 | 0.62647 |
| Climatología de entrenamiento | 2.58991 | 3.36224 | 0.74524 |
| XGBoost | **2.08755** | **2.83070** | **0.81943** |
| ConvLSTM | 2.21107 | 3.01232 | 0.79551 |

No se afirma superioridad estadísticamente significativa entre modelos:
no se estimaron intervalos de incertidumbre para esas diferencias.

### Enero de 2026 y artefactos

Se generaron estimaciones retrospectivas a un mes desde enero–diciembre de 2025.
**No hay una observación objetivo de enero de 2026 en estos cubos**, por lo que
no se atribuye precisión verificada a ese mapa.

| Modelo | Píxeles estimados | Media regional de la estimación (°C) |
| --- | ---: | ---: |
| Persistencia | 11,064 | 18.67987 |
| Estacional | 11,058 | 21.34613 |
| Climatología | 11,095 | 23.99223 |
| XGBoost | 11,095 | 20.40782 |
| ConvLSTM | 11,095 | 20.67882 |

Las referencias permanecen ausentes donde falta su observación necesaria;
no se rellenan para igualar cobertura. La comparación común se aplica a los
benchmarks observados, no fuerza observaciones futuras inexistentes.

Salidas locales en `outputs/aurora5/queretaro_lst/`:

- `xgboost/model.ubj`, `convlstm/best_model.pt` y `climatology_model.npz`.
- `normalization.json`, `metrics.json`, `final_benchmark.json` y curvas de entrenamiento.
- `validation_predictions.npz` y `test_predictions.npz`, con máscaras y fechas.
- `forecast/<modelo>/forecast.npz`, metadatos y GeoTIFF `forecast_lst.tif`, en °C.

`forecast_saved.py` recarga los pesos, normalización y climatología exportados,
comprueba la identidad SHA-256 del cubo y reproduce las cinco estimaciones sin
entrenar. La comparación con `outputs/aurora5/lst_reloaded_final/` dio **diferencia
máxima cero** en las cinco. Los GeoTIFF conservan CRS, transformada, NoData y unidad.
Los comandos antiguos específicos de NDVI rechazan LST con una instrucción
explícita para usar la nueva ruta, evitando recortes o normalizaciones incorrectos.

Predictive Intelligence incorpora selectores de región y variable; mantiene las
ocho vistas originales, sus mapas, diferencias, importancia y curvas. Se
verificaron las ocho vistas de NDVI y las ocho de LST. La propiedad de capacidad
predictiva del registro LST ahora es verdadera.

## Fase 2 — Periodos mensuales

`aurora.temporal` centraliza interpretación de fechas, selección inclusiva y
requisitos temporales. `desktop.temporal.TemporalSelector` se utiliza en la
investigación principal, Time Machine, Planetary Explorer y el laboratorio conjunto.

- Campos QDateEdit con calendario y escritura manual, confirmada al terminar
  la edición. Los días se normalizan al mes: ambos extremos incluyen su mes.
- Dos controles de línea temporal enlazados, para comienzo y final del intervalo.
- Periodos rápidos de 5, 10, 15 y 25 años, deshabilitados si no están disponibles.
- Límites derivados del calendario real del dataset; fechas fuera del dominio,
  calendarios repetidos e intervalos invertidos son rechazados.
- Los visores reproducen solamente el intervalo elegido. Las fechas no generan
  cuadros intermedios ni interpolación de observaciones.
- En los laboratorios, los controles detallados se despliegan desde el botón
  de fechas, dejando espacio para gráficas y mapas.

La elegibilidad de tendencia exige al menos 15 años con nueve meses seleccionados;
los motores existentes siguen comprobando la cobertura por píxel y por región.
Un periodo corto se exporta como **descriptivo**, con medias y cobertura mensuales,
sin pendientes, p, q ni afirmaciones de tendencia de largo plazo.

Ejecuciones reales adicionales:

- LST 2025-02 — 2025-10: nueve meses descriptivos, sin mapas de significancia.
- LST 2010-01 — 2025-12: análisis histórico completo mediante los motores
  existentes, con OLS, Sen, diagnósticos, HAC y serie regional.

Las salidas están bajo `outputs/investigations/` con esos intervalos en sus nombres.
No se sobrescribieron las investigaciones previas. El panel global de
investigación ahora admite desplazamiento vertical; conserva sus controles.

## Fase 3 — Multivariate Laboratory

Se implementaron el módulo científico `aurora.multivariate`, un CLI reproducible
y una novena pestaña, con proceso de análisis separado de la interfaz.

Se comprobó igualdad exacta de CRS, afín, forma y calendario. Una discrepancia
produce error; no hay reproyección, interpolación ni emparejamiento silencioso.
La intersección regional tiene **11,511** píxeles y contiene **3,149,060** pares
observados válidos durante 2001–2025.

Método y salidas:

- Pearson y Spearman por píxel; rangos con empates y faltantes pareados.
- Climatologías mensuales por píxel, referencia **2002–2018**, calculadas sobre
  pares coincidentes. Se exigen ocho pares de referencia para el mes del calendario.
- Correlaciones de anomalías y mapas para desfases −12, −6, −3, −1, 0, 1, 3, 6 y
  12 meses; al menos 36 pares para cada correlación espacial.
- Convención explícita: desfase positivo = **NDVI(t) frente a LST(t+desfase)**.
  No se comprimen meses ausentes.
- Perfil regional exploratorio para todos los desfases −12..12.
- Mapas GeoTIFF con CRS, matrices NPZ, dispersión de medias regionales coincidentes
  y series temporales con ejes separados para anomalías NDVI y LST en °C.
- Sensibilidad a cobertura 50/70/90/95%, por estación, excluyendo cada mes del
  calendario, usando una huella espacial más estable y retirando tendencia lineal.
- Diagnóstico de autocorrelación lag-1 con pares calendarios consecutivos;
  tamaño efectivo AR(1), p i.i.d. y p AR(1) claramente denominados diagnósticos.
- Una familia BH conjunta para **Pearson bruto y de anomalías en todos los desfases**.
  Los mapas Spearman no tienen afirmaciones de significancia.
- Intervalo regional mediante 499 remuestreos circulares en bloques de 12 meses,
  con semilla 42. No es una inferencia causal ni una prueba espacial completa.

Los supuestos de independencia de la inferencia ordinaria Pearson se documentan
en [SciPy](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.pearsonr.html).
AR(1) y BH no corrigen universalmente dependencia temporal, dependencia espacial,
no estacionariedad ni selección por disponibilidad. Por eso no se presenta un
mapa diagnóstico como evidencia causal o significancia espacial calibrada.

### Resultados descriptivos reales

Con cobertura regional coincidente ≥70%:

| Asociación regional | Pearson | Spearman | Meses |
| --- | ---: | ---: | ---: |
| Valores mensuales brutos | −0.51988 | −0.49727 | 284 |
| Anomalías mensuales | −0.75998 | −0.72721 | 280 |
| Anomalías con tendencia lineal retirada | −0.75660 | −0.71309 | 280 |
| Anomalías, huella estable | −0.76665 | −0.72832 | 291 |

La huella estable contiene 9,339 píxeles con al menos 90% de pares durante el
periodo. El intervalo de bloques para Pearson regional de anomalías fue
**[−0.81594, −0.68532]**; depende de las aproximaciones de estacionariedad y bloques.
La mediana del Pearson espacial de anomalías a desfase cero fue **−0.61717**.

La asociación cambia con el filtrado: a cobertura ≥90% el Pearson regional de
anomalías es −0.70041. Por estación, las correlaciones de anomalías fueron:
DJF −0.46023 (75 meses), MAM −0.75126 (75), JJA −0.92166 (61) y SON −0.72306 (69).
La composición espacial y estacional de los faltantes importa. Estos resultados
no establecen que modificar NDVI provoque un cambio determinado de LST.

Artefactos finales: `outputs/aurora5/multivariate/queretaro_scientific/`.
Se conservan las corridas incrementales previas; la interfaz elige la última
corrida terminada compatible con los identificadores del dataset.

## Fase 4 — Catálogo, ventanas y escala planetaria

`aurora.catalog.DatasetRegistry` descubre productos observados en
`data/processed/*/cube_metadata.json`. Registra región, variable, fuente, unidad,
CRS, resolución en unidades del CRS, fechas, forma, almacenamiento y cobertura
**declarada**. Excluye productos sintéticos y comunica errores de metadatos.
Los selectores de regiones y las rutas de investigación consultan ese catálogo.
Para cubos heredados sin `region_id` se utiliza una convención de nombre;
los productos nuevos deben declarar ese identificador explícitamente.

`config/dataset_targets.json` registra México a 5 km como **pendiente de
observaciones**, sin crear un dataset ficticio. Se conserva el acceso de
navegación geográfica a México. La incorporación futura exige rejilla, CRS,
calendario, fuente, unidades y QA documentados; no se impone UTM 14N a todo México.

`CubeReader` ofrece `read(time, rows, cols)` y un iterador de bloques:

- **NPZ existente:** descompresión secuencial de miembros NPY exactos a caché,
  con búfer de 1 MiB; después memoria mapeada de solo lectura. NPZ comprimido
  no proporciona lectura aleatoria de ventanas: no se atribuye esa capacidad.
- **NPY:** lectura directa con memoria mapeada y presupuesto previo de ventana.
- **Zarr:** adaptador opcional; exige relleno NaN para X y falso para validez,
  evitando interpretar bloques ausentes como ceros medidos. **No está instalado**
  en este entorno: su ejecución física queda pendiente de validación.

Se preparó una copia NPY exacta del LST real en
`outputs/aurora5/storage/queretaro_lst/`. Las ventanas de 2001, 2021 y 2025
coinciden con NPZ, incluyendo máscaras. Una ventana 12×32×32 tarda aproximadamente
**0.019 ms** con caché caliente en esta máquina; no es un benchmark de disco frío,
red, Zarr ni de un producto continental.

`ObservationSeries` lee un cuadro bajo demanda en los visores. Prepara niveles
virtuales por selección del píxel fuente, con afín ajustada para conservar sus
centros. El máximo de dimensión de visualización es 2,048; se informa el stride.
No interpola valores. La representación reducida puede omitir detalle y alterar
la apariencia de cobertura: sus estadísticas corresponden a celdas muestreadas.
Los análisis científicos y predicciones usan la rejilla nativa.

La caché de miembros usa ruta, tamaño y mtime del origen para invalidarse; no es
un control criptográfico contra cambios que conserven esos atributos. Se
conservan además las cachés de base/proyección/trazos de Planetary Explorer.
No hay eliminación automática de caché ni pirámides persistentes multirresolución.

### Estrategia continental/global

1. Ingesta validada con región, CRS, rejilla, variable y calendario explícitos.
2. Convertir el empaquetado pesado a NPY local o Zarr fragmentado; conservar
   validez y NoData independientemente de valores.
3. Procesar ventanas temporales/espaciales; para predicción, incorporar halo de
   12 meses anterior al objetivo, con particiones temporales intactas.
4. Para estadísticas multivariadas, calcular bloques espaciales con todo el
   soporte temporal necesario y aplicar la corrección múltiple a la familia
   completa, no separadamente a cada bloque.
5. Diseñar niveles cartográficos y caché por dataset/variable/fecha/nivel/ventana.
   Una reducción visual nunca debe sustituir el producto científico original.
6. Evaluar chunks iniciales como 12×256×256×1 y shards mayores con datos reales,
   midiendo consultas, compresión, transferencia, RAM y sesgo de acceso.

Zarr diferencia unidades de lectura por chunk y agrupación física por shard;
la elección debe medirse según el patrón de consulta, como explica su
[documentación de rendimiento](https://zarr.readthedocs.io/en/latest/user-guide/performance/).
Las rutas científicas actuales de entrenamiento y análisis conjunto siguen
siendo regionales y usan carga completa limitada por presupuesto de entrada.
Un dataset grande se rechaza con instrucciones para usar bloques. **No se
implementó ni se afirma entrenamiento planetario distribuido**. Los adaptadores
y la lectura del visor preparan esa siguiente etapa sin cargar todos sus meses.

## Fase 5 — Validación, recursos y preservación

Suite final, advertencias de Python tratadas como errores:

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-mpl \
  .venv/bin/python -m pytest -q -W error
```

**90 pruebas aprobadas, cero fallos, código de salida 0, 9.57 s.**
Se conservaron los 72 casos anteriores; se actualizaron dos expectativas que el
alcance cambia deliberadamente: LST admite predicción y existen nueve pestañas.
No se eliminaron casos. Se añadieron 18 casos para normalización sin futuro,
cabeza lineal, inferencia sin objetivo, población común, fechas, umbrales,
correlación/rangos/faltantes, desfases, climatología pareada, catálogo, ventanas,
bloques, centros LOD y pruebas de integración con resultados reales.

Los controles de cierre Qt se destruyen explícitamente en las pruebas para que
el proceso termine correctamente. El script visual también verifica todos los
modos predictivos, las vistas multivariadas, LST en el globo y el tamaño mínimo.
Las capturas fueron inspeccionadas; se corrigió una superposición de etiquetas
al plegar controles de fechas y ampliar el espacio del laboratorio.

| Ejecución real | Tiempo de pared del proceso | RSS máximo |
| --- | ---: | ---: |
| Entrenamiento/evaluación/exportación LST | 40.68 s | 3,431,800 KiB ≈3.27 GiB |
| Análisis multivariado final | 17.02 s | 977,624 KiB ≈0.93 GiB |

Los tiempos internos registrados son 1.49 s para ajuste XGBoost y 33.79 s para
entrenamiento ConvLSTM. Pico PyTorch asignado: **189.86 MiB**; no incluye toda la
reserva CUDA, memoria de XGBoost ni el compositor. `/usr/bin/time -v` registra RAM
máxima del proceso, tiempos e I/O en los archivos de evidencia.

**35 archivos históricos de NDVI conservan exactamente su SHA-256**. Sus
modelos, métricas, mapas y resultados no se sobrescribieron. No se modificó
`aurora/trend.py` ni se cambió el significado de resultados históricos.

Errores detectados y resueltos durante las fases:

- Cabeza y recorte NDVI incompatibles con LST: cabeza lineal, unidades físicas
  y comandos heredados protegidos contra uso incorrecto.
- Rutas regionales duplicadas: catálogo central y resolución de productos por metadatos.
- `Affine * Affine` emite advertencia en el entorno: se utiliza `@`.
- La primera lectura parcial mostraba solo YYYY-MM donde se esperaba la fecha
  mensual completa: se preservó el formato de día inicial en el visor.
- Cierre Qt con código 139 tras pasar aserciones: limpieza explícita de widgets,
  con suites finales y scripts visuales terminados correctamente.
- Superposición de títulos/ejes en la vista multivariada inicial: distribución
  revisada y evidencias regeneradas.

## Archivos y evidencias

Nuevos módulos: `src/aurora/{catalog,geospatial,temporal,multivariate}.py`,
`src/aurora/models/forecasting.py`,
`src/aurora/desktop/{temporal,multivariate_lab}.py`.

Módulos actualizados: `variables.py`, `models/convlstm.py`,
`desktop/{window,ai_lab,globe,time_machine,geospatial}.py`.
`desktop/geospatial.py` mantiene los imports compatibles de las transformaciones,
cuya implementación ahora reside en el núcleo compartido.

Nuevos comandos: `train_multivariable.py`, `forecast_saved.py`,
`analyze_multivariate.py`, `catalog_datasets.py`, `prepare_dataset_store.py`,
`validate_aurora5.py`. Actualizados: `explore.py`, `predict.py`, `train_deep.py`
y la expectativa de pestañas de `validate_planetary.py`.

Pruebas nuevas: `test_forecasting_multivariable.py`, `test_temporal.py`,
`test_multivariate.py`, `test_catalog.py`, `test_aurora5_integration.py`.
Se extendieron las pruebas del explorador y se actualizó el indicador LST.

`docs/evidence/aurora5/` incluye:

- Métricas LST, benchmark, informe multivariado y catálogo.
- Versiones del entorno, hashes de preservación y reproducción de inferencia.
- Recursos de entrenamiento, inferencia, historia y análisis multivariado.
- Salida de las 90 pruebas y validación de modos de interfaz.
- Capturas bajo `visual/`: benchmark LST, estimación espacial, aprendizaje,
  laboratorio, desfases, sensibilidad, LST en el globo y ventana mínima.

Las salidas pesadas permanecen locales bajo `outputs/`; no se añadieron datos
satelitales al seguimiento de Git. Los hashes del código final y los productos
exportados están en `artifact_manifest.json` para vincular la evidencia.

## Reproducción

Utilizar el entorno virtual existente y salidas nuevas por ejecución. El
entrenador, analizador e inferencia rechazan sobrescribir un directorio de corrida.

```bash
.venv/bin/python scripts/catalog_datasets.py

.venv/bin/python scripts/train_multivariable.py \
  --dataset data/processed/queretaro_lst --variable lst \
  --output outputs/aurora5/lst_reproduction --epochs 12

.venv/bin/python scripts/forecast_saved.py \
  --dataset data/processed/queretaro_lst --run outputs/aurora5/queretaro_lst \
  --output outputs/aurora5/lst_inference_reproduction

.venv/bin/python scripts/analyze_multivariate.py \
  --ndvi data/processed/queretaro --lst data/processed/queretaro_lst \
  --start 2001-01 --end 2025-12 \
  --output outputs/aurora5/multivariate/reproduction

.venv/bin/python scripts/prepare_dataset_store.py \
  --dataset data/processed/queretaro_lst \
  --output outputs/aurora5/storage/lst_reproduction

QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-mpl \
  .venv/bin/python scripts/validate_aurora5.py

.venv/bin/python scripts/desktop.py
```

Los tiempos y detalles numéricos de GPU pueden variar por versiones y algoritmos
CUDA; no se afirma reproducibilidad bit a bit de un reentrenamiento entre equipos.
La recarga de los pesos exportados sí se contrastó exactamente en este entorno.
Los tests de integración que necesitan artefactos locales se omiten en una copia
sin esos productos; en esta ejecución **no se omitió ninguno**.

## Limitaciones y pendientes

- Falta la observación de enero de 2026: las estimaciones retrospectivas no tienen
  validación futura ni intervalos calibrados de incertidumbre.
- México aún no tiene observaciones locales. No se crearon ni simularon datos.
- Zarr está preparado como interfaz opcional, pero requiere instalar y validar
  una versión compatible antes de usarlo. NPY y NPZ están verificados con datos reales.
- Entrenamiento y correlaciones globales por bloques, pirámides persistentes,
  política de caché y mediciones continentales/globales siguen pendientes.
- La reducción visual muestrea celdas: puede ocultar detalle o huecos pequeños.
  Las estadísticas de esa vista se identifican como muestreadas; no se usan para ciencia.
- No hay validación espacial fuera de Querétaro ni pruebas de cambio de dominio;
  un buen error temporal regional no demuestra transferencia a México.
- Persisten dependencia espacial, autocorrelación residual, composición cambiante,
  no estacionariedad y sesgo por faltantes no aleatorios. El bootstrap y AR(1)
  son aproximaciones documentadas, no una solución general a esos problemas.
- La ponderación regional uniforme es adecuada para esta rejilla métrica; una
  rejilla global geográfica requiere pesos de área y políticas adicionales.
- La identidad del proveedor, unidades y georreferencia se comprueban contra el
  contrato; no se revalida desde cero la geolocalización orbital ni el QA original.
- Falta prueba física de calendarios, ratón, HiDPI y rendimiento gráfico en el
  equipo de presentación. La revisión de interfaz fue mediante Qt sin pantalla.
