# Respuesta Venezuela Data Acquisition Plan

Updated: 2026-07-01

This document summarizes the current data acquisition strategy before spending more Hugging Face VLM credits. The detailed working package is under `ops/data_acquisition_plan/`.

## Current Decision

Do not run broad parallel VLM jobs yet. Run data acquisition and QA gates first.

The highest-risk issue is source freshness: the live Copernicus EMSR884 activation remains open, and the local catalog is not the latest source of record. AOI12 Caraballeda has a GRA PRODUCT v2 with a Built Up Grading correction, so existing AOI12 VLM evidence must be treated as pending until v1/v2 geometry mapping is complete.

EMS is authoritative for official counts, but it is not exhaustive proof that everything outside an EMS polygon is undamaged. Any visually collapsed or strongly damaged building with no EMS polygon must enter an `external_visual_gap` review lane, backed by before/after imagery, HOT/MapSwipe/human-validated data, Microsoft/HDX or fAIr candidates, geolocated field media, or another documented source. These rows remain triage-only until human/official validation.

## Required Artifacts

- `ops/data_acquisition_plan/2026-06-30_data_acquisition_plan.md`: final synthesized plan.
- `ops/data_acquisition_plan/source_inventory.csv`: clean source/API/dataset inventory.
- `ops/data_acquisition_plan/agent_disagreements.md`: comparison of Perplexity, Gemini, Claude, and ChatGPT findings.
- `ops/data_acquisition_plan/agent_batches.md`: actionable agent tickets and batch assignments.
- `ops/data_acquisition_plan/emsr884_ingest_status.md`: live Copernicus ingest status and current official layer counts.
- `ops/data_acquisition_plan/official_imagery_manifest.csv`: official EMS imagery URL, acquisition, sensor, and range validation inventory.
- `ops/data_acquisition_plan/official_product_layer_inventory.csv`: inspected official ZIP/GPKG layer counts and damage-class summaries.
- `ops/data_acquisition_plan/source_access_manifest.csv`: URL status, content-type, content-length, and range validation for all planned sources.
- `ops/data_acquisition_plan/aoi12_v1_v2_remap.csv`: geometry remap between stale AOI12 public v1 and official AOI12 GRA v2.
- `ops/data_acquisition_plan/aoi12_vlm_v1_v2_reuse_queue.csv`: existing AOI12 VLM rows split into reuse versus regenerate.
- `ops/data_acquisition_plan/pre_event_imagery_coverage.csv`: Vantor pre-event STAC coverage by AOI without bulk TIFF downloads.
- `ops/data_acquisition_plan/external_prediction_official_overlap_summary.csv`: Microsoft/HDX external candidates split by overlap with official GRA polygons.
- `ops/data_acquisition_plan/vlm_spend_control_batches.csv`: no-spend, hold, chip-QA, and sample-first VLM batch controls.

## Current Live Ingest

The live Copernicus EMSR884 ingest was run on 2026-06-30 from:

`https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884`

Current snapshot:

- Activation remains open.
- 13 AOIs.
- 19 products.
- 10 downloadable final products.
- 22 official image records.
- 53 live API layer records.
- 10 official ZIPs downloaded locally under `ops/data_acquisition_plan/official_products/` for ops inspection only.

The local ZIP cache is about 241 MB and should not be committed or moved into public runtime assets without an explicit operational reason. The small CSV/JSON manifests are the commit-safe inventory.

Current follow-on ingest:

- AOI12 v1/v2 remap is complete: 93 existing before/after VLM rows are reusable with v2 binding, 14 have no v2 binding and should be retired, and 61 new AOI12 v2 features need new consideration.
- Vantor pre-event coverage is inventoried from STAC: AOI02 and AOI12 have useful official-feature coverage after coarse gates; AOI05, AOI06, AOI08, and AOI10 still lack Vantor pre-event coverage.
- Microsoft/HDX external prediction GPKGs are profiled: 11,173 high-priority candidates, 7,897 high-priority candidates outside current official GRA polygons.
- HOT now reports human-validated damage assessment coverage for Caraballeda, La Guaira, and Caracas, plus fAIr/Microsoft/OSU source splits in `hotosm/venezuela_eq_2026`. This is now a high-priority source for EMS-gap triage, not official EMS metrics.
- Current recommended next HF spend is capped at 61 AOI12 v2 calls after chip QA. External prediction spend should start with deduped samples capped at 554 calls, not full coverage.
- The data acquisition package was uploaded to R2 under `ops/data-acquisition/2026-06-30/`; see the R2 manifest at `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/ops/data-acquisition/2026-06-30/r2_upload_manifest.csv`.

## Execution Gates

1. Latest Copernicus product manifest is saved from the live API.
2. Revised official products are downloaded and versioned, especially AOI12 GRA v2 and AOI00 GRM v2.
3. AOI12 v1 to v2 feature remap exists with geometry hashes and overlap classes.
4. Official and public imagery manifests include acquisition time, source URL, license, COG/range validation, and coverage.
5. Candidate footprints are separated by source family: official EMS, MONIT01, OSM, Microsoft AI4G/HDX, HOT/fAIr, SAR/context.
6. Chip QA manifest exists before VLM: valid pixels, black/missing flags, blur/haze/pixelation, alignment, target visibility, and license gate.

Only candidates that pass these gates should enter HF VLM batches.
