# AURORA — Global Intelligence Engine: informe de implementación

Fecha: 15 de noviembre de 2026. Rama: `feature/model-core`. Entorno: Python 3.14.4, PySide6 y entorno virtual existente. No se realizaron commits, push, merges, eliminación de datos ni sustitución de resultados históricos.

## Resultado y alcance científico

Se implementó y validó un motor local de lectura parcial, estadística por bloques, catálogo configurable, trabajos cancelables y exportaciones científicas. Los datos científicos disponibles continúan siendo **Querétaro NDVI y LST**, 300 meses de enero de 2001 a diciembre de 2025, malla 171 × 161, EPSG:32614. No se recibieron observaciones de México a 5 km ni terrestres mundiales a 50–100 km. Ambos objetivos quedan explícitamente pendientes en `config/dataset_targets.json`. La compatibilidad arquitectónica y la prueba sintética de almacenamiento no constituyen cobertura mundial científicamente validada.

Las 90 pruebas anteriores se conservaron. La suite final tiene **113 pruebas aprobadas en 12.10 s**. Se verificó la identidad SHA256 de **81 archivos históricos**; no se reentrenaron ni sustituyeron los modelos existentes. Predictive Intelligence ofrece únicamente las combinaciones regionales con modelos entrenados, evaluación retenida y procedencia verificable: Querétaro NDVI y LST.

## Inspección previa y arquitectura

Antes de editar se inspeccionaron la rama, el estado de Git, los archivos pendientes, los metadatos y la arquitectura. El árbol ya contenía cambios locales de AURORA 5: catálogo, selector temporal, laboratorio multivariado y generalización predictiva. Se conservaron. El punto de partida tenía 90 pruebas aprobadas, motores estadísticos en `aurora.trend`, modelos en `aurora.models` e interfaz PySide6/Matplotlib con vistas de planeta, tiempo, resultados y predicción. Las rutas históricas basadas en NPZ y análisis completos no eran adecuadas para conjuntos de tamaño planetario.

La nueva ruta conserva las funciones estadísticas existentes: catálogo → lector por ventanas → trabajo científico aislado → mapas temporales en disco → manifiesto completo → interfaz/exportación. NPZ se extrae una sola vez por streaming a NPY exactos bajo bloqueo de archivo y cuota de caché; NPY usa mmap; Zarr lee chunks. No se simula acceso aleatorio eficiente a miembros NPZ comprimidos.

## Implementación y archivos

| Archivos | Cambio funcional |
|---|---|
| `src/aurora/catalog.py` | Registro por configuración y metadatos; NPZ, NPY y Zarr; ventanas, límites de lectura/chunks, validación de formas/calendario/unidades/máscaras, liberación de recursos, caché y vistas de resolución limitada. Variables nuevas mediante definición explícita en metadatos. |
| `src/aurora/storage.py`, `scripts/convert_zarr.py` | Conversión exacta por bloques a Zarr local, publicación de metadatos al completar, sin sobrescribir destinos. |
| `src/aurora/area.py` | Áreas elipsoidales y ponderación por superficie, mallas de área equivalente, antimeridiano y polos. |
| `src/aurora/block_engine.py` | Estadística nativa por teselas: anualización, OLS, Sen, HAC, cobertura y series ponderadas; mapas en disco y BH global mediante ordenación SQLite. |
| `src/aurora/block_multivariate.py` | Pares observados alineados, anomalías, Pearson/Spearman, desfases, sensibilidad a cobertura y corrección múltiple global en disco. |
| `src/aurora/jobs.py` | Estados/progreso, cancelación cooperativa, publicación atómica de manifiestos, huellas de procedencia y catálogo de resultados vigentes. |
| `src/aurora/exports.py`, `model_exports.py` | Paquetes CSV, JSON, GeoTIFF y PNG con metodología/procedencia; rechazo de productos desactualizados y cancelación. |
| `src/aurora/model_catalog.py` | Elegibilidad de modelos por variable/región, evaluación retenida, unidades, entrada y pesos; sin extrapolar modelos regionales a regiones nuevas. |
| `src/aurora/desktop/tasks.py`, `global_results.py` | Lecturas en trabajadores, entrega Qt en hilo principal, rechazo de generaciones antiguas, selección de resultados, inspección nativa, progreso y exportación. |
| `src/aurora/desktop/window.py`, `globe.py`, `time_machine.py`, `multivariate_lab.py`, `ai_lab.py` | Detección dinámica de datasets/modelos, selección funcional en todos los módulos, trabajos pesados mediante QProcess, cancelación, lectura parcial y cierre seguro. |
| `src/aurora/models/forecasting.py` | Registro SHA256 de pesos en futuros productos; modelos históricos intactos. |
| `config/datasets.json`, `config/dataset_targets.json`, `requirements-global.txt` | Registro externo de las dos copias reales Zarr, objetivos pendientes e instalación reproducible del backend. Las rutas registradas son locales y se deben registrar de nuevo al trasladar el proyecto. |
| `scripts/register_dataset.py`, `scientific_job.py`, `paired_job.py`, `export_result.py`, `export_model_result.py` | Interfaces CLI para registro, cálculo y exportación. |
| `scripts/explore.py`, `validate_aurora5.py` | Adaptación de CLI al motor por bloques y de validación anterior a cargas asíncronas. |
| `scripts/benchmark_partial_zarr.py`, `validate_global_engine.py` | Prueba de presión identificada como sintética y validación científica/funcional reproducible. |
| `tests/test_global_engine.py`, `tests/test_global_async.py` | 23 pruebas nuevas de exactitud, límites de recursos, cancelación, procedencia, formatos e interacción asíncrona. |

