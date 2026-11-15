# Reporte de validación independiente — Sophia

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

## 3. Parte B — tres píxeles con linregress (COMPLETADA)
Datos: 300 TIFF mensuales (`data/raw`) y `manifest.csv` de Yatz. Regla de selección: en cada clase, el píxel con serie
completa cuya pendiente está más cerca de la mediana de su clase (ver `scripts/validate_independent.py`).
Método: medias anuales con ≥ 9 meses válidos, `scipy.stats.linregress` sobre años reales (≥ 15 años). Tolerancia: 1e-6 NDVI/año.

| Clase | Fila | Col | Años | Pend. linregress | Pend. Ian | Dif. (NDVI/año) | p linregress | p Ian | ¿OK? |
|---|---|---|---|---|---|---|---|---|---|
| Aumento significativo | 73 | 104 | 25 | +0.002751 | +0.002751 | 7.4e-11 | 0.000296 | 0.000296 | Sí |
| Disminución significativa | 91 | 12 | 25 | −0.003509 | −0.003509 | 6.4e-11 | 0.000189 | 0.000189 | Sí |
| Sin evidencia significativa | 125 | 48 | 25 | +0.000749 | +0.000749 | 4.6e-13 | 0.312374 | 0.312374 | Sí |

**Conclusión:** los tres píxeles reproducen la pendiente y el p de Ian dentro de la tolerancia; no se detectaron discrepancias.
Las diferencias (≤ 1e-10) son compatibles con la precisión Float32 de los TIFF.
**Alcance:** valida medias anuales y regresión desde los TIFF mensuales; no valida la extracción desde Earth Engine,
la predicción ni los 11 288 píxeles restantes. Evidencia: `docs/evidence/science/validation_pixels.csv`.

## 4. Revisión de interpretación
- [x] p y q no se presentan como probabilidad de cambio (ver `scientific_report.md`, 6.6).
- [x] Hay corrección por pruebas múltiples (Benjamini–Hochberg, q < 0.05).
- [x] Cobertura (`map_coverage*.png`) y magnitud (`map_change.png`) visibles.
- [x] No se afirma causalidad; las explicaciones se marcan como hipótesis.
- [ ] Split 2002–2018 / 2019–2021 / 2022–2025 sin fuga: se recibieron métricas finales de Ian (XGBoost y ConvLSTM, 2022–2025);
      PENDIENTE revisar configuración y confirmar que test no se usó para selección. Faltan métricas de persistencia,
      climatología mensual y OLS estacional sobre los mismos pares.

## 5. Observaciones y preguntas para Ian
1. **HAC (respondido por Ian y verificado por Sophia).** Es intencional: OLS admite series con años faltantes, pero la
   implementación de HAC exige serie anual completa y descarta series constantes. Verificado: HAC probó exactamente los
   10 053 píxeles con 25 años válidos; los 1 235 píxeles con 15–24 años solo entran al método principal.
   La comparación justa es solo entre esos 10 053: OLS q<0.05 → 2 123 (21.1 %); HAC → 1 965 (19.5 %); ambos → 1 690.
2. **Sesgo estacional por meses excluidos (limitación abierta).** Los 10 meses con cobertura regional < 70 % caen entre
   junio y octubre, cerca del máximo de NDVI. Ian confirma que aún no se evalúa; se documenta como limitación.
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
Parte A y Parte B: **completas**. 

Pendiente solo la confirmación de Ian de que la prueba 2022–2025 no se usó para selección, y las métricas MAE/R² de las referencias. Ninguna cifra se corrigió a mano.
