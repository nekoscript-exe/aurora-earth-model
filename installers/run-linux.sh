#!/usr/bin/env bash
set -euo pipefail
AURORA_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$AURORA_ROOT"
"$AURORA_ROOT/.aurora-venv/bin/python" "$AURORA_ROOT/scripts/doctor.py" --integrity-only
exec "$AURORA_ROOT/.aurora-venv/bin/python" "$AURORA_ROOT/scripts/desktop.py" --device cpu "$@"
