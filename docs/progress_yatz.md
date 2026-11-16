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
