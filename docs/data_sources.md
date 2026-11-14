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
