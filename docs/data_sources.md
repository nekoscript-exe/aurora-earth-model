Documentación técnica: Extracción de NDVI mediante MODIS MOD13Q1

1. Fuente de información

Para obtener los datos relacionados con el índice de vegetación NDVI (Normalized Difference Vegetation Index), se utilizó el producto satelital MODIS MOD13Q1, disponible en Google Earth Engine.

Colección utilizada:

MODIS/061/MOD13Q1

Nombre del producto: MOD13Q1.061 Terra Vegetation Indices 16-Day Global 250m.

Organización responsable: NASA LP DAAC, distribuido mediante Google Earth Engine.

Este producto proporciona información sobre índices de vegetación calculados a partir de imágenes satelitales del sensor MODIS instalado en el satélite Terra.

Su finalidad es monitorear las condiciones de la vegetación y analizar sus cambios a través del tiempo.

2. Características del conjunto de datos

Las principales características del producto MOD13Q1 son:

Característica

Descripción

Colección

MODIS/061/MOD13Q1

Satélite

Terra

Sensor

MODIS

Producto

MOD13Q1 versión 6.1

Cobertura espacial

Global

Resolución espacial original

250 metros

Resolución temporal

16 días

Índice principal

NDVI

Banda de calidad

SummaryQA

Factor de escala del NDVI

0.0001

Inicio de disponibilidad

18 de febrero de 2000

El producto genera composiciones de imágenes cada 16 días, seleccionando información satelital para representar las condiciones de la vegetación durante ese periodo.

La resolución espacial de 250 metros significa que cada píxel representa aproximadamente un área de 250 x 250 metros sobre la superficie terrestre.

3. Bandas utilizadas

Para el procesamiento se seleccionaron dos bandas del producto MOD13Q1:

3.1 NDVI (Normalized Difference Vegetation Index)

La banda NDVI representa el índice de vegetación de diferencia normalizada.

Este índice permite estimar la presencia y las condiciones generales de la vegetación mediante la respuesta espectral de la superficie terrestre.

Se obtiene a partir de la relación entre la reflectancia del infrarrojo cercano (NIR) y la reflectancia del rojo (RED).

Su fórmula es:

NDVI = (NIR - RED) / (NIR + RED)

Los valores del índice se encuentran conceptualmente entre -1 y 1.

Interpretación general:

Valores negativos: pueden representar agua, nieve u otras superficies sin vegetación.

Valores cercanos a 0: generalmente representan suelo desnudo o superficies con poca vegetación.

Valores positivos: representan presencia de vegetación.

Valores más elevados: generalmente indican vegetación más densa o con mayor actividad fotosintética.

Factor de escala: 0.0001

Los valores originales almacenados en la banda NDVI son enteros y deben multiplicarse por 0.0001 para obtener los valores reales del índice.

Ejemplo:

Valor original: 6500

Valor convertido: 6500 × 0.0001 = 0.65

Por lo tanto, es necesario aplicar este factor antes de realizar los análisis estadísticos y las interpretaciones del NDVI.

3.2 SummaryQA

La banda SummaryQA proporciona información sobre la calidad y confiabilidad de los valores del índice de vegetación.

Se utiliza para identificar píxeles que presentan condiciones adecuadas para el análisis.

El catálogo establece los siguientes valores:

Valor

Significado

Interpretación

0

Good data, use with confidence

Datos de buena calidad

1

Marginal data

Datos marginales

2

Pixel covered with snow/ice

Píxel cubierto de nieve o hielo

3

Pixel is cloudy

Píxel con presencia de nubes

¿Por qué se utiliza SummaryQA == 0?

Se utiliza la condición SummaryQA == 0 para conservar únicamente los píxeles clasificados como datos de buena calidad.

Esta decisión permite:

Reducir la presencia de información afectada por condiciones atmosféricas.

Excluir píxeles identificados con nieve o hielo.

Evitar utilizar datos clasificados como marginales.

Mejorar la confiabilidad de los valores NDVI.

Disminuir posibles errores durante el análisis temporal de la vegetación.

En consecuencia, se considera que los valores que cumplen esta condición son los más adecuados para el procesamiento.

Es importante señalar que esta condición utiliza exclusivamente la clasificación general de calidad SummaryQA y no sustituye un análisis más detallado de los indicadores de calidad disponibles en DetailedQA.

