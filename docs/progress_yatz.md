# Progreso Yatz: ingeniería de datos

Rama: `feature/data-validation`

## Hecho
- Región de Querétaro: `config/region.geojson` (FAO/GAUL_SIMPLIFIED_500m/2015/level1).
- Script de exportación: `scripts/export_ndvi.py` (commit 22dc7b9).
- Lote histórico 2001-01 a 2025-12 exportado (300 meses), extraído el 14 de noviembre de 2026.
- Validación: `scripts/validate_data.py`, 300 archivos, 0 errores. Resultado en `docs/evidence/data/qa_report.csv`.
- Pruebas: `tests/test_data.py`, 11 pruebas en verde.
- Revisión visual parcial contra Earth Engine (ver sección más abajo).

## Comandos usados
    python scripts/export_ndvi.py --project quantum-yen-514718-s4 --start 2001-01 --end 2025-12   (ejecutado por tramos)
    python scripts/make_manifest.py
    python scripts/validate_data.py --start 2001-01 --end 2025-12
    python -m pytest tests/test_data.py -q

## Resultados
- Tamaño: aproximadamente 43 KB por mes.
- Validación final: 300 archivos, 0 errores, 10 meses a revisar (cobertura < 70 %).

## Meses a revisar (cobertura < 70 % dentro del estado)
Se conservan en el manifest. La decisión de cómo tratarlos corresponde a Ian.
- 2002-09 (0.66), 2003-08 (0.61), 2004-08 (0.69), 2006-08 (0.55), 2007-08 (0.48)
- 2009-10 (0.43), 2018-06 (0.54), 2018-10 (0.53), 2019-10 (0.46), 2025-06 (0.32)
Todos caen entre junio y octubre. Hipótesis (sin comprobar): nubosidad en temporada de lluvias.

## Limitaciones
- El límite viene de FAO GAUL (2015, simplificado a 500 m), no del INEGI.
- `valid_fraction` se calcula solo sobre píxeles dentro de la región.
- En `grid.json`, `transform` va en orden Affine (a, b, c, d, e, f).
- Mi entorno usa Python 3.14; el plan pide 3.11 o 3.12.
- `scripts/make_manifest.py` no figura en la lista de archivos propios del plan.

## Revisión visual (14 de noviembre de 2026)
Comparación de medias de NDVI sobre la región entre Earth Engine (mismo filtro:
SummaryQA == 0, mediana mensual, factor 0.0001) y los TIFF locales:
- 2001-01: 0.3869 (EE) vs 0.3866 (local)
- 2003-08: 0.5601 (EE) vs 0.5802 (local); diferencia de 0.02, mes con cobertura de 61 %
  (hipótesis, sin comprobar: distinto promedio al agregar a 1000 m con datos parciales)
- 2025-12: 0.5129 (EE) vs 0.5093 (local)
Patrón espacial de 2001-01 coincide (norte/noreste verde, suroeste con valores bajos).
Figura local: docs/evidence/data/visual_check_local.png.
Limitación: la comprobación usa la misma lógica de filtrado que la exportación, así que
verifica consistencia, no independencia.
Pendiente: comparar en Earth Engine el patrón espacial de 2003-08 y 2025-12 (solo se vio 2001-01).

## Pendientes y bloqueos
- Confirmar que Ian y Sofía abren el paquete completo de Drive.
- Abrir el PR borrador hacia `main` para revisión de Ian.

# Documentación: Validación y publicación de datos de México

## 1. Objetivo

Documentar el estado de procesamiento de los datos correspondientes a México, verificar la cobertura mensual, identificar los meses que presentan una cobertura inferior al 70 % y registrar la publicación del archivo ZIP que contiene los resultados.

También se establecen criterios para controlar los archivos que serán incluidos en el repositorio de GitHub, evitando subir archivos geoespaciales pesados o información intermedia que no forma parte de la documentación final.

## 2. Estado de los datos de México

Se debe registrar el estado real de procesamiento de México, considerando la disponibilidad de información y la cobertura obtenida para cada mes.

La evaluación permitirá identificar si los datos disponibles son suficientes para realizar los análisis correspondientes.

**Estado general de México:**

