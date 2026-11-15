# Bitácora de Sophia — AURORA 

## Registro

### Nov 14, 2026; 4:36 PM
**Hecho**
- Instalé Git, VS Code y Python.
- Cloné el repositorio y me cambié a `feature/science-validation`.
- Creé el entorno virtual e instalé rasterio, numpy, pandas, scipy, matplotlib y pytest.

**Siguiente paso**
- Investigación (glosario y reglas oficiales) y `scripts/plot_results.py` con pruebas.

**Bloqueos**
- De momento no encontramos bloqueos

**Comandos usados:** `git clone ...`, `git switch feature/science-validation`, `python -m pip install ...`

### Nov 14, 2026; 10:03 PM
**Hecho**
- Entorno listo (Git, VS Code, Python, librerías); trabajo en la rama `feature/science-validation`.
- Recibí el paquete real de Ian (MODIS/061/MOD13Q1, NDVI de Querétaro 2001–2025). Los 15 archivos coinciden con los SHA-256 de `package_manifest.json`.
- `scripts/plot_results.py`: genera 7 figuras (pendiente, cambio, significancia, HAC, cobertura, cobertura mensual y serie regional).
- `tests/test_figures.py`: 14 pruebas, todas pasan.
- `scripts/validate_independent.py` (archivo nuevo mío): Parte A de coherencia, 17/17 comprobaciones correctas.
- `docs/scientific_report.md` con resultados reales, `docs/validation_report.md`, `docs/demo_script.md`, `docs/submission_checklist.md` y `docs/project_description_en.md`.
- Figuras y CSV de evidencia en `docs/evidence/science/`. Todo subido a mi rama.

**Resultados clave (datos reales)**
- 11 288 píxeles probados: 17.8 % aumento significativo, 4.5 % disminución, 77.7 % sin evidencia (q < 0.05).
- Serie regional: +0.00116 NDVI/año, p = 0.066, no significativa al 5 %.

**Siguiente paso**
- Abrir PR borrador hacia `main` (sin fusionar).
- Validar 3 píxeles con `linregress` cuando Yatz entregue `manifest.csv` y los TIFF mensuales.
- Verificar referencias y los `[VERIFICAR]` del reporte.
- Hacer las 7 diapositivas en inglés y redactar con el equipo el campo de uso de IA.
- Preguntar al Local Lead por el horario del juzgamiento local.

**Bloqueos**
- Faltan `manifest.csv` y los TIFF mensuales de Yatz (validación de 3 píxeles).
- Faltan las métricas de predicción de Ian (revisión del split sin fuga).
- Por confirmar con Ian: si el repo será público y si acepta `validate_independent.py` en mi carpeta.

**Commits:** 5fbda23 (HEAD -> feature/science-validation, origin/feature/science-validation) docs: complete submission checklist
7397cb7 docs: update validation report
26a23b4 docs: update validation report
1a14738 docs: report, validation, demo script and evidence
a27198c feat: figure script, independent validation and tests

**Comandos:** `python -m pytest tests/test_figures.py -q`, `python scripts/plot_results.py ...`, `python scripts/validate_independent.py ...`

### Nov 15, 2026; 9:08 AM