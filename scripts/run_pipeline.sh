#!/usr/bin/env bash

set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MODE="${1:?Specify build, history, forecast or all}"
REGION="${2:?Specify region name}"
PACKAGE="${3:?Specify dataset package path}"
GEOMETRY="${4:?Specify region GeoJSON path}"

PYTHON="$ROOT/.venv/bin/python"

if [[ ! "$REGION" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Invalid region name"
    exit 1
fi

PROCESSED="data/processed/$REGION"
RESULTS="outputs/$REGION"
CUBE="$PROCESSED/cube.npz"
METADATA="$PROCESSED/cube_metadata.json"

mkdir -p "$PROCESSED" "$RESULTS/logs"

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=8

trap 'echo "PIPELINE FAILED at line $LINENO" >&2' ERR

run() {
    local name="$1"
    shift

    echo ""
    echo "================================================"
    echo "AURORA | $name"
    echo "================================================"

    "$@" 2>&1 | tee "$RESULTS/logs/$name.log"
}

validate_cube() {
    "$PYTHON" - "$CUBE" "$METADATA" <<'PY'
import json
import sys
import numpy as np

with open(sys.argv[2]) as f:
    metadata = json.load(f)

assert metadata["received_months"] == 300
assert metadata["expected_months"] == 300
assert not metadata["missing_months"]

with np.load(sys.argv[1]) as data:
    X = data["X"]
    valid = data["valid"]
    region = data["region_mask"]
    dates = data["dates"].astype("datetime64[M]")

assert X.shape == valid.shape
assert X.shape[0] == 300
assert X.shape[-1] == 1
assert region.shape == X.shape[1:3]
assert region.dtype == bool
assert region.any()

assert dates[0] == np.datetime64("2001-01")
assert dates[-1] == np.datetime64("2025-12")
assert np.all(np.diff(dates).astype(int) == 1)
assert np.array_equal(valid, np.isfinite(X))
assert not valid[:, ~region, :].any()

print("Cube shape:", X.shape)
print("Regional pixels:", region.sum())
print("Valid observations:", valid.sum())
print("CUBE VALIDATION: PASSED")
PY
}

build() {
    run build "$PYTHON" scripts/build_cube.py \
        --package "$PACKAGE" \
        --region "$GEOMETRY" \
        --output "$PROCESSED" \
        --start 2001-01 \
        --end 2025-12

    run validation validate_cube
}

history() {
    validate_cube

    run history "$PYTHON" scripts/analyze_history.py \
        --cube "$CUBE" \
        --metadata "$METADATA" \
        --output "$RESULTS/history"
}

forecast() {
    validate_cube

    run xgboost "$PYTHON" scripts/train_xgb.py \
        --cube "$CUBE" \
        --output "$RESULTS/xgboost" \
        --device cuda

    run convlstm "$PYTHON" scripts/train_deep.py \
        --cube "$CUBE" \
        --output "$RESULTS/convlstm" \
        --epochs 15 \
        --batch-size 16 \
        --patience 4

    run benchmark "$PYTHON" scripts/evaluate.py \
        --cube "$CUBE" \
        --xgb "$RESULTS/xgboost/model.ubj" \
        --deep "$RESULTS/convlstm/best_model.pt" \
        --output "$RESULTS/final_benchmark.json"

    run forecast_xgboost "$PYTHON" scripts/predict.py \
        --cube "$CUBE" \
        --metadata "$METADATA" \
        --model "$RESULTS/xgboost/model.ubj" \
        --engine xgboost \
        --output "$RESULTS/forecast/xgboost"

    run forecast_convlstm "$PYTHON" scripts/predict.py \
        --cube "$CUBE" \
        --metadata "$METADATA" \
        --model "$RESULTS/convlstm/best_model.pt" \
        --engine convlstm \
        --output "$RESULTS/forecast/convlstm"
}

case "$MODE" in
    build)
        build
        ;;
    history)
        history
        ;;
    forecast)
        forecast
        ;;
    all)
        build
        history
        forecast
        ;;
    *)
        echo "Invalid mode: $MODE"
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo "AURORA | PIPELINE COMPLETED"
echo "Region: $REGION"
echo "Mode: $MODE"
echo "Results: $RESULTS"
echo "================================================"
