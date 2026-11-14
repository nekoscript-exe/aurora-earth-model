# AURORA — Earth System Intelligence Model
NASA Space Apps Challenge 2026 | Ian & Yatz

Modelo de regresión con imágenes satelitales: tendencias espaciales, magnitud y significancia; predicción NDVI opcional. No es un dashboard. Estado: inicialización, sin resultados científicos todavía.

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
