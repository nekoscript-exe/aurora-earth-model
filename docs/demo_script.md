# AURORA — Demo (7 slides, English) and form drafts

> Rules (official): max 7 slides including title; all text in English; public link, tested in incognito;
> no people under 18 in images/video; names of team, members and the challenge must appear.
> Numbers below come from the real run (`metrics.json`, `regional_trend.json`). Re-check them against the final run.

## Slides
**1. Title.** AURORA — Earth System Intelligence Model. *Where is vegetation changing, and is it significant?*
Team AURORA: Ian, Yatz, René, Sophia · NASA Space Apps 2026 · Challenge: "Changes in the Earth System" (title as listed on the site).

**2. The challenge.** What is changing, where, how much, and is it significant? A trend can go up in one place and
down in another. Case study: vegetation (NDVI) in Querétaro, Mexico, 2001–2025.

**3. NASA data.** MODIS/Terra Vegetation Indices (MOD13Q1 v061), 250 m, every 16 days, accessed via Google Earth Engine.
Quality-filtered, monthly composites, 1 km grid, 11,511 pixels.

**4. How it works.** Monthly NDVI → annual means (≥ 9 valid months) → per-pixel linear trend (OLS) →
Benjamini–Hochberg correction (q < 0.05) → maps. Sen's slope and HAC errors as robustness checks.

**5. Results (maps).** Slide image: `map_significance.png` + `map_slope.png`.
17.8 % of tested pixels show a significant increase, 4.5 % a significant decrease, 77.7 % no significant evidence.
Regional mean: +0.0012 NDVI/year, not significant at 5 % (p = 0.066).

**6. Validity and limits.** Independent recomputation (scipy) reproduces the results; multiple-testing correction;
coverage 94.7 %. Limits: 1 km pixels, clouds in the rainy season, only linear trends, no causal claims.

**7. Impact and next steps.** An open, reproducible tool for "data detectives": any region, any variable.
Next: add rainfall and land cover to test explanations; extend to other regions. Credits: NASA, LP DAAC, Google Earth Engine.

Speaker split: Yatz slides 3, Ian slide 4, Sophia slides 5–6, all slides 1–2 and 7.
Add readable fonts, one image per slide, few words.

## Form drafts (English) — edit to match what the team really did
**Project Name:** AURORA — Earth System Intelligence Model

**High-Level Project Summary:** AURORA is a reproducible tool that finds where and how much vegetation (NDVI) changes
in Querétaro, Mexico, from 2001 to 2025 using NASA MODIS data, and tests whether each change is statistically
significant. It produces maps of trend, magnitude, significance and data coverage.

**Detailed Project Description:** [Adapt sections 1, 3, 6 and 7 of `docs/scientific_report.md` to English.]

**NASA Data:** MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061 (MOD13Q1; Didan, 2021,
DOI 10.5067/MODIS/MOD13Q1.061), accessed through Google Earth Engine.

**Use of Super Intelligence (SI):** [Team to confirm and write exactly what was used. Draft:] "Team members used AI
assistants (e.g., ChatGPT and Claude) to help plan the workflow, draft code, tests and documentation. All data
processing, statistics and results were run and checked by the team; AI-generated code was reviewed and tested,
and results were independently recomputed with SciPy."

**Space Agency Partner Data and Other References:** Google Earth Engine; SciPy; XGBoost; PyTorch; references in the report.
