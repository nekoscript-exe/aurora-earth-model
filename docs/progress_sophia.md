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

---

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

---

### Nov 15, 2026; 9:08 AM

**Hecho**
- Recibí los 300 TIFF mensuales de Yatz (`data/raw`) y `manifest.csv`; la comprobación de rutas dio 300 archivos, 0 faltantes.
- Validación independiente completa:
  - Parte A: 17/17 comprobaciones correctas (conteos, Benjamini–Hochberg recalculado, serie regional con linregress).
  - Parte B: tres píxeles (73,104), (91,12) y (125,48) recalculados con `scipy.stats.linregress` desde los TIFF mensuales. Diferencia máxima de pendiente 7.4e-11 NDVI/año (tolerancia 1e-6); los p coinciden. 3/3 dentro de la tolerancia.
- Actualicé `docs/validation_report.md` y `docs/scientific_report.md` con ese resultado.
- Incorporé la respuesta de Ian sobre HAC (solo evalúa píxeles con 25 años completos: 10 053 píxeles) y documenté el sesgo estacional como limitación abierta.
- Incorporé las métricas de predicción de Ian (RMSE: XGBoost 0.063527, ConvLSTM 0.063608, climatología 0.078366, persistencia 0.082473, persistencia estacional 0.097873; mismas 489 633 observaciones de prueba).
- Generé el mapa de significancia en inglés (`map_significance_en.png`) y armé la presentación de 7 diapositivas en inglés [pasada a Google Slides: SÍ/NO].
- Actualicé `docs/submission_checklist.md` y `docs/project_description_en.md`.

**Siguiente paso**
- Llenar el formulario del proyecto en NASA Space Apps y guardar el progreso.
- Redactar con el equipo el campo de uso de IA.
- Resolver con Ian el "Link to Final Project" y compartir el enlace de las diapositivas, probando ambos en modo incógnito.
- Verificar referencias y los `[VERIFICAR]` de `docs/scientific_report.md`.
- Enviar con "Submit for Judging" antes del domingo 15 nov, 11:59 p.m. (Guadalajara).

**Bloqueos**
- Ian y Yatz no respondieron durante varias horas; los TIFF de Yatz llegaron por [medio]. Falta aprobación final de Ian y decidir si el repo es público.
- Pendiente de Ian: confirmar que la prueba 2022–2025 no se usó para selección, y MAE/R² de las referencias de predicción.
- La estimación de enero de 2026 no está contrastada; no se presenta como resultado.

**Commits:** 61c2a82 (HEAD -> feature/science-validation, origin/feature/science-validation) docs: complete three-pixel independent validation
ac45538 docs: complete three-pixel independent validation
763f8e6 docs: update progress, pixel selection and checklist
4788115 docs: update progress, pixel selection and checklist
c5bbadf docs: add forecast baselines and split description
bc914e6 docs: checklist and English project description
**Comandos:** `python scripts/validate_independent.py --outputs outputs --dest docs/evidence/science --manifest manifest.csv --root .`, `python scripts/plot_results.py --outputs outputs --dest docs/evidence/science`, `python -m pytest tests/test_figures.py -q`