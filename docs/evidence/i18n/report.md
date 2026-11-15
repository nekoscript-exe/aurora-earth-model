# AURORA — Internacionalización final inglés/español

Fecha: 15 de noviembre de 2026. Base y HEAD: `0c8eb08`. Rama: `feature/model-core`. Se trabajó sobre el estado existente, inicialmente limpio. No se realizaron commits, push, merges, cambios de rama ni actualizaciones de dependencias.

## Resultado

La aplicación de escritorio usa inglés en una instalación nueva y ofrece un selector **Language / Idioma** en la cabecera. La preferencia se guarda mediante el mismo `QSettings("AURORA", "Desktop")` existente, clave `language`. El cambio se aplica de inmediato a los controles y gráficos existentes, sin reiniciar, reconstruir ventanas, cargar modelos nuevos ni ejecutar cálculos científicos. Los valores de configuración inválidos vuelven al inglés.

Se reutilizaron y ampliaron los catálogos Qt `.ts`/`.qm`: **612 mensajes completos**, sin traducciones pendientes. Se cargan también las traducciones españolas de Qt incluidas en PySide6. Los diálogos de archivo usan Qt para respetar el idioma elegido con independencia del idioma del sistema operativo.

Las nueve pestañas quedan traducidas:

| Inglés | Español |
|---|---|
| Home | Inicio |
| Planetary Explorer | Explorador planetario |
| Time Machine | Máquina del tiempo |
| Predictive intelligence | Inteligencia predictiva |
| Multivariate Laboratory | Laboratorio multivariable |
| Scientific results | Resultados científicos |
| Spatial analysis | Análisis espacial |
| Temporal analysis | Análisis temporal |
| Execution log | Registro de ejecución |

Se localizaron botones, etiquetas, ayudas, títulos, leyendas, mensajes de disponibilidad/carga/progreso/cancelación/exportación, errores, informes, calendarios, navegación Matplotlib, editor de gráficos y diálogos. Los mensajes parciales de trabajadores se acumulan hasta completar la línea antes de traducir su presentación; no se altera el protocolo original ni el análisis de progreso.

## Implementación

| Archivos | Cambios |
|---|---|
| `src/aurora/desktop/i18n.py` | Preferencia y carga Qt existentes ampliadas; cambio en vivo; fuentes canónicas; actualización de controles con señales bloqueadas; traducción de mensajes compuestos y texto HTML sin alterar etiquetas, atributos, estilos o rutas; vistas localizadas de metadatos/logs; errores externos con resumen traducido y diagnóstico original en el registro técnico de Python. |
| `src/aurora/desktop/translations/aurora_es.ts`, `aurora_es.qm` | Catálogo español ampliado y compilado con `pyside6-lrelease` del entorno existente. |
| `src/aurora/desktop/canvas.py` | Traducción de títulos, leyendas y etiquetas regeneradas por Matplotlib. Un formateador delega el cálculo/formato numérico y traduce exclusivamente la cadena final, conservando localizadores y la política de formateadores predeterminados. |
| `src/aurora/desktop/toolbar.py` | Presentación localizada de acciones/ayudas; identificadores de callbacks originales intactos. |
| `src/aurora/desktop/dataset_controls.py` | Traducción de etiquetas del catálogo después de poblar/refrescar controles; conserva todos los IDs y la lógica del registro central. |
| `src/aurora/desktop/window.py` | Selector persistente, nueve títulos, controles/mensajes/informes, acumulación de líneas de log y claves internas de selección independientes del idioma. |
| `src/aurora/desktop/ai_lab.py`, `multivariate_lab.py`, `global_results.py` | Modos y capas con claves canónicas en `itemData`; presentación y gráficos bilingües; mensajes y diálogos localizados. |
| `src/aurora/desktop/globe.py`, `time_machine.py`, `temporal.py` | Controles, estados temporales, leyendas, tooltips, marcadores y mensajes traducidos; dimensiones de etiquetas de marcadores medidas con el texto traducido. |
| `src/aurora/desktop/welcome.py`, `pixel_lab.py`, `report.py` | Inicio, laboratorio de píxeles e informe científico traducidos, incluidas advertencias y límites de inferencia. |
| `scripts/validate_i18n.py` | Validación de sólo lectura con resultados/datos reales existentes y capturas en ambos idiomas; preferencias aisladas en `/tmp`. |
| `tests/test_i18n.py` | 18 pruebas específicas adicionales; ninguna prueba anterior se eliminó o debilitó. |

Las etiquetas excesivamente largas de exportación y de transparencia se abreviaron, con los formatos completos conservados en el tooltip. No se modificaron colores, estilos, disposición científica, escalas, funciones de navegación ni cálculos.

## Casos de estabilidad comprobados

