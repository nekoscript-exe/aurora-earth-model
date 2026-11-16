# AURORA — Auditoría técnica final posterior a la entrega

Fecha: 16 de noviembre de 2026. Rama: `integration/final-consolidation`.
Base inspeccionada: `96e7bca`; código de ejecución validado y empaquetado: `85ad3b0`. Ajuste posterior exclusivo de auditoría CI: `59ba48e`. El commit documental posterior contiene este informe y sus evidencias.

## Resultado y alcance

Se corrigieron los 31 diagnósticos iniciales, defectos reproducibles de seguridad local, integridad, instalación y presentación. La suite completa pasó de **192 a 212 pruebas aprobadas**. Pyright informa **0 errores, 0 advertencias y 0 informaciones**, también utilizando el nuevo entorno CPU.

La auditoría abarcó arquitectura, adquisición, almacenamiento, estadística, modelos, interfaz, internacionalización, instalación y distribución. Incluyó inventario, revisión de cambios pendientes, búsquedas por superficies, revisiones estáticas independientes y ejecución de regresiones. No constituye una prueba formal de ausencia de vulnerabilidades ni una validación científica exhaustiva de todas las observaciones nacionales y mundiales.

No se modificaron algoritmos estadísticos, fórmulas predictivas, pesos, observaciones, productos históricos, archivos originales del concurso, README ni CONTRIBUTORS. No hubo push, publicación, merge, cambios de etiquetas, reescritura de historial ni cambios de autoría. Las únicas referencias Git modificadas corresponden a los nuevos commits locales de consolidación. Durante el cierre se detectó una edición concurrente del apartado del equipo en README; se conservó sin editar ni incluir en estos commits. El README de `HEAD` sigue siendo idéntico al inicial; su árbol de trabajo contiene esa edición ajena a la auditoría. CONTRIBUTORS permanece idéntico.

## Estado inicial y arquitectura

Antes de editar se registraron el estado Git, el diff binario pendiente, las referencias y hashes de archivos. El inventario inicial tenía 432 archivos versionados. Existían siete modificaciones locales: `.gitignore`, `pyrightconfig.json` y los cinco scripts científicos `qa_grid.py`, `sensitivity_regional.py`, `validate_data.py`, `validate_independent.py` y `validate_lst.py`. Se revisaron, conservaron y verificaron antes de incorporarlas a los commits.

La configuración ignorada `pyrightconfig.local.json` permite resolver Earth Engine desde su entorno separado. Sigue fuera del repositorio. No se desactivaron reglas de Pyright ni se introdujeron supresiones indiscriminadas.

El sistema tiene estas conexiones principales:

- **Adquisición:** scripts de Earth Engine y descarga de GeoTIFF; flujo separado del escritorio y de la demostración sin credenciales.
- **Datos:** `DatasetRegistry`, `CubeReader`, `storage`, `geospatial`, `variables` y `area`. NPZ se extrae a NPY mapeado; NPY admite ventanas; Zarr proporciona bloques. Las máscaras, calendario, rejilla y unidades acompañan cada almacén.
- **Ciencia:** `trend`, `block_engine`, `multivariate`, trabajos y manifiestos. Se mantienen OLS, Theil–Sen, HAC y BH sobre la familia completa; las agregaciones regionales del motor por bloques ponderan por superficie.
- **Predicción:** referencias temporales, características, datasets de parches, ConvLSTM, XGBoost y catálogo de modelos evaluados. Los resultados disponibles dependen de datos y artefactos verificables.
- **Escritorio:** PySide6 y Matplotlib; procesos para trabajos científicos y `ReaderJobs` para lecturas con entrega al hilo Qt. Los tokens de generación impiden aplicar resultados atrasados.
- **Distribución:** perfiles Lite/Full, selección CPU/CUDA, manifiestos SHA-256, rutas relativas y superposiciones de procedencia para conservar manifiestos históricos sin editarlos.

