# AURORA — Model Card

## Overview

AURORA is a geospatial analytical engine designed to
detect, quantify and investigate long-term vegetation
trends using satellite-derived NDVI observations.

## Satellite data

- Source: MODIS/061/MOD13Q1
- Variable: Normalized Difference Vegetation Index
- Historical period: January 2001 – December 2025
- Regional resolution: 1 km
- Initial study area: Queretaro, Mexico

## Statistical engine

- Ordinary Least Squares regression
- Theil-Sen robust slope estimation
- Benjamini-Hochberg FDR correction
- Lag-1 residual autocorrelation
- Durbin-Watson diagnostics
- Newey-West HAC sensitivity analysis

Annual composites require at least nine valid months.
Trend estimation requires at least 15 valid years.
The nominal FDR significance threshold is 0.05.

## Predictive engine

- Persistence baseline
- Seasonal persistence baseline
- Historical climatology
- XGBoost regression
- Convolutional LSTM neural network

The predictive task estimates NDVI one month ahead
using the previous 12 months of observations.

## ConvLSTM architecture

- Input channels: NDVI and observation mask
- First recurrent layer: 16 channels
- Second recurrent layer: 32 channels
- Trainable parameters: 65,889
- Optimizer: Adam
- GPU acceleration: CUDA
- Mixed precision: BF16

## Temporal evaluation

- Training targets: 2002–2018
- Validation targets: 2019–2021
- Held-out test targets: 2022–2025

## Synthetic benchmark

| Model | MAE | RMSE | R2 |
|---|---:|---:|---:|
| ConvLSTM | 0.020950 | 0.026288 | 0.982040 |
| XGBoost | 0.022034 | 0.027742 | 0.979999 |
| Seasonal | 0.028501 | 0.035717 | 0.966845 |
| Persistence | 0.046637 | 0.056370 | 0.917418 |
| Climatology | 0.064273 | 0.080871 | 0.830025 |

Evaluated on 611,569 comparable synthetic observations.

These results do not establish predictive accuracy
on actual satellite observations.

## Limitations

- NDVI does not directly measure biodiversity.
- Vegetation trends do not establish causal relationships.
- Missing observations may introduce seasonal bias.
- Spatial and temporal dependence may affect significance.
- HAC is a sensitivity analysis, not a guarantee of validity.
- Non-significant trends do not establish absence of change.
- ConvLSTM patch boundaries may introduce spatial artifacts.
- One-month forecasts are not long-term climate projections.
- Real satellite model evaluation remains pending.

## Intended use

Environmental exploration, scientific education,
vegetation monitoring and hypothesis generation.

AURORA is not intended to replace field observations
or independent scientific validation.
