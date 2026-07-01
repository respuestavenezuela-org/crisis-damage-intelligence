# EMSR884 Live Ingest Status

Checked: 2026-06-30T07:47:07Z

Source API:

`https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884`

## Summary

- Activation: EMSR884, still open.
- AOIs: 13.
- Products from live API: 19.
- Downloadable final products: 10.
- Official image records: 22.
- Live API layer records: 53.
- Inspected ZIP/GPKG layer rows: 54.
- Local official ZIP cache: 10 files, about 241 MB.

This ingest updates ops evidence only. It does not publish new public layers, change official public metrics, or make VLM claims.

## Generated Artifacts

- `ops/data_acquisition_plan/emsr884_live_products_20260630T074707Z.json`
- `ops/data_acquisition_plan/emsr884_live_products_latest.json`
- `ops/data_acquisition_plan/emsr884_product_manifest.csv`
- `ops/data_acquisition_plan/emsr884_product_images.csv`
- `ops/data_acquisition_plan/official_imagery_manifest.csv`
- `ops/data_acquisition_plan/emsr884_product_layers.csv`
- `ops/data_acquisition_plan/official_product_zip_manifest.csv`
- `ops/data_acquisition_plan/official_product_layer_inventory.csv`
- `ops/data_acquisition_plan/emsr884_ingest_summary.json`
- `ops/data_acquisition_plan/source_access_manifest.csv`
- `ops/data_acquisition_plan/aoi12_v1_v2_remap.csv`
- `ops/data_acquisition_plan/aoi12_vlm_v1_v2_reuse_queue.csv`
- `ops/data_acquisition_plan/pre_event_imagery_coverage.csv`
- `ops/data_acquisition_plan/pre_event_imagery_coverage_summary.csv`
- `ops/data_acquisition_plan/external_prediction_gpkg_inventory.csv`
- `ops/data_acquisition_plan/external_prediction_field_profiles.csv`
- `ops/data_acquisition_plan/external_prediction_official_overlap_summary.csv`
- `ops/data_acquisition_plan/external_prediction_official_overlap_detail.csv`
- `ops/data_acquisition_plan/vlm_spend_control_batches.csv`

## Official Built-Up Layer Counts

Official EMS GRA and MONIT01 counts must remain separated.

| Product | Layer | Official rows | Damage counts |
| --- | --- | ---: | --- |
| AOI02_GRA_v1 | builtUpA_v1 | 17 | Possibly damaged: 17 |
| AOI02_GRA_MONIT01_v2 | builtUpP_v1 | 20 | Destroyed: 3; Possibly damaged: 17 |
| AOI05_GRA_v1 | builtUpP_v1 | 3 | Destroyed: 3 |
| AOI06_GRA_v1 | builtUpA_v1 | 129 | Damaged: 34; Destroyed: 2; Possibly damaged: 93 |
| AOI06_GRA_MONIT01_v2 | builtUpP_v1 | 96 | Damaged: 39; Destroyed: 8; Possibly damaged: 49 |
| AOI08_GRA_v1 | builtUpA_v1 | 43 | Damaged: 8; Possibly damaged: 35 |
| AOI08_GRA_MONIT01_v2 | builtUpP_v1 | 183 | Damaged: 14; Possibly damaged: 169 |
| AOI12_GRA_v2 | builtUpA_v2 | 166 | Damaged: 130; Destroyed: 10; Possibly damaged: 26 |
| AOI12_GRA_MONIT01_v1 | builtUpP_v1 | 1004 | Damaged: 346; Destroyed: 422; Possibly damaged: 236 |

AOI08 MONIT01 reports `Feature Count: 0` through `ogrinfo` for `builtUpP_v1`, but direct SQLite row count is 183 and damage-class grouping also totals 183. Use `sqlite_row_count` for this product until the GPKG metadata issue is inspected.

## Official Imagery Validation

- Optical COGs: 20/20 responded to HEAD with 200 and range GET with 206.
- SAR COGs for AOI00 GRM: 2/2 returned 403 from the derived public S3 path.
- Direct building VLM source eligibility: optical COGs are conditional pending chip QA and pre-event match; SAR remains context only.

## Source Inventory Access Validation

- Inventory sources checked: 44.
- HEAD 200: 38.
- Range GET usable: 44.
- P0 official ZIP URLs return HEAD 405 but range GET 206, so they remain ingestible.
- Vantor pre-event TIFFs are reachable with range support, but are large: about 3 GB to 55 GB each. Use windowed/range reads for chip generation and QA; do not bulk-download all scenes without a specific coverage job.
- Microsoft AI4G/HDX GPKGs are reachable with range support and are small enough for schema/dedupe ingestion, but remain external triage only.

