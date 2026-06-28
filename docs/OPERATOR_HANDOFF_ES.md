# Guia Operativa - Primeros 5 Minutos

## Objetivo

Usar el mapa para ubicar rapidamente poligonos oficiales de daño de Copernicus EMSR884, priorizar inspeccion y compartir coordenadas/exportaciones con equipos de respuesta.

## Como usarlo

1. Abra la app y confirme que la zona activa sea una zona afectada operativa de Venezuela, no el demo xBD.
2. Use la navegacion de zonas afectadas para cambiar entre areas como `La Guaira / Caraballeda / Catia La Mar`, `Moron`, `San Felipe`, `Caracas`, `Antimano` y `Guacara`.
3. Revise los indicadores:
   - `estructuras`: numero de poligonos built-up en el AOI.
   - `destruidos/dañados oficiales`: suma de `Destroyed` + `Damaged` segun EMS.
   - `posibles oficiales`: `Possibly damaged` segun EMS.
   - `MONIT01`: puntos oficiales de monitoreo EMS cuando existen.
   - `candidatos externos`: predicciones solo para triage cuando existen.
4. Use filtros:
   - `Todos`: todos los poligonos EMS.
   - `Destruido/Dañado`: solo `Destroyed` + `Damaged`.
   - `Revisado VLM`: solo elementos con revision VLM, si existe. Revise el tipo de revision VLM antes de usarla.
5. En `Prioridad`, haga click en un elemento. El mapa centra el poligono a zoom 18 y abre el popup.
6. Use el link `Google Maps` para compartir la ubicacion con equipos de campo.
7. Descargue CSV, GeoJSON o KML para analisis externo, QGIS, Google Earth o tableros.

## Confianza del Dato

- Las etiquetas vectoriales oficiales de Copernicus EMS son la fuente principal para AOI02, AOI06, AOI08 y AOI12.
- Las capas de puntos MONIT01 son productos oficiales de monitoreo, pero estan separadas de los poligonos GRA `builtUpA`.
- `Destroyed` y `Damaged` se tratan como daño confirmado por el producto EMS.
- `Possibly damaged` se muestra por separado. No debe contarse como destruido/dañado confirmado.
- VLM, si aparece, es evidencia auxiliar para priorizar revision; no reemplaza EMS ni validacion humana.
- VLM antes/despues existe publicamente solo para AOI12 y AOI02. AOI12 es el patron canonico; AOI02 tiene alta incertidumbre porque muchos chips estan oscuros, con bruma, sombras o centrado debil.
- AOI06 y AOI08 actualmente tienen VLM solo post-evento. No describa esos registros como comparaciones antes/despues.
- AOI03 Antimano tiene una cola interna de revision VLM sobre candidatos OSM, pero no es dato publico operativo de daño.
- La capa `Catia La Mar - Daño predicho Microsoft AI4G` viene de HDX/Microsoft AI for Good Lab. Es prediccion externa de huellas dañadas, util para triage, pero no es etiqueta oficial EMS.
- Los links de Google Maps y la imagen base de Esri son referencias visuales solamente. No son evidencia oficial, este proyecto no las cachea, y no deben citarse como verificacion.

## Reglas de imagen antes

- `Vantor usable para VLM`: imagen pre-evento fechada que puede apoyar VLM antes/despues a nivel de edificio cuando la cobertura, alineacion y visibilidad sean adecuadas.
- `Esri solo referencia visual`: contexto operativo para orientacion. No usar como evidencia cacheada ni como imagen antes para VLM.
- `Sin before`: no hay imagen pre-evento adecuada. Mantenga las etiquetas VLM como solo post-evento o solo candidatos.

## No Sobreafirmar

- Los features EMS `builtUpA` pueden no representar un edificio individual cada uno.
- Las etiquetas oficiales EMS son la fuente principal de verdad para este paquete.
- VLM y etiquetas inferidas son ayudas de triage, no confirmacion oficial.
- Las capas externas de daño predicho son indicios solamente; no las cite como conteos oficiales ni como edificios dañados confirmados.
- Las capas Microsoft/HDX son capas de prediccion de modelo. Interpretelas como huellas candidatas externas para priorizacion, no como etiquetas EMS, confirmacion de campo ni estadisticas de respuesta.
- No describa vistas de Google o Esri como evidencia oficial, imagen fuente de verdad, ni imagen antes retenida/cacheable.
- La ausencia de un poligono marcado no prueba que no haya daño.

## Limitaciones Conocidas

- AOI12 ya incluye vector oficial EMS, imagen posterior EMS y referencia pre-evento Vantor/OpenData. La referencia Vantor no es imagen oficial EMS y tiene cobertura parcial/huecos; AOI12 VLM reviso 107 comparaciones y omitio 13 por cobertura antes faltante/negra.
- AOI02 tiene referencia Vantor antes solo en chips de evidencia; no hay capa de mapa antes publicada, y 15 de 17 registros VLM antes/despues son problemas de comparacion incierta.
- AOI06 y AOI08 tienen imagen posterior y VLM solo post-evento, pero no tienen imagen antes de alta resolucion adecuada para VLM antes/despues a nivel de edificio en el catalogo actual.
- La capa externa Microsoft/HDX tiene 9,134 candidatos predichos en Catia La Mar; debe usarse como indicio adicional, no como conteo oficial de daño.
- Los poligonos `builtUpA` son features oficiales de evaluacion built-up; no siempre equivalen a un edificio individual.
- Para AOIs grandes puede ser necesario convertir GeoJSON a PMTiles/vector tiles.
- Los datasets HOT/HDX nacionales de edificios/caminos/POI son utiles para contexto, pero no se cargan por defecto porque son pesados para Vercel.

## Nuevas fuentes revisadas

- Microsoft AI for Good Lab via HDX: `Venezuela Earthquakes: Building Damage Assessment in Catia La Mar`. Agregado como AOI externo con 9,134 huellas `damaged=1`.
- HOT via HDX: `Venezuela - M 7.5 Earthquake - June 2026 - OSM & Overture Data`. Documentado como fuente de contexto; no cargado por defecto por tamaño.