`data` y `outputs` contienen enlaces hacia recursos externos locales. Se utilizaron solo para lectura. Las nuevas salidas se generaron en directorios independientes temporales, sin escribir a través de esos enlaces.

Entorno comprobado: Ubuntu 26.04.1 LTS, Python 3.14.4, PySide6 6.12.0, PyTorch 2.14.1 y RTX 5070 Laptop. Se utilizaron el entorno científico existente, el entorno Earth Engine y entornos CPU/auditoría independientes. No se actualizaron los entornos originales.

## Problemas y correcciones

| Problema | Gravedad / alcance | Corrección y verificación |
|---|---|---|
| Importación desde `/tmp/aurora-mexico-reference/scripts` | Media, ejecución local condicionada a precreación o control de esa ruta | El exportador de meses faltantes importa el helper del repositorio. Proyecto, rejilla y calendarios son argumentos explícitos. Validación previa de fechas y guardia `main`; importar ya no inicia Earth Engine ni exportaciones. |
| Caché NPZ compartida, predecible y sin vinculación de contenido | Media, integridad científica local | Nueva caché privada `aurora-arrays-v2`, controles POSIX de propietario/permisos y enlaces, identidad SHA-256 del origen, hashes de miembros, comprobación al reutilizar, bloqueo y publicación atómica. Se rechaza la sustitución de arrays aunque forma, rango y fecha sean plausibles. |
| Temporales de extracción tras cancelación | Baja, recursos y recuperación | Limpieza en `finally` de los temporales propios; publicación de manifiesto cancelable. Prueba de cancelación durante escritura y reintento exacto. No se borró la caché histórica del usuario. |
| Inferencia directa sin comprobar pesos | Media para procedencia; sin RCE demostrado | `forecast_saved` verifica hashes antes de los parsers nativos. Usa hashes del run o el manifiesto histórico preservado, igual que el catálogo. Los modelos históricos disponibles siguen funcionando; un artefacto sin procedencia verificable se rechaza. |
| Verificación de enlaces después de `resolve()` | Baja, incumplimiento de política; no escape independiente demostrado | Se rechazan enlaces del archivo y de sus componentes antes de resolver. Se prueban alias internos con bytes idénticos y enlaces a directorios. |
| Descubrimiento implícito del proyecto hermano | Baja, portabilidad/procedencia | El generador exige `--source-root` explícito cuando faltan recursos locales. Ese directorio aporta datos, nunca código importado. Se conserva el soporte de raíces de datos enlazadas intencionalmente. |
| Creación del entorno antes del preflight | Baja, instalación incompleta evitable | Se comprueban locks, perfil y wheelhouse antes de crear el entorno. Se conserva el rechazo de destinos existentes. |
| Herramientas de instalación con avisos conocidos | Riesgo de cadena de suministro | Nuevos perfiles: `pip==26.2` y `setuptools==84.1.0`, con hashes actualizados. Instalación CPU independiente y `pip-audit` sin avisos conocidos. Los entornos y RC1 históricos permanecen sin actualizar. |
| `tqdm` ausente en CPU | Media, importación de entrenamiento y advertencia estática | Se añadió `tqdm==4.70.1`, versión ya usada, con hash del wheel universal. Se verificó la importación de `train_deep` sin entrenar. |
| Estados opcionales y contratos de tipos | Baja/media según ruta | Guardias de Rasterio, tareas EE sin `config`, `getInfo`, QSettings no textual, spec/loader, leyendas y etiquetas. Escritura GeoTIFF con argumentos explícitos; resultados numéricos de QA estrechados correctamente. |
| Máscara regional vacía | Baja, división por cero / producto inválido | El exportador rechaza una máscara vacía o incompatible antes de crear el TIFF. |
| Cuatro textos no traducidos | Baja, funcionalidad bilingüe | Catálogo TS/QM: Explore, Research, Dark y Light. Regresiones verifican traducción compilada y retorno al inglés. El selector de apariencia adapta su tamaño al cambiar idioma. |
| Cachés Matplotlib predecibles en validadores | Baja, temporales | Los validadores crean directorios exclusivos cuando no se proporciona `MPLCONFIGDIR`. |

