# Distribution guide

See the English README for CPU installation, Linux/Windows recipes, architecture,
existing scores, hardware policy, numerical tolerances and platform limitations.
The application needs Python 3.14.4; new environments must not overwrite `.venv`.

The immutable payload is listed in `distribution-manifest.json`. Verify it with
`python scripts/doctor.py --integrity-only` before launching. CPU dependencies
are fully pinned by platform and wheel SHA-256. Runtime user-generated outputs
are not required to appear in that original payload manifest.

Historical scientific bytes are copied unchanged. `config/portable_provenance.json`
binds each original manifest hash to relative inputs and content fingerprints.
Keep it with the package. Do not manually replace absolute paths inside archived
scientific results: their provenance remains historical; runtime resolution is
provided by the separate relocation binding.

Windows wheels/recipes are supplied as unvalidated Windows execution candidates.
The original Linux NVIDIA environment was not replaced; offline GPU wheels and a
new clean NVIDIA installation were not validated. No Earth Engine credentials are
needed to explore the supplied real Querétaro data and evaluated model products.