- Región analizada: México.
- Cobertura mínima de referencia: 70 %.
- Evaluación: cobertura mensual de los datos procesados.
- Resultado: pendiente de registrar con los valores obtenidos en la ejecución final.

## 3. Cobertura mensual

Se utilizará un umbral del 70 % para identificar los meses que presentan una cobertura insuficiente.

Los meses que no alcancen este porcentaje deberán quedar identificados para su revisión.

| Mes | Cobertura (%) | Estado |
|---|---:|---|
| Enero | Por verificar | Por determinar |
| Febrero | Por verificar | Por determinar |
| Marzo | Por verificar | Por determinar |
| Abril | Por verificar | Por determinar |
| Mayo | Por verificar | Por determinar |
| Junio | Por verificar | Por determinar |
| Julio | Por verificar | Por determinar |
| Agosto | Por verificar | Por determinar |
| Septiembre | Por verificar | Por determinar |
| Octubre | Por verificar | Por determinar |
| Noviembre | Por verificar | Por determinar |
| Diciembre | Por verificar | Por determinar |

### Criterios de clasificación

- **Cobertura igual o superior al 70 %:** mes que cumple con el umbral establecido.
- **Cobertura inferior al 70 %:** mes que requiere revisión por disponibilidad insuficiente de información.

Los porcentajes definitivos deben obtenerse de los resultados reales del procesamiento y no estimarse manualmente.

## 4. Archivo ZIP de resultados

Los resultados correspondientes a México se organizarán en un archivo comprimido ZIP para facilitar su distribución y descarga.

Se deberá registrar la siguiente información:

| Característica | Información |
|---|---|
| Archivo | Nombre del ZIP generado |
| Región | México |
| Formato | ZIP |
| Integridad | Verificada mediante SHA-256 |
| Hash SHA-256 | Pendiente de registrar |
| Enlace de descarga | Pendiente de registrar |

### 4.1 Verificación de integridad

Para garantizar que el archivo no haya sufrido modificaciones, se utilizará el algoritmo SHA-256.

El hash permitirá comprobar que el archivo descargado corresponde exactamente al archivo publicado.

Comando para generar el hash:

```bash
sha256sum nombre_del_archivo.zip
```

El resultado deberá conservarse en la documentación para futuras verificaciones.

### 4.2 Enlace de descarga

Se deberá incorporar el enlace directo al archivo ZIP publicado, preferentemente mediante GitHub Releases o el almacenamiento definido para el proyecto.

**Enlace:** Pendiente de registrar.

## 5. Control de archivos para GitHub

Antes de realizar el commit, se debe verificar que únicamente se encuentren preparados los archivos correspondientes a la documentación y publicación de resultados.

No deben incluirse archivos TIFF ni directorios de datos intermedios.

### 5.1 Archivos que deben excluirse

Se deben evitar archivos como:

- Imágenes TIFF.
- Archivos temporales de procesamiento.
- Resultados intermedios del directorio `data/`.
- Archivos geoespaciales globales que no formen parte de la entrega.
- Archivos auxiliares que no sean necesarios para reproducir o documentar el proyecto.

También se debe revisar especialmente que no aparezcan entre los archivos preparados:

```text
grid_global_50km.json
config/region_global.geojson
```

Si aparecen, se debe verificar si corresponden a archivos que no deben formar parte de esta publicación y retirarlos del área de preparación cuando corresponda.

### 5.2 Verificación de archivos preparados

Antes de confirmar el commit se ejecutará:

```bash
git diff --cached --stat
```

Este comando permite revisar un resumen de los archivos que se encuentran preparados para el siguiente commit.

**Criterio de aceptación:**

El resultado debe mostrar únicamente los archivos correspondientes a esta entrega, sin imágenes TIFF, archivos del directorio `data/` ni archivos globales ajenos a la publicación.

Si aparecen archivos que no corresponden, deberán retirarse del área de preparación antes de continuar.

## 6. Criterios de aceptación

La publicación se considerará correctamente preparada cuando se cumplan los siguientes puntos:

1. Se encuentre documentado el estado real de México.
2. Se identifiquen los meses cuya cobertura sea inferior al 70 %.
3. Se registre el porcentaje de cobertura de cada mes.
4. Se genere el archivo ZIP correspondiente a México.
5. Se calcule y registre el hash SHA-256 del archivo.
6. Se incorpore el enlace de descarga.
7. Se verifique que no existan archivos TIFF ni contenido innecesario de `data/` entre los archivos preparados.
8. Se compruebe que `grid_global_50km.json` y `config/region_global.geojson` no aparezcan indebidamente entre los archivos pendientes de publicación.
9. Se confirme que `git diff --cached --stat` muestre exclusivamente los archivos correspondientes a esta entrega.

## 7. Resultado esperado

Al finalizar, se contará con una publicación documentada de los datos de México que incluya el estado de procesamiento, la cobertura mensual, la identificación de los meses con cobertura inferior al 70 %, el archivo ZIP, su hash de integridad y su enlace de descarga.

Esto permitirá mantener un registro verificable de los resultados y facilitar su consulta y distribución desde GitHub.

# AURORA EARTH MODEL
## Documentación técnica: Adquisición, procesamiento y validación de datos históricos de México

**Proyecto:** AURORA Earth Model  
**Participación:** NASA Space Apps Challenge  
**Área de trabajo:** Adquisición, procesamiento y validación de datos geoespaciales  
**Responsable:** Yatzury Garcidueñas  
**Periodo de datos:** Enero de 2001 – Diciembre de 2025  
**Región de estudio:** México  

---

# 1. Introducción

AURORA Earth Model es un proyecto enfocado en el análisis de información ambiental mediante datos geoespaciales e históricos, con el propósito de contribuir al estudio de las condiciones ambientales de la Tierra.

Dentro del desarrollo del proyecto se realizó un proceso de adquisición, organización y validación de datos históricos correspondientes al territorio mexicano. El trabajo se concentró en dos variables ambientales principales:

- NDVI (Normalized Difference Vegetation Index): índice de vegetación de diferencia normalizada.
- LST (Land Surface Temperature): temperatura de la superficie terrestre.

El objetivo fue preparar una serie histórica mensual de ambas variables, manteniendo una estructura geoespacial uniforme que permitiera su integración posterior con los componentes globales del proyecto.

# 2. Objetivo general

Obtener, organizar y documentar datos históricos mensuales de NDVI y LST correspondientes a México, utilizando una cuadrícula geoespacial de referencia y procedimientos de control de calidad que permitan verificar la consistencia espacial, temporal y numérica de los archivos generados.

## 2.1 Objetivos específicos

- Obtener información histórica de NDVI y LST para el periodo 2001–2025.
- Establecer una cuadrícula geoespacial uniforme para México.
- Procesar los datos mediante scripts desarrollados en Python.
- Mantener la correspondencia temporal de los registros mensuales.
- Validar la estructura y características de los archivos raster.
- Identificar meses faltantes y posibles anomalías.
- Documentar los resultados mediante manifiestos y reportes.
- Preparar un paquete de datos para compartir con el equipo de desarrollo.
- Publicar los scripts, configuraciones y documentación ligera en GitHub.

# 3. Alcance del trabajo

El trabajo se concentró en la preparación de información ambiental histórica de México.

Se estableció como periodo objetivo enero de 2001 a diciembre de 2025.

Esto representa:

- 25 años de información.
- 12 meses por año.
- 300 registros mensuales esperados de NDVI.
- 300 registros mensuales esperados de LST.
- 600 archivos raster esperados en total.

La cantidad anterior representa el objetivo de adquisición y no debe confundirse con el número de archivos cuya descarga final ya fue verificada.

El trabajo de procesamiento global y la generación de la máscara terrestre mundial corresponden a otras responsabilidades dentro del equipo, particularmente a Ian.

# 4. Configuración geoespacial

Para garantizar que todos los archivos de México compartieran las mismas características espaciales, se utilizó una cuadrícula de referencia.

## 4.1 Sistema de referencia de coordenadas

- Sistema de referencia: EPSG:6933.
- Tipo: proyección equivalente de área.
- Resolución espacial: 5,000 metros.
- Columnas: 426.
- Filas: 612.
- Valor NoData: -9999.

La cuadrícula permite que los archivos mensuales tengan una estructura espacial consistente y puedan compararse entre diferentes fechas.

