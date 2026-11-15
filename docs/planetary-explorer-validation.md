# Planetary Explorer — informe de implementación y validación

Fecha: 15 de noviembre de 2026. Rama: `feature/model-core`.
Entorno ejecutado: Python **3.14.4**, PySide6 **6.12.0**; dependencias existentes.
No se realizaron commits, push, merges ni cambios de rama.

## Inspección previa y alcance

Antes de editar se comprobó la rama y `git status`. Existían:

- `src/aurora/desktop/window.py`, modificado localmente para importar e integrar
  Planetary Explorer como pestaña.
- `src/aurora/desktop/globe.py`, archivo local nuevo sin seguimiento.

Se conservaron y extendieron ambos cambios. No se encontró un `AGENTS.md`
aplicable en el árbol inspeccionado. No se revirtieron cambios del usuario.

La arquitectura separa los modelos (`src/aurora/models`), tendencias y registro
científico de variables de los widgets PySide6 del escritorio. El pipeline
`scripts/build_cube.py` construye `X[T,H,W,C]`, `valid`, `region_mask`, fechas y
metadatos de rejilla; el escritorio consume esos productos locales. Time Machine
usa Matplotlib; el explorador usa NumPy, Rasterio y QPainter. Los análisis y
predicciones conservan sus rutas y comportamiento.

El código inicial del explorador realizaba una inversión ortográfica y muestreo
por píxel, pero dependía de una caja geográfica para filtrar candidatos y no
validaba completamente la entrada. Esto presentaba riesgos en el antimeridiano,
rejillas rotadas, NoData finito, máscaras y metadatos inconsistentes. No se
estableció evidencia de un desplazamiento sistemático previo en Querétaro:
la validación final demuestra la colocación según la rejilla de entrada.

Las 27 pruebas preexistentes pasaban antes de las modificaciones.

## Cambios científicos y geoespaciales

`src/aurora/desktop/geospatial.py` contiene lógica independiente del widget:

- Proyecciones ortográficas directa e inversa en una esfera de referencia,
  coordenadas geográficas en orden longitud/latitud.
- Validación de CRS, transformadas afines finitas e invertibles, dimensiones,
  transformadas homogéneas de seis o nueve coeficientes y forma del cubo.
- Muestreo de referencia por inversión afín, pertenencia en coordenadas nativas
  y bordes semiabiertos; admite rejillas rotadas y longitudes que cruzan ±180°.
- Ruta de renderizado con GDAL: proyecta identificadores enteros de píxel con
  vecino más cercano y `tolerance=0.0`, y después consulta valores y máscaras.
  No reproyecta una imagen de valores con huecos que pudieran rellenarse.
- Exclusión explícita del hemisferio posterior y de píxeles fuera del disco.
- Comprobación del tipo de producto, fuente MODIS, variable, unidades, canal,
  fechas ordenadas, dimensiones, máscaras booleanas y rango del registro.
- Conservación de ceros observados. QA falso, NoData, NaN, infinito y exterior
  regional quedan transparentes. No se aplica otra vez el factor de escala.

No se modificaron los motores estadísticos ni predictivos, el registro de
variables, el contrato científico ni los archivos de datos existentes.
No se crearon observaciones satelitales, ni se interpolaron huecos espaciales o
fechas faltantes. Los arreglos artificiales de las pruebas son exclusivamente
fixtures de software y nunca se ofrecen como productos científicos.

## Cambios visuales e interacción

`src/aurora/desktop/globe.py` incorpora:

- Base cartográfica Natural Earth más detallada, costas vectoriales, colores
  oscuros, iluminación ilustrativa y un borde atmosférico discreto.
- Rasterización cartográfica regional adaptada al encuadre para evitar ampliar
  únicamente la máscara global de tierra. Esto no cambia las observaciones.
- Retícula con cobertura suavizada y fronteras con antialiasing.
- Fronteras internacionales y límites estatales con control de visibilidad.
  Límites internos visibles desde zoom 2; México usa trazos de escala 1:10m.
- Transiciones de 650 ms con aceleración y frenado, arco longitudinal corto y
  zoom logarítmico. El arrastre interrumpe una transición; la rueda admite
  órdenes sucesivas y los límites de zoom originales, 0.75–100.
- Rotación calculada con tiempo monotónico y limitada mientras se arrastra o
  se ejecuta una transición. Se evita renderizar la rotación con el widget oculto.
- Caché de geometría, base, proyección y trazos durante la reproducción temporal.
  Renderizado de hasta 640 píxeles por lado mayor en movimiento y 960 en reposo;
  se conserva la relación del encuadre y el espacio rectangular disponible.