La lista anterior corresponde a esta ampliación; el estado Git incluye además trabajo local previo. `implementation_manifest.json` registra hashes de archivos de esta implementación; `working_tree_status.txt` conserva el estado completo para distinguirlo de un checkout limpio.

## Validez geoespacial y estadística

Se preservan valores físicos, máscaras, canales, calendario, CRS y afín. Zarr utiliza NaN para chunks ausentes de X y False para validez/huella: una ausencia nunca se convierte en un cero observado. Las unidades canónicas NDVI/LST no pueden relabelarse arbitrariamente. Una variable en Kelvin requiere identidad explícita distinta; no se aplica una conversión silenciosa.

Los cálculos espaciales operan en la malla nativa. El laboratorio exige identidad espacial y calendario compatibles; no remuestrea ni rellena observaciones. Las vistas reducidas son muestreo para visualización; no generan observaciones nuevas ni reemplazan mapas científicos nativos. Las exportaciones GeoTIFF conservan la transformación y el CRS, con float64 para no perder precisión en probabilidades.

La media y cobertura regional se ponderan por área. En geográficas norte-arriba, el área usa una integral elipsoidal exacta de cada celda, compatible con cruce del antimeridiano y polos. En proyecciones de área equivalente usa determinante del afín y unidades. En otras proyecciones usa polígonos geodésicos con ocho segmentos por borde: **aproximación documentada**, sin corrección fraccional de costa/huella. Las pruebas geométricas no equivalen a validar un producto polar real. La superficie WGS84 calculada en la prueba global es 510065621724088.5 m². Referencia primaria: [pyproj Geod](https://pyproj4.github.io/pyproj/stable/api/geod.html).

La estadística univariada reutiliza los motores existentes. Exige nueve meses válidos por año y quince años válidos para tendencias; los intervalos cortos producen series/cobertura descriptivas sin presentar una tendencia de largo plazo válida. BH se calcula sobre toda la familia espacial por método (OLS/HAC), no por tesela. La ruta multivariada usa pares válidos, climatología por defecto 2002–2018 cuando está disponible, ocho pares de referencia por mes y 36 pares mínimos para correlación. Su familia BH incluye Pearson bruto y de anomalías en todos los píxeles y desfases configurados. El ajuste AR1 y BH son diagnósticos; autocorrelación, ausencia estacional y comparaciones múltiples limitan la inferencia. Correlación no demuestra causalidad.

## Resultados con observaciones reales

Productos finales: `outputs/global_engine/queretaro_ndvi_final`, `queretaro_lst_final` y `queretaro_paired_final`.

| Validación contra procesamiento convencional | Resultado |
|---|---|
| Conversión NPZ → Zarr, NDVI y LST | X, valid, region_mask, dates y channels exactamente iguales |
| OLS: pendiente, p, cambio, n; Sen; p HAC | Diferencia absoluta máxima 0.0 en ambos cubos |
| BH OLS/HAC | Diferencia máxima 2.220446049250313e-16 |
| Medias/coberturas mensuales ponderadas | Coinciden con referencia convencional, tolerancia relativa 1e-12 |
| Pearson y Spearman por píxel | Diferencia máxima 0.0 |
| Familia BH multivariada completa | Coincide con referencia |
| Observaciones emparejadas válidas | 3,149,060 |
| Productos históricos | 81 archivos con SHA256 preservado |

Estas comparaciones convencionales se realizaron únicamente sobre los cubos regionales disponibles. No validan un análisis mundial real.

## Rendimiento y recursos

Medición con `/usr/bin/time -v`, mismo entorno local; son ejecuciones individuales, sin reclamar un benchmark controlado de caché fría ni comparación universal.

| Trabajo real | Tiempo interno | Tiempo total de proceso | Pico RSS |
|---|---:|---:|---:|
| NDVI, 300 meses | 11.364 s | 12.25 s | 317896 KiB |
| LST, 300 meses | 14.284 s | 15.07 s | 335292 KiB |
| NDVI/LST emparejado | 18.216 s | 18.93 s | 270080 KiB |

Los trabajos univariados solicitaron 32 MiB de buffers de cálculo y ajustaron la tesela a 21 × 21, estimación 15.585 MiB. El emparejado solicitó 64 MiB y usó 19 × 19. **El presupuesto de buffers no es un límite del RSS del proceso**: Python, bibliotecas, cachés y páginas mmap añaden memoria. Las funciones liberan páginas cuando el sistema lo permite; el consumo total debe medirse en cada entorno. Se precomprueba espacio de resultados y temporales, con cuota por defecto 16 GiB (`AURORA_RESULT_DISK_LIMIT_GIB`); la extracción NPZ tiene cuota 16 GiB (`AURORA_CACHE_LIMIT_GIB`, directorio configurable `AURORA_CACHE_DIR`). No se borran automáticamente datos del usuario para satisfacer cuotas.

La prueba **explícitamente sintética** creó un Zarr disperso de forma 300 × 8192 × 16384 × 1: X lógico 161061273600 bytes (150 GiB), almacenamiento físico 2857 bytes y un chunk matemático constante. Leyó 12 × 32 × 32 valores, 49152 bytes, en 0.00283 s; pico RSS de 98572 a 104840 KiB. El lector rechazó una lectura completa por presupuesto. Esto verifica acceso parcial y rechazo de asignaciones enormes; **no mide rendimiento denso, datos satelitales globales ni completitud territorial**. El fixture está fuera del registro de producción en `outputs/global_test_fixtures/EXPLICIT_SYNTHETIC_LOGICAL_161GB`.

Zarr probado: biblioteca 3.4.2, almacenes locales formato 2, chunks típicos 12 × 128 × 128 × 1 y concurrencia limitada a cuatro. No se validaron sharding v3, almacenamiento remoto ni ejecución distribuida. Referencias primarias: [arrays Zarr](https://zarr.readthedocs.io/en/stable/user-guide/arrays/) y [rendimiento Zarr](https://zarr.readthedocs.io/en/latest/user-guide/performance/).

## Integración, exportación y robustez

Planetary Explorer, Time Machine, Scientific Results, Spatial Analysis, Temporal Analysis y Multivariate Laboratory consumen el catálogo; Predictive Intelligence aplica además elegibilidad de modelo. Se observan cambios del registro/directorios/metadatos mediante QFileSystemWatcher con debounce y refresco manual. Los mapas usan contexto de región, variable y periodo; se corrigió el aspecto geográfico de la malla. La identidad oscura se conserva, sin trabajo cosmético adicional.

Los trabajos científicos/exportaciones corren en procesos separados; las lecturas y descubrimientos se realizan en trabajadores. El progreso informa fase y avance, y la cancelación se revisa entre bloques y durante exportación. Un manifiesto completo sólo se publica al finalizar y comprobar vigencia; productos parciales, fallidos, cancelados y desactualizados no se presentan como actuales. El cierre cancela lecturas y procesos; callbacks antiguos o de widgets destruidos se descartan.

Se verificaron paquetes completos de cuatro formatos en `outputs/global_exports/queretaro_ndvi_scientific` y `outputs/global_exports/queretaro_lst_predictive`, incluyendo metadatos, fuentes, región, periodo, unidades y metodología. La predicción exportada está identificada como estimación de modelo, no observación.

## Pruebas, errores encontrados y evidencia

La suite final pasó 113/113. Las pruebas nuevas incluyen equivalencia con dos tamaños de bloque, BH global y empates, ventanas NPZ/NPY/Zarr y conversión exacta, chunks faltantes, máscaras, unidades, polos/antimeridiano, áreas equivalentes, cuotas de RAM/disco, rechazo de lectura completa, cancelación antes/durante ejecución, no sobrescritura, resultados obsoletos, exportaciones y errores/cierre de trabajadores Qt.

La validación funcional recorrió nueve pestañas, cargó los dos visores desde Zarr, revisó dieciséis vistas predictivas y ejecutó desde la interfaz un trabajo descriptivo real y otro cancelado. Terminó sin excepciones Qt no manejadas. Detectó y corrigió dos errores que las pruebas previas no cubrían: altura cero de la figura al cargar Time Machine oculto y emisión de señales de trabajadores después de destruir su propietario. También se corrigieron llamadas de dibujo fallidas, selección asíncrona antigua, aspecto espacial y manejos de R² indefinido/memoria GPU no disponible.

Evidencia en `docs/evidence/global_engine/`: `scientific_validation.json`, `pressure_validation.json`, `ui_validation.json`, `environment.json`, `catalog.json`, `tests-final.txt`, registros de recursos y ejecución, manifiestos y capturas `visual/`. `pip check`, compilación de módulos y `git diff --check` finalizaron sin errores. Las capturas se generaron offscreen: prueban renderizado/funciones Qt, no certifican rendimiento interactivo de GPU o compositor de escritorio.

## Comandos de reproducción

Ejecutar en el directorio del proyecto y en `feature/model-core`. Los destinos deben ser nuevos; los siguientes comandos con sufijo `repro` fallarán deliberadamente si ya existen.

```bash
.venv/bin/python -m pip install -r requirements-global.txt
PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-mpl .venv/bin/python -m pytest -q
.venv/bin/python scripts/convert_zarr.py --dataset data/processed/queretaro --output outputs/global_engine/stores/queretaro_ndvi_repro
.venv/bin/python scripts/register_dataset.py --dataset outputs/global_engine/stores/queretaro_ndvi_repro --id queretaro_ndvi_repro --region queretaro --priority 10 --validate-all
/usr/bin/time -v .venv/bin/python scripts/scientific_job.py --dataset data/processed/queretaro --output outputs/global_engine/queretaro_ndvi_repro --region queretaro --memory-mib 32 --block-size 32
/usr/bin/time -v .venv/bin/python scripts/scientific_job.py --dataset outputs/global_engine/stores/queretaro_lst_zarr --output outputs/global_engine/queretaro_lst_repro --region queretaro --memory-mib 32 --block-size 32
/usr/bin/time -v .venv/bin/python scripts/paired_job.py --x data/processed/queretaro --y outputs/global_engine/stores/queretaro_lst_zarr --region queretaro --output outputs/global_engine/queretaro_paired_repro --memory-mib 64
.venv/bin/python scripts/export_result.py --result outputs/global_engine/queretaro_ndvi_repro --output outputs/global_exports/queretaro_ndvi_repro
PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-mpl .venv/bin/python scripts/validate_global_engine.py --ui-only
.venv/bin/python -m pip check
.venv/bin/python -m compileall -q src scripts tests
git diff --check
```

`validate_global_engine.py` sin `--ui-only` comprueba resultados finales, valores convencionales, exportaciones y preservación; debe ejecutarse después de producir los trabajos finales indicados en el script. `scripts/benchmark_partial_zarr.py` contiene el fixture sintético y su destino fijo; rechaza ejecutarse sobre un destino existente. Para repetirlo sin alterar esta evidencia, elegir antes un destino nuevo en una copia del script. La interfaz ofrece cancelación; por CLI se puede crear `CANCEL` dentro del trabajo o el archivo adyacente `nombre_del_trabajo.cancel`. SIGINT/SIGTERM de los trabajos científicos también se manejan cooperativamente.

## Bloqueos y límites pendientes

1. **Datos nacionales/mundiales ausentes:** recibir de Yatz observaciones, fuentes, QA, máscara terrestre, unidades, CRS/afín, calendario y validación de cobertura. Registrar mediante configuración; revisar dominio, resolución y completitud antes de cualquier afirmación nacional/global.
2. **Escala real pendiente:** medir I/O denso, RSS y disco con productos nacionales/globales reales. La resolución 50–100 km reduce el problema inicial, pero no garantiza que cualquier resolución quepa; el motor rechaza presupuestos insuficientes. Para millones de chunks conviene índice de generación, sharding y catálogo remoto, aún sin validar.
3. **Vigencia de fuentes:** las huellas combinan SHA de metadatos con nombres/tamaños/mtime_ns del almacenamiento, no hashes completos de todos los datos. Cambios que preserven timestamps/tamaños pueden eludir la detección. Preferir generaciones inmutables y republicar metadatos. El watcher no observa individualmente millones de chunks profundos.
4. **Geografía:** se preparan EPSG:8857 y EPSG:6933 con tratamiento explícito del dominio polar; no se impone un remuestreo silencioso. Costas fraccionales, georreferenciación y QA polar/antimeridiano de datasets reales siguen pendientes. Alineaciones incompatibles fallan claramente.
5. **Predicción:** no se entrenaron modelos nacionales/globales ni se reutilizaron modelos de Querétaro para ellos. La procedencia de entrenamiento actual usa los NPZ históricos; entrenar directamente desde Zarr requiere adaptar y validar ese productor. No se modificaron las métricas históricas para mejorar resultados.
6. **Recursos y recuperación:** cancelación cooperativa no implica interrupción instantánea de una llamada de biblioteca; quedan artefactos parciales identificados y no publicados. Caché y resultados tienen cuotas, sin limpieza destructiva automática. El presupuesto de trabajo no impone un techo de RSS al sistema operativo.
7. **Inferencia:** la falta de observaciones y su estacionalidad pueden sesgar resultados; las sensibilidades son diagnósticas. AR1, HAC y BH no eliminan todos los supuestos ni autorizan causalidad. Las pruebas sintéticas nunca ingresan al catálogo científico de producción.