## 4.2 Región de estudio

Se utilizó el archivo:

`config/region_mexico.geojson`

Este archivo define la región geográfica de México y se utiliza como referencia para delimitar el análisis territorial.

La región se rasteriza sobre la cuadrícula nacional, permitiendo distinguir las celdas que pertenecen al área de estudio de aquellas que quedan fuera de ella.

# 5. Variables ambientales

## 5.1 NDVI

El NDVI es un indicador utilizado para estudiar la presencia y comportamiento de la vegetación mediante información obtenida por sensores satelitales.

Sus valores permiten analizar cambios en la cobertura vegetal y observar variaciones ambientales a lo largo del tiempo.

Para este proyecto se estableció como rango de revisión:

- Valor mínimo: -0.2.
- Valor máximo: 1.0.
- Unidad: adimensional.

Los valores fuera de este intervalo deben identificarse durante la validación para determinar si representan anomalías o problemas en los datos.

## 5.2 LST

La temperatura de la superficie terrestre permite estudiar las variaciones térmicas de la superficie y su comportamiento a través del tiempo.

En AURORA se trabaja con LST diurna expresada en grados Celsius.

Se estableció el siguiente intervalo de revisión:

- Valor mínimo de referencia: -90 °C.
- Valor máximo de referencia: 80 °C.
- Unidad: grados Celsius.

Los valores fuera de este intervalo se consideran alertas que requieren revisión. No deben modificarse ni recortarse automáticamente sin una justificación técnica.

# 6. Adquisición y procesamiento de datos

La adquisición se realizó mediante Google Earth Engine, utilizando scripts desarrollados en Python.

El procesamiento se ejecutó desde el repositorio local del proyecto:

`/home/yatzury/aurora-earth-model`

El script principal utilizado fue:

`scripts/export_grid.py`

## 6.1 Configuración de exportación

Se utilizó el proyecto de Google Earth Engine:

`quantum-yen-514718-s4`

Los parámetros de ejecución incluyeron:

- Proyecto de Google Earth Engine.
- Variable ambiental.
- Cuadrícula de México.
- Archivo GeoJSON de delimitación regional.
- Fecha inicial.
- Fecha final.
- Directorio de salida.

## 6.2 Procesamiento por bloques temporales

Para organizar la adquisición histórica, el periodo se dividió en bloques de cinco años.

Los bloques considerados fueron:

| Bloque | Periodo |
|---|---|
| 1 | 2001–2005 |
| 2 | 2006–2010 |
| 3 | 2011–2015 |
| 4 | 2016–2020 |
| 5 | 2021–2025 |

Esta división permitió ejecutar diferentes procesos de exportación y consultar sus registros de actividad mediante archivos de log.

## 6.3 Directorios de salida

Los datos se organizaron en:

`data/mexico/ndvi/`

`data/mexico/lst/`

Los archivos raster se identifican mediante nombres asociados a la variable y al periodo correspondiente.

Ejemplos de nomenclatura:

`ndvi_2001_01.tif`

`lst_day_2001_01.tif`

La nomenclatura permite identificar la variable, el año y el mes de cada archivo.

# 7. Seguimiento de exportaciones

Para supervisar los procesos se generaron archivos de registro (logs).

Los registros se almacenaron en:

`~/logs_aurora/`

Entre ellos se encuentran:

- mx_ndvi_2001.log
- mx_ndvi_2006.log
- mx_ndvi_2011.log
- mx_ndvi_2016.log
- mx_ndvi_2021.log
- mx_lst_2001.log
- mx_lst_2006.log
- mx_lst_2011.log
- mx_lst_2016.log
- mx_lst_2021.log

Estos archivos permiten consultar el avance de las exportaciones, identificar archivos guardados y localizar errores durante la descarga.

## 7.1 Manejo de errores

Durante el procesamiento se identificó un error HTTP 503 relacionado con la capacidad de memoria de Google Earth Engine:

`Earth Engine memory capacity exceeded`

Este error se registró durante una ejecución del bloque LST correspondiente a 2011–2015.

Se consideró necesario revisar los meses afectados y recuperar exclusivamente los registros faltantes, manteniendo la misma configuración de procesamiento.

