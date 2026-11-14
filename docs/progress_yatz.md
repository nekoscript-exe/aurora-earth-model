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
