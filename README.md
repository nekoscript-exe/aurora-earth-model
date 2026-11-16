# AURORA — Earth System Intelligence

A local scientific desktop application for exploring real satellite observations, spatial/temporal trends, paired NDVI–LST relationships, and evaluated one-month predictive models. The interface supports English and Spanish with an immediate, persistent language selector. English is the default on a new installation.

**Validated observations:** Querétaro, Mexico; NDVI and daytime LST; 300 monthly observations from January 2001 through December 2025, native EPSG:32614 grid, 171 × 161 cells. Missing/QA-excluded observations remain missing. Mexico at 5 km and worldwide land coverage at 50–100 km are preparation targets, **not complete or scientifically validated datasets**.

## Demo distribution

The distribution builder includes the two real historical cubes, exact Zarr copies, existing scientific results, and four trained models: XGBoost and ConvLSTM for each of NDVI and LST. It excludes development environments, credentials, Earth Engine authentication, synthetic result directories, and unrelated regions. The offline demonstration does **not** require a Google Earth Engine account, token, or network connection after installation.

The application archive and CPU wheel archives are separate, SHA-256-manifested artifacts. Extract the application and the wheel archive for your platform. Verify the archive SHA-256 sidecars, then use the installer. The payload verifier runs before dependencies are installed; pip additionally verifies every locked CPU wheel hash. SHA-256 provides integrity, not publisher authentication; obtain the sidecar hashes through a trusted channel.

### Linux CPU — clean-environment validation performed

Provide **Python 3.14.4**, x86-64 Linux with the desktop system libraries needed by Qt. The supplied wheels require glibc ≥2.34; this is a wheel-tag requirement, not a claim that every such Linux distribution has been tested. Do not run the installer in the development `.venv`.

```bash
# Run from the extracted application directory.
bash installers/install-linux.sh --wheelhouse /path/to/linux-cpu-wheels
bash installers/run-linux.sh
```

Without `--wheelhouse`, the installer retrieves the same hashed CPU wheels online. It creates `.aurora-venv` and refuses to overwrite an existing environment. To use another new location:

```bash
python3.14 scripts/install.py --prefix /new/path/aurora-cpu --profile cpu --wheelhouse /path/to/linux-cpu-wheels
/new/path/aurora-cpu/bin/python scripts/desktop.py --device cpu
```

### Windows CPU — installer recipe, not Windows compatibility certification

PowerShell wrappers and a platform-specific hashed wheel lock are supplied. Windows wheel availability and Python dependency metadata closure were checked from Linux; **installation, DLL loading, desktop rendering and inference have not been executed on Windows**. Windows support remains unvalidated. Python 3.14.4 x64 and the appropriate Microsoft/Qt runtime system components are required; those OS prerequisites have not been experimentally established here.

```powershell
# In the extracted application directory; use a new environment path.
powershell -File installers/install-windows.ps1 -Wheelhouse C:\AuroraWheels\windows-cpu
powershell -File installers/run-windows.ps1 -Device cpu
```

The Windows wheel archive is separate from the Linux wheel archive. Do not point an installer at wheels for another platform. Existing tests that create symlinks may require Windows Developer Mode/appropriate permissions; Windows tests have not been run.

### NVIDIA profile and explicit device selection

The original development environment is preserved. New CPU environments use `torch==2.14.1+cpu` and Linux `xgboost-cpu==3.4.1`; they contain no CUDA/NVIDIA runtime packages. The NVIDIA profile pins the original Linux environment (`torch==2.14.1+cu130`, XGBoost 3.4.1 and NVIDIA dependencies). A separate clean NVIDIA installation and Windows GPU installation were not validated; GPU wheels are not bundled in the CPU archives.

```bash
# Optional Linux NVIDIA recipe, always targeting a NEW environment.
python3.14 scripts/install.py --profile nvidia --prefix /new/path/aurora-nvidia
python3.14 scripts/desktop.py --device cpu   # when using an already provisioned interpreter
# Prefer the installed environment interpreter, not a system Python without dependencies.
.aurora-venv/bin/python scripts/desktop.py --device cpu
.aurora-venv/bin/python scripts/doctor.py --device auto
```

`auto` probes actual CUDA execution and falls back to CPU if unavailable/incompatible. `cpu` does not probe CUDA. Explicit `cuda` fails clearly if execution is unsupported. `AURORA_DEVICE=cpu` is also available to the saved-inference functions; the desktop CLI has `--device`. XGBoost map inference deliberately remains on CPU. Existing training scripts are not invoked by installation or the demo.

## Health checks and inference reproduction

```bash
.aurora-venv/bin/python scripts/doctor.py --device cpu
.aurora-venv/bin/python scripts/doctor.py --integrity-only
.aurora-venv/bin/python scripts/validate_distribution_inference.py --require-cpu-build
.aurora-venv/bin/python scripts/forecast_saved.py --dataset data/processed/queretaro_lst --run outputs/aurora5/queretaro_lst --output /new/path/verification-estimates --device cpu
```

Health checks verify imports, registered observations, evaluated model qualification, result freshness, hardware policy, and distribution integrity. Outputs must use new directories. Forecasts for January 2026 are **retrospective model estimates, not new satellite observations**.

The saved ConvLSTM CUDA maps were produced with TF32-enabled convolutions. CPU FP32 inference is bit-identical between the original and independent CPU environments for all four models, but differs slightly from those archived CUDA maps. Validation keeps exact masks/dates, uses strict XGBoost tolerance (1e-6), and a documented TF32 envelope for ConvLSTM (1e-3 NDVI; 1e-2 °C LST). Observed maximum differences are approximately 0.0003101 NDVI and 0.0015831 °C; a CUDA control reproduced the archived maps exactly with TF32 and approached CPU results with TF32 disabled. No historical maps or scores are rewritten.

## Architecture and portability

- `aurora.catalog`: central metadata/configuration registry and bounded NPZ/NPY/Zarr reads. NPZ extraction is cached; scientific calculations use native grids, masks and physical units.
- `aurora.block_engine` / `block_multivariate`: spatial blocks, disk-backed maps and global BH correction; area-weighted regional summaries, explicit observation support and inference limits.
- `aurora.models`: existing statistical baselines, XGBoost and ConvLSTM; temporal splits and train-only normalization are preserved.
- `aurora.desktop`: nine PySide6/Matplotlib tabs, cancellable workers, bilingual controls, scientific exports and qualified model discovery.
- `aurora.hardware`: explicit CPU/auto/CUDA inference policy and execution probe.
- `aurora.portability`: content-based, path/mtime-independent dataset identities. The distribution carries a separate, manifest-hash-bound relocation sidecar; historical JSON/NPZ/Zarr/GeoTIFF/model bytes and absolute provenance records remain intact. Runtime references resolve inside the extracted package rather than the original workstation. New jobs within a registered project record relative input locations and content identities.
- `aurora.distribution`: allowlisted demo assembly, scientific-audit checks, deterministic ZIP timestamps/order, per-file SHA-256 manifest, and integrity verification. User-generated files/environments are outside the immutable payload manifest; listed payload files remain verified.

```bash
# Development checkout, existing environment; never modifies scientific sources.
.venv/bin/python scripts/build_distribution.py --output /new/path/demo --archive /new/path/aurora-demo.zip
# Optional single-archive Linux bundle:
.venv/bin/python scripts/build_distribution.py --output /new/path/demo-offline --archive /new/path/demo-offline.zip --wheelhouse /path/to/linux-cpu-wheels
```

Keep the extracted project structure and `config/portable_provenance.json` together. Copied legacy results without a verified relocation binding remain stale; paths are never silently guessed. Archive reconstruction is deterministic for identical source snapshots. The original development requirements files remain as historical environment snapshots; new installations use `requirements/locks/*-hashed.txt` for CPU.

## Existing scientific results — unchanged

Held-out monthly test period: 2022–2025. Models are compared on common valid observations within each variable. MAE/RMSE are dimensionless for NDVI and degrees Celsius for LST.

| Variable | Model | MAE | RMSE | R² | Common observations |
|---|---|---:|---:|---:|---:|
| NDVI | XGBoost | 0.042175 | 0.063527 | 0.884433 | 489,633 |
| NDVI | ConvLSTM | 0.044379 | 0.063608 | 0.884137 | 489,633 |
| LST | XGBoost | 2.087552 °C | 2.830701 °C | 0.819426 | 507,583 |
| LST | ConvLSTM | 2.211072 °C | 3.012322 °C | 0.795511 | 507,583 |

Sources: `outputs/queretaro/final_benchmark.json` and `outputs/aurora5/queretaro_lst/final_benchmark.json`. This release does not retrain, tune, recompute, or replace these scores. Correlation is not causation; missing/seasonal coverage, autocorrelation and multiple comparisons constrain inference. Regional models are not certified for other regions.

## Requirements: measurements versus estimates

**Measured host:** Linux x86-64, glibc 2.43, Python 3.14.4, 16 logical CPUs and approximately 59.6 GiB RAM. An independent CPU-only environment was provisioned; CPU runtime installation occupies about 2.3 GiB. The Linux wheel set is about 614 MiB; Windows wheel set about 563 MiB. Qt screenshots use the real application with `offscreen`; the physical display compositor and Windows were not certified by these checks.

**Estimates, not experimentally established minima:** 4 logical CPU cores, 4 GiB RAM and 8 GiB free disk for a modest Querétaro demo; 8 cores and 8 GiB RAM recommended. Keep additional disk space for archives, extracted wheels, caches and new outputs. No NVIDIA GPU is required for the CPU demo. Exact timings/resource measurements and platform limitations belong in `docs/evidence/distribution/report.md` in the development checkout.

## Validation and evidence

The original 136 tests are retained. New tests cover relocation/mtime loss, content tampering, unsafe cross-platform paths, immutable legacy manifests, deterministic archives, CPU policy, independent installation and payload integrity.

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-mpl .venv/bin/python -m pytest -q
.venv/bin/pyright
.venv/bin/python -m compileall -q src scripts tests
.venv/bin/python -m pip check
git diff --check
```

Use the new CPU environment interpreter to repeat pytest without CUDA. `scripts/validate_i18n.py` reads the available real data and captures all nine tabs in both languages with isolated preferences. The distribution report records checks from an independently extracted copy, CPU inference comparisons and remaining platform limits. Previous implementation reports remain under `docs/`.

## Project and third-party licensing

This workflow does **not** select a project license or grant new redistribution rights. `DISTRIBUTION_NOTICE.txt` in generated packages records that status. Third-party software retains its own terms included in its wheels/installations; geography attribution is in `assets/desktop/geography/README.md`, and MODIS sources are retained in dataset metadata. The project owners must decide the project license before public licensing claims are made.