No se debe asumir que un error de exportación implica que todo el bloque histórico falló.

# 8. Validación y control de calidad

La validación tiene como finalidad comprobar que los archivos generados mantengan las características necesarias para integrarse correctamente al modelo.

Se establecieron revisiones espaciales, estructurales, temporales y numéricas.

## 8.1 Validación espacial

Cada archivo raster debe cumplir con:

- CRS: EPSG:6933.
- Resolución: 5 km.
- Dimensiones: 426 × 612.
- Una sola banda.
- Tipo de dato: float32.
- NoData: -9999.

También debe conservar la transformación geoespacial correspondiente a la cuadrícula de referencia.

## 8.2 Validación temporal

Se estableció un calendario esperado de 300 meses por variable.

La validación debe comprobar:

- Que cada mes tenga un registro.
- Que no existan fechas duplicadas.
- Que los archivos correspondan al periodo esperado.
- Que los meses faltantes queden identificados.
- Que los nombres de archivo coincidan con los registros del manifiesto.

No se deben inventar valores para completar meses faltantes.

## 8.3 Validación de valores

Para NDVI se revisa el intervalo de -0.2 a 1.0.

Para LST se utiliza el intervalo de -90 °C a 80 °C como referencia de revisión.

Los valores fuera de estos intervalos deben registrarse para su análisis.

No se deben modificar silenciosamente los valores originales.

## 8.4 Validación de cobertura

La cobertura se calcula considerando únicamente las celdas válidas que se encuentran dentro de la máscara regional de México.

La fórmula utilizada es:

Cobertura = Celdas válidas dentro de México / Total de celdas de la región de México

Se estableció que una cobertura inferior al 70 % debe generar una alerta de revisión.

Esto no significa que el archivo deba rechazarse automáticamente, sino que debe analizarse y documentarse.

También se deben registrar las celdas válidas que se encuentren fuera de la región de estudio.

# 9. Manifiestos y organización de metadatos

Los manifiestos permiten mantener un registro de los archivos generados y facilitan la trazabilidad de la información.

Se identificaron los siguientes archivos:

- manifest_mexico_ndvi.csv
- manifest_mexico_lst.csv

Los manifiestos permiten documentar la información relacionada con las exportaciones de cada variable.

Entre los elementos que deben conservarse se encuentran:

- Fecha correspondiente al registro.
- Nombre del archivo.
- Ruta del archivo.
- Variable ambiental.
- Estado de exportación.
- Información de cobertura disponible.
- Metadatos asociados al procesamiento.

Los manifiestos son importantes para identificar los archivos disponibles y detectar posibles inconsistencias entre el calendario esperado y los datos obtenidos.

# 10. Scripts desarrollados y documentación técnica

Dentro del repositorio se trabajó con scripts y archivos de documentación para organizar y validar la información.

Entre los archivos identificados se encuentran:

| Archivo | Función |
|---|---|
| scripts/export_grid.py | Adquisición y exportación de datos geoespaciales. |
| scripts/cobertura_mes.py | Análisis de cobertura mensual. |
| grid_mexico.json | Configuración de la cuadrícula nacional. |
| config/region_mexico.geojson | Delimitación geográfica de México. |
| manifest_mexico_ndvi.csv | Registro de exportaciones NDVI. |
| manifest_mexico_lst.csv | Registro de exportaciones LST. |
| docs/evidence/data/missing_months.csv | Registro de meses faltantes. |
| docs/evidence/data/validation_report.md | Reporte de validación. |

Estos archivos permiten documentar el procedimiento y facilitar su revisión por los demás integrantes del equipo.

# 11. Organización y entrega de información

Se estableció una separación entre los archivos destinados al repositorio GitHub y los archivos de datos pesados.

## 11.1 Archivos destinados a GitHub

Se consideraron para publicación:

- Scripts de procesamiento.
- Configuraciones geoespaciales.
- Manifiestos.
- Reportes de validación.
- Documentación.
- Evidencias ligeras.

## 11.2 Archivos destinados a la entrega compartida

Los archivos raster históricos deben compartirse mediante un paquete comprimido, debido a su tamaño.

La estructura de entrega propuesta contempla:

AURORA_Mexico_Ian.zip