- Leyendas que cambian con la variable: NDVI −0.2 a 1, `RdYlGn`; LST −10 a 70 °C,
  `turbo`. Los extremos saturados se indican con ≤/≥. La escala permanece fija
  entre fechas para permitir comparación. NoData se explica como transparente.
- Indicador de opacidad de 0–100%, controles temporales deshabilitados sin datos,
  pausa al ocultar la página, fecha original, cobertura, media y procedencia.
- Dos marcadores urbanos aproximados y pines WGS84 por doble clic; ocultación en
  hemisferio posterior, separación de etiquetas y borrado de pines temporales.
- Panel lateral desplazable y separador redimensionable; los controles siguen
  accesibles en la ventana mínima mediante desplazamiento vertical.

`window.py` conserva la integración local anterior y contrae el panel de
investigación al entrar al explorador. Un botón permite recuperarlo. Al cambiar
de pestaña se restaura; las ocho pestañas actuales siguen disponibles.

## Cartografía, archivos y procedencia

Nuevos recursos en `assets/desktop/geography/`:

| Archivo | Contenido |
| --- | --- |
| `land_50m.geojson` | 1,420 entidades de tierra, escala 1:50m |
| `countries.geojson` | 390 trazos de fronteras terrestres internacionales, 1:50m |
| `states.geojson` | 581 trazos internos de nueve países, 1:50m |
| `states_mexico.geojson` | 85 trazos internos de México, extraídos de 1:10m |
| `sources.json` | URL, fecha, CRS, escala, conteo y SHA-256 de los recursos |
| `README.md` | Procedencia, licencia, cobertura y límites cartográficos |

