# 2026-06-30 Data Acquisition Plan

## Executive Summary

The five agent reports agree on the main operating principle: do not spend Hugging Face credits on broad VLM runs until the data layer is fresher, versioned, and QA-gated.

The most important blockers are:

1. Copernicus EMSR884 source freshness.
2. AOI12 Caraballeda v1 to v2 geometry and damage-class mapping.
3. High-resolution pre-event imagery coverage outside AOI02/AOI12/AOI03 pilot areas.
4. Candidate-source separation and dedupe for OSM, Microsoft AI4G/HDX, HOT/fAIr, MONIT01, and official EMS polygons.
5. Chip-level QA metadata before VLM.
6. Licensing and redistribution decisions for Vantor/Planet, OSM, Microsoft/HDX, HOT/fAIr, SAR, and social or field reference material.

Current broad VLM status:

- Official EMS post-event-only VLM: 309 records.
- Official EMS before/after HF VLM: 124 records.
- Blind calibration QA: 119 records.
- Internal OSM/no-official-vector AOI03 pilot: 95 reviewed, 19 shortlisted/adjudicated.
- Microsoft AI4G/HDX external candidates loaded: 11,084, with 0 VLM reviewed.

## Source-Of-Truth Policy

Official Copernicus EMSR884 products are the source of record for official damage metrics. VLM, OSM, Microsoft AI4G/HDX, HOT/fAIr, SAR, social media, and human reference products are triage or adjudication sources only.

Never merge external predictions into EMS official counts. Never label absence of visible change as absence of damage. Never treat absence of an EMS polygon as proof that a building is undamaged. Before/after VLM requires dated pre-event and post-event evidence plus chip QA.

## EMS-Gap Visual Triage Policy

Buildings that look collapsed or heavily damaged but have no EMS GRA polygon must be tracked as `external_visual_gap`, not discarded. The required record is:

- candidate geometry or point
- source family: HOT human validation, HOT/fAIr, Microsoft AI4G/HDX, OSM/Overture candidate, field/geolocated media, or manual visual finding
- evidence URLs and dates
- before image source/date and post image source/date when VLM is requested
- overlap check against official EMS GRA, MONIT01, and existing external predictions
- triage class and confidence
- explicit `not_official_ems=true`

These candidates can enter chip QA and HF VLM if they have licensed before/after imagery and target visibility. They must not change official EMS destroyed/damaged metrics unless an authoritative official update later confirms them.

## P0 Data To Acquire First

### 1. Live EMSR884 Product Manifest

Build a full machine-readable manifest from:

`https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884`

Required fields:

- activation code
- AOI number and name
- product type
- monitoring flag and monitoring number
- version number
- status code
- delivery time
- version reason
- downloadPath
- vector tile layers
- JSON layer URLs
- image file names
- image sensor
- image acquisition time
- image sensor type and resolution class

Save:

- `ops/data_acquisition_plan/emsr884_live_products_YYYYMMDDTHHMMSSZ.json`
- `ops/data_acquisition_plan/emsr884_product_manifest.csv`

### 2. Official Product Refresh And Versioning

Priority downloads:

- AOI12 Caraballeda GRA PRODUCT v2.
- AOI00 Central Coastal Venezuela GRM PRODUCT v2.
- Latest MONIT01 for AOI02, AOI06, AOI08.
- Keep AOI02/AOI05/AOI06/AOI08/AOI12 product ZIPs versioned.

Do not overwrite existing public AOI layers until remap and validation pass.

### 3. AOI12 v1 To v2 Remap

AOI12 is the largest current risk because existing VLM rows were produced against older feature IDs/geometries.

Build `aoi12_v1_v2_remap.csv` with:

- old source feature id
- new source feature id
- old damage class
- new damage class
- old geometry hash
- new geometry hash
- intersection-over-union
- centroid distance
- area ratio
- remap action: reuse, review, regenerate, retire, new

Safe remap only if geometry is stable. Suggested rules:

- exact geometry hash match: reuse
- IoU >= 0.97 and centroid distance <= 1 m: reuse geometry, update official attributes
- IoU 0.75 to 0.97: human review
- split, merge, no overlap, new, deleted: regenerate or retire

### 4. Official Imagery Manifest

Build `official_imagery_manifest.csv` for all official post-event COGs.

Fields:

- AOI
- product version
- source product
- COG URL
- sensor
- acquisition time
- resolution class
- byte size
- content type
- range support
- bounds
- local path if cached
- R2/CDN path if mirrored
- checksum if available