Contenido:

- Datos históricos NDVI.
- Datos históricos LST.
- Cuadrícula de México.
- Archivo de delimitación regional.
- Manifiestos.
- Parámetros de exportación.
- Evidencias de validación.

Se contempla utilizar una huella SHA-256 para comprobar la integridad del paquete después de su transferencia.

La entrega debe almacenarse en la carpeta compartida del equipo y comunicarse a Ian.

# 12. Publicación en GitHub

El trabajo de documentación y validación se integró al repositorio:

https://github.com/nekoscript-exe/aurora-earth-model

Se trabajó sobre la rama:

`feature/data-validation`

Durante la publicación se identificó que el repositorio remoto contenía cambios que todavía no estaban presentes en la copia local.

Para evitar sobrescribir el trabajo de otros integrantes se realizó una actualización mediante:

`git fetch origin`

Posteriormente se integraron los cambios remotos con:

`git pull --rebase origin feature/data-validation`

Finalmente, los cambios se publicaron correctamente con:

`git push -u origin feature/data-validation`

## 12.1 Confirmación de publicación

La operación de GitHub terminó correctamente.

Referencia de actualización remota:

`f0b4ade..40576fb`

Commit local inicial:

`e6c956f`

Commit actualizado después de integrar los cambios remotos:

`40576fb`

La rama quedó configurada para realizar seguimiento de:

`origin/feature/data-validation`

Esto confirma que la publicación de los cambios locales en la rama compartida fue exitosa.

# 13. Resultados y estado del trabajo

Como resultado del trabajo se cuenta con:

- Una configuración geoespacial definida para México.
- Un procedimiento de exportación mediante Python y Google Earth Engine.
- Organización de los datos NDVI y LST por directorios.
- Registros de ejecución para supervisar las exportaciones.
- Manifiestos independientes por variable.
- Un registro de meses faltantes.
- Un reporte de validación.
- Un script de análisis de cobertura mensual.
- Documentación incorporada al repositorio del proyecto.
- Publicación exitosa de los cambios en GitHub.

Durante el seguimiento de los archivos se contabilizaron 476 archivos raster en un corte intermedio del procesamiento. Esta cifra no debe interpretarse como el conteo definitivo de la entrega, ya que las exportaciones todavía requerían una comprobación final por variable.

También se identificó un error de capacidad de memoria durante una ejecución de LST, por lo que se requiere revisar los meses correspondientes antes de certificar la serie completa.

# 14. Pendientes de verificación y cierre

Para considerar terminada la entrega histórica de México se deben completar las siguientes comprobaciones:

1. Confirmar que NDVI tenga 300 archivos mensuales.
2. Confirmar que LST tenga 300 archivos mensuales.
3. Comparar los archivos físicos con sus respectivos manifiestos.
4. Revisar los meses faltantes y los errores de exportación.
5. Ejecutar la validación final de todos los archivos.
6. Confirmar la estructura del paquete ZIP.
7. Generar y verificar la huella SHA-256.
8. Compartir el paquete con Ian mediante la carpeta de Drive del equipo.
9. Comunicar el enlace y el hash del archivo entregado.

Estas comprobaciones permiten garantizar que la entrega sea reproducible y que los demás integrantes puedan utilizar los datos conociendo su procedencia y sus limitaciones.

# 15. Conclusión

El trabajo realizado para AURORA Earth Model permitió establecer una estructura de adquisición, organización y validación de información ambiental histórica correspondiente a México.

Mediante el uso de Python, Google Earth Engine y herramientas de procesamiento geoespacial se preparó un procedimiento para trabajar con las variables NDVI y LST, utilizando una cuadrícula de referencia uniforme y un periodo histórico de 25 años.

Además de la adquisición de datos, se trabajó en la trazabilidad de las exportaciones, la identificación de meses faltantes, el análisis de cobertura y la documentación de los resultados.

La publicación de los cambios en GitHub permitió integrar los avances de documentación y validación al repositorio compartido del equipo, conservando la separación entre los archivos ligeros de desarrollo y los datos raster de mayor tamaño.

Este trabajo constituye una parte importante de la preparación de los datos nacionales para su posterior integración con los componentes globales de AURORA Earth Model.
