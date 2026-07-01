# Agent Tickets And Batch Plan

Updated: 2026-07-01

## Batch 0: Coordination Rules

All agents must follow these rules:

- Do not run VLM.
- Do not publish official damage claims.
- Do not merge external predictions into EMS official metrics.
- Do not treat absence of an EMS polygon as absence of damage.
- Do not cache or bulk-download Google/Esri tiles.
- Do not download heavy SAR SICD/SIDD unless explicitly approved.
- Record URL, license, date checked, source owner, and confidence for every source.
- Prefer machine-readable outputs: CSV, JSON, GeoJSON, or markdown tables.

## Ticket P0-1: Live EMSR884 Product Snapshot

Owner type: data/API agent

Goal:
Save and parse the live EMSR884 activation API.

Inputs:

- `https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884`
- `https://mapping.emergency.copernicus.eu/activations/EMSR884/`

Outputs:

- `ops/data_acquisition_plan/emsr884_live_products_<timestamp>.json`
- `ops/data_acquisition_plan/emsr884_product_manifest.csv`

Acceptance criteria:

- Every AOI listed.
- Every product listed.
- Product type, monitoring, status, version, delivery time, reason, downloadPath captured.
- Image sensor/acquisition metadata captured.
- Layer JSON/vector tile URLs captured.
- Date checked and checksum recorded.

## Ticket P0-2: Official Product Download And Version Inventory

Owner type: geospatial ingest agent

Goal:
Download and inspect revised official product ZIPs without modifying public layers.

Priority products:

- AOI12 GRA PRODUCT v2.
- AOI00 GRM PRODUCT v2.
- Latest MONIT01 for AOI02, AOI06, AOI08.

Outputs:

- `ops/data_acquisition_plan/official_product_zip_manifest.csv`
- extracted layer inventory markdown
- per-layer feature counts and damage-class counts

Acceptance criteria:

- ZIP URL, size, last modified, checksum if available.
- GPKG layers listed.
- CRS recorded.
- feature count by layer.
- official update reason included.

## Ticket P0-3: AOI12 v1 To v2 Remap

Owner type: geospatial diff agent

Goal:
Determine whether existing AOI12 VLM rows can be reused or must be regenerated.

Outputs:

- `ops/data_acquisition_plan/aoi12_v1_v2_remap.csv`
- `ops/data_acquisition_plan/aoi12_v1_v2_remap_summary.md`

Acceptance criteria:

- geometry hashes for v1 and v2.
- attribute hashes for v1 and v2.
- IoU and centroid distance for candidate matches.
- action per feature: reuse, review, regenerate, retire, new.
- counts by action.

Status: complete.

Current outputs:

- `ops/data_acquisition_plan/aoi12_v1_v2_remap.csv`
- `ops/data_acquisition_plan/aoi12_v1_v2_remap_summary.json`
- `ops/data_acquisition_plan/aoi12_vlm_v1_v2_reuse_queue.csv`

Current decision:

- Reuse 93 existing before/after VLM rows with v2 binding.
- Retire 14 existing before/after rows whose v1 geometry is not located in v2.
- Generate new chips/VLM for 61 new AOI12 v2 features after chip QA.

## Ticket P0-4: Official COG And Imagery Validation

Owner type: imagery QA agent

Goal:
Validate official post-event COGs and bind them to product versions.

Outputs:

- `ops/data_acquisition_plan/official_imagery_manifest.csv`
- `ops/data_acquisition_plan/official_cog_validation.md`

Acceptance criteria:

- content type, byte size, range support.
- bounds and CRS.
- sensor and acquisition time.
- product version binding.
- local/R2 availability.
- quality notes.

## Ticket P0-5: Pre-Event Imagery Coverage

Owner type: imagery discovery agent

Goal:
Inventory public/licensed high-resolution pre-event imagery per AOI.

Sources:

- Vantor Open Data S3.
- OpenAerialMap/HOT references.
- Planet sources only if terms are clear.

Outputs:

- `ops/data_acquisition_plan/pre_event_imagery_coverage.geojson`
- `ops/data_acquisition_plan/pre_event_imagery_manifest.csv`

Acceptance criteria:

- scene id, source, sensor, acquisition UTC, license, bounds.
- AOI intersections.
- suitability for building-level chips.
- known gaps listed.

Status: initial Vantor STAC pass complete.

Current outputs:

- `ops/data_acquisition_plan/pre_event_imagery_coverage.csv`
- `ops/data_acquisition_plan/pre_event_imagery_coverage_summary.csv`
- `ops/data_acquisition_plan/pre_event_imagery_coverage_summary.json`

Current decision:

- AOI02 and AOI12 have useful official-feature Vantor coverage after coarse gates.
- AOI05, AOI06, AOI08, and AOI10 still lack Vantor pre-event coverage.
- All eligible rows still require chip-level QA before HF VLM.

## Ticket P0-6: Chip QA Manifest Design And Pilot

Owner type: pipeline QA agent

Goal:
Define and pilot no-inference chip QA before more HF spend.

Outputs:

- `ops/data_acquisition_plan/chip_qa_schema.md`
- `ops/data_acquisition_plan/chip_qa_pilot.csv`

Acceptance criteria:

- black/missing before and after flags.
- valid pixel percentage.
- haze/cloud/blur/pixelation score.
- target visibility.
- alignment score.
- license gate.
- final VLM eligibility flag.

## Ticket P1-1: OSM/HOT Candidate Footprints

Owner type: OSM/HOT agent

Goal:
Export candidate building footprints for AOIs without official GRA polygons.

Priority AOIs:

- AOI01 Petare
- AOI03 Antimano
- AOI04 Maracay
- AOI07 Puerto Cabello
- AOI09 Valencia
- AOI10 Guacara
- AOI11 Villa de Cura

Outputs:

- `ops/data_acquisition_plan/osm_hot_candidate_manifest.csv`
- per-AOI GeoJSON extracts stored under ops only

Acceptance criteria:

- extraction timestamp.
- ODbL attribution.
- building count.
- geometry validity stats.
- overlap with official EMS and external predictions.

## Ticket P0-7: EMS-Gap Visual Damage Queue

Owner type: visual triage / geospatial agent

Goal:
Create an `external_visual_gap` queue for buildings that appear collapsed or heavily damaged but have no current EMS GRA polygon.

Priority sources:

- HOT human-validated damage assessment for Caraballeda, La Guaira, and Caracas.
- `hotosm/venezuela_eq_2026` split by fAIr, Microsoft, OSU/CUNY, combined H3, and validated MapSwipe outputs.
- Microsoft AI4G/HDX candidates outside official EMS GRA polygons.
- Vantor/OpenAerialMap and Planet/Source Cooperative post-event imagery for manual visual confirmation.
- Geolocated field media or trusted local reports, only if PII risk and source terms are recorded.

Outputs:

- `ops/data_acquisition_plan/ems_gap_visual_queue.geojson`
- `ops/data_acquisition_plan/ems_gap_visual_queue.csv`
- `ops/data_acquisition_plan/ems_gap_visual_queue_summary.md`

Acceptance criteria:

- every candidate has source family, URL, date checked, geometry, and `not_official_ems=true`.
- every candidate has overlap status against EMS GRA, MONIT01, Microsoft/HDX, HOT/fAIr, and existing VLM outputs.
- candidates are separated into `visual_confirmed`, `needs_before_after_vlm`, `needs_human_review`, `hold_license_or_quality`, and `discard_duplicate`.
- no candidate changes official EMS metrics.

## Ticket P1-2: Microsoft AI4G / HDX Schema And Dedupe

Owner type: external prediction agent

Goal:
Parse Microsoft AI4G/HDX datasets and dedupe them against official and external sources.

Outputs:

- `ops/data_acquisition_plan/msft_hdx_schema_manifest.csv`
- `ops/data_acquisition_plan/external_prediction_dedupe_summary.md`

Acceptance criteria:

- dataset URL, GPKG URL, license, CRS, fields.
- feature count by dataset.
- damage/confidence field interpretation.
- bounds and AOI overlap.
- duplicate/overlap strategy.

Status: schema and official-overlap pass complete; dedupe sampling still pending.

Current outputs:

- `ops/data_acquisition_plan/external_prediction_gpkg_inventory.csv`
- `ops/data_acquisition_plan/external_prediction_field_profiles.csv`
- `ops/data_acquisition_plan/external_prediction_official_overlap_summary.csv`
- `ops/data_acquisition_plan/external_prediction_official_overlap_detail.csv`

Current decision:

- 71,296 external prediction features profiled.
- 11,173 high-priority external features identified.
- 7,897 high-priority features are outside current official GRA polygons and are candidates for a deduped external triage batch, not official counts.

## Current Spend-Control Batches

Output:

- `ops/data_acquisition_plan/vlm_spend_control_batches.csv`
- `ops/data_acquisition_plan/vlm_spend_control_batches_summary.json`

Current decision:

- Run no-cost updates first: reuse 93 AOI12 VLM rows, retire 14 stale AOI12 rows, validate existing AOI02.
- Do not spend on AOI05, AOI06, AOI08, or AOI10 before/after VLM until high-resolution pre-event imagery exists.
- Next official paid batch should be at most 61 AOI12 v2 features, and only after chip QA.
- External Microsoft/HDX work should start as deduped samples with a 554-call ceiling after chip QA, not all 7,897 outside-official high-priority candidates.

## Ticket P1-3: HOT/HF Venezuela Dataset Split

Owner type: external prediction agent

Goal:
Inventory the `hotosm/venezuela_eq_2026` dataset by source family and license.

Output:

- `ops/data_acquisition_plan/hotosm_hf_dataset_manifest.csv`

Acceptance criteria:

- rows split by fAIr, Microsoft, OSU/CUNY SAR, combined H3, validation data.
- license per source family.
- candidate counts by geography.
- recommendation for which subsets are eligible for internal triage.

## Ticket P1-4: SAR Context Inventory

Owner type: SAR/context agent

Goal:
Inventory Sentinel-1/GRM and Umbra SAR context products.

Outputs:

- `ops/data_acquisition_plan/sar_context_manifest.csv`
- `ops/data_acquisition_plan/sar_overlap_summary.md`

Acceptance criteria:

- scene footprints.
- acquisition times.
- polarization/mode.
- AOI overlap area.
- GEC URL for Umbra.
- "worth downloading" flag.
- no recommendation to use SAR as direct building VLM labels.

## Ticket P1-5: Human Reference Inventory

Owner type: validation-source agent

Goal:
Inventory non-satellite references for adjudication.

Sources:

- VOSOCC/Rescue sector maps.
- local government/civil protection reports.
- verified geolocated media.
- HOT MapSwipe/ChatMap/tasking references.

Outputs:

- `ops/data_acquisition_plan/human_reference_inventory.csv`

Acceptance criteria:

- source owner.
- URL.
- license/permission.
- georeferenced yes/no.
- coverage.
- PII risk.
- use case.

## Ticket P2-1: LiDAR/DSM Search Note

Owner type: elevation data agent

Goal:
Create a documented "checked and not found" note unless real data exists.

Output:

- `ops/data_acquisition_plan/elevation_data_search.md`

Acceptance criteria:

- providers checked.
- date checked.
- result.
- if none found, recommend defer.

## Ticket P2-2: Embedding Model Inventory

Owner type: ML research agent

Goal:
Inventory embedding models for later chip similarity search.

Output:

- `ops/data_acquisition_plan/embedding_model_inventory.csv`

Acceptance criteria:

- model/source.
- license.
- input modality.
- deployment requirements.
- whether it supports geospatial or image embeddings.
- recommended first prototype.

## Batch Order

1. Run P0-1 through P0-3 first.
2. Run P0-4 and P0-5 in parallel after P0-1.
3. Run P0-7 as soon as HOT/Microsoft/field candidate sources are inventoried; it is triage-only and does not require new HF spend.
4. Run P0-6 after P0-4/P0-5 have at least one AOI sample.
5. Run P1 tickets only after official source families are cleanly separated.
6. Run P2 tickets opportunistically.

## HF Credit Gate

No new broad VLM batch should start until P0-1, P0-3, P0-4, P0-5, and a chip QA pilot from P0-6 are complete. EMS-gap candidates from P0-7 may enter only capped sample batches after dedupe, licensing, and chip QA.