4. Disponibilidad temporal de los datos

De acuerdo con el catálogo de Google Earth Engine, la colección MODIS/061/MOD13Q1 tiene registros disponibles desde el:

18 de febrero de 2000.

El catálogo también muestra disponibilidad hasta el 16 de octubre de 2026 en la consulta realizada.

La colección se actualiza con una frecuencia de 16 días.

Consideración para el año 2001

Para el análisis temporal se debe comprobar específicamente la disponibilidad de imágenes correspondientes a enero de 2001.

Aunque enero de 2001 se encuentra dentro del periodo general de cobertura del producto, es necesario verificar que existan composiciones disponibles dentro del intervalo:

2001-01-01 a 2001-02-01

Esto permite evitar asumir que todos los días o meses cuentan con imágenes disponibles únicamente porque se encuentran dentro del periodo general del catálogo.

La comprobación debe realizarse directamente sobre la colección de Google Earth Engine.

5. Decisiones de extracción y procesamiento

Para preparar los datos y generar una serie temporal uniforme se establecieron las siguientes decisiones:

5.1 Generación de valores mensuales mediante mediana

El producto MOD13Q1 proporciona imágenes cada 16 días, por lo que no contiene directamente una observación para cada mes.

Para obtener una serie temporal mensual se decidió calcular la mediana de los valores NDVI disponibles dentro de cada mes.

Este procedimiento consiste en:

Seleccionar las imágenes correspondientes al mes.

Aplicar el filtro de calidad SummaryQA == 0.

Aplicar el factor de escala de 0.0001 a la banda NDVI.

Calcular la mediana de los valores disponibles para cada píxel.

Generar una imagen representativa del mes.

Justificación del uso de la mediana:

La mediana permite obtener un valor central representativo de las observaciones disponibles durante el mes.

Además, presenta menor sensibilidad a valores extremos que la media aritmética.

Esto resulta conveniente para trabajar con información satelital, donde pueden existir variaciones entre las diferentes composiciones de 16 días.

Es importante considerar que la mediana mensual se calcula únicamente con las imágenes disponibles y los píxeles que cumplen los criterios de calidad establecidos.

5.2 Sistema de referencia espacial: EPSG:32614

Para estandarizar la información espacial se seleccionó el sistema de referencia de coordenadas:

EPSG:32614

Este código corresponde a:

WGS 84 / UTM Zone 14N

Se eligió este sistema porque permite trabajar con coordenadas proyectadas en metros y resulta adecuado para la zona geográfica de estudio, ubicada en México dentro de la zona UTM 14 norte.

Su utilización facilita:

La medición de distancias.

El procesamiento de información espacial.

La integración con otras capas geográficas.

La generación de una cuadrícula uniforme.

5.3 Resolución espacial de salida: 1000 metros

Aunque la resolución espacial original del producto MOD13Q1 es de 250 metros, para la extracción se estableció una resolución de salida de:

1000 metros (1 km).

Esto significa que los resultados se organizarán en una cuadrícula espacial de aproximadamente 1 km por 1 km.

La decisión permite trabajar con una estructura espacial más uniforme y reducir el volumen de información generado.

Es importante distinguir entre la resolución original del producto y la resolución de salida:

Resolución original: 250 metros.

Resolución de procesamiento: 1000 metros.

Sistema de referencia: EPSG:32614.

La transformación a 1000 metros debe realizarse mediante un procedimiento de agregación o remuestreo espacial correctamente definido, documentando el método utilizado para evitar interpretaciones incorrectas de los valores originales.

6. Resumen de los parámetros de extracción

Parámetro

Valor establecido

Fuente

Google Earth Engine

Colección

MODIS/061/MOD13Q1

Satélite

Terra

Banda principal

NDVI

Banda de calidad

SummaryQA

Filtro de calidad

SummaryQA == 0

Factor de escala

0.0001

Resolución original

250 m

Frecuencia original

16 días

Frecuencia de salida

Mensual

Estadístico mensual

Mediana

Sistema de coordenadas

EPSG:32614

Resolución de salida

1000 m

Unidad espacial de salida

Metros

7. Consideraciones metodológicas

Durante la extracción de los datos se deben considerar los siguientes aspectos:

