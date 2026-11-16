# Reparación de estabilidad y Pyright — AURORA

15 de noviembre de 2026. Trabajo exclusivo en `feature/model-core`, continuando el árbol local existente. Diagnóstico inicial: `/tmp/aurora-diagnostics-v9.txt`, 51 errores. No se instalaron ni actualizaron dependencias, no se eliminaron ni debilitaron pruebas y no se realizaron commits, push ni merges.

## Cambios

- `pyrightconfig.json`: selecciona `.venv` como entorno del analizador. No desactiva reglas ni excluye código. No se añadieron `Any` ni `type: ignore` para ocultar los diagnósticos.
- `desktop/ai_lab.py`, `window.py`: comprueban explícitamente la existencia del directorio predictivo, resultado e historial antes de operar con rutas. Los estados ausentes fallan con un mensaje controlado o no ejecutan la interacción.
- `desktop/globe.py`, `time_machine.py`: descartan cuadros recibidos con la vista vacía o índices fuera de su calendario. Las decisiones sobre tamaño usan la máscara del dataset activo. Se comprueba que la rasterización de la cartografía haya devuelto una imagen.
- `desktop/time_machine.py`: la reproducción ahora vuelve al inicio/final del intervalo seleccionado; anteriormente podía quedar detenida en un extremo al usar módulo sobre el calendario completo.
- `desktop/temporal.py`: resuelve los cruces de extremos usando los sliders concretos y protege el calendario vacío, sin asumir que `QObject.sender()` tenga método `value()`.
- `desktop/tasks.py`: contrato `Callable[[str], None]` para la devolución de errores. Se preservó el mecanismo local existente de buzón, temporizador Qt, cancelación y tokens de generación.
- `block_engine.py`, `desktop/global_results.py`: ventanas Rasterio mediante `Window.from_slices`, equivalente para estos índices y compatible con sus contratos estáticos.
- `geospatial.py`, `desktop/globe.py`, `desktop/window.py`: acceso explícito a las dos componentes de transformaciones 2D, evitando la ambigüedad de la firma 2D/3D de Rasterio.
- `block_multivariate.py`, `scripts/evaluate_hac.py`, `tests/test_geospatial.py`: `allow_pickle=False` explícito en guardado NumPy. El entorno actual expone ese argumento reservado; los arrays científicos usados no requieren objetos serializados.
- `models/convlstm.py`: rechaza explícitamente una secuencia de longitud cero antes de acceder al estado final. Arquitectura, pesos y cálculo de secuencias válidas permanecen iguales.
- `trend.py`: acceso al primer componente de `theilslopes`, equivalente al atributo `slope`, sin modificar la fórmula ni sus parámetros.
- `scripts/validate_aurora5.py`, `validate_global_engine.py`, `validate_planetary.py`: variable de ventana inicializada, comprobación de rutas creadas y argumentos de cámara explícitos.
- Pruebas existentes: comprobación de bias antes de modificarlo en el fixture ConvLSTM; referencias numéricas SciPy convertidas explícitamente a arrays numéricos; sin cambiar tolerancias ni expectativas científicas.

Se añadieron cinco pruebas y se reforzó una existente: cuadros tardíos tras reset, índices inválidos, selector temporal vacío/cruces, fallo de una generación cancelada mientras ya existe una nueva y secuencia ConvLSTM vacía. La prueba de Time Machine también verifica reproducción bidireccional dentro del intervalo y un cuadro tardío después de reset.

Los archivos modificados antes de esta intervención, incluidas traducciones y reparaciones previas, se conservaron. El estado Git completo incluye esos cambios anteriores; no debe interpretarse todo el diff de la rama como trabajo de esta reparación.

## Validaciones finales

| Validación | Resultado |
|---|---|
| `.venv/bin/pyright` | **0 errores, 0 advertencias, 0 informaciones** |
| `PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-mpl .venv/bin/python -m pytest -q` | **118 pruebas aprobadas en 19.58 s**, conservando las 113 iniciales |
| `.venv/bin/python -m compileall -q src scripts tests` | Código de salida 0 |
| `.venv/bin/python -m pip check` | `No broken requirements found.` |
| `git diff --check` | Código de salida 0 |

La validación funcional utilizó `validate_ui(Path('docs/evidence/desktop-repair'))` de `scripts.validate_global_engine`, guardando evidencia nueva sin sobrescribir el informe anterior. Recorrió nueve pestañas, cargó Zarr en Planetary Explorer y Time Machine, verificó dieciséis vistas predictivas y ejecutó un trabajo descriptivo real y otro cancelado. Resultado: **ninguna excepción Qt no manejada**. Los nombres de los nuevos trabajos únicos constan en `ui_validation.json`; no sustituyen resultados anteriores.

Se ejecutó además `validate_real` del mismo módulo con el nuevo directorio de evidencia. La conversión NPZ/Zarr volvió a comprobarse exacta. OLS, Sen, HAC y coeficientes Pearson/Spearman coincidieron con los productos existentes; diferencias BH máximas de 2.22e-16. No se reentrenaron modelos ni se recalibraron resultados. Se verificaron **315 archivos** contra los manifiestos previos, incluyendo ambos cubos NPZ, modelos/productos históricos y exportaciones: todos conservaron su SHA256.

## Evidencia y alcance

Los registros de comandos, resultados, preservación, verificaciones finales y capturas están en `docs/evidence/desktop-repair/`. `changed_source_manifest.json` documenta el estado de los archivos intervenidos, no un commit ni una sustitución del trabajo local previo.

La validación Qt se ejecutó con plataforma **offscreen**, por lo que verifica carga, renderizado, eventos, cancelación y cierre, pero no certifica el compositor gráfico ni el rendimiento interactivo de la pantalla de presentación. La cancelación sigue siendo cooperativa entre operaciones. No se identificó un bloqueo funcional en los recorridos ejecutados. Las limitaciones de cobertura nacional/global y de datos de los informes anteriores siguen vigentes.