El modelo de amenaza de los dos primeros hallazgos requiere influencia de otro usuario local sobre ubicaciones compartidas; no se identificó un servicio remoto expuesto. Una ruta existente con propietario y permisos adecuados limita la precreación. No se accedió a credenciales ni se ejecutó código atacante con cuentas reales.

## Integridad científica y equivalencia

### Cinco scripts previamente modificados

`scripts/audit_scientific_scripts.py` extrae las versiones originales del commit indicado a una carpeta nueva y ejecuta originales y actuales con las mismas entradas reales. Comparación exacta, sin ampliar tolerancias:

| Script | Entradas y resultado |
|---|---|
| `qa_grid.py` | 300 GeoTIFF NDVI: listas de incidencias y estadísticas idénticas. |
| `validate_data.py` | 300 GeoTIFF NDVI: resultados idénticos. |
| `validate_lst.py` | 300 GeoTIFF LST: resultados idénticos. |
| `sensitivity_regional.py` | 300 filas mensuales reales: tablas idénticas, incluidos umbrales y soporte estacional común. |
| `validate_independent.py` | 17 verificaciones históricas y tres series de píxel: agregación y regresión idénticas. |

No se sustituyeron observaciones ni se interpolaron faltantes. El auditor requiere Python sin `-O` para no desactivar sus aserciones.

### Motor estadístico y multivariable

Se ejecutó el validador científico con los cubos reales pequeños de Querétaro y exportaciones nuevas separadas:

- NPZ y Zarr coinciden exactamente en valores, máscaras y calendario.
- Pendiente, p, cambio, n, Theil–Sen y p HAC: diferencia máxima **0** frente al cálculo convencional.
- q BH y q HAC: diferencia máxima **2.220446049250313e-16**, dentro de las tolerancias originales del validador; no se modificaron.
- Series mensuales ponderadas por superficie coinciden con el cálculo convencional.
- Correlaciones Pearson/Spearman: diferencia máxima **0**; se comprobó la familia BH conjunta de mapas/desfases/anomalías. **3,149,060 pares observados** en la referencia de Querétaro.
- La validación histórica verificó **81 archivos** preservados en el registro científico utilizado. Además, los **35 hashes** del registro NDVI de consolidación coinciden al finalizar.
- Exportaciones científicas y predictivas nuevas incluyeron CSV, JSON, GeoTIFF y PNG; no sobrescribieron los originales.

Las pruebas conservan la separación de entrenamiento 2002–2018, validación 2019–2021 y prueba 2022–2025; historia de 12 meses y normalización ajustada solo con entrenamiento. La evaluación es un paso mensual con meses anteriores observados. No es validación de pronósticos recursivos largos.

Se contrastó la preparación de MOD13C1 con el [catálogo oficial de Earth Engine](https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13C1): sus factores ya están aplicados. Se mantuvo su escala, evitando introducir una conversión adicional incorrecta. Los productos MOD13Q1 y LST conservan sus conversiones existentes.

Las anomalías mantienen climatología documentada y soporte coincidente; la inferencia AR(1) es diagnóstica. Autocorrelación, faltantes estacionales, selección de cobertura y comparaciones múltiples limitan la inferencia. Una correlación no demuestra causalidad.

### Modelos y reproducción CPU/CUDA

No se entrenó ningún modelo. Métricas históricas de prueba, copiadas como referencia y conservadas:

| Variable / modelo | Observaciones comunes | MAE | RMSE | R² |
|---|---:|---:|---:|---:|
| NDVI / XGBoost | 489633 | 0.04217497 | 0.06352680 | 0.88443305 |
| NDVI / ConvLSTM | 489633 | 0.04437915 | 0.06360813 | 0.88413696 |
| LST / XGBoost | 507583 | 2.08755228 °C | 2.83070128 °C | 0.81942634 |
| LST / ConvLSTM | 507583 | 2.21107229 °C | 3.01232161 °C | 0.79551145 |