Se preservó `land.geojson`, recurso original de 110m. La aplicación funciona
sin red después de incluir los recursos. Natural Earth publica sus datos en
[dominio público](https://www.naturalearthdata.com/about/terms-of-use/).
La capa mexicana se filtró por `ADM0_A3 == MEX` sin simplificar sus coordenadas.
La densificación en memoria se aplica solamente a trazos cartográficos para
seguir la curva del globo, nunca a observaciones.

Archivos adicionales nuevos:

- `tests/test_geospatial.py`: 37 casos geoespaciales y de validación de entrada.
- `tests/test_planetary_explorer.py`: 8 casos de interacción y de integración.
- `scripts/validate_planetary.py`: validación reproducible contra archivos reales,
  capturas y mediciones locales; no descarga ni modifica datos.
- `docs/evidence/planetary/validation.json`: resultados estructurados.
- `docs/evidence/planetary/{earth,mexico,queretaro}.png`: vistas independientes.
- `docs/evidence/planetary/application.png`: aplicación integrada, 1280×820.
- `docs/evidence/planetary/application_minimum.png`: aplicación, 1000×680.
- Este informe.

## Pruebas y resultados

Comando de la suite completa:

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-mpl \
  .venv/bin/python -m pytest -q -W error
```

**72 pruebas aprobadas**, sin fallos ni advertencias de Python; última ejecución
8.62 s. Incluye las 27 originales y 45 nuevas. Los casos nuevos cubren:

- Punto de control UTM 14N: meridiano −99°, ecuador, falso este 500,000 m.
- Centros de píxel, orientación norte/sur, rejillas afines rotadas y bordes.
- Antimeridiano en dominios 170..190 y −190..−170, proyección Web Mercator,
  polos, centro de cámara y ocultación posterior.
- Coincidencia de identificadores de píxel GDAL/analíticos en ocho escenarios.
- Rechazo de CRS, transformadas, fechas, canales, unidades, fuentes, dimensiones
  y máscaras incompatibles. Cero real, QA, NoData y NaN; LST sin doble escalado.
- Zoom inicial sin transición previa, arco corto, interpolación de cámara,
  interrupción por ratón, pines, opacidad, leyenda LST y datasets ausentes.
- Mes completamente vacío durante reproducción, pausa, ciclo temporal, cambio
  de región, cachés y transparencia; conservación de pestañas y panel global.

Validación real reproducible:

```bash
PYTHONPATH=src QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/aurora-mpl \
  .venv/bin/python scripts/validate_planetary.py
```

Se compararon **300 GeoTIFF** del paquete de Querétaro con el cubo NDVI
`[300,171,161]`, de enero de 2001 a diciembre de 2025, en **EPSG:32614**:

- CRS, transformadas y dimensiones coincidentes.
- Igualdad exacta de valores observados y faltantes después de aplicar máscara.
- Máscara regional idéntica a la reconstruida desde el GeoJSON mediante
  `geometry_mask`, `all_touched=False`.
- Primer cuadro: **11,466** píxeles válidos.
- Cero diferencias de identificadores de píxel para Querétaro y México;
  ningún píxel de ese cubo visible desde el hemisferio opuesto.
- Las capturas generadas se inspeccionaron visualmente, incluida la ventana
  mínima y el escritorio integrado. No se requirió abrir una sesión gráfica.

Mediciones orientativas del último `validation.json`, sin pantalla, 1280×800:

| Operación | Mediana |
| --- | ---: |
| Cambiar cuadro temporal con cámara estable | 6.96 ms |
| Recalcular cámara en modo movimiento | 81.24 ms |
| Recalcular vista en reposo, Querétaro | 161.87 ms |
| Recalcular vista en reposo, México | 121.84 ms |
| Recalcular vista en reposo, Tierra | 133.27 ms |

Son mediciones CPU de esta máquina, no una garantía de FPS interactivos. El
cambio temporal reutiliza la proyección. La recuperación de resolución al
terminar una transición requiere un recálculo de reposo.

## Errores encontrados y resueltos

- La capa de estados de 50m excluye México. Se detectó al inspeccionar sus
  atributos y se añadió la selección mexicana de 10m. La cobertura se documenta.
- Durante la optimización, la aproximación GDAL predeterminada de 0.125 píxeles
  produjo 439 identificadores distintos en una comparación exploratoria de
  603,200 destinos. Se estableció `tolerance=0.0`; esa comparación quedó en cero
  diferencias, y la equivalencia está cubierta por pruebas.
- GDAL puede abortar una transformación de puntos si otro punto sale del dominio
  UTM, y puede devolver un mensaje genérico después de suprimir errores
  repetidos. La ruta analítica separa esos puntos, conserva los válidos y elimina
  coordenadas no finitas antes de invertir la afín.
- Los enums de estado de animación PySide6 son verdaderos incluso para `Stopped`.
  Se sustituyeron las comprobaciones booleanas por comparación explícita.
- La conexión directa de `clicked` a `QFrame.setVisible` no transmitía el booleano
  en este entorno. Una lambda explícita resolvió el `TypeError`. La ejecución
  fallida terminó con código 139 al cerrar Qt; después de corregir la señal, la
  suite completa terminó satisfactoriamente con código 0.
- Matplotlib no podía escribir su caché predeterminada en el sandbox inicial.
  Las verificaciones utilizan `MPLCONFIGDIR` dentro de `/tmp`.
- El backend Qt sin pantalla emite `This plugin does not support
  propagateSizeHints()`: es una limitación del backend de prueba, no un fallo de
  proyección. No afecta las capturas ni los resultados verificados.

## Limitaciones pendientes

- Solo Querétaro NDVI tiene el cubo completo esperado. `queretaro_lst`, `mexico`
  y `mexico_lst` no existen en las rutas seleccionadas. Hay muestras LST locales,
  pero no se reasignaron como un producto completo. La interfaz informa ausencia.
- Por ello LST está verificado mediante fixtures de contrato, unidades y leyenda;
  su proyección completa con observaciones reales queda pendiente de recibir el
  cubo correspondiente. Lo mismo aplica al cubo nacional de México.
- La validación contrasta el visor con los archivos de entrada y el contrato;
  no verifica de forma independiente la geolocalización orbital ni el QA que el
  proveedor aplicó antes de producir los GeoTIFF.
- Natural Earth es cartografía generalizada: puede diferir de la máscara regional
  y no representa un catastro. Los estados de países fuera de la selección de
  50m y México no están incorporados. Los marcadores urbanos son aproximados.
- El globo es una vista ortográfica esférica y estilizada, sin fotografía global,
  relieve ni iluminación astronómica real. La iluminación se identifica como
  ilustrativa. No se presenta una textura inventada como observación.
- El renderizado sigue siendo por CPU y la cámara no alcanza 60 FPS en esta
  medición. La carga y validación del cubo son síncronas; un producto mucho mayor
  puede bloquear temporalmente la interfaz y requiere evaluar memoria y latencia.
- Los pines son temporales, no se exportan. A tamaños pequeños hay desplazamiento
  vertical de controles. La evaluación visual fue sin pantalla; resta probar
  interacción física, escalado HiDPI y rendimiento en el equipo de presentación.

`git diff --check` terminó sin errores. Los cambios permanecen locales en
`feature/model-core`, listos para revisión; no se autorizó ni realizó su commit.