La colección MOD13Q1 contiene composiciones de 16 días, no observaciones diarias.

Los valores originales de NDVI deben convertirse utilizando el factor de escala de 0.0001.

El filtro SummaryQA == 0 permite conservar únicamente los píxeles identificados como datos de buena calidad.

La mediana mensual se calcula a partir de las imágenes disponibles dentro de cada mes.

Los meses sin imágenes válidas deben identificarse y registrarse como datos faltantes, evitando asignarles valores artificiales.

La resolución espacial de 1000 metros corresponde a una decisión del procesamiento y no a la resolución original del producto satelital.

La transformación espacial debe conservar correctamente la referencia geográfica y documentar el método de agregación utilizado.

La disponibilidad temporal debe comprobarse directamente en Google Earth Engine antes de ejecutar la extracción completa.

8. Referencias bibliográficas

Google Earth Engine. (s. f.). MOD13Q1.061 Terra Vegetation Indices 16-Day Global 250m. Google for Developers.

NASA LP DAAC. MODIS/Terra Vegetation Indices 16-Day L3 Global 250m SIN Grid V061.

DOI del producto:

10.5067/MODIS/MOD13Q1.061

Catálogo oficial de Google Earth Engine:

https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13Q1

Documentación técnica: MODIS LST (Land Surface Temperature)

1. Información general del conjunto de datos

Para el análisis de temperatura superficial terrestre se utilizará el producto MODIS LST, que permite obtener información sobre la temperatura de la superficie terrestre mediante observaciones satelitales.

Colección: MODIS/061/MOD11A2

Plataforma: MODIS Terra.

Resolución espacial: 1000 metros (1 km).

Resolución temporal: Composiciones de 8 días.

Unidad original: Kelvin (K).

Periodo de referencia: El catálogo presenta información desde el 18 de febrero de 2000 hasta el 8 de octubre de 2025 en su resumen. Sin embargo, el campo de disponibilidad indica información hasta el 1 de noviembre de 2026. Debido a esta diferencia, es necesario realizar una consulta directa para confirmar la última fecha disponible.

2. Bandas utilizadas

Se utilizarán dos bandas principales del producto:

Banda

Descripción

Uso

LST_Day_1km

Temperatura superficial terrestre durante el día.

Obtener la temperatura superficial.

QC_Day

Indicador de calidad de la temperatura diurna.

Identificar la confiabilidad de los datos.

2.1 Banda LST_Day_1km

Esta banda contiene los valores de temperatura superficial terrestre durante el día.

Características:

Resolución espacial: 1000 metros.

Unidad original: Kelvin.

Factor de escala: 0.02.

Resolución temporal: 8 días.

Para convertir los valores originales a grados Celsius se debe aplicar la siguiente fórmula:

Temperatura (°C) = DN × 0.02 − 273.15

Donde:

DN: valor digital almacenado en el píxel.

0.02: factor de escala del producto.

273.15: constante utilizada para convertir de Kelvin a Celsius.

La conversión debe realizarse antes de generar los resultados finales de temperatura en grados Celsius.

3. Control de calidad: QC_Day

La banda QC_Day permite identificar la calidad de los datos de temperatura superficial.

Se utilizan principalmente los bits 0-1 para determinar el estado general de calidad del píxel.

Valor

Significado

Interpretación

0

Pixel bueno

Dato de buena calidad.

1

Pixel dudoso

Dato con calidad cuestionable.

2

No producido por nubes

No existe un valor válido debido a condiciones de nubosidad.

3

No producido por otras causas

El dato no pudo generarse por otros motivos.

3.1 Bits 6-7: Error estimado de LST

Los bits 6-7 contienen información sobre el error estimado de la temperatura superficial.

Valor

Error estimado

0

≤ 1 K

1

≤ 2 K

2

≤ 3 K

3

> 3 K

Esta información permite establecer criterios adicionales para seleccionar los píxeles que se utilizarán en el análisis.

3.2 Propuesta de filtrado

Se propone utilizar inicialmente los píxeles cuyo valor de los bits 0-1 sea igual a 0, debido a que representan datos de buena calidad.

También se debe evaluar si es conveniente limitar el error estimado de LST mediante los bits 6-7.

