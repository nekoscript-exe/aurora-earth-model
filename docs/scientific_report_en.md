# AURORA — Earth System Intelligence Model
**Scientific report · NASA Space Apps Challenge 2026**
Team AURORA: Ian, Yatz, Sophia and René · Local Event: Guadalajara (working virtually with UNAQ)
Case study: Querétaro, Mexico · Variables: NDVI and daytime land surface temperature (LST) · Period: 2001–2025

## Summary
AURORA transforms NASA MODIS satellite observations into scientific evidence: where an environmental variable changes, by how much, and whether the change is statistically significant. For Querétaro we analyzed 25 years of vegetation (NDVI) and daytime land surface temperature (LST) on a 1 km grid. 17.8% of tested NDVI pixels show a significant increase and 4.5% a significant decrease, while the regional NDVI and LST trends are not significant at the 5% level. NDVI and LST anomalies are strongly and negatively associated (Pearson r = −0.760), which does not establish causation. XGBoost and ConvLSTM forecast both variables one month ahead; XGBoost has about 19% (NDVI) and 16% (LST) lower RMSE than the best simple baseline.

## 1. Challenge and objectives
Earth's environment changes constantly, and a variable can rise in one place and fall in another. AURORA answers four questions: what is changing, where, how much, and how certain we are. Objectives: (1) build quality-controlled monthly series from NASA data; (2) estimate per-pixel trends, change magnitude and corrected significance; (3) map trend, magnitude, significance and data coverage; (4) validate results independently; (5) forecast one month ahead and compare with simple baselines; (6) relate NDVI and LST.

## 2. Variables
**NDVI** = (NIR − Red) / (NIR + Red). Healthy vegetation absorbs red light and reflects near-infrared, giving high values; water, bare soil and built surfaces give low values. A higher NDVI is not always "better": irrigation, crop changes or a wet year can raise it.
**LST** is the temperature of the land surface during the day, measured in °C. It is not air temperature.
**Slope** is the average yearly change. **p** is the probability of a slope at least this extreme if there were no trend; it is not the probability that the change is real. **q** is p adjusted for testing thousands of pixels (Benjamini–Hochberg). **Coverage** is the share of valid observations.

## 3. Data
| | NDVI | LST (daytime) |
|---|---|---|
| Product | Terra MODIS MOD13Q1 V061 | Terra MODIS MOD11A2 V061 |
| Native resolution / frequency | 250 m / 16 days | 1 km / 8 days |
| Monthly images, period | 300, 2001–2025 | 300, 2001–2025 |
| Analysis grid | 1 km, EPSG:32614 | 1 km, EPSG:32614 |
| Temporal coverage | 94.73% | 95.27% |
| Valid observations | 3,271,411 | 3,289,859 |
| Unit | dimensionless | °C |

The grid has 161 × 171 cells, of which 11,511 lie inside Querétaro. Data were acquired through Google Earth Engine; files are Float32 GeoTIFFs with NoData = −9999, and gaps are never filled with zeros. NDVI quality filter: SummaryQA = 0, raw range −2000 to 10000, scale 0.0001. LST quality filter: QC_Day bits 0–1 = 0, raw range 7500–65535, conversion DN × 0.02 − 273.15. Monthly composites are medians of the selected observations, followed by spatial aggregation of valid observations.

## 4. Methods
1. **Annual means** per pixel with at least 9 valid months per year; at least 15 valid years per pixel.
2. **Trend**: ordinary least squares (OLS) on annual means against the actual year; Theil–Sen as a robust estimator; HAC (Newey–West) as a sensitivity analysis on complete annual series.
3. **Significance**: Benjamini–Hochberg false discovery rate, q < 0.05.
4. **Regional series**: months with coverage ≥ 70%, at least 9 months per year, OLS with a 95% confidence interval.
5. **Multivariable analysis**: valid NDVI and LST pairs on the same grid and month; anomalies from a monthly climatology of 2002–2018 (at least 8 coincident observations per calendar month); Pearson and Spearman correlation; a stable-footprint sensitivity and a detrended test.
6. **Forecasting**: next-month value from the previous 12 observed months. Chronological split by target date: context 2001, training 2002–2018, validation 2019–2021, test 2022–2025. Models: XGBoost and ConvLSTM, compared with climatology, persistence and seasonal persistence on the same test pairs. Hyperparameters were selected on validation, according to the recorded configuration.

## 5. Results
### 5.1 NDVI (Querétaro, 2001–2025)
| Category (OLS + Benjamini–Hochberg) | Pixels | % of tested |
|---|---|---|
| Significant increase | 2,010 | 17.8% |
| Significant decrease | 505 | 4.5% |
| No significant evidence | 8,773 | 77.7% |
| Tested | 11,288 | 100% |
| Not tested (< 15 valid years) | 223 | — |

Regional trend: +0.00116 NDVI/year (+0.0116 per decade; +0.0279 over 24 years), p = 0.0659, R² = 0.139, 95% CI [−0.00008, +0.00241]. Mean pixel slope: +0.000832 NDVI/year. Increases cluster mainly in the central-east and northeast; decreases cluster in the southwest. HAC was applied to the 10,053 pixels with complete series (1,965 significant); within them 2,123 pixels are significant with OLS and 1,690 with both methods. Theil–Sen regional slope: +0.00133 NDVI/year (95% CI −0.00009 to +0.00261).