## AOI12 v1 To v2 Remap

- Old public AOI12 GRA v1 features: 120.
- New official AOI12 GRA v2 features: 166.
- Matched old features: 105.
- New v2 features requiring new chip/VLM consideration: 61.
- Retired or not-located v1 features: 15.
- Existing AOI12 before/after VLM rows: 107.
- Existing VLM rows reusable with v2 binding: 93.
- Existing VLM rows to retire because no v2 binding exists: 14.
- Official class changes on matched geometry: 3 features changed from `Possibly damaged` to `Damaged`.

The remap is geometry-based. It does not publish AOI12 v2 into the public app yet.

## Pre-Event Coverage

- Vantor pre-event STAC items inventoried: 10.
- AOI-scene intersections: 27.
- AOIs with Vantor pre-event coverage: 9.
- AOIs with at least one scene eligible after chip QA: 8.
- Official AOIs with currently useful Vantor coverage: AOI02 and AOI12, including their MONIT01 products.
- Official AOIs still lacking Vantor pre-event coverage in this manifest: AOI05, AOI06, AOI08, and AOI10.

Eligible means source/range/coverage passed coarse gates. It still requires chip-level valid-pixel, target visibility, blur/haze, and alignment QA before VLM.

## External Prediction Triage Inventory

- Microsoft/HDX GPKGs downloaded/profiled: 4.
- External prediction features profiled: 71,296.
- High-priority external features by `damaged = 1` or max damage pct >= 0.5: 11,173.
- High-priority external features outside current official GRA polygons: 7,897.
- Official GRA polygons compared: 355.

These remain external triage candidates only. They must not be merged into official EMS counts.

## VLM Spend Control

- Spend-control batches generated: 12.
- Ready with no HF spend: 3 batches.
- Maximum justified next official VLM calls before more dedupe: 61, for new AOI12 v2 features after chip QA.
- External sample ceiling after dedupe/chip QA: 554 calls, not 7,897.
- Holds: AOI05, AOI06, AOI08, and AOI10 before/after VLM are blocked on high-resolution pre-event imagery.

## R2 Upload Status

Uploaded: 2026-06-30.

- Bucket: `crisis-damage-intelligence`.
- Prefix: `ops/data-acquisition/2026-06-30/`.
- Objects uploaded: 48.
- Uploaded bytes: 272,852,190 bytes.
- Public manifest: `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/ops/data-acquisition/2026-06-30/r2_upload_manifest.csv`.
- Public range audit: 48 checked, 0 failed.
- Sampled large object: `official_products/EMSR884_AOI00_GRM_PRODUCT_v2.zip` returned HTTP 206 with `application/zip`.

The upload includes official EMS product ZIPs, external Microsoft/HDX GPKGs, manifests, remap outputs, pre-event coverage outputs, and spend-control batches. It does not include bulk Vantor TIFF downloads.

## Downloaded Final Products

- AOI00_GRM_v2, Central Coastal Venezuela, delivered 2026-06-29T15:08:43.758312.
- AOI02_GRA_v1, Caracas, delivered 2026-06-26T04:01:10.948274.
- AOI02_GRA_MONIT01_v2, Caracas, delivered 2026-06-29T18:18:07.700477.
- AOI05_GRA_v1, Santa Cruz, delivered 2026-06-27T23:49:49.849118.
- AOI06_GRA_v1, Moron, delivered 2026-06-26T07:24:29.440918.
- AOI06_GRA_MONIT01_v2, Moron, delivered 2026-06-29T11:25:23.016205.
- AOI08_GRA_v1, San Felipe, delivered 2026-06-26T17:38:03.884275.
- AOI08_GRA_MONIT01_v2, San Felipe, delivered 2026-06-29T17:28:21.981067.
- AOI12_GRA_v2, Caraballeda, delivered 2026-06-27T19:54:43.077956.
- AOI12_GRA_MONIT01_v1, Caraballeda, delivered 2026-06-27T18:17:36.339574.

## Current Blockers Before Broad VLM Spend

1. Build chip QA manifests from official optical COGs plus licensed pre-event imagery before launching parallel HF jobs.
2. Build new AOI12 v2 chip/VLM queue for the 61 new v2 features and archive 14 retired/not-located prior VLM rows.
3. Find high-resolution pre-event imagery for AOI05, AOI06, AOI08, and AOI10 before before/after VLM there.
4. Dedupe and sample the 7,897 high-priority external candidates outside official GRA polygons before any broad external VLM spend.
5. Keep MONIT01 and GRA products separate in metrics and review queues.
6. Do not commit the local `official_products/` ZIP cache unless explicitly approved; commit the manifests instead.
