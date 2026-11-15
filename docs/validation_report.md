# Reporte de validación independiente — Sofía

Datos: paquete real MODIS/061/MOD13Q1 de Ian (`package_manifest.json`, commit `bcb20fa0…`).
Script: `scripts/validate_independent.py` (reproducible). Evidencia: `docs/evidence/science/validation_outputs.csv`.
Fecha: Noviembre 14, 2026 · Revisora: Sophia · Decisiones de corrección: Ian.

## 1. Integridad del paquete
- Los 15 archivos del paquete coinciden con los SHA-256 de `package_manifest.json`. 
- Rejilla: EPSG:32614, 161 × 171, 1000 m, nodata −9999 (`run_metadata.json`).
- Productos con `dataset: "satellite"` y fuente MODIS/061/MOD13Q1 (no sintéticos).

## 2. Parte A — coherencia interna (17/17 correctas)
| Comprobación | Esperado | Observado |
|---|---|---|
| Píxeles regionales | 11 511 | 11 511 |
| Píxeles probados | 11 288 | 11 288 |
| No probados (n < 15) | 223 | 223 (máx. n = 14) |
| Aumentos significativos (q<0.05) | 2 010 | 2 010 |
| Disminuciones significativas | 505 | 505 |
| No significativos | 8 773 | 8 773 |
| `trend_significant` = (q < 0.05) | sí | sí |
| q = BH(p) recalculado | dif. < 1e-6 | 6.6e-8 (Float32) |
| Signo OLS = Sen (píxeles significativos) | 100 % | 100 % |
| Cambio = pendiente × intervalo | 14–24 años | 14.00–24.00 |
| Pendiente media | 0.000832 | 0.000832 |
| Regional: pendiente, p, R², IC 95 % | `regional_trend.json` | idénticos con `linregress` |
| Regional: media anual | media de meses con cobertura ≥ 0.7 | dif. 5.6e-17 |

## 3. Parte B — tres píxeles con `linregress` (PENDIENTE)
Requiere `manifest.csv` y los TIFF mensuales (`data/raw`) de Yatz.
Regla de selección (documentada, determinista): en cada clase (aumento, disminución, sin evidencia), el píxel con serie
completa cuya pendiente está más cerca de la mediana de su clase. Tolerancia propuesta: 1e-6 NDVI/año.

| Clase | Fila | Col | Años | Pend. linregress | Pend. Ian | Dif. | p linregress | p Ian | ¿OK? |
|---|---|---|---|---|---|---|---|---|---|
| Aumento | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Disminución | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| Sin evidencia | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

## 4. Revisión de interpretación
- [x] p y q no se presentan como probabilidad de cambio (ver `scientific_report.md`, 6.6).
- [x] Hay corrección por pruebas múltiples (Benjamini–Hochberg, q < 0.05).
- [x] Cobertura (`map_coverage*.png`) y magnitud (`map_change.png`) visibles.
- [x] No se afirma causalidad; las explicaciones se marcan como hipótesis.
- [ ] Split 2002–2018 / 2019–2021 / 2022–2025 sin fuga: [PENDIENTE: no se recibieron métricas ni código de predicción]

## 5. Observaciones y preguntas para Ian
1. **HAC prueba menos píxeles** (10 053 de 11 288). ¿Qué criterio excluye a 1 235 píxeles?
2. **Meses excluidos en época de lluvias.** Los 10 meses con cobertura regional < 70 % caen entre junio y octubre,
   cerca del máximo de NDVI. ¿Se evaluó el posible sesgo de la media anual?
3. **Dos criterios de calidad distintos:** por píxel (≥ 9 meses válidos por año) y regional (cobertura ≥ 0.7 por mes).
   Conviene dejarlo explícito en el README.
4. **Dependencia espacial.** BH asume independencia o dependencia positiva; con píxeles vecinos correlacionados puede
   ser imperfecta. Conviene mencionarlo como límite.
5. **Regional no significativa (p = 0.066)** frente a 17.8 % de píxeles con aumento significativo: no es contradicción,
   pero el mensaje público debe decirlo claramente.
6. **Sen regional (calculado por Sofía):** +0.00133 NDVI/año, IC 95 % [−0.00009, +0.00261]; Kendall τ = 0.27, p = 0.065.
   Consistente con OLS. Autocorrelación lag-1 de residuos anuales regionales ≈ 0.20.
7. `trend_p/q` están en Float32: diferencias del orden de 1e-8 al recalcular son normales.

## 6. Estado
Parte A: **completa**. Parte B y revisión de split: **pendientes de datos de Yatz / Ian**. Ninguna cifra se corrigió a mano.
