"""Explicit scientific payloads for AURORA distribution editions."""

LITE_DATASETS = {
    "queretaro_ndvi_zarr": "queretaro",
    "queretaro_lst_zarr": "queretaro",
}

FULL_DATASETS = {
    **LITE_DATASETS,
    "mexico_ndvi_2001_2025_zarr": "mexico",
    "mexico_lst_2001_2025_zarr": "mexico",
    "global_ndvi_2001_2025_zarr": "global",
    "global_lst_2001_2025_zarr": "global",
    "global_precip_2001_2025_zarr": "global",
}

LITE_RESULTS = (
    "outputs/global_engine/queretaro_ndvi_final",
    "outputs/global_engine/queretaro_lst_final",
    "outputs/global_engine/queretaro_paired_final",
)

FULL_RESULTS = LITE_RESULTS + tuple(
    f"outputs/global_engine/jobs/{name}"
    for name in (
        "mexico_ndvi_2001_2025",
        "mexico_lst_2001_2025",
        "mexico_ndvi_lst_2001_2025",
        "global_ndvi_2001_2025",
        "global_lst_2001_2025_final",
        "global_ndvi_lst_2001_2025_final",
        "global_precip_2001_2024",
        "global_ndvi_precip_2001_2025",
        "global_lst_precip_2001_2025",
    )
)

PROFILES = {
    "lite": {
        "datasets": LITE_DATASETS,
        "results": LITE_RESULTS,
    },
    "full": {
        "datasets": FULL_DATASETS,
        "results": FULL_RESULTS,
    },
}
