# Progreso Yatz: ingeniería de datos

Rama: `feature/data-validation`

## Hecho
- Región de Querétaro: `config/region.geojson` (FAO/GAUL_SIMPLIFIED_500m/2015/level1).
- Script de exportación: `scripts/export_ndvi.py` (commit 22dc7b9).
- Muestras exportadas: 2001-01 a 2001-03, extraídas el 14 de noviembre de 2026.
- Validación: `scripts/validate_data.py`, resultado en `docs/evidence/data/qa_report.csv`.
- Pruebas: `tests/test_data.py`, 11 pruebas en verde.

## Comandos usados
    python scripts/export_ndvi.py --project quantum-yen-514718-s4 --start 2001-01 --end 2001-03
    python scripts/make_manifest.py
    python scripts/validate_data.py --start 2001-01 --end 2001-03
    python -m pytest tests/test_data.py -q

## Resultados
- Tamaño: aproximadamente 43 KB por mes.
- Cobertura dentro del estado: 99.6 % a 99.8 % en las tres muestras.

## Limitaciones
- El límite viene de FAO GAUL (2015, simplificado a 500 m), no del INEGI.
- `valid_fraction` se calcula solo sobre píxeles dentro de la región.
- En `grid.json`, `transform` va en orden Affine (a, b, c, d, e, f).
- Mi entorno usa Python 3.14; el plan pide 3.11 o 3.12.

## Pendientes y bloqueos
- Confirmar que Ian y Sofía abren el paquete de Drive.
- Revisión visual de tres fechas en Earth Engine.
- Lote histórico 2001–2025 por tramos.
