# AURORA — final form texts (English), ready to paste

> Paste field by field. Lines starting with "CHECK:" are NOT part of the text: confirm them, then delete.
> Include only what is verified. Do NOT mention LST, national or global results unless the files were checked.

## Project Name
AURORA — Earth System Intelligence Model

## High-Level Project Summary
AURORA is a reproducible tool that shows where vegetation is changing, by how much, and whether the change is statistically significant. Using NASA MODIS vegetation data (NDVI) for Querétaro, Mexico, from 2001 to 2025, it produces maps of trend, magnitude, significance and data coverage, and a one-month-ahead NDVI forecast, so students and the public can act as "data detectives".

## Link to Project Demo
CHECK: public Google Slides link (7 slides max), tested in an incognito window.

## Link to Final Project
CHECK: public link (GitHub repo if Ian makes it public, or the public Drive folder "AURORA_Final"). It must open without login.

## Detailed Project Description
**Team.** AURORA: Ian, Yatz, Sophia and René (Local Event: Guadalajara, working virtually with UNAQ).

**Challenge.** Earth's environment is always changing, and a variable can rise in one region while falling in another. With so many variables and regions, it is hard to know what is changing, where, how much, and whether the change is "significant" in the scientific sense. AURORA answers those four questions for a case study: vegetation greenness (NDVI) in Querétaro, Mexico.

**What it does.** For every 1 km pixel in the region, AURORA estimates the yearly NDVI trend, the total estimated change, and a statistical test of whether the trend is distinguishable from no change. Maps also show how much valid data supports each pixel, so users can see where results are strong or weak.

**Data.** MODIS/Terra Vegetation Indices MOD13Q1 v061 (250 m, 16-day) via Google Earth Engine. We keep only the best-quality observations (SummaryQA = 0), build monthly composites and aggregate to a 1 km grid (EPSG:32614) with 11,511 pixels inside Querétaro. Mean temporal coverage is 94.7%.

**Method.** (1) Monthly NDVI → annual means per pixel (at least 9 valid months per year, at least 15 valid years per pixel). (2) Linear trend per pixel (ordinary least squares), with Theil–Sen slopes as a robust check. (3) Significance with the Benjamini–Hochberg false-discovery-rate correction (q < 0.05), because thousands of pixels are tested at once. (4) A sensitivity run with autocorrelation-robust (HAC) errors on pixels with complete series. (5) A regional time series with a 95% confidence interval.

**Results.**
- Of 11,288 tested pixels, 17.8% show a significant NDVI increase, 4.5% a significant decrease, and 77.7% show no significant evidence of change.
- Increases cluster mainly in the central-east and northeast of the region; decreases cluster in the southwest.
- The regional mean trend is +0.0012 NDVI per year (+0.028 over 2001–2025) but is not significant at 5% (p = 0.066; 95% CI −0.00008 to +0.00241). Changes of opposite sign in different places partly cancel in the regional average, which is why mapping matters.
- The regional trend stayed positive (+0.0009 to +0.0012 NDVI/year) but never reached significance in seven sensitivity variants (coverage thresholds of 50–90% and common-months designs; p = 0.066–0.146). Low-coverage months fall mostly in June–October, so a seasonal bias is possible and not yet quantified.
- We do not claim causes. Irrigation, rainfall, land-use change or urban growth are hypotheses that need additional data.

**Forecast.** We predict next-month NDVI from the previous 12 months with a strict date-based split (train 2002–2018, validation 2019–2021, test 2022–2025). On the same 489,633 test observations, XGBoost reaches RMSE 0.0635 (MAE 0.0422, R² 0.884) and ConvLSTM RMSE 0.0636 (MAE 0.0444, R² 0.884), about 19% lower error than the best simple baseline (monthly climatology, RMSE 0.0784, R² 0.824). The two models are essentially equivalent. We make no claim about other regions.

**Validity.** All outputs are reproducible from code and automated tests. An independent check with SciPy passed 17 of 17 consistency controls, reproduced the regional slope, p-value, R² and confidence interval, and reproduced the slopes of three pixels (increase, decrease, no evidence) within 1e-10 NDVI/year. Limits: 1 km pixels mix land covers; cloudy-season gaps; only linear trends; neighboring pixels are not independent, so corrections can be imperfect; and 25 years is a short record.

**Impact and future.** The pipeline is region- and variable-agnostic. Next steps: add rainfall and land cover to test explanations, and extend to other variables and regions.

## NASA Data
MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1), NASA LP DAAC. Didan, K. (2021). DOI: 10.5067/MODIS/MOD13Q1.061. Accessed via Google Earth Engine.

## Space Agency Partner Data and Other References
- Google Earth Engine data catalog: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1
- Gorelick, N., et al. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote Sensing of Environment, 202, 18–27.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. Journal of the Royal Statistical Society B, 57(1), 289–300.
- Virtanen, P., et al. (2020). SciPy 1.0: fundamental algorithms for scientific computing in Python. Nature Methods, 17, 261–272.
- XGBoost and PyTorch documentation.
CHECK: verify each citation (year, pages, DOI/URL) before pasting; delete any you cannot verify.

## Use of Super Intelligence (SI)
Team members used AI assistants (ChatGPT, Codex and Claude) to help plan the workflow, write and review code and tests, and draft documentation and explanations of statistical concepts. The team made the design decisions, ran all data processing and statistics, reviewed and tested AI-generated code, and checked results independently with SciPy. XGBoost and ConvLSTM are machine-learning components of the tool, not tools used to write it.
CHECK: each member confirms which AI tools they really used; edit the list to match. Do not claim NASA certification.
