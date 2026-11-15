# Cartografía local de Planetary Explorer

Capas de Natural Earth, coordenadas longitud/latitud OGC:CRS84, dominio público.
No son observaciones satelitales. El explorador no necesita red en ejecución.
`sources.json` registra URL de descarga, fecha, escala, SHA-256 y número de entidades.
Los archivos de 50m son copias del GeoJSON original. El archivo de México conserva
las entidades ADM0_A3 == MEX del original de 10m, sin simplificar coordenadas.
Los hashes permiten verificar las copias locales aunque cambie la rama upstream.

- `land_50m.geojson`: tierra e islas; reemplaza en el visor la base de 110m.
- `countries.geojson`: fronteras terrestres internacionales; costas en la capa de tierra.
- `states.geojson`: límites internos de nueve países de la distribución de 50m:
  Australia, Brasil, Canadá, China, India, Indonesia, Rusia, Sudáfrica y Estados Unidos.
- `states_mexico.geojson`: 85 trazos internos mexicanos de la distribución de 10m.
- `land.geojson`: archivo de 110m preexistente, conservado.

Natural Earth representa límites cartográficos generalizados; no constituye un
catastro ni una referencia legal. No se espera coincidencia exacta con la máscara
del proveedor del cubo, especialmente al ampliar a kilómetros. Fuentes:
[Admin 1 10m](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/),
[Admin 1 50m](https://www.naturalearthdata.com/downloads/50m-cultural-vectors/50m-admin-1-states-provinces/),
[términos de uso](https://www.naturalearthdata.com/about/terms-of-use/).

Las coordenadas de los dos marcadores urbanos son referencias aproximadas de
Querétaro y Ciudad de México, no posiciones de estaciones ni mediciones.
Los pines añadidos por doble clic se calculan por inversión ortográfica WGS84,
son temporales y no modifican el cubo.