- Preferencia persistente verificada desde otro proceso, instalación nueva en inglés y preferencia inválida.
- Arranque directo en inglés y español, cambio repetido entre ambos y conservación de la pestaña, valores internos de selectores y cámara.
- Fuentes distintas para etiquetas ambiguas: `Home` y `Start` se muestran como `Inicio`, pero recuperan correctamente su texto inglés original.
- Modos predictivos y capas resueltos mediante claves canónicas, sin depender del texto traducido ni emitir cambios de selección al retraducir.
- Gráficos de modelos de referencia y meses regenerados en cada dibujo: la revisión visual encontró que traducir objetos Text una sola vez no bastaba; se corrigió en el formateador visual.
- Aplicación real de opciones del editor Matplotlib en español, manteniendo datos, unidades, escala e IDs de acciones.
- HTML, atributos, estilos y rutas intactos después de traducir; códigos EPSG, nombres de variables, unidades y fórmulas preservados.
- Actualización del catálogo y estados de datos no disponibles traducidos después del cambio de idioma.
- Mensajes parciales de trabajadores: no se muestran fragmentos JSON mezclados con la traducción de una línea posterior.

## Validación final

| Comprobación | Resultado |
|---|---|
| `.venv/bin/pyright` | **0 errores, 0 advertencias, 0 informaciones** |
| Suite completa pytest | **136 aprobadas en 21.74 s**: 118 anteriores + 18 nuevas |
| `compileall` en `src scripts tests` | Código de salida 0 |
| `pip check` | `No broken requirements found.` |
| `git diff --check` | Código de salida 0 |
| Validación Qt con datos reales | Nueve pestañas, 16 vistas predictivas por idioma, cinco vistas multivariadas, capas disponibles, inspección nativa, diálogos de archivos/error y editor de gráficos; sin excepciones Qt no manejadas |
| Preservación científica | **315 archivos** verificados contra SHA256 previos, todos iguales; huellas de los dos almacenes Zarr registrados sin cambios |

No se desactivaron reglas de Pyright ni se añadieron `Any` o `type: ignore` para silenciar diagnósticos. Las modificaciones de archivos previamente versionados se limitan a `src/aurora/desktop/`; no se modificaron motores científicos, métricas, modelos, datos, NPZ, Zarr, GeoTIFF o checkpoints. El formateo localizado afecta únicamente la presentación de metadatos: los JSON originales y sus valores siguen intactos.

Las primeras ejecuciones con Zarr dentro del sandbox quedaron bloqueadas en la señalización del bucle asíncrono (`zarr.core.sync` / `zarr_io`). Se interrumpieron y repitieron fuera del aislamiento con autorización. No se cambiaron el backend, las pruebas ni sus expectativas para sortear ese bloqueo. Los registros finales corresponden a las ejecuciones completadas.

## Comandos reproducibles

Desde la raíz del repositorio, con el entorno virtual existente:

```bash
.venv/bin/pyside6-lrelease src/aurora/desktop/translations/aurora_es.ts -qm src/aurora/desktop/translations/aurora_es.qm
.venv/bin/pyright
PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-i18n-mpl .venv/bin/python -m pytest -q -o faulthandler_timeout=30
PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-i18n-mpl .venv/bin/python scripts/validate_i18n.py
.venv/bin/python -m compileall -q src scripts tests
PIP_CACHE_DIR=/tmp/aurora-i18n-pip-cache .venv/bin/python -m pip check
git diff --check
```

Para uso normal: `.venv/bin/python scripts/desktop.py`. El selector guarda la preferencia del usuario real. Los tests y el script de evidencia aíslan sus preferencias temporales y no cambian esa configuración.

## Evidencias y límites

- `pyright-final.txt`, `pytest-final.txt`, `final_checks.json`: validaciones finales y códigos de salida.
- `ui_validation.json`, `translation-audit.json`, `ui-log.txt`: recorrido funcional y textos observados.
- `visual/`: **40 capturas PNG reales de Qt**, con las nueve pestañas en ambos idiomas y vistas/diálogos adicionales.
- `preservation.json`: verificación de archivos científicos y huellas del almacenamiento.
- `changed_files.json`, `implementation_manifest.json`, `artifact_manifest.json`: inventario de cambios y hashes de fuentes/evidencias.
- `initial-text-inventory.json`: inventario previo de textos para rastrear la ampliación del catálogo.

Las capturas se realizaron con la plataforma Qt **offscreen**; son renderizados de la aplicación real, no maquetas, pero no certifican el compositor o la GPU de la pantalla de presentación. No se identificaron textos relevantes de la interfaz existente pendientes de traducción en los recorridos y la auditoría realizados.

Se conservan deliberadamente nombres propios y marcas (AURORA, NASA, Natural Earth, nombres geográficos), identificadores científicos/técnicos (NDVI, LST, XGBoost, ConvLSTM, EPSG, nombres de características y mapas de colores), rutas, fechas ISO y unidades originales (`degC`, `°C`, `NDVI/year`, `1/year`, `years`). Los nombres nativos `English` y `Español` facilitan seleccionar idioma. Esto no representa una mezcla de mensajes de interfaz. Los diagnósticos técnicos externos conservan su texto original en el registro técnico de Python; el mensaje mostrado al usuario se localiza mediante una traducción conocida o un resumen traducido.
