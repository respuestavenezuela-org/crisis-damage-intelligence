# Resumen Detallado De Capacidades Del Mapa

Este documento resume lo que puede hacer actualmente el mapa publico **Respuesta Venezuela**, segun la aplicacion, el catalogo estatico y los componentes operativos del repositorio.

## Proposito

Respuesta Venezuela es un mapa publico, bilingue y estatico para apoyar el triage geoespacial de danos tras el terremoto de Venezuela asociado a Copernicus EMSR884.

El objetivo principal es ayudar a equipos, voluntarios y coordinadores a:

- ubicar zonas afectadas;
- priorizar revision de estructuras o puntos;
- distinguir fuentes oficiales de senales de triage;
- descargar datos operativos;
- consultar evidencia visual cuando exista;
- seguir usando informacion basica con baja conectividad.

La app publica no necesita Supabase, VLM en vivo, analitica, R2/CDN ni servicios privados para abrir y mostrar los datos estaticos disponibles.

## Datos Que Puede Mostrar

El catalogo publico actual contiene 16 AOIs o capas. El catalogo esta marcado como actualizado el `2026-07-01T17:55:00Z`.

### Capas oficiales EMSR884

- **AOI02 Caracas - vector oficial EMSR884**
  - 17 features.
  - 0 destruidos/danados confirmados.
  - 17 posibles.
  - VLM antes/despues publicado para 17 registros, con alta incertidumbre.

- **AOI06 Moron - vector oficial EMSR884**
  - 129 features.
  - 36 destruidos/danados confirmados.
  - 93 posibles.
  - VLM post-evento publicado para 129 registros.

- **AOI08 San Felipe - vector oficial EMSR884**
  - 43 features.
  - 8 destruidos/danados confirmados.
  - 35 posibles.
  - VLM post-evento publicado para 43 registros.

- **AOI12 Caraballeda / La Guaira - vector oficial EMSR884**
  - 120 features.
  - 96 destruidos/danados confirmados.
  - 24 posibles.
  - VLM antes/despues publicado para 107 registros.
  - 13 registros omitidos por falta de imagen antes util.
  - 73 senales accionables y 33 de revision urgente segun VLM.

### Capas oficiales MONIT01

El mapa tambien puede mostrar puntos oficiales EMSR884 MONIT01. Estos son productos oficiales de monitoreo, pero se mantienen separados de los conteos vectoriales `builtUpA`.

- AOI02 Caracas MONIT01: 20 puntos.
- AOI05 Santa Cruz: 3 puntos oficiales.
- AOI06 Moron MONIT01: 96 puntos.
- AOI08 San Felipe MONIT01: 183 puntos.
- AOI12 Caraballeda / La Guaira MONIT01: 1004 puntos.

### Zonas solo-imagen

Algunas zonas tienen imagen o metadatos de imagen, pero no vector oficial de dano publicado:

- AOI03 Antimano.
- AOI10 Guacara.

Estas zonas sirven como contexto visual o areas a vigilar. No deben contarse como dano oficial.

### Capas externas de triage

El mapa incluye fuentes externas que sirven como pistas de busqueda o priorizacion, no como confirmacion oficial:

- Microsoft AI4G / HDX Catia La Mar: 9134 candidatos.
- Microsoft AI4G Caraballeda Este: 622 candidatos.
- Microsoft AI4G Catia La Mar Este: 1209 candidatos.
- Microsoft AI4G La Guaira Este: 119 candidatos.
- HOT/MapSwipe brechas visuales fuera de EMS: 460 candidatos.

Estas capas no deben mezclarse con las metricas oficiales EMS.

## Navegacion Operativa

El mapa agrupa capas por areas afectadas, para que el usuario no tenga que entender cada archivo tecnico individualmente:

- La Guaira / Caraballeda / Catia La Mar.
- San Felipe.
- Santa Cruz.
- Moron.
- Caracas.
- Antimano.
- Guacara.

La lista se ordena por valor de respuesta: primero dano oficial confirmado, luego posibles, MONIT01, VLM y candidatos externos limitados.

## Visualizacion Del Mapa

El mapa permite:

- cambiar entre base de mapa y base aerea;
- ver capas vectoriales de dano;
- ver puntos MONIT01;
- ver zonas de impacto agregadas;
- alternar imagen antes/despues cuando existe una capa publicada;
- usar imagen post-evento EMS cuando esta disponible;
- usar referencia pre-evento Vantor/OpenData cuando esta publicada;
- usar Esri World Imagery como referencia visual aproximada cuando no existe una capa antes nativa;
- ajustar la opacidad de la capa de dano;
- centrar automaticamente el AOI activo;
- centrar una estructura seleccionada a zoom alto;
- mostrar popup con ID, clase de dano, score/porcentaje y enlace a Google Maps.

## Filtros

La consola tiene tres filtros principales:

- **Todos**: muestra todos los features cargados del AOI activo.
- **Destruido/Danado**: muestra solo features severos, usando `damage_gra`, `damage_class` o campos equivalentes.
- **Revisado VLM**: muestra solo features que tienen evidencia VLM cargada.

El filtro severo no cuenta `Possibly damaged` como destruido/danado confirmado.

## Lista De Prioridad

La app genera una lista de prioridad para el AOI activo. La lista puede ordenarse por:

- valor de respuesta por defecto;
- mayor dano;
- elementos con VLM;
- oficial EMS;
- ID fuente;
- cercania al centro del AOI.

Cada fila de prioridad permite:

- seleccionar la estructura o punto;
- centrar el mapa;
- copiar coordenadas;
- abrir Google Maps;
- revisar evidencia asociada si existe.

## Evidencia VLM

Cuando hay evidencia VLM disponible, el panel muestra:

- clase VLM;
- tipo de revision;
- prioridad de accion;
- evidencia textual;
- razon de incertidumbre;
- chip visual de evidencia;
- chip antes, despues, comparativo o tripleta, segun disponibilidad.

El mapa distingue entre:

- **VLM antes/despues**: requiere evidencia pre-evento y post-evento.
- **VLM post-evento**: usa solo imagen posterior y tiene menor valor probatorio.

VLM es una ayuda de triage. No reemplaza Copernicus EMS ni validacion humana.

## Imagenes Y Cobertura

El mapa puede informar:

- si existe imagen posterior;
- si existe imagen anterior;
- si la imagen esta publicada como capa de mapa o solo como evidencia/descarga;
- sensor;
- fecha UTC de adquisicion;
- tamano aproximado;
- cobertura y limitaciones;
- enlace COG cuando esta publicado.

Reglas importantes:

- La imagen post-evento Copernicus EMS es contexto oficial de imagen, pero la etiqueta de dano sigue siendo el vector EMS.
- Vantor/OpenData puede servir como referencia pre-evento cuando la cobertura y calidad lo permiten.
- Esri/Google son referencias visuales externas, no evidencia oficial cacheada ni fuente de verdad.
- No se debe inferir ausencia de dano por ausencia de feature o por huecos de imagen.

## Zonas De Impacto

El mapa puede mostrar zonas agregadas de impacto. Estas combinan senales de:

- geometria oficial EMS;
- puntos MONIT01;
- brechas externas;
- reportes comunitarios agregados;
- eventos como acceso, agua, salud, dano estructural u otros.

Las zonas tienen prioridad:

- alta;
- media;
- contexto.

Al seleccionar una zona de impacto, el mapa muestra:

- prioridad;
- etiqueta del sector;
- reportes comunitarios agregados;
- dano oficial EMS destruido/danado;
- puntos MONIT01;
- candidatos de brecha externa;
- eventos comunitarios agregados;
- advertencia de que es solo triage.

No se publican nombres, telefonos, direcciones exactas, texto libre ni reportes individuales.

## Lentes De Planificacion

La consola tiene tres lentes:

- **Priorizar**: orienta hacia las areas y features de mayor valor de respuesta.
- **Verificar**: enfoca el panel en evidencia, imagen y VLM.
- **Acceso**: resalta senales de acceso y zonas de impacto antes de mover equipos.

La tarjeta de planificacion muestra:

