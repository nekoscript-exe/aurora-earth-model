# AURORA — Earth System Intelligence Model
NASA Space Apps Challenge 2026 | Ian & Yatz

Entorno de investigación con observaciones satelitales reales: tendencias espaciales, predicción NDVI/LST y análisis multivariado. El estado actual, los resultados y los límites de validación se documentan en el informe AURORA 5.0 al final de esta página.

## Trabajo en equipo
- main: integración revisada; no subir trabajo directo.
- feature/data-validation: Yatz; extracción MODIS, QA, fuentes, figuras.
- feature/model-core: Ian; cubo, regresión, significancia, XGBoost y ConvLSTM.
- Abrir PR hacia main, no fusionar hasta revisión conjunta. No force push.

## Inicio inmediato — Yatz
```bash
git clone https://github.com/nekoscript-exe/aurora-earth-model.git
cd aurora-earth-model
git switch feature/data-validation
```
Leer docs/data-contract.md. Configurar Python 3.11/3.12, Earth Engine y proyecto Cloud propio. Exportar tres meses de prueba antes de lotes. Subir scripts, manifest, metadatos y QA ligero; entregar TIFF por almacenamiento compartido. Si no hay acceso GitHub, trabajar localmente hasta aceptar invitación.

## Archivos previstos
- config/region.geojson, scripts/export_ndvi.py, scripts/validate_data.py, scripts/plot_results.py, tests/test_data.py, docs/data_sources.md, requirements-data.txt: Yatz.
- scripts/build_cube.py, scripts/train_baseline.py, scripts/train_xgb.py, scripts/train_deep.py, scripts/evaluate.py, src/aurora/, tests/test_trend.py, requirements-model.txt: Ian.
- data/raw, data/processed, checkpoints: locales, no subir datos pesados ni credenciales.

## Prioridad
1. Tendencias reales NDVI, significancia corregida, cobertura.
2. Baselines predictivos y XGBoost con split temporal.
3. ConvLSTM si tiempo y validación lo permiten.

Fuente: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1

## AURORA 5.0 — desarrollo local

En `feature/model-core` hay predicción LST con XGBoost/ConvLSTM y tres referencias,
selector mensual compartido, Multivariate Laboratory para NDVI/LST y catálogo
local con lectura por ventanas. Los productos científicos existentes de NDVI se
conservan. Hay 90 pruebas aprobadas en Python 3.14.4 / PySide6.

Consultar [el informe de implementación, resultados y reproducción](docs/aurora5-report.md).
Las estimaciones de enero de 2026 son retrospectivas y no observaciones verificadas.
México sigue sujeto a disponibilidad de datos; la validación posterior del backend Zarr se documenta a continuación.

## Global Intelligence Engine — validación local

Lectura parcial NPZ/NPY/Zarr, estadística por bloques, catálogo configurable,
trabajos cancelables y exportaciones CSV/JSON/GeoTIFF/PNG. Instalar las extensiones
con `.venv/bin/python -m pip install -r requirements-global.txt`.
La suite conserva las 90 pruebas anteriores y pasa 113 pruebas en total.
Zarr está validado con observaciones reales de Querétaro; México a 5 km y la
cobertura mundial a 50–100 km siguen pendientes de datos reales.
Consultar el [informe, comandos, rendimiento y limitaciones](docs/global-intelligence-engine-report.md).