### 5.2 Sensitivity of the regional NDVI trend
| Variant | Years | Slope (NDVI/yr) | p |
|---|---|---|---|
| Coverage ≥ 50% | 25 | +0.00096 | 0.133 |
| Coverage ≥ 60% | 25 | +0.00094 | 0.132 |
| Coverage ≥ 70% (main) | 25 | +0.00116 | 0.066 |
| Coverage ≥ 80% | 24 | +0.00099 | 0.146 |
| Coverage ≥ 90% | 24 | +0.00115 | 0.083 |
| Same calendar months, ≥ 50% in all years | 25 | +0.00100 | 0.112 |
| Same calendar months, ≥ 70% in all years | 25 | +0.00105 | 0.123 |

The slope stays positive in every variant but none is significant at 5%; the 70% threshold used as the main analysis gives the lowest p. The 10 months below 70% coverage fall in June (2), August (4), September (1) and October (3), so a seasonal bias is possible and has not been quantified.

### 5.3 LST (Querétaro, 2001–2025)
Regional trend: −0.0406 °C/year (−0.406 °C per decade; −0.975 °C over 24 years), p = 0.258, R² = 0.055, 95% CI [−0.113, +0.032] °C/year. Of 11,100 tested pixels, none is significant after correction; HAC (10,828 pixels) also finds none. Mean pixel slope: −0.0383 °C/year. The interval includes zero, so cooling cannot be claimed; zero significant pixels does not prove that no real change exists.

### 5.4 NDVI–LST relationship
3,149,060 valid paired pixel-months. Regional anomalies: Pearson r = −0.760. Stable footprint (9,339 pixels, 291 months): Pearson −0.767, Spearman −0.728. After detrending (280 months): Pearson −0.757, Spearman −0.713. Relatively greener periods tend to coincide with relatively cooler land surfaces. Rainfall, irrigation, seasonality and crop changes may explain part of this; the analysis does not establish causation.

### 5.5 Forecast (one month ahead, test 2022–2025)
| NDVI (489,633 pairs) | RMSE | MAE | R² |
|---|---|---|---|
| XGBoost | 0.0635 | 0.0422 | 0.884 |
| ConvLSTM | 0.0636 | 0.0444 | 0.884 |
| Climatology | 0.0784 | 0.0560 | 0.824 |
| Persistence | 0.0825 | 0.0565 | 0.805 |
| Seasonal persistence | 0.0979 | 0.0683 | 0.726 |

| LST (507,583 pairs) | RMSE (°C) | MAE (°C) | R² |
|---|---|---|---|
| XGBoost | 2.831 | 2.088 | 0.819 |
| ConvLSTM | 3.012 | 2.211 | 0.796 |
| Climatology | 3.362 | 2.590 | 0.745 |
| Seasonal persistence | 4.071 | 3.071 | 0.626 |
| Persistence | 4.272 | 3.371 | 0.589 |

Compared with monthly climatology, XGBoost lowers RMSE by about 18.9% (NDVI) and 15.8% (LST). We did not test the significance of differences between models. XGBoost and ConvLSTM are practically equivalent for NDVI. The forecast was evaluated only in Querétaro; we make no claim for other regions. A retrospective estimate for January 2026 exists but has not been compared with observations and is not presented as a validated forecast.

## 6. Validation and reproducibility
- **Independent NDVI checks (SciPy):** 17 of 17 consistency controls passed (pixel counts, Benjamini–Hochberg recomputed from p, regional slope, p, R², confidence interval and annual means). Three pixels (increase, decrease, no evidence) were recomputed from the monthly images with `scipy.stats.linregress`; the largest slope difference was 7.4 × 10⁻¹¹ NDVI/year (tolerance 10⁻⁶, consistent with Float32 storage).
- **LST:** the equivalent independent three-pixel recomputation has not been completed yet; LST results come from the team's processing engine.
- **Software tests:** 118 automated tests passed in the team's technical review; the application has 9 analysis tabs and 16 predictive views checked.
- **Scalability:** a synthetic Zarr test of 150 GiB (logical size) showed partial block access; it is a software test, not a real global satellite dataset.
- National and global acquisition are in progress and are not part of these results.

## 7. Limitations
1 km pixels mix land covers. Cloud gaps remove some months, mostly June–October for NDVI. The observed spatial composition may vary over time. Neighboring pixels and consecutive years are not independent; Benjamini–Hochberg and HAC do not guarantee calibration. A 25-point annual record has limited power, and a linear trend cannot capture non-linear change. Significance is not magnitude or causation. LST is a surface temperature, not air temperature. Forecasts were evaluated only in Querétaro. An independent audit of the training code is not yet completed.

## 8. Use of AI
Team members used AI assistants to help plan workflows, draft and review code, tests and documentation, and explain statistical concepts. The team made the design decisions, ran the processing and reviewed the outputs. XGBoost and ConvLSTM are machine-learning components of AURORA, not tools used to write it.

## 9. References
- Didan, K. (2021). MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1). NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD13Q1.061
- Wan, Z., Hook, S., & Hulley, G. (2021). MODIS/Terra Land Surface Temperature/Emissivity 8-Day L3 Global 1km SIN Grid V061 (MOD11A2). NASA LP DAAC. https://doi.org/10.5067/MODIS/MOD11A2.061
- Earth Engine catalog: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1 and .../MODIS_061_MOD11A2
- Gorelick, N., et al. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote Sensing of Environment, 202, 18–27.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. Journal of the Royal Statistical Society B, 57(1), 289–300.
- Sen, P. K. (1968). Estimates of the regression coefficient based on Kendall's tau. Journal of the American Statistical Association, 63(324), 1379–1389.
- Newey, W. K., & West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. Econometrica, 55(3), 703–708.
- Chen, T., & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. KDD '16.
- Shi, X., et al. (2015). Convolutional LSTM network. Advances in Neural Information Processing Systems 28.
- Virtanen, P., et al. (2020). SciPy 1.0. Nature Methods, 17, 261–272.
