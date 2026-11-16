#!/usr/bin/env bash
set -euo pipefail
AURORA_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
AURORA_PYTHON="${AURORA_PYTHON:-python3.14}"
exec "$AURORA_PYTHON" "$AURORA_ROOT/scripts/install.py" "$@"