### 5. Pre-Event Imagery Coverage Manifest

Build `pre_event_imagery_coverage.geojson` and CSV from Vantor/OpenAerialMap/other licensed public sources.

Required fields:

- scene id
- source
- sensor
- acquisition UTC
- pre/post flag
- license
- terms URL
- bounds
- intersects AOIs
- cloud/haze notes
- valid-pixel sample result
- chip suitability: yes, no, conditional

High-priority coverage gaps:

- AOI01 Petare
- AOI04 Maracay
- AOI05 Santa Cruz
- AOI06 Moron
- AOI07 Puerto Cabello
- AOI08 San Felipe
- AOI09 Valencia
- AOI10 Guacara
- AOI11 Villa de Cura

## P1 Data Needed, But Not Direct Building VLM Labels

### SAR Context

Use SAR for prioritization and context, not direct building labels.

Needed:

- Sentinel-1 AOI00 GRM v2 layer and scene inventory.
- Umbra GEC footprint inventory with acquisition time, polarization, mode, scene bounds, AOI overlap, license, and "download/use" flag.
- NASA/OSU-CUNY Sentinel-1 likelihood product metadata, if it can be retrieved and licensed.

Do not download huge SICD/SIDD products unless a specific SAR analyst task requires them. Start with GEC only.

### External Prediction Layers

Microsoft AI4G/HDX and HOT/fAIr are candidate sources, not official damage.

Needed:

- HOT human-validated damage assessment and `hotosm/venezuela_eq_2026` source-family splits; treat MapSwipe-confirmed cells/candidates as the first external source to cross-check EMS gaps.
- schema parse for every GPKG/dataset
- confidence/damage fields
- feature counts by source and geography
- CRS
- bounding boxes
- license terms
- overlap/dedupe against official EMS polygons and other external datasets
- sampling plan before any VLM spend

### Human Validation And Reference Products

Needed for adjudication:

- VOSOCC/Rescue sector maps, if permission allows
- local government or civil protection reports
- geolocated social/photo/video evidence
- HOT/MapSwipe validation exports
- field-confirmed examples for collapse, false positive, no visible change, shadow/haze cases

These sources should support review queues, not official metrics.

## P2 Nice-To-Have Data

### LiDAR / DSM / Elevation Change

Useful only if concrete public/licensed pre/post coverage exists. Current reports did not identify an actionable dataset. Document providers checked and date checked, then defer.

### Geospatial And Image Embeddings

Useful after chip manifests are clean. Candidate uses:

- find chips similar to confirmed collapse
- find known false positives
- cluster no-change cases
- support human review ordering

Do not use embeddings as damage authority.

## Recommended Spend Gate Before HF VLM

A candidate is VLM-eligible only if:

- source family is known and separated
- official product version is current, if applicable
- geometry/version mapping is resolved
- before image exists and is dated
- after image exists and is dated
- license allows the intended use
- chip has enough valid pixels
- target is visible
- before/after alignment is acceptable
- haze/cloud/blur/pixelation is below threshold or marked for manual review

## Immediate Next 5 Actions

1. Save a raw live EMSR884 API snapshot and extract `emsr884_product_manifest.csv`.
2. Download/version AOI12 GRA v2, AOI00 GRM v2, and latest MONIT01 updates.
3. Build AOI12 v1 to v2 remap and decide which VLM rows can be reused.
4. Build official and pre-event imagery manifests with COG/range/license/coverage validation.
5. Build candidate-source and chip-QA manifests before any new parallel HF run.

## Low-Value Or Blocked Right Now

- Broad HF VLM over all official and external candidates.
- AOI12 v1 VLM as final evidence.
- Sentinel-2 10 m imagery for building-level before/after.
- External MS/HOT/fAIr/OSU predictions as official metrics.
- Google/Esri basemap tile caching or evidence chips.
- SAR as direct building-level optical damage classification.
- Umbra SICD/SIDD downloads without a specific SAR question.
- Social or field reports as count sources.

## Source-Agent Synthesis

- Perplexity deep research: strongest on missing implementation artifacts, AOI12 remap, chip QA, and licensing gaps.
- Gemini: strongest concise framing of seven production blockers.
- Perplexity search: strongest source inventory and "do not use" list.
- Claude Opus 4.8: useful on Vantor, HDX, OSM/HOT, Umbra, and embeddings, but its Copernicus API state conflicts with direct workspace verification and is treated as superseded.
- ChatGPT 5.5 Pro: strongest detailed inventory structure, remap strategy, chip QA gate, and exact known URLs.
