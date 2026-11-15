# AURORA — texts for the submission (English)

## Project Name
AURORA — Earth System Intelligence Model

## High-Level Project Summary
AURORA is a reproducible tool that shows where vegetation is changing, by how much, and whether the change is statistically significant. Using NASA MODIS vegetation data (NDVI) for Querétaro, Mexico, from 2001 to 2025, it produces maps of trend, magnitude, significance and data coverage, so students and the public can act as "data detectives".

## Detailed Project Description

**The challenge.** Earth's environment is always changing, and a variable can rise in one region while falling in another. With so many variables and regions, it is hard to know what is changing, where, how much, and whether the change is "significant" in the scientific sense. AURORA answers those four questions for one case study: vegetation greenness in Querétaro, Mexico.

**What it does.** AURORA turns a satellite time series into maps. For every 1 km pixel of the region it estimates the yearly trend in NDVI (a vegetation greenness index), the total estimated change, and a statistical test of whether that trend is distinguishable from no change. It also shows how much valid data supports each pixel, so users can see where results are strong or weak.

**Data.** MODIS/Terra Vegetation Indices (MOD13Q1 v061), 250 m, every 16 days, accessed through Google Earth Engine. We keep only the highest-quality observations (SummaryQA = 0), build monthly composites, and aggregate to a 1 km grid (EPSG:32614) with 11,511 pixels inside Querétaro. Mean temporal coverage is 94.7%.

**Method.**
1. Monthly NDVI → annual means per pixel (at least 9 valid months per year; at least 15 valid years per pixel).
2. Linear trend per pixel (ordinary least squares) with Theil–Sen slopes as a robust check.
3. Significance with the Benjamini–Hochberg false discovery rate correction (q < 0.05), because thousands of pixels are tested at once.
4. A sensitivity test with autocorrelation-robust (HAC) errors.
5. A regional time series with a 95% confidence interval.

**Results.**
- Of 11,288 tested pixels, **17.8%** show a significant increase in NDVI, **4.5%** a significant decrease, and **77.7%** show no significant evidence of change.
- Increases cluster mainly in the central-east and northeast of the region; decreases cluster in the southwest.
- The regional mean trend is +0.0012 NDVI per year (+0.028 over 2001–2025), but it is **not significant at 5%** (p = 0.066; 95% CI −0.00008 to +0.00241). Opposite-sign changes in different places partly cancel in the regional average, which is exactly why mapping matters.
- We do not claim causes. Irrigation, rainfall, land-use change or urban growth are hypotheses that would need extra data to test.

**Validity.** All outputs are reproducible from code and tests. An independent check with SciPy reproduces the regional slope, p-value, R² and confidence interval, and recomputing the multiple-testing correction from the raw p-values matches our q-values. [Add: independent recomputation of three pixels, once completed.] Months with low cloud-free coverage fall mostly in the rainy season (June–October), which may bias annual means; we have not yet quantified this.rainy-season clouds remove some months; only linear trends are tested; neighboring pixels are not independent, so corrections can be imperfect; and 25 years is a short record.

**Forecasting (complementary).** We also predict next-month NDVI with a date-based split (train 2002–2018, validation 2019–2021, test 2022–2025). On the test period (about 490,000 comparable pixel-month pairs) XGBoost reaches R² 0.884, MAE 0.042, RMSE 0.064, and ConvLSTM R² 0.884, MAE 0.044, RMSE 0.064, essentially equivalent. [ADD baseline comparison (persistence, monthly climatology, seasonal OLS) once Ian provides it; NDVI is strongly seasonal, so baselines matter.] We make no claim about performance in other regions.

**Impact and future.** The pipeline is region- and variable-agnostic: the same steps can be applied to rainfall, land surface temperature or soil moisture in other regions. Next steps are adding rainfall and land cover to test explanations, and extending to more regions.

**Audience.** High-school and college students and the public with some scientific background. Plain-language definitions of NDVI, slope, p, q and coverage are included in our report.

## NASA Data
MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1), NASA LP DAAC. Didan, K. (2021). DOI: 10.5067/MODIS/MOD13Q1.061. Accessed via Google Earth Engine.

## Space Agency Partner Data and Other References
Google Earth Engine (Gorelick et al., 2017); SciPy; XGBoost; PyTorch. Full reference list: `docs/scientific_report.md`, section 10. [Verify each citation before submitting.]

## Use of Super Intelligence (SI)
[TEAM MUST CONFIRM — write exactly what each member used. Draft:] "Team members used AI assistants (e.g., ChatGPT and Claude) to help plan the workflow, draft code, tests and documentation, and to explain statistical concepts. All data processing and statistics were run by the team; AI-generated code was reviewed and tested, results were independently recomputed with SciPy, and every claim in this submission was checked against the data."

---

## Slide text (7 slides, short)
**1. AURORA** — Where is vegetation changing, and is it significant? · Team AURORA: Ian, Yatz, Sofía · Challenge: Earth system trends · NASA Space Apps 2026
**2. The challenge** — What is changing? Where? How much? Is it significant? A trend can rise in one place and fall in another.
**3. NASA data** — MODIS NDVI (MOD13Q1 v061) · 2001–2025 · Querétaro, Mexico · 11,511 pixels at 1 km · via Google Earth Engine
**4. How it works** — Monthly NDVI → annual means → trend per pixel → false-discovery-rate correction (q < 0.05) → maps
**5. Results** — [image: significance map] 17.8% significant increase · 4.5% significant decrease · 77.7% no significant evidence · Regional trend not significant (p = 0.066)
**6. Validity and limits** — Independent recomputation matches · 94.7% data coverage · 1 km pixels, cloud gaps, linear trends only · No causal claims
**7. Impact** — Open, reproducible "data detective" tool for any region or variable · Next: rainfall and land cover · Thanks: NASA LP DAAC, Google Earth Engine