Reproducción de mapas retrospectivos de enero de 2026 contra los archivos existentes:

| Modelo | Píxeles | Diferencia máxima CPU | Tolerancia absoluta existente |
|---|---:|---:|---:|
| NDVI XGBoost | 11123 | 0 | 1e-6 |
| NDVI ConvLSTM | 11123 | 0.0003100634 | 1e-3 |
| LST XGBoost | 11095 | 0 | 1e-6 °C |
| LST ConvLSTM | 11095 | 0.0015830994 °C | 1e-2 °C |

Las máscaras coinciden exactamente. Se conservaron las tolerancias justificadas previamente por la referencia CUDA/TF32. Ambas ConvLSTM ejecutadas en la RTX 5070 reprodujeron su referencia con diferencia máxima **0**. XGBoost utiliza deliberadamente CPU en esta reproducción; no se afirma una prueba nueva de inferencia XGBoost CUDA.

Estas salidas son estimaciones de modelos, no nuevas observaciones satelitales. La reproducción también pasó desde las dos distribuciones nuevas y desde un ZIP extraído independientemente.

## Seguridad

- **Gitleaks:** nueva revisión de todas las referencias, 115 commits hasta el último ajuste CI, sin secretos detectados. También se escaneó el árbol local. El commit documental posterior se comprobó por separado antes de incorporarlo.
- **Dependencias:** la auditoría inicial reportó 17 registros de avisos en `pip 25.1.1` y `setuptools 78.1.0`, con duplicaciones de identificadores; no deben interpretarse como 17 vulnerabilidades distintas. El entorno CPU nuevo con herramientas corregidas presenta **cero avisos conocidos** en las consultas ejecutadas. La consulta directa omite `torch 2.14.1+cpu` porque PyPI no reconoce esa versión local; se ejecutó además una consulta estricta de la versión upstream `torch==2.14.1`, también sin avisos. Esto no audita de forma independiente diferencias del wheel CPU ni sus bibliotecas nativas.
- La actualización de setuptools incluye la corrección descrita en el [aviso del mantenedor](https://github.com/pypa/setuptools/security/advisories/GHSA-xmj3-9gf7-h52w). Esto no demuestra compatibilidad funcional con Windows.
- **Bandit:** no se introdujeron `nosec` ni exclusiones. El resultado final conserva avisos bajos de aserciones, subprocess con argumentos y semilla científica, y un aviso medio sobre XML. Este último lee el catálogo TS incluido en el código confiable; no se demostró entrada XML de un tercero que cruzara esa frontera. Véase la salida completa.
- Deserialización: se conserva `allow_pickle=False` y `torch.load(..., weights_only=True)`. Los comandos revisados usan listas de argumentos. Los lectores NPZ extraen miembros fijos, no rutas arbitrarias de archivo.
- SHA-256 detecta cambios respecto al manifiesto confiable; **no autentica al editor** si un atacante sustituye simultáneamente payload, manifiesto y sidecar.
- El flujo administrado de `codex-security:security-scan` falló al persistir el checkpoint: **`Scan output parent must not be group- or world-writable without the sticky bit.`** Se registró el fallo, sin cambiar permisos generales del usuario ni declarar generado un informe sellado. Las revisiones estáticas y regresiones del presente informe se realizaron independientemente.

No se certifica seguridad de bibliotecas nativas incorporadas en GDAL/Qt/CUDA a partir de `pip-audit`. Tampoco se considera segura una dependencia por ausencia de avisos en esa consulta.

## Rendimiento, interfaz y distribución

La comparación científica convencional, limitada a Querétaro, alcanzó aproximadamente **1.03 GiB de RSS**. Una ejecución medida tomó **40.87 s**. Incluye intérprete, bibliotecas, lectura y referencias completas para comparación; no representa el presupuesto de un bloque ni una carga planetaria completa.

La comprobación CUDA registró **32.25 MiB** de máximo de tensores asignados por PyTorch, excluyendo contexto/driver. Las inferencias ConvLSTM medidas tardaron aproximadamente 0.34 s NDVI y 0.15 s LST; no son un benchmark general ni incluyen instalación/carga integral de la interfaz.

Se comprobaron **81 ventanas** pequeñas de nueve entradas del catálogo Full: NPZ de Querétaro y siete almacenes Zarr. Se mantuvieron valores, máscaras y rangos, con un presupuesto de lectura de 8 MiB. El intento inicial con 1 MiB fue rechazado correctamente porque los chunks almacenados superaban el límite de decodificación. No se cargaron arreglos mundiales completos para esa comprobación.

Se ejecutaron pruebas de entrega Qt al hilo principal, respuesta del event loop, generaciones obsoletas, cancelación y destrucción del propietario. La validación real del escritorio recorrió las nueve pestañas, vistas predictivas/multivariables, mapas y diálogos en inglés y español, regresó al inglés y no registró errores Qt. También se ejecutó desde la copia Lite independiente con el Python instalado por el instalador.

Las capturas son renderizados Qt reales con `QT_QPA_PLATFORM=offscreen`, no diseños simulados: [inglés](evidence/desktop-en.png), [español](evidence/desktop-es.png). No equivalen a una campaña manual en un servidor gráfico físico.

Se generaron nuevas copias locales, sin sobrescribir RC1:

- Lite: dos combinaciones región/variable de Querétaro, en NPZ y Zarr, tres resultados frescos y cuatro modelos.
- Full: siete combinaciones región/variable; nueve entradas por coexistencia de NPZ/Zarr, doce resultados frescos y los mismos cuatro modelos de Querétaro. Precipitación mundial termina en septiembre de 2025.
- Diagnóstico, integridad y cuatro inferencias CPU aprobaron en ambas ediciones.
- Los ZIP históricos Lite/Full RC1 se extrajeron independientemente: coincidieron con sus sidecars y validaron 776 y 5424 archivos respectivamente. Permanecieron intactos.
- Un nuevo ZIP Lite también pasó extracción independiente, diagnóstico e inferencia sin Earth Engine ni credenciales.
- Instalación real en un entorno nuevo: hashes obligatorios, actualización de bootstrap, dependencias CPU, `pip check` y diagnóstico correctos. Dos intentos redundantes en `/tmp` fallaron con `Errno 122` por cuota pese al espacio mostrado; el intento en `/var/tmp` terminó correctamente. Solo se limpiaron entornos desechables creados por esta auditoría, conservando registros y originales.

El contenido empaquetado se verifica contra su manifiesto. Las fuentes científicas externas se seleccionan explícitamente y la procedencia portable se verifica por contenido. Los manifiestos científicos históricos con rutas antiguas se conservan byte a byte mediante la superposición existente.

## Validaciones e integración continua

| Comprobación ejecutada | Resultado |
|---|---|
| pytest inicial | 192 aprobadas, 28.24 s |
| pytest final con datos reales disponibles | **212 aprobadas**, 26.45 s en la ejecución registrada |
| Copia limpia de Git, CPU, sin datasets externos | **207 aprobadas, 5 omitidas**, 21.50 s |
| Pyright entorno científico / CPU | 0 errores, 0 advertencias, 0 informaciones |
| `compileall` | Correcto en Python 3.14.4 |
| `pip check` científico, Earth Engine y CPU nuevo | Sin requisitos rotos |
| `pip-audit` CPU nuevo | Sin avisos conocidos; omisión del wheel `+cpu` y consulta upstream separada documentadas |
| Gitleaks historial / árbol local | Sin secretos detectados |
| Equivalencia de cinco scripts | Exacta con las mismas entradas reales |
| Equivalencia estadística / multivariable | Dentro de tolerancias originales; resultados arriba |
| Distribución Lite/Full, modelos CPU, GUI bilingüe | Correctos en Linux |
| `git diff --check` | Correcto al cierre |

Las cinco pruebas externas no fueron eliminadas ni debilitadas. Su marcador permite separarlas en CI; la ejecución local completa las mantiene habilitadas y aprobadas.

`.github/workflows/validate.yml` configura Python 3.14.4 sin GPU, entorno CPU con hashes y entorno de auditoría separado, Pyright, pytest, `compileall`, `pip check`, `pip-audit`, Bandit y Gitleaks. CI rechaza omisiones inesperadas en la auditoría; la omisión conocida de Torch `+cpu` tiene consulta upstream separada y explícita. Las acciones se fijaron a commits, con permisos de lectura y sin persistir credenciales Git. El YAML y los pasos locales se comprobaron; **no se publicó ni ejecutó remotamente el workflow**. Las observaciones y modelos externos no se descargan automáticamente.

## Archivos y commits

El listado completo de cambios de código está en [modified-files.txt](evidence/modified-files.txt); los commits locales por propósito, en [local-commits.txt](evidence/local-commits.txt). A esto se añade `docs/audit/FINAL_TECHNICAL_AUDIT.md` y `docs/audit/evidence/` en el commit documental.

Los cambios principales corresponden a `array_cache.py`, `catalog.py`, `forecasting.py`, `distribution.py`, instalador/generador, scripts con diagnósticos, guardias de interfaz, catálogos TS/QM, validadores reproducibles, requisitos/bloqueos, CI y regresiones. Los motores de estadística y entrenamiento no se modificaron.

Las evidencias pequeñas incluidas son resultados reales. Se anonimizaron únicamente rutas personales en sus representaciones diagnósticas; no se alteraron cifras. Los datasets, modelos, ZIP y salidas científicas completas permanecen fuera de Git.

## Límites y riesgos pendientes

1. **Entornos y RC1 históricos:** conservan las versiones antiguas de herramientas con avisos conocidos. No se modificaron. Las instalaciones nuevas deben usar los bloqueos corregidos; la comprobación de compatibilidad no convierte esos entornos antiguos en libres de vulnerabilidades.
2. **Windows:** no ejecutado. Las recetas/hashes preparados no son evidencia de funcionamiento nativo.
3. **NVIDIA limpio:** no se instaló desde cero el perfil NVIDIA; su lock sigue sin hashes completos. La prueba CUDA se realizó en el entorno existente. No se afirma portabilidad a otra GPU/driver.
4. **Cobertura científica:** las ventanas nacionales/globales validan infraestructura, no totalidad de cobertura, QA o conclusiones. No se volvió a adquirir el histórico ni se validó cada observación remota. No se afirma que México o el mundo estén completos.
5. **Seguridad administrada:** no hay reporte sellado del plugin debido al bloqueo indicado. Gitleaks, análisis de dependencias, revisión estática y regresiones sí tienen evidencias independientes.
6. **Entorno adicional no utilizado:** la inspección detectó `python-debian` sin `charset-normalizer` en un entorno de consolidación ajeno a los tres necesarios. Se dejó sin modificar; el criterio de compatibilidad aprobado corresponde a los entornos efectivamente usados y al nuevo perfil CPU.
7. **Disponibilidad:** los presupuestos protegen arrays/chunks, no todo el RSS de intérprete, bibliotecas, parsers nativos o respuestas HTTP de adquisición. Los descargadores todavía leen respuestas en memoria; no se midió adquisición planetaria interactiva.
8. **Caché:** comprobar hashes añade E/S, especialmente en NPZ grande. Se prioriza integridad; Zarr sigue siendo la opción por bloques. Un usuario que controla código, manifiestos y archivos de su propia cuenta permanece dentro de la frontera de confianza.
9. **Cifras de rendimiento:** son mediciones locales puntuales; no hay benchmark continental/global completo ni garantía sobre hardware mínimo.

## Reproducción

Ejecutar desde la rama de consolidación. Definir rutas de entornos ya existentes y una raíz científica histórica de solo lectura; ninguno de estos valores se incorpora al repositorio:

```bash
export DEV_PYTHON=/ruta/al/entorno/cientifico/bin/python
export CPU_PYTHON=/ruta/al/entorno/cpu-independiente/bin/python
export AUDIT_TOOLS=/ruta/al/entorno/de/auditoria/bin
export SCIENCE_ROOT=/ruta/al/checkout/con/entradas-y-resultados-historicos
export AUDIT_TMP="$(mktemp -d -p /var/tmp aurora-audit.XXXXXXXX)"
export QT_QPA_PLATFORM=offscreen
export PYTHONPATH=src
export MPLCONFIGDIR="$AUDIT_TMP/matplotlib"

"$DEV_PYTHON" -m pyright --project pyrightconfig.local.json --pythonpath "$DEV_PYTHON"
"$DEV_PYTHON" -m pyright --project pyrightconfig.local.json --pythonpath "$CPU_PYTHON"
"$DEV_PYTHON" -m pytest -q
"$DEV_PYTHON" -m compileall -q src scripts tests
"$DEV_PYTHON" -m pip check
"$CPU_PYTHON" -m pip check
git diff --check

gitleaks detect --source . --log-opts=--all --redact --no-banner
gitleaks detect --source . --no-git --redact --no-banner
"$AUDIT_TOOLS/pip-audit" --path /ruta/al/entorno/cpu-independiente/lib/python3.14/site-packages
"$AUDIT_TOOLS/pip-audit" --strict --no-deps --disable-pip -r requirements/locks/torch-advisory.txt
"$AUDIT_TOOLS/bandit" -r src scripts -lll

"$DEV_PYTHON" scripts/audit_scientific_scripts.py \
  --baseline 96e7bca --scientific-root "$SCIENCE_ROOT" --output "$AUDIT_TMP/five-scripts"
"$CPU_PYTHON" scripts/validate_global_engine.py --scientific-only \
  --data-root "$SCIENCE_ROOT" --output "$AUDIT_TMP/science"
"$CPU_PYTHON" scripts/validate_distribution_inference.py --root "$SCIENCE_ROOT" \
  --require-cpu-build --output "$AUDIT_TMP/inference.json"
"$CPU_PYTHON" scripts/validate_i18n.py --output "$AUDIT_TMP/desktop"

"$DEV_PYTHON" scripts/build_distribution.py --edition lite --source-root "$SCIENCE_ROOT" \
  --output "$AUDIT_TMP/lite" --archive "$AUDIT_TMP/lite.zip"
"$DEV_PYTHON" scripts/build_distribution.py --edition full --source-root "$SCIENCE_ROOT" \
  --output "$AUDIT_TMP/full"
"$DEV_PYTHON" "$AUDIT_TMP/lite/scripts/install.py" --profile cpu --prefix "$AUDIT_TMP/new-cpu"
"$AUDIT_TMP/new-cpu/bin/python" "$AUDIT_TMP/lite/scripts/doctor.py" --device cpu
```

El entorno CPU reproducible se instala con `requirements/locks/installer-bootstrap.txt` y `linux-cpu-hashed.txt`; las herramientas separadas con `requirements/locks/audit-tools.txt`. Véanse los comandos exactos de CI y [clean-installer.txt](evidence/clean-installer.txt). No se debe reutilizar un destino de instalación existente ni ejecutar validadores con `-O`.

La copia limpia se obtuvo mediante `git archive` del código validado, extrayéndolo con el filtro seguro `data` en un directorio nuevo y ejecutando pytest allí con el entorno CPU. Carece intencionalmente de los recursos externos ignorados, de ahí las cinco omisiones documentadas.
