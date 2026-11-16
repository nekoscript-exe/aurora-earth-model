# AURORA — final form texts (English), ready to paste

> Paste field by field. Lines starting with "CHECK:" are NOT part of the text: complete them, then delete the line.
> National and global results are NOT included.

## Project Name
AURORA — Earth System Intelligence Model

## High-Level Project Summary
AURORA is an interactive Earth system intelligence model that transforms NASA MODIS satellite observations into maps of environmental trends, statistical significance, data coverage and one-month-ahead forecasts. Our validated case study uses 25 years of vegetation (NDVI) and daytime land surface temperature observations in Querétaro, Mexico. AURORA combines reproducible scientific analysis, machine learning and interactive exploration to help users investigate environmental changes and their uncertainty.

## Link to Project Demo
CHECK: public Google Slides link (7 slides max), tested in an incognito window.

## Link to Final Project
CHECK: public link (GitHub repo if Ian makes it public, or the public Drive folder "AURORA_Final"). It must open without login.

## Detailed Project Description
**Team.** AURORA: Ian, Yatz, Sophia and René (Local Event: Guadalajara, working virtually with UNAQ).

**Challenge.** Earth's environment is always changing, and a variable can rise in one region while falling in another. AURORA answers four questions for a real case study, Querétaro, Mexico: what is changing, where, how much, and whether the change is statistically significant.

**Data.** 25 years (2001–2025) of NASA Terra MODIS observations obtained through Google Earth Engine: 300 monthly NDVI images (MOD13Q1 v061) and 300 monthly daytime land surface temperature images (MOD11A2 v061), quality-filtered and aggregated to a 1 km grid with 11,511 cells inside Querétaro. Temporal coverage is 94.7% (NDVI) and 95.3% (LST). Missing data are never filled with zeros.

**Method.** Space–time data cubes with validity masks; annual means per pixel (at least 9 valid months, at least 15 valid years); ordinary least squares trends with Theil–Sen and HAC robustness checks; Benjamini–Hochberg false-discovery-rate correction (q < 0.05) because thousands of pixels are tested at once; Pearson and Spearman correlation of NDVI and LST anomalies.

**Scientific findings.**
- 17.8% of 11,288 tested NDVI pixels show a significant increase and 4.5% a significant decrease; increases cluster in the central-east and northeast, decreases in the southwest.
- The regional NDVI trend (+0.0012 per year, p = 0.066) and the regional LST trend (−0.041 °C per year, p = 0.258) are not statistically significant at 5%. No LST pixel is significant after correction, which does not prove that no change exists.
- NDVI and LST anomalies are strongly negatively associated (Pearson r = −0.760; −0.757 after detrending). Association does not imply causation.
- The regional NDVI trend stayed positive but never significant in seven sensitivity variants (p = 0.066–0.146).

**Predictive intelligence.** XGBoost and ConvLSTM forecast each variable one month ahead from 12 months of history, with a chronological split (train 2002–2018, validation 2019–2021, test 2022–2025). Against the best simple baseline (monthly climatology), XGBoost lowers RMSE by about 19% for NDVI (0.0635 vs 0.0784) and 16% for LST (2.83 °C vs 3.36 °C). We make no claim for other regions.

**Validation and quality.** An independent SciPy check passed 17 of 17 consistency controls for NDVI and reproduced three pixel regressions from the monthly images within 1e-10 NDVI/year. The software passed 118 automated tests in our technical review.

**Interactive experience.** AURORA Desktop includes Planetary Explorer (geographic dataset exploration), Time Machine (navigation through dates and historical imagery), Pixel Lab (individual pixel series), AI Lab (model evaluation and forecasts) and multivariable NDVI–LST analysis, with export of results.

**Limitations.** 1 km pixels mix land covers; cloudy-season gaps; neighboring pixels and consecutive years are not independent; a 25-year record has limited power; LST is surface, not air, temperature; no causal attribution. National and global acquisition are in progress and are not part of these results.

**Impact.** A reproducible tool for students, researchers and environmental data explorers that turns satellite history into evidence, uncertainty and forecasts.

## NASA Data
MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1), NASA LP DAAC, DOI 10.5067/MODIS/MOD13Q1.061; and MODIS/Terra Land Surface Temperature/Emissivity 8-Day L3 Global 1km SIN Grid V061 (MOD11A2), NASA LP DAAC, DOI 10.5067/MODIS/MOD11A2.061. Accessed via Google Earth Engine.

## Space Agency Partner Data and Other References
- Google Earth Engine data catalog: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1 and https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD11A2
- Gorelick, N., et al. (2017). Google Earth Engine: Planetary-scale geospatial analysis for everyone. Remote Sensing of Environment, 202, 18–27.
- Benjamini, Y., & Hochberg, Y. (1995). Controlling the false discovery rate. Journal of the Royal Statistical Society B, 57(1), 289–300.
- Newey, W. K., & West, K. D. (1987). Econometrica, 55(3), 703–708. · Sen, P. K. (1968). Journal of the American Statistical Association, 63(324), 1379–1389.
- Chen, T., & Guestrin, C. (2016). XGBoost. KDD '16. · Shi, X., et al. (2015). Convolutional LSTM network. NeurIPS 28.
- Virtanen, P., et al. (2020). SciPy 1.0. Nature Methods, 17, 261–272.
CHECK: verify each citation (year, pages, DOI/URL) and delete any you cannot verify.

## Use of Super Intelligence (SI)
Team members used AI assistants (ChatGPT, Codex and Claude) to help plan the workflow, write and review code and tests, and draft documentation and explanations of statistical concepts. The team made the design decisions, ran all data processing and statistics, reviewed and tested AI-generated code, and checked results independently with SciPy. XGBoost and ConvLSTM are machine-learning components of the tool, not tools used to write it.
CHECK: each member confirms which AI tools they really used; edit the list to match. Do not claim NASA certification.
