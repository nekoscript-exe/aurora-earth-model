# Contrato de datos v1
Caso inicial: Querétaro, NDVI mensual 2001–2025, MODIS/061/MOD13Q1; máscara SummaryQA == 0; factor 0.0001; mediana mensual de observaciones válidas. Verificar catálogo. EPSG:32614, 1000 m, extensión y transformada fijas, máscara regional. No rellenar faltantes con cero. Documentar agregación espacial.
- data/raw/ndvi_YYYY_MM.tif: GeoTIFF Float32, nodata=-9999, una banda, rejilla idéntica.
- manifest.csv (raíz): date,path,variable,unit,crs,scale_m,valid_fraction,source_id. date YYYY-MM-01; paths relativos a raíz.
- config/region.geojson: límite documentado; grid.json: CRS, transformada, width, height, nodata.
- data/processed/cube.npz: X [T,H,W,C] float32, valid [T,H,W,C] bool, dates [T] ISO, channels [C]; faltantes NaN.
- outputs/trend_slope.tif, trend_p.tif, trend_q.tif, trend_change.tif, trend_n.tif, forecast_ndvi.tif (opcional), metrics.json, run_metadata.json.
Entregar primero tres TIFF por almacenamiento compartido, manifest y grid.json por Git. Resultados ligeros QA pueden ir en docs/evidence/ (outputs/ se ignora). No subir claves ni datos pesados.
Yatz puede comenzar sin Ian: entorno, acceso Earth Engine, región, tres imágenes, exportador, validador y QA. Luego exportar lotes conservando rejilla; registrar bloqueos.
Ian: mínimo 9 meses/año y 15 años válidos por píxel, pendiente OLS/Sen, prueba de significancia, FDR BH y cobertura. Predicción opcional del siguiente mes con 12 meses previos; train 2002–2018, val 2019–2021, test 2022–2025. No fuga temporal.
Cambios del contrato requieren acuerdo de ambos.