El criterio definitivo de filtrado deberá establecerse junto con Ian, considerando el equilibrio entre calidad de los datos y cantidad de información disponible.

4. Composición temporal de los datos

El producto MOD11A2 proporciona composiciones de 8 días.

Es importante considerar que:

La composición representa un promedio de 8 días.

El promedio no realiza un filtrado previo utilizando los bits de control de calidad.

El valor de calidad asignado a cada píxel se determina mediante la mayoría de los valores diarios de calidad.

Por lo tanto, no se debe asumir que todos los valores de temperatura incluidos en una composición cumplen automáticamente con el criterio de calidad seleccionado.

4.1 Asignación mensual

Para generar información mensual será necesario definir cómo se asignarán las composiciones de 8 días a cada mes.

Existen dos aspectos que deben verificarse:

Cómo se distribuyen las composiciones de 8 días cuando coinciden con el final de un mes o de un año.

Si cada composición se asignará al mes correspondiente a su fecha de inicio o si se considerará el traslape de días entre diferentes meses.

Esta decisión debe establecerse junto con Ian para mantener un criterio uniforme en el procesamiento temporal.

No se debe asumir una metodología de asignación mensual hasta verificar el comportamiento de las fechas del producto.

5. Disponibilidad temporal

El catálogo presenta una diferencia entre sus campos de disponibilidad:

Campo del catálogo

Fecha

Fecha inicial indicada en el resumen

2000-02-18

Fecha final indicada en el resumen

2025-10-08

Fecha final indicada en disponibilidad

2026-11-01

Debido a esta discrepancia, es necesario realizar una consulta directa al conjunto de datos para identificar la última composición disponible.

Consideración: No se debe garantizar un periodo de análisis de 2001 a 2025 sin comprobar previamente la disponibilidad real de las imágenes.

También se debe verificar si existen datos para enero de 2001, debido a que el producto comienza a registrar información en febrero de 2000.

6. Procesamiento espacial

La banda LST_Day_1km ya cuenta con una resolución espacial de 1000 metros.

Por lo tanto, no es necesario realizar una agregación espacial adicional para obtener una resolución de 1 km.

El procesamiento espacial únicamente requiere:

Reproyectar los datos a la rejilla espacial de referencia del proyecto.

Mantener la resolución espacial de 1000 metros.

Asegurar que las imágenes coincidan espacialmente con las demás variables utilizadas en el análisis.

Esto permitirá integrar los datos de temperatura superficial con otros productos satelitales y variables ambientales.

7. Consideraciones para el procesamiento

Antes de generar los resultados definitivos se deben resolver los siguientes puntos:

Aspecto

Estado

Acción requerida

Selección del producto

Definido

Utilizar MODIS/061/MOD11A2.

Banda de temperatura

Definido

Utilizar LST_Day_1km.

Factor de escala

Definido

Aplicar 0.02.

Conversión a Celsius

Definido

Restar 273.15 después de aplicar el factor de escala.

Control de calidad

Pendiente de decisión

Definir el filtro de bits 0-1.

Error estimado de LST

Pendiente de decisión

Determinar si se limitarán los bits 6-7.

Composición temporal

Definido

Considerar que representa un promedio de 8 días.

Asignación mensual

Pendiente de verificación

Definir el criterio de asignación de composiciones.

Disponibilidad temporal

Pendiente de verificación

Consultar la última fecha real disponible.

Resolución espacial

Definido

Mantener 1000 metros.

Reproyección

Definido

Ajustar los datos a la rejilla de referencia.

8. Resultado esperado

El procesamiento de MODIS LST permitirá obtener información de temperatura superficial terrestre en grados Celsius, con una resolución espacial de 1 km y una frecuencia temporal basada en composiciones de 8 días.

Los datos procesados podrán utilizarse para realizar análisis ambientales, identificar variaciones de temperatura superficial y estudiar su comportamiento temporal y espacial.

La integración con otros productos MODIS permitirá construir una base de información ambiental homogénea para el desarrollo de análisis posteriores.

9. Referencias

NASA LP DAAC. MODIS/Terra Land Surface Temperature and Emissivity 8-Day L3 Global 1km SIN Grid.

Google Earth Engine Data Catalog: MODIS/061/MOD11A2.

Documentación técnica del producto MOD11A2, colección 061.