- razon de prioridad;
- confianza de fuente;
- senales de acceso;
- cantidad de filas de prioridad;
- descargas de campo disponibles;
- siguiente accion recomendada.

## Descargas

El mapa agrupa descargas por uso:

- **Paquete de campo**: CSV y KML.
- **Datos GIS**: GeoJSON, SHP o GDB cuando existan.
- **Evidencia**: VLM JSONL, CSV y resumen.
- **Imagen**: COG, TIFF, XLS/XLSX, PDF o web.
- **Otros**: metadatos, ZIPs, HDX, datasets fuente.

Esto permite usar los datos fuera de la app en QGIS, Google Earth, hojas de calculo, tableros o flujos internos.

## Busqueda

La busqueda global permite encontrar:

- zonas afectadas;
- AOIs concretos;
- features por ID;
- clases de dano;
- resultados VLM;
- descargas disponibles.

Los resultados permiten cambiar de AOI, seleccionar un feature o abrir una descarga.

## Vista Ligera

La ruta `/lite` ofrece una vista rapida para telefonos, voluntarios y coordinadores no tecnicos.

La vista ligera muestra:

- selector ES/EN;
- mapa esquematico de zonas;
- ranking publico;
- resumen por ciudad o zona;
- descargas rapidas CSV/KML/GeoJSON;
- enlace para abrir la consola operativa completa.

Esta vista evita la complejidad del mapa operacional y es util con enlaces debiles.

## Movil, PWA Y Offline

La app esta preparada para telefonos:

- paneles inferiores para zona, capas, evidencia/prioridad y acerca;
- controles tactiles;
- prompt de instalacion como app;
- service worker;
- pantalla offline;
- aviso de nueva version;
- cache de shell y datos;
- precarga de tiles y chips importantes del AOI activo.

La precarga offline intenta guardar:

- tiles antes/despues cuando existen;
- chips VLM importantes;
- areas alrededor de features oficiales o revisados;
- zooms utiles para inspeccion.

Respeta un presupuesto de almacenamiento para no llenar el dispositivo.

## Analitica Y Privacidad

La app puede registrar eventos operativos sanitizados si se configura un proveedor:

- carga de app;
- cambio de idioma;
- seleccion de AOI;
- cambio de filtro;
- cambio de base o modo antes/despues;
- clicks en prioridad;
- descargas;
- apertura de chips;
- links a Google Maps;
- fallos de carga;
- uso de paneles moviles.

La analitica evita enviar:

- nombres;
- correos;
- coordenadas exactas;
- IDs de feature en eventos de prioridad;
- URLs completas;
- texto libre;
- datos personales.

La app sigue funcionando si la analitica esta desactivada o bloqueada.

## API Interna Opcional

El repositorio incluye una API interna cerrada bajo `/api/internal/v1/*`.

Puede exponer, si se habilita explicitamente con token:

- catalogo;
- lista de AOIs;
- AOI individual;
- features paginados;
- cola de prioridad;
- busqueda;
- resumen agregado;
- health check.

Esta API esta deshabilitada por defecto y no forma parte del requisito publico del mapa.

## Advertencias Operativas

- Copernicus EMS oficial es la fuente principal para conteos oficiales.
- Los features EMS `builtUpA` pueden no equivaler a un edificio individual.
- MONIT01 es oficial, pero se mantiene separado de los vectores GRA `builtUpA`.
- VLM es evidencia auxiliar y no autoridad.
- Predicciones Microsoft/HDX son candidatos externos, no dano confirmado.
- HOT/MapSwipe fuera de EMS es brecha visual de triage, no conteo oficial.
- Google Maps y Esri son referencias externas, no evidencia oficial.
- La ausencia de un poligono marcado no prueba ausencia de dano.
- No se deben mezclar conteos oficiales, MONIT01, VLM y predicciones externas en una sola cifra de dano confirmado.

## En Una Frase

El mapa sirve para navegar zonas afectadas, ver dano oficial y senales de triage separadas, priorizar estructuras o sectores, revisar evidencia visual, descargar datos de campo/GIS y mantener una experiencia usable en moviles con baja conectividad, sin depender de servicios privados para la vista publica.
