# Crisis Damage Intelligence Operational QA

Base URL: http://localhost:3000
Generated: 2026-06-28T14:44:20.792Z

## Result

PASS - no functional failures found in requested scope

## Passes

- desktop: default AOI selector: La Guaira active with 120 AOI12 features
- desktop: default: AOI isolation: 120 visible features all belong to emsr884-aoi12-caraballeda
- desktop: AOI12: downloads: CSV=/data/aoi/emsr884-aoi12-caraballeda/damage.csv, GEOJSON=/data/aoi/emsr884-aoi12-caraballeda/damage.geojson, KML=/data/aoi/emsr884-aoi12-caraballeda/damage.kml, COG=https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/AOI12/GRA_PRODUCT/EMSR884_AOI12_GRA_PRODUCT_LEGION_20260626_1510_ORTHO_cog.tif, VLM_JSONL=/data/aoi/emsr884-aoi12-caraballeda/vlm_review.jsonl, VLM_CSV=/data/aoi/emsr884-aoi12-caraballeda/vlm_review_summary.csv, VLM_SUMMARY=/data/aoi/emsr884-aoi12-caraballeda/vlm_summary.json, VLM_BEFORE_AFTER_JSONL=/data/aoi/emsr884-aoi12-caraballeda/vlm_before_after_review.jsonl, VLM_BEFORE_AFTER_CSV=/data/aoi/emsr884-aoi12-caraballeda/vlm_before_after_summary.csv, VLM_BEFORE_AFTER_SUMMARY=/data/aoi/emsr884-aoi12-caraballeda/vlm_before_after_summary.json
- desktop: AOI12 Vantor before: before raster active
- desktop: AOI12 after: after raster active
- desktop: severe filter: 96/120
- desktop: VLM filter: 107/120
- desktop: all filter restore: 120
- desktop: opacity: opacity=0.62, zoom unchanged=11.820152168111578
- desktop: priority click zoom/popup: focused=emsr884-aoi12-caraballeda__ems_00050, zoom=18
- desktop: click outside clears popup: selection cleared
- desktop: AOI selector Antimano: imagery-only AOI active with no features
- desktop: Antimano: AOI isolation: 0 visible features all belong to emsr884-aoi03-antimano
- desktop: Esri approximate before fallback: before uses approximate raster
- desktop: Antimano: downloads: COG=https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/AOI03/GRA_PRODUCT/EMSR884_AOI03_GRA_PRODUCT_LEGION_20260625_1517_ORTHO_cog.tif, CSV=/data/aoi/emsr884-aoi03-antimano/damage.csv, GEOJSON=/data/aoi/emsr884-aoi03-antimano/damage.geojson, KML=/data/aoi/emsr884-aoi03-antimano/damage.kml
- mobile: default AOI selector: La Guaira active with 120 AOI12 features
- mobile: default: AOI isolation: 120 visible features all belong to emsr884-aoi12-caraballeda
- mobile: AOI12: downloads: CSV=/data/aoi/emsr884-aoi12-caraballeda/damage.csv, GEOJSON=/data/aoi/emsr884-aoi12-caraballeda/damage.geojson, KML=/data/aoi/emsr884-aoi12-caraballeda/damage.kml, COG=https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/AOI12/GRA_PRODUCT/EMSR884_AOI12_GRA_PRODUCT_LEGION_20260626_1510_ORTHO_cog.tif, VLM_JSONL=/data/aoi/emsr884-aoi12-caraballeda/vlm_review.jsonl, VLM_CSV=/data/aoi/emsr884-aoi12-caraballeda/vlm_review_summary.csv, VLM_SUMMARY=/data/aoi/emsr884-aoi12-caraballeda/vlm_summary.json, VLM_BEFORE_AFTER_JSONL=/data/aoi/emsr884-aoi12-caraballeda/vlm_before_after_review.jsonl, VLM_BEFORE_AFTER_CSV=/data/aoi/emsr884-aoi12-caraballeda/vlm_before_after_summary.csv, VLM_BEFORE_AFTER_SUMMARY=/data/aoi/emsr884-aoi12-caraballeda/vlm_before_after_summary.json
- mobile: AOI12 Vantor before: before raster active
- mobile: AOI12 after: after raster active
- mobile: severe filter: 96/120
- mobile: VLM filter: 107/120
- mobile: all filter restore: 120
- mobile: opacity: opacity=0.62, zoom unchanged=10.47070301046031
- mobile: priority click zoom/popup: focused=emsr884-aoi12-caraballeda__ems_00050, zoom=18
- mobile: click outside clears popup: selection cleared
- mobile: AOI selector Antimano: imagery-only AOI active with no features
- mobile: Antimano: AOI isolation: 0 visible features all belong to emsr884-aoi03-antimano
- mobile: Esri approximate before fallback: before uses approximate raster
- mobile: Antimano: downloads: COG=https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/AOI03/GRA_PRODUCT/EMSR884_AOI03_GRA_PRODUCT_LEGION_20260625_1517_ORTHO_cog.tif, CSV=/data/aoi/emsr884-aoi03-antimano/damage.csv, GEOJSON=/data/aoi/emsr884-aoi03-antimano/damage.geojson, KML=/data/aoi/emsr884-aoi03-antimano/damage.kml

## Findings

- None

## Screenshots

- desktop-01-default-aoi12.png
- desktop-02-aoi12-vantor-before.png
- desktop-03-priority-popup.png
- desktop-04-antimano-esri-before.png
- mobile-01-default-aoi12.png
- mobile-02-aoi12-vantor-before.png
- mobile-03-priority-popup.png
- mobile-04-antimano-esri-before.png
