# Operational Progress

Update this after every work loop. Keep entries factual: what changed, how it was tested, where evidence lives, what remains blocked, and the next recommended action.

## Current Deployment

- Public app: https://crisis-damage-intelligence.vercel.app
- Package/repo path: `/Users/luisrosal/Documents/Codex/2026-06-26/he/outputs/crisis_damage_intelligence_platform`
- Primary app file: `src/components/OperationsConsole.tsx`
- Map implementation: `src/components/map/MapPanel.tsx`
- Catalog: `public/data/catalog.json`

## Current Operational Data State

- AOI12 La Guaira / Caraballeda:
  - Official EMSR884 vector: 120 features.
  - EMS post-event imagery: available.
  - Vantor pre-event reference: available with partial coverage/gaps.
  - VLM before/after comparisons: 107 reviewed, 13 skipped because before coverage was missing/black.
- AOI02 Caracas:
  - Official EMSR884 vector: 17 features.
  - MONIT01 points: 20.
  - Post-event imagery available.
  - Vantor pre-event reference scene identified: B160001100FD1910, 2026-03-20, LG06, 1% cloud cover.
  - VLM before/after comparisons: 17 reviewed, 0 skipped, but 15 are uncertain comparison problems because many post-event chips are dark/hazy, shadowed, or centered on canopy rather than clear rooftops.
- AOI06 Moron:
  - Official EMSR884 vector: 129 features.
  - MONIT01 points: 96.
  - Post-event imagery available.
- AOI08 San Felipe:
  - Official EMSR884 vector: 43 features.
  - MONIT01 points: 183.
  - Post-event imagery available.
- AOI03 Antimano:
  - Imagery available.
  - No official damage vector currently shown.
- AOI10 Guacara:
  - Imagery available.
  - No official damage vector currently shown.
- Catia La Mar:
  - Microsoft AI4G external prediction layer: 9,134 candidates.
  - This is triage-only and not official EMS confirmation.

## Recent Completed Work

### 2026-06-28 - AOI02 Before Tiles and Approximate Reference Queue

- Objective: move quickly on missing pre-event references without pretending approximate basemaps are official before imagery.
- Files changed/generated:
  - Generated AOI02 Vantor pre-event WebP tiles under `public/data/tiles/emsr884-aoi02-caracas/before/`.
  - Updated `public/data/catalog.json` with AOI02 `layers.beforeTiles` and before tile pyramid metadata.
  - Documented AOI12 WV03 `10400100B979DD00` as a candidate west-edge gap-fill scene, but did not promote it into the published AOI12 before mosaic because it has 30% cloud cover and limited incremental coverage.
  - Added `scripts/build_approximate_basemap_reference_queue.py`.
  - Generated `ops/approximate_basemap_reference_queue/queue.csv`, `queue.json`, `queue.jsonl`, and `README.md`.
- AOI02 tile result:
  - Source: Vantor Open Data scene `B160001100FD1910`, LG06, 2026-03-20T14:46:55Z, 1% cloud.
  - Tile range: z12-z18.
  - Tile count: 10,092.
  - Size: 64,840,354 bytes.
  - Caveat: northern AOI edge may contain transparent/black pixels where the Vantor scene does not cover the full AOI bounds.
- Approximate reference queue:
  - Records: 172.
  - AOI06 Moron: 129.
  - AOI08 San Felipe: 43.
  - Evidence mode: `approximate_aerial_reference_not_dated_before`.
  - Intended only for triage when no dated high-resolution baseline exists.
  - Do not merge these results into official EMS or dated before/after VLM counts.
- R2 sync status:
  - Wrangler object-by-object upload was tested and is too slow for the full AOI02 before tile set.
  - 148 AOI02 before tiles were uploaded before stopping the test.
  - To avoid blocking publication, AOI02 before tiles now use a GitHub raw static fallback URL in `public/data/catalog.json`.
  - R2 remains the preferred long-term host, but production no longer needs the incomplete AOI02 R2 upload to show Caracas before imagery.
- Next recommended action:
  - Use S3-compatible R2 credentials with `scripts/upload_to_object_storage.py`, or run a GitHub Actions/cloud sync, to upload `public/data/tiles/emsr884-aoi02-caracas/before/` in bulk and then switch AOI02 back from GitHub raw to R2.
  - After sync, run `python3 scripts/validate_remote_asset_urls.py --sample-per-template 20 --sample-chips 40`.
  - Until that migration, validate the GitHub raw AOI02 before URL samples after each push.

### 2026-06-28 - External Source Quality/Recency Review

- Objective: classify newly supplied sources by operational value, recency, and publication risk.
- Files changed:
  - Updated `public/data/sources/earthquake_source_review.json`.
  - Updated `ops/external_source_review/review_queue.csv`.
- Commands/checks run:
  - Queried HDX CKAN metadata for Microsoft AI4G Venezuela datasets.
  - Checked VOSOCC JPEG URLs for HTTP availability and file type.
  - Checked ArcGIS item metadata through ArcGIS REST.
  - Checked PKU, INGV, Rodolfo Franco, EarthquakeInsights, and Marksblogg pages for availability and relevance.
  - `python3 scripts/validate_external_source_registry.py`
- Keep as high-value operational/triage data:
  - Microsoft AI4G via HDX: Catia La Mar, Catia La Mar East, La Guaira, and Caraballeda datasets. These are recent, include GPKG/GeoJSON/JPEG resources, and are useful as external model triage, but they remain non-official and must stay separate from EMS labels.
  - VOSOCC-hosted Rescue International sector JPEGs for Macuto, Los Corales/Caraballeda W, and Vargas/La Guaira. The JPEGs are available and high-resolution, but not georeferenced and redistribution/derivative rights are not confirmed.
  - Mitchell Ulrich X thread reporting 295 visually mapped collapsed/partially collapsed structures. This is very recent and potentially valuable, especially west-to-east coastal coverage, but no downloadable coordinates/vector source or reuse permission was found.
- Keep as secondary/reference only:
  - Rodolfo Franco ArcGIS WebScene. It visualizes Microsoft AI4G/HDX Catia La Mar data and is useful for cross-checking, but direct HDX GPKG ingestion remains the reproducible source.
  - HOT/OSM/Overture HDX context export. Useful for exposure/roads/buildings context after filtering, not a damage source.
- Keep as scientific/context only:
  - PKU preliminary rupture model.
  - INGV extended source article.
  - EarthquakeInsights Substack article.
  - Rodolfo Franco disaster geodata directory.
- Do not spend operational product time on:
  - Marksblogg SAR aircraft article. It is remote-sensing methodology background and not Venezuela earthquake damage data.
- Next recommended action:
  - Georeference the VOSOCC sector JPEGs outside the repo and use them as human validation evidence.
  - Request or derive geometry for the Mitchell Ulrich collapse inventory before using it in any map/count.
  - Review the newly found Microsoft AI4G GPKGs against official EMS AOI12/AOI02/AOI06 coverage before adding any public layer.

### Before/After VLM For AOI12

- Added `scripts/run_minimax_ems_before_after_review.py`.
- AOI12 catalog now points to `vlm_before_after_review.jsonl`.
- Evidence panel prefers before/after comparison chip where available.
- Public QA verified `ems_00050` shows `dated_pre_event_comparison`.
- Deployment: https://crisis-damage-intelligence.vercel.app

Results:
- reviewed: 107
- skipped no-before/black-before: 13
- likely_destroyed: 26
- possible_major_damage: 33
- uncertain_comparison_problem: 32
- minor_visible_damage: 14
- no_change_visible: 2

QA evidence:
- `qa/local-before-after-vlm-qa.png`
- `qa/vercel-before-after-vlm-qa.png`

### Popup Clear On Background Click

- Map popup opens when clicking a feature.
- Clicking outside a polygon clears selected feature, popup, marker, and highlight.
- Public QA passed.

QA evidence:
- `qa/local-click-background-clears-popup.png`
- `qa/vercel-click-background-clears-popup.png`

### Affected Area Navigation

- Left navigation now shows affected areas instead of technical AOI/layer records.
- Label changed from `Ir a ciudad / AOI` to `Ir a zona afectada`.
- Areas are sorted by aggregated impact signal.
- Current order in Spanish:
  1. La Guaira / Caraballeda / Catia La Mar
  2. San Felipe
  3. Moron
  4. Caracas
  5. Antimano
  6. Guacara

QA evidence:
- `qa/local-city-nav-impact-order.png`
- `qa/vercel-city-nav-impact-order.png`

### Damage Opacity Behavior

- Damage opacity now applies to polygon and point outlines, not only fill.
- Moving opacity slider no longer refocuses the selected feature or forces zoom.
- Public QA passed with opacity `0.52 -> 0.05` and same focused feature.

QA evidence:
- `qa/local-opacity-slider-no-refocus.png`
- `qa/vercel-opacity-slider-no-refocus.png`

### AOI02 Caracas Before/After VLM Pilot

- Objective: expand credible before/after VLM beyond AOI12.
- Inventory result:
  - AOI02 has usable Vantor pre-event scene coverage for all 17 official EMS features.
  - Scene selected: `B160001100FD1910`, Vantor LG06, `2026-03-20T14:46:55Z`, 1% cloud cover.
  - AOI06 Moron, AOI08 San Felipe, and AOI10 Guacara have no Vantor Open Data pre-event scene intersection in the current Venezuela Earthquake Jun 2026 STAC collection.
  - AOI03 Antimano has Vantor pre-event scene intersections, but no official EMS damage vector yet.
- Implementation:
  - Generalized `scripts/run_minimax_ems_before_after_review.py` to support remote `/vsicurl/` Vantor COGs and CRS-safe chip extraction via `-projwin_srs EPSG:4326`.
  - Added yellow/black EMS feature outline overlays to before/after chips so the VLM and human reviewer can compare the mapped feature geometry, not only the centroid reticle.
  - Added `--force` and `--chips-only` runner modes so chips can be regenerated with better evidence overlays without re-spending VLM calls.
  - Ran VLM before/after for all 17 AOI02 official EMS features.
  - Updated `public/data/catalog.json` so AOI02 VLM layer uses `vlm_before_after_review.jsonl`.
- Results:
  - reviewed: 17
  - skipped no-before/black-before: 0
  - uncertain_comparison_problem: 15
  - no_change_visible: 1
  - minor_visible_damage: 1
  - action priorities: 13 review, 3 urgent_review, 1 deprioritize
- QA performed:
  - `npm run lint && npm run build`
  - Local browser QA: navigated to Caracas, opened `ems_00001`, verified compare chip loads and evidence shows `dated_pre_event_comparison`.
- Evidence:
  - `qa/aoi02-before-after-vlm-pilot-contact-sheet.png`
  - `qa/aoi02-before-after-vlm-full-contact-sheet.png`
  - `qa/aoi02-before-after-vlm-outlined-pilot-contact-sheet.png`
  - `qa/aoi02-before-after-vlm-outlined-full-contact-sheet.png`
  - `qa/local-aoi02-before-after-vlm.png`
- Result:
  - AOI02 now has complete before/after VLM coverage, but outputs are mostly uncertainty flags. The outline overlays show why: several EMS polygons are broad or edge-aligned and the centroid/outlined geometry may include canopy, road edge, or shadow instead of a clean roof target. This should be treated as a successful evidence-quality finding, not as a strong damage classifier.
- Next recommended action:
  - Search for better non-Vantor pre-event imagery for AOI02 or use AOI03 as an imagery-only comparison pilot only if there are credible damage candidates. Do not scale AOI02 further without improving post-event chip quality or candidate centering.

### AOI02 Coordinate Verification

- Objective: verify that AOI02 map navigation, Google Maps links, and before/after chips are using the intended coordinates.
- Checks performed:
  - Compared `centroid_lat` / `centroid_lon` against each feature's `google_maps_url` query for AOI02, AOI12, and AOI06 samples.
  - Confirmed all 17 AOI02 feature centroids fall inside their source geometry bounding boxes.
  - Browser QA selected Caracas `ems_00001` and confirmed map center is `10.4101149,-66.8746227` at zoom 18, matching the feature centroid `10.41011488724138,-66.87462265793104`.
  - Checked chip extraction window for AOI02 `ems_00001`; before and after raster pixel coordinates both fall inside their respective rasters, with the same EPSG:4326 source window.
- Result:
  - No lat/lon swap or wrong-coordinate navigation was found.
  - The visual issue in AOI02 appears to come from EMS feature centroids and imagery quality: some `builtUpA` features/centroids fall on canopy, shadows, or broad mapped areas rather than a clearly visible roof center.
- Evidence:
  - `qa/local-aoi02-coordinate-centering-check.png`
- Next recommended action:
  - For VLM chips, consider using a better representative point derived from polygon interior/building footprint or a small multi-chip context around the feature, instead of relying only on the EMS centroid.

### 2026-06-27 - AOI03 OSM Candidate Before/After VLM Pilot

- Objective: continue before/after VLM expansion without pretending AOI03 has official EMS damage vectors.
- Files changed:
  - Added `scripts/inventory_pre_event_baselines.py`.
  - Added `scripts/extract_aoi03_osm_candidates.py`.
  - Added `scripts/run_aoi03_osm_before_after_pilot.py`.
  - Wrote baseline inventory under `ops/baseline_inventory/`.
  - Wrote candidate-only VLM pilot outputs under `ops/aoi03_osm_before_after_pilot/`.
- Commands run:
  - `python3 scripts/inventory_pre_event_baselines.py`
  - `python3 scripts/extract_aoi03_osm_candidates.py`
  - `python3 scripts/run_aoi03_osm_before_after_pilot.py --run-vlm --limit 24 --workers 4`
  - `python3 scripts/run_aoi03_osm_before_after_pilot.py --run-vlm --limit 60 --workers 5`
- Baseline inventory result:
  - AOI03 Antimano has Vantor Open Data pre-event scene intersections suitable for a building-level pilot.
  - AOI06 Moron, AOI08 San Felipe, and AOI10 Guacara still only found Sentinel-2 context imagery in this inventory pass; this is not suitable for building-level VLM.
- Candidate extraction result:
  - Extracted 498 AOI03 OpenStreetMap building-footprint candidates.
  - These are not damage claims and are not official EMS features.
- Parallel VLM result:
  - Selected first 60 prioritized OSM candidates.
  - Generated 25 usable before/after chip triplets.
  - Skipped/failed 35 because before/after chips were missing, blank, or unusable.
  - VLM classes among 25 generated comparisons:
    - uncertain_comparison_problem: 17
    - possible_major_damage: 6
    - minor_visible_damage: 1
    - likely_destroyed: 1
  - Action priorities:
    - urgent_review: 6
    - review: 18
    - deprioritize: 1
- QA performed:
  - Visual contact sheet review confirmed many AOI03 after chips are degraded by haze/smoke/blank imagery.
  - The `possible_major_damage` and `likely_destroyed` outputs are useful as a review queue signal only; they are not publishable as operational damage because AOI03 features are OSM candidates and several comparisons have imagery-quality caveats.
- Evidence:
  - `ops/aoi03_osm_before_after_pilot/pilot_records.json`
  - `ops/aoi03_osm_before_after_pilot/pilot_summary.json`
  - `ops/aoi03_osm_before_after_pilot/pilot_summary.csv`
  - `qa/aoi03-osm-before-after-vlm-25-contact-sheet.png`
- Deployment:
  - Not deployed and not added to `public/data/catalog.json`.
  - Temporary public chip files were removed after copying pilot artifacts to `ops/`.
- Result:
  - The before/after VLM pipeline now supports a parallel candidate-only workflow for areas without official EMS damage vectors.
  - AOI03 can produce a triage review queue, but the current post-event imagery quality is too weak for public operational claims.
- Blockers:
  - AOI03 needs better post-event imagery, official damage vectors, or human-verified candidate reports before any candidate layer should be published.
  - The Vantor `/vsicurl/` path emits GDAL `.msk` warnings and can be slow; larger batches need chunking/timeouts or cached source rasters.
- Next recommended action:
  - Use the AOI03 candidate pilot only as internal triage evidence.
  - For public app value, prioritize official EMS AOI updates and better pre-event baselines for AOI06/AOI08, or move current tiles/chips to R2 so public loading stays fast.

### 2026-06-27 - AOI03 Internal Review Queue Export

- Objective: make the AOI03 candidate-only VLM pilot actionable for human review without publishing it as confirmed/operational damage.
- Files changed:
  - Added `scripts/build_aoi03_internal_review_queue.py`.
  - Generated `ops/aoi03_internal_review_queue/review_queue.csv`.
  - Generated `ops/aoi03_internal_review_queue/review_queue.geojson`.
  - Generated `ops/aoi03_internal_review_queue/review_queue.kml`.
  - Generated `ops/aoi03_internal_review_queue/README.md`.
- Commands run:
  - `python3 scripts/build_aoi03_internal_review_queue.py`
- Result:
  - Exported 8 AOI03 OSM candidate points for internal review:
    - 1 `likely_destroyed`
    - 6 `possible_major_damage`
    - 1 `minor_visible_damage`
  - The queue is sorted by severity/confidence and includes Google Maps links, compare-chip paths, before/after source metadata, VLM evidence, uncertainty text, and a repeated internal-only warning.
- Guardrail:
  - These outputs remain under `ops/`, not `public/data/`.
  - They are not in `public/data/catalog.json`.
  - They should be used only to request human validation or better imagery, not as a public damage layer.
- Next recommended action:
  - If humans can review these 8 candidates, record validation outcomes as static JSONL/CSV before considering any public display.
  - Otherwise, continue official EMS monitoring and before-baseline search for AOI06/AOI08.

### 2026-06-27 - Public VLM Coverage And Uncertainty Metrics

- Objective: make before/after VLM output more useful and less misleading in the public app.
- Files changed:
  - Added `scripts/update_catalog_vlm_metrics.py`.
  - Updated `public/data/catalog.json` with normalized before/after VLM metrics from summary JSON.
  - Updated `src/components/OperationsConsole.tsx` to show a bilingual VLM before/after quality panel.
  - Updated `src/app/globals.css` with compact metric styling.
- Commands run:
  - `python3 scripts/update_catalog_vlm_metrics.py`
  - `npm run lint`
  - `npm run build`
  - `portless vlm-quality npm start`
- Result:
  - AOI12 public UI now surfaces:
    - 107 reviewed
    - 13 skipped no-before
    - 32 uncertain, 30%
    - 73 visible-change signals
    - 33 urgent review
    - 89% usable coverage
  - AOI02 public UI now surfaces:
    - 17 reviewed
    - 0 skipped no-before
    - 15 uncertain, 88%
    - 1 visible-change signal
    - 3 urgent review
    - 100% usable coverage
  - The panel explicitly says VLM signals are triage aids only and high uncertainty means the imagery pair could not support a reliable damage call.
- QA performed:
  - Local production server via Portless.
  - Browser QA confirmed Spanish panel values for La Guaira and Caracas.
  - Browser QA confirmed English panel copy for La Guaira.
- Evidence:
  - `qa/local-vlm-quality-panel.png`
  - `qa/local-vlm-quality-panel-en.png`
- Deployment:
  - Not deployed in this loop.
- Next recommended action:
  - Deploy after review, or continue with before-baseline search for AOI06/AOI08 if we want more VLM coverage before pushing another public update.

### 2026-06-27 - Expanded Internal AOI03 Before/After VLM Batch

- Objective: continue VLM analysis in parallel, but only where before/after imagery exists, without publishing candidate-only results as operational EMS damage.
- Commands run:
  - `VLM_WORKERS=5 python3 scripts/run_aoi03_osm_before_after_pilot.py --limit 120 --workers 5 --run-vlm`
  - `python3 scripts/build_aoi03_internal_review_queue.py`
- Result:
  - Selected 120 OpenStreetMap building candidates in AOI03 Antimano.
  - Generated 62 usable before/after chip triplets.
  - Skipped/failed 58 candidates because before/after chips were missing, blank, or unusable.
  - VLM classes across the 62 generated records:
    - 47 `uncertain_comparison_problem`
    - 9 `possible_major_damage`
    - 2 `likely_destroyed`
    - 2 `minor_visible_damage`
    - 2 `no_change_visible`
  - Internal human-review queue now has 13 candidates.
- Files updated:
  - `ops/aoi03_osm_before_after_pilot/pilot_records.json`
  - `ops/aoi03_osm_before_after_pilot/pilot_summary.json`
  - `ops/aoi03_osm_before_after_pilot/pilot_summary.csv`
  - `ops/aoi03_internal_review_queue/review_queue.csv`
  - `ops/aoi03_internal_review_queue/review_queue.geojson`
  - `ops/aoi03_internal_review_queue/review_queue.kml`
- Guardrail:
  - AOI03 outputs remain internal only. They use OSM candidate footprints, not official EMS damage vectors, and must not be displayed as confirmed Venezuela operational damage.
- Next recommended action:
  - Human-review the 13 AOI03 candidates before any public display, or continue searching for better before baselines for AOI06/AOI08.

### 2026-06-27 - R2 Reality Check And Lightweight Remote Outputs

- Objective: unblock deployability by verifying what can safely move out of Vercel.
- Findings:
  - Local `public/data` has 64,500 files.
  - `public/data/tiles` and `public/data/chips` account for 64,426 files and about 395 MB.
  - `vercel deploy --prod --yes` failed because Vercel received 64,691 files, above the 15,000-file request limit.
  - `vercel deploy --prod --yes --archive=tgz` did not complete in a practical time window and was interrupted.
  - Cloudflare R2 bucket `crisis-damage-intelligence` exists.
  - Previous R2 uploads were likely local Wrangler uploads because `--remote` was missing.
  - Public R2 access via `r2.dev` is now enabled at `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev`.
  - Confirmed remote upload/read works with `ems/generated/catalog.json`.
- Commands run:
  - `npx wrangler r2 bucket list`
  - `npx wrangler r2 bucket info crisis-damage-intelligence --json`
  - `npx wrangler r2 bucket dev-url get crisis-damage-intelligence`
  - `npx wrangler r2 bucket dev-url enable crisis-damage-intelligence`
  - `npx wrangler r2 object put crisis-damage-intelligence/ems/generated/catalog.json --remote --file public/data/catalog.json --content-type application/json --cache-control 'public, max-age=300'`
  - `npx wrangler r2 object get crisis-damage-intelligence/ems/generated/catalog.json --remote --file /tmp/cdi-r2-catalog.json`
- Current status:
  - Static lightweight AOI outputs were uploaded under `ems/generated/aoi/...`.
  - Verified public R2 catalog URL returns HTTP 200:
    - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/ems/generated/catalog.json`
  - Verified public R2 AOI12 GeoJSON returns HTTP 200 and 120 features:
    - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/ems/generated/aoi/emsr884-aoi12-caraballeda/damage.geojson`
  - Tiles/chips are not yet moved to R2/CDN. Uploading 64k files through one-file-at-a-time Wrangler commands is technically possible but operationally poor.
- Blocker:
  - Before deploying a pruned Vercel package, tiles/chips need either a proper bulk S3/R2 sync path or a generated deploy catalog pointing imagery/chip URLs to a verified public R2/CDN base.

### 2026-06-27 - Coordinate Focus Verification

- Objective: verify map focus and Google Maps links are not using inverted or wrong coordinates.
- Commands run:
  - Python GeoJSON audit comparing `centroid_lat`/`centroid_lon`, Google Maps query strings, and geometry locations across all `public/data/aoi/*/damage.geojson`.
- Result:
  - No evidence of lat/lon inversion.
  - Google Maps links match `query=lat,lon` from feature properties.
  - A small number of feature centroid points fall just outside the polygon geometry, generally by less than 30 m. This is a focus precision issue, not a wrong-city/wrong-coordinate issue.
- Code changed:
  - `src/components/map/MapPanel.tsx` now centers/popup-focuses on `centroid_lat`/`centroid_lon` only when that point intersects the geometry. If not, it falls back to an interior polygon point, then extent center.
- QA performed:
  - `npm run lint`
  - `npm run build`

### 2026-06-27 - Vercel Remote-Asset Package Path

- Objective: make the app deployable without sending 64k local tile/chip files to Vercel.
- Files changed:
  - Added `scripts/build_vercel_remote_asset_package.py`.
  - Updated `src/components/OperationsConsole.tsx` so evidence chip links preserve full remote URLs instead of reconstructing `/data/chips/...` from older paths.
  - Updated `.gitignore` for generated package artifacts.
- Commands run:
  - `python3 -m py_compile scripts/build_vercel_remote_asset_package.py`
  - `python3 scripts/build_vercel_remote_asset_package.py --force`
  - `npm run lint`
  - `npm run build`
  - From generated package: `npm install && npm run build`
- Result:
  - Generated package path:
    - `/Users/luisrosal/Documents/Codex/2026-06-26/he/outputs/crisis_damage_intelligence_vercel_remote_assets`
  - Package excludes:
    - `public/data/tiles`
    - `public/data/chips`
    - `.git`, `.next`, `.vercel`, `node_modules`, `ops`, `qa`, `outputs`
  - Package manifest:
    - `/Users/luisrosal/Documents/Codex/2026-06-26/he/outputs/crisis_damage_intelligence_vercel_remote_assets/REMOTE_ASSET_PACKAGE_MANIFEST.json`
  - Package file count before install/build: 128.
  - Package rewrites tile/chip references to:
    - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/...`
    - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/chips/...`
  - Clean install/build from the package succeeds.
- Current blocker:
  - R2 public URLs for rewritten tile/chip paths currently return 404.
  - Verified examples:
    - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/chips/emsr884-aoi12-caraballeda/ems_00006_before_after_compare.png` -> 404
    - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/emsr884-aoi12-caraballeda/after/18/82294/123319.webp` -> 404
- Next recommended action:
  - Bulk upload `public/data/chips` and `public/data/tiles` to the R2 bucket preserving the `data/chips/...` and `data/tiles/...` keys, preferably using S3-compatible credentials and `aws s3 sync`. One-file-at-a-time Wrangler uploads are too slow for 64k tile files.

### 2026-06-27 - Evidence Chips Mirrored To Public R2

- Objective: make the remote-asset package useful for VLM evidence previews by moving chips out of Vercel.
- Commands run:
  - `find public/data/chips -type f ... > /tmp/cdi-chip-files.txt`
  - Parallel `npx wrangler r2 object put crisis-damage-intelligence/data/chips/... --remote --file ... --content-type image/png --cache-control 'public, max-age=31536000, immutable'`
  - Full public URL audit with `curl` against `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/chips/...`
- Result:
  - 681 evidence chip images uploaded to R2 under `data/chips/...`.
  - One Cloudflare R2 500 occurred for `emsr884-aoi12-caraballeda/ems_00081_after_event.png`; retry succeeded.
  - A high-concurrency audit produced 71 `429` responses from `r2.dev`; a slower follow-up audit confirmed those objects return HTTP 200.
- Verified examples:
  - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/chips/emsr884-aoi12-caraballeda/ems_00006_before_after_compare.png` -> HTTP 200, PNG 1024x548.
  - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/chips/emsr884-aoi02-caracas/ems_00001_before_after_compare.png` -> HTTP 200, PNG 1024x548.
- Current blocker:
  - Tile URL sample still returns 404:
    - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/emsr884-aoi12-caraballeda/after/18/82294/123319.webp`
  - Wrangler has no bulk `r2 object sync` or `list` command in the installed version; object-level `put/get/delete` only.
- Next recommended action:
  - Upload tiles with S3-compatible R2 credentials and `aws s3 sync`, or install/use an S3-compatible sync client. Avoid Wrangler-per-file for the 63k tile pyramid unless there is no alternative.

### 2026-06-27 - AOI12 Medium-Zoom Tiles Mirrored To Public R2

- Objective: make La Guaira/Caraballeda imagery available from R2 at useful entry/city zoom levels while avoiding an impractical 19k-file Wrangler run for all z18 residential tiles.
- Files changed:
  - Added `scripts/upload_r2_tiles_with_wrangler.py`, a resumable, logged Wrangler fallback uploader for scoped tile batches.
  - Added upload logs under `ops/r2_tile_uploads/`.
- Commands run:
  - `python3 -m py_compile scripts/upload_r2_tiles_with_wrangler.py`
  - Smoke: `python3 scripts/upload_r2_tiles_with_wrangler.py --aoi emsr884-aoi12-caraballeda --kind after --min-zoom 18 --max-zoom 18 --limit 20 --workers 8`
  - Full scoped batch: `python3 scripts/upload_r2_tiles_with_wrangler.py --aoi emsr884-aoi12-caraballeda --kind after --kind before --min-zoom 12 --max-zoom 16 --workers 10`
- Result:
  - AOI12 z12-z16 before/after tiles uploaded: 1,409/1,409, 0 failures.
  - Additional interrupted exploratory AOI12 upload logged 451 successful tiles across z12-z18 before stopping because full z18 upload via Wrangler was too slow.
  - Initial z18 smoke uploaded 20/20 tiles.
- Verified public examples:
  - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/emsr884-aoi12-caraballeda/after/12/1285/1927.webp` -> HTTP 200
  - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/emsr884-aoi12-caraballeda/after/16/20555/30824.webp` -> HTTP 200
  - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/emsr884-aoi12-caraballeda/before/12/1285/1926.webp` -> HTTP 200
  - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/emsr884-aoi12-caraballeda/before/16/20555/30826.webp` -> HTTP 200
- Still pending:
  - Most AOI12 z17-z18 tiles are not mirrored yet. Example z18 tile still returns 404:
    - `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/emsr884-aoi12-caraballeda/after/18/82294/123319.webp`
- Next recommended action:
  - Use S3-compatible sync for z17-z18 and other AOIs. Wrangler fallback is acceptable for scoped z12-z16 batches but too slow for the full residential tile pyramid.

### 2026-06-27 - Privacy-Safe Analytics Foundation

- Objective: track whether responders use the public app effectively without collecting personal data, feature ids, coordinates, or full external URLs.
- Files changed:
  - Added `@vercel/analytics` pageview support.
  - Added `src/lib/analytics.ts` provider-neutral event queue/dispatcher.
  - Added `src/components/AnalyticsEvents.tsx` delegated click tracking for links.
  - Instrumented language, AOI, imagery mode, basemap, damage filter, priority click, downloads, Google Maps, and evidence chip interactions.
  - Added `docs/ANALYTICS.md`.
- Privacy guardrails:
  - Custom events do not send names, emails, IPs, coordinates, feature/building ids, full Google Maps URLs, chip URLs, or free text.
  - Custom Vercel event sending is opt-in with `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=vercel`; otherwise events remain local/provider-neutral and pageviews use Vercel Web Analytics only.
- QA performed:
  - `npm run lint`
  - `npm run build`
- Next recommended action:
  - Deploy with pageview analytics enabled and only enable custom interaction forwarding after confirming Vercel quota/cost settings.

### 2026-06-27 - AOI03 Internal Before/After VLM Expansion

- Objective: make concrete progress on before/after VLM analysis where official EMS vectors are unavailable, without publishing non-official OSM candidates as operational damage.
- Scope:
  - AOI03 Antimano only.
  - OpenStreetMap building candidates only.
  - Internal QA/review outputs only; nothing was added to the public operational catalog.
- Commands run:
  - `VLM_WORKERS=5 python3 scripts/run_aoi03_osm_before_after_pilot.py --limit 180 --workers 5 --run-vlm`
  - `python3 scripts/build_aoi03_internal_review_queue.py`
- Result:
  - 180 candidates selected.
  - 95 before/after chip triplets generated and reviewed by VLM.
  - 85 chip-generation failures, mostly due to missing/blank/insufficient source tiles.
  - Damage classes:
    - `likely_destroyed`: 6
    - `possible_major_damage`: 10
    - `minor_visible_damage`: 3
    - `no_change_visible`: 4
    - `uncertain_comparison_problem`: 72
  - Internal review queue increased to 19 candidates.
- Files changed:
  - `ops/aoi03_osm_before_after_pilot/pilot_records.json`
  - `ops/aoi03_osm_before_after_pilot/pilot_summary.json`
  - `ops/aoi03_osm_before_after_pilot/pilot_summary.csv`
  - `ops/aoi03_osm_before_after_pilot/chips/`
  - `ops/aoi03_internal_review_queue/review_queue.csv`
  - `ops/aoi03_internal_review_queue/review_queue.geojson`
  - `ops/aoi03_internal_review_queue/review_queue.kml`
  - `ops/aoi03_internal_review_queue/review_report.md`
  - `ops/aoi03_internal_review_queue/review_packet.html`
  - `ops/aoi03_internal_review_queue/README.md`
  - `qa/aoi03-internal-review-queue-19-contact-sheet.png`
- Guardrail:
  - AOI03 VLM results are OSM-candidate triage evidence, not official EMS damage. They must stay out of `public/data/catalog.json` until explicitly promoted with source/confidence labels.
- QA evidence:
  - Internal queue GeoJSON contains 19 features.
  - Contact sheet generated at `qa/aoi03-internal-review-queue-19-contact-sheet.png` with class, confidence, priority, and coordinates visible per candidate.
  - `review_packet.html` references 19 comparison images, 0 missing.
  - `review_report.md` includes internal-only, not-official, and not-proof-of-no-damage warnings.
- Next recommended action:
  - Have a human review the 19 AOI03 contact-sheet candidates first, then either run another bounded AOI03 batch or prioritize AOI06/AOI08 only after credible pre-event imagery is identified.

### 2026-06-27 - AOI03 Internal VLM Second-Pass Adjudication

- Objective: reduce overclaim risk in the AOI03 internal OSM-candidate queue by running a stricter second-pass VLM adjudication on the 19 before/after comparison chips.
- Commands run:
  - `python3 -m py_compile scripts/adjudicate_aoi03_internal_review_queue.py`
  - `VLM_WORKERS=2 python3 scripts/adjudicate_aoi03_internal_review_queue.py --limit 2 --workers 2`
  - `VLM_WORKERS=5 python3 scripts/adjudicate_aoi03_internal_review_queue.py --workers 5`
- Result:
  - 19 candidates adjudicated.
  - Adjudicated classes:
    - `likely_destroyed`: 4
    - `possible_major_damage`: 2
    - `uncertain_comparison_problem`: 13
  - Recommended actions:
    - `urgent_human_review`: 5
    - `human_review`: 1
    - `hold_for_better_imagery`: 13
- Files changed:
  - `scripts/adjudicate_aoi03_internal_review_queue.py`
  - `ops/aoi03_internal_review_queue/adjudication/aoi03_internal_adjudication.json`
  - `ops/aoi03_internal_review_queue/adjudication/aoi03_internal_adjudication.csv`
  - `ops/aoi03_internal_review_queue/adjudication/summary.json`
  - `ops/aoi03_internal_review_queue/adjudication/adjudication_report.md`
  - `ops/aoi03_internal_review_queue/adjudication/adjudication_packet.html`
  - `qa/aoi03-internal-adjudication-19-contact-sheet.png`
- Guardrail:
  - This second-pass output is internal only. It makes the system more conservative: most AOI03 OSM candidates should be held for better imagery instead of being shown as operational damage.
- QA evidence:
  - Adjudication JSON count is 19.
  - `adjudication_packet.html` references 19 comparison images, 0 missing.
  - `adjudication_report.md` includes internal-only and not-official warnings.
- Next recommended action:
  - Only the 5 `urgent_human_review` AOI03 candidates should be manually checked first. Do not expand or publish AOI03 candidates until a human review or better post-event imagery is available.

### 2026-06-27 - Separate Before/After VLM From Post-Event-Only VLM

- Objective: prevent the app/catalog from implying before/after comparison where only post-event VLM exists.
- Files changed:
  - `scripts/sync_vlm_review_metrics.py`
  - `scripts/update_catalog_vlm_metrics.py`
  - `public/data/catalog.json`
  - `public/data/aoi/*/vlm_summary.json`
  - `public/data/aoi/*/vlm_review_summary.csv`
  - `src/components/OperationsConsole.tsx`
- Result:
  - Before/after VLM metrics remain under `vlmBeforeAfter*`.
  - Post-event-only VLM metrics are now under `vlmPostEvent*`.
  - AOI06 and AOI08 no longer expose generic `vlmReviewed` as if they had before/after review.
  - The KPI label now says `VLM before/after` when temporal comparison exists and `VLM post-event`/`VLM post-evento` when only lower-confidence post-event review exists.
- Current metric split:
  - AOI02: 17 before/after reviewed; 17 post-event-only records also available.
  - AOI06: 0 before/after reviewed; 129 post-event-only records.
  - AOI08: 0 before/after reviewed; 43 post-event-only records.
  - AOI12: 107 before/after reviewed; 120 post-event-only records.
- Guardrail:
  - AOI06/AOI08 still need credible high-resolution pre-event imagery before they can be used for building-level before/after VLM. Sentinel-2 context imagery remains too coarse for this.
- Next recommended action:
  - Keep searching for high-resolution pre-event AOI06/AOI08 baselines or human-review the 5 urgent AOI03 adjudicated candidates; do not run post-event-only VLM as before/after evidence.

### 2026-06-27 - Pre-Event Baseline Suitability Rerun

- Objective: verify whether AOI06, AOI08, or AOI10 can honestly support building-level before/after VLM before running more model calls.
- Commands run:
  - `python3 -m py_compile scripts/inventory_pre_event_baselines.py`
  - `python3 scripts/inventory_pre_event_baselines.py`
- Result:
  - AOI03: 4 Vantor Open Data building-level candidates, usable only for internal OSM-candidate pilot work.
  - AOI06: 0 building-level candidates; 3 Sentinel-2 context-only candidates covering 129 features at 10 m GSD.
  - AOI08: 0 building-level candidates; 3 Sentinel-2 context-only candidates covering 43 features at 10 m GSD.
  - AOI10: 0 building-level candidates; 8 Sentinel-2 context-only candidates and no official damage vector.
- Files changed:
  - `scripts/inventory_pre_event_baselines.py`
  - `ops/baseline_inventory/pre_event_baseline_inventory.json`
  - `ops/baseline_inventory/pre_event_baseline_suitability_report.md`
- Guardrail:
  - Do not run or publish AOI06/AOI08/AOI10 before/after building VLM until a high-resolution pre-event baseline is found. Sentinel-2 is context-only for this use.
- Next recommended action:
  - Human-review the 5 AOI03 urgent candidates or continue external source search specifically for high-resolution AOI06/AOI08/AOI10 pre-event imagery.

### 2026-06-27 - AOI03 Urgent Human Review Shortlist

- Objective: turn the second-pass AOI03 VLM adjudication into the smallest actionable internal review artifact.
- Files changed:
  - `ops/aoi03_internal_review_queue/adjudication/urgent_human_review_shortlist.md`
  - `ops/aoi03_internal_review_queue/README.md`
- Result:
  - Shortlist contains 5 `urgent_human_review` OSM-candidate leads.
  - Each row includes candidate id, name, adjudicated class, confidence, Google Maps link, and before/after chip link.
- QA evidence:
  - 5 Google Maps links present.
  - 5 chip links present, 0 missing.
  - Internal-only / not official EMS warning present.
- Next recommended action:
  - A human operator should inspect these 5 chips and locations before any field escalation or public presentation.

### 2026-06-27 - AOI03 Human Validation Templates

- Objective: make the 5 urgent AOI03 VLM leads reviewable by humans without publishing them as official damage.
- Files changed:
  - `ops/aoi03_internal_review_queue/adjudication/human_validation/README.md`
  - `ops/aoi03_internal_review_queue/adjudication/human_validation/human_validation_template.csv`
  - `ops/aoi03_internal_review_queue/adjudication/human_validation/human_validation_template.jsonl`
  - `ops/aoi03_internal_review_queue/README.md`
- Result:
  - 5 validation rows generated, one for each `urgent_human_review` candidate.
  - Each row includes candidate id, AOI, name, centroid, Google Maps URL, before/after chip, VLM adjudication, uncertainty, and blank human review fields.
  - Allowed human statuses documented: `confirmed_damage`, `false_positive`, `needs_better_imagery`, `needs_field_check`, `duplicate_or_bad_footprint`.
- QA evidence:
  - CSV rows: 5.
  - JSONL rows: 5.
  - Google Maps links: 5.
  - Missing chip links: 0.
  - Human review fields intentionally blank.
- Next recommended action:
  - Have a reviewer fill the CSV/JSONL. Only rows with `human_status=confirmed_damage` and an evidence URI should be considered for any public/internal escalation beyond triage.

### 2026-06-28 - Public VLM Publication Guardrail Validation

- Objective: add a local verification gate that prevents public VLM outputs from overstating before/after evidence.
- Files changed:
  - Added `scripts/validate_vlm_publication_guardrails.py`.
- Commands run:
  - `python3 -m py_compile scripts/validate_vlm_publication_guardrails.py`
  - `python3 scripts/validate_vlm_publication_guardrails.py`
  - `python3 scripts/sync_vlm_review_metrics.py`
  - `python3 scripts/validate_vlm_publication_guardrails.py`
- Result:
  - Validation passes on the regenerated current catalog/output state.
  - Verified public before/after VLM reviewed count: 124.
  - Verified before/after skipped-no-before count: 13.
  - Verified post-event-only VLM reviewed count: 309.
  - Verified AOI03 public damage feature count remains 0.
- Guardrail:
  - The script fails if before/after VLM records are missing `before_event_chip`, `post_event_chip`, `compare_chip`, `dated_pre_event_comparison`, or `before_source`.
  - The script fails if post-event-only VLM records contain before/compare chip fields or regain nonzero legacy `vlmReviewed` without before/after coverage.
  - The script fails if AOI03 exposes public VLM downloads or nonzero public official damage metrics.
- Confidence caveat:
  - This validates publication integrity and local file references; it does not create new credible AOI06/AOI08/AOI10 before/after coverage because those AOIs still lack high-resolution pre-event baselines.
- Next recommended action:
  - Run `python3 scripts/validate_vlm_publication_guardrails.py` after any VLM metric sync, catalog edit, or before/after batch. Actual Priority 1 expansion still depends on human validation of the 5 urgent AOI03 candidates or a new high-resolution pre-event source for AOI06/AOI08/AOI10.

## Known Gaps

1. Imagery is still active-area based. The map loads all vector features, but not all AOI imagery at once.
2. Vercel deployment package is too large because chips/tiles are still bundled.
3. Source-weighted area ranking is implemented locally; deployed Vercel order still needs validation after publish.
4. Public VLM before/after exists for AOI12 and AOI02 only. AOI03 has an internal OSM-candidate VLM pilot with 95 reviewed comparisons and 19 review candidates, but it is not public operational data.
5. Mobile end-to-end QA is incomplete.
6. Operator docs have been refreshed for area navigation, AOI12 Vantor before reference, VLM review limits, and external prediction caveats; deployed app wording still needs normal post-deploy spot checks.
7. Human validation workflow is not implemented.
8. External bookmarked/social sources still need systematic review and ingestion only if trustworthy.

## Blockers

- More before imagery coverage is needed before running credible before/after VLM for AOI06, AOI08, and AOI10. AOI02 has coverage but poor comparison quality in many chips.
- AOI03 has before/after candidate chips, but current after imagery quality and non-official OSM candidates make it unsuitable for public damage claims.
- Moving assets to R2/CDN requires confirming public object URLs and updating catalog paths safely.
- Any social media/bookmark evidence requires source verification before it can be shown as operational data.

## Active Goal

Improve the crisis damage intelligence app, prioritizing more before/after VLM analysis. The markdown files are memory and guardrails for the loop; they are not the goal.

### 2026-06-28 - Optional OpenPanel Analytics Provider

- Objective: add OpenPanel analytics without making public app viewing depend on analytics infrastructure.
- Files changed:
  - `package.json`
  - `package-lock.json`
  - `src/app/layout.tsx`
  - `src/components/OpenPanelAnalytics.tsx`
  - `src/lib/analytics.ts`
  - `docs/ANALYTICS.md`
- Result:
  - Added `@openpanel/nextjs`.
  - Added an OpenPanel initializer that only renders when `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=openpanel` and `NEXT_PUBLIC_OPENPANEL_CLIENT_ID` are both configured.
  - Existing sanitized `trackAnalytics` wrapper now forwards custom interaction events to OpenPanel when enabled.
  - Session replay, automatic outgoing-link tracking, profile ids, and user identification remain disabled.
- Commands run:
  - `npm install @openpanel/nextjs`
  - `npm run lint`
  - `npm run build`
  - `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=openpanel NEXT_PUBLIC_OPENPANEL_CLIENT_ID=test_client npm run build`
  - `npm run build`
- QA performed:
  - Lint passed.
  - Default production build passed.
  - OpenPanel-enabled production build passed with a dummy public client id.
  - Rebuilt again without analytics env vars so local artifact remains in default no-OpenPanel mode.
- Blockers:
  - Production capture still requires adding a real OpenPanel client id in Vercel and validating events in the OpenPanel dashboard.
- Next recommended action:
  - Configure Vercel env vars for OpenPanel, deploy, then verify screen views and sanitized interaction events before using analytics for decisions.

### 2026-06-28 - Source-Aware Operational Ranking

- Objective: ensure affected-area and priority-item ordering reflects response value and source confidence, not raw feature count alone.
- Files changed:
  - `src/components/OperationsConsole.tsx`
  - `docs/OPERATIONAL_PROGRESS.md`
- Commands run:
  - `npm run lint`
  - `npm run build`
  - `portless priority-ranking npm start`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh open https://priority-ranking.localhost`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh open http://localhost:4262`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh snapshot`
- QA performed:
  - Production build passed.
  - Browser snapshot verified the Spanish area order is now La Guaira, Moron, San Felipe, Caracas, Antimano, Guacara.
  - Browser snapshot verified area labels now separate official destroyed/damaged, official possible, MONIT01, VLM before/after, and external triage-only candidates.
  - Browser snapshot verified priority rows show official EMS class separately from VLM class, e.g. `EMS oficial: destroyed · VLM: likely_destroyed`.
- Ranking evidence:
  - Previous raw-count score put La Guaira first mostly because `9134` external Catia La Mar candidates were added to `120` official features.
  - Source-aware score now weights official confirmed damage first, official possible next, then MONIT01, VLM before/after critical signals, and a capped external-prediction contribution.
  - New score order: La Guaira `103640`, Moron `63730`, San Felipe `31470`, Caracas `5010`, Antimano `1`, Guacara `1`.
- Blockers:
  - `priority-ranking.localhost` did not register in `portless list` during final dev-server QA because another Next dev server was already running for this repo. Final browser check used the existing local server on `http://localhost:4262`.
  - Local browser QA still logs expected local-only 404s for Vercel analytics and some missing AOI12 tile URLs at the tested zoom; ranking UI rendered correctly despite those asset misses.
- Next recommended action:
  - Validate the same source-aware order on the deployed Vercel app after the current working tree is merged/deployed.

### 2026-06-28 - Remote Asset Validation Preflight

- Objective: make remote chip/tile readiness measurable before deploying the pruned Vercel package.
- Files changed:
  - `scripts/validate_remote_asset_urls.py`
  - `docs/DEPLOYMENT_CHECKLIST.md`
  - `ops/remote_asset_validation/latest.json`
  - `ops/remote_asset_validation/latest.md`
  - `docs/OPERATIONAL_PROGRESS.md`
- Commands run:
  - `du -sh . public public/data public/data/chips public/data/tiles`
  - `find public/data -type f -size +1M -print0 | xargs -0 du -h | sort -hr`
  - `python3 -m py_compile scripts/validate_remote_asset_urls.py`
  - `python3 scripts/validate_remote_asset_urls.py --sample-per-template 12 --sample-chips 32 --allow-failures`
- Result:
  - Disk usage snapshot: repo `1.7G`, `public/data` `445M`, chips `69M`, tiles `326M`.
  - Logical package-pressure report: `public/data` 64,504 files / 241.4 MB; chips 681 files / 67.3 MB; tiles 63,745 files / 124.2 MB.
  - Top bundled non-tile/chip offenders are Catia La Mar KML/GeoJSON/CSV and EMS PDF reports.
  - Static `/data/aoi` references checked: 66; missing local static references: 0. Public read-only viewing still has a Supabase-free static data path.
  - Remote checks sampled: 92; passed: 49; failed: 43.
  - All sampled evidence chip URLs passed; all failures were tile URLs returning HTTP 404.
  - Missing tile samples cover AOI02 after, AOI06 after, AOI08 after, and AOI12 z17-z18 before/after.
- Evidence:
  - `ops/remote_asset_validation/latest.md`
  - `ops/remote_asset_validation/latest.json`
- Blocker:
  - Do not deploy the remote-asset Vercel package yet. Required tile paths still need bulk R2/S3 sync or a reduced catalog that only points at verified remote tile zooms.
- Next recommended action:
  - Upload `public/data/tiles` to R2 with an S3-compatible sync preserving `data/tiles/...`, then rerun `python3 scripts/validate_remote_asset_urls.py` without `--allow-failures`.

### 2026-06-28 - Imagery Coverage Labels And Tile Extent Guard

- Objective: improve Priority 2 imagery loading/coverage clarity without adding heavy assets or redesigning the public app.
- Files changed:
  - `src/components/OperationsConsole.tsx`
  - `src/components/map/MapPanel.tsx`
  - `src/components/types.ts`
  - `src/app/globals.css`
  - `docs/OPERATIONAL_PROGRESS.md`
- Commands run:
  - `npm run lint`
  - `npm run build`
  - `portless imagery-coverage npm start`
  - `portless imagery-coverage-dev npm run dev`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh open https://field-usability.localhost`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh snapshot`
- Functional changes:
  - Replaced the post-event-only right-rail imagery panel with an imagery coverage panel showing after imagery, before imagery, map-layer availability, evidence-chip-only availability, and catalog caveats.
  - AOI12 now explicitly labels after imagery as Copernicus EMS post-event imagery and before imagery as Vantor/OpenData reference, not official EMS imagery, with partial-coverage/gap warning.
  - AOI02 now distinguishes the Vantor before reference used in evidence chips from a non-published before map layer.
  - Imagery-only AOIs still show 0 official damage and now show before imagery as unavailable.
  - Generated XYZ raster layers are constrained to active AOI bounds so map fits do not request WebP tiles outside the known generated pyramid.
- Current coverage by AOI:
  - AOI12 La Guaira / Caraballeda: after map layer available; Vantor/OpenData before map layer available; before coverage is partial with gaps; before/after VLM reviewed 107 and skipped no-before 13.
  - AOI02 Caracas: after map layer available; Vantor before reference exists for evidence chips only; no before map layer is published; before/after VLM reviewed 17 with high uncertainty.
  - AOI06 Moron: after map layer available; no high-resolution before imagery; post-event-only VLM only.
  - AOI08 San Felipe: after map layer available; no high-resolution before imagery; post-event-only VLM only.
  - AOI03 Antimano: post-event imagery available; no official damage vector; public app remains imagery-only.
  - AOI10 Guacara: post-event imagery available; no official damage vector; public app remains imagery-only.
  - MONIT01 layers and Catia La Mar external prediction: no bundled imagery; use parent AOI imagery or aerial basemap reference only.
- QA performed:
  - Build and lint passed.
  - Browser snapshot verified AOI12 coverage panel labels before imagery as `Referencia Vantor/OpenData - no es imagen oficial EMS`.
  - Browser snapshot verified AOI02 coverage panel labels before imagery as evidence-chip-only and says no before map layer is published.
  - Browser snapshot verified AOI03 imagery-only panel shows 0 official damage and before imagery unavailable.
  - Fresh AOI12 load and AOI12 before-toggle console had no generated-tile 404s after the raster layer extent guard.
- Evidence:
  - `.playwright-cli/page-2026-06-28T09-45-14-901Z.yml`
  - `.playwright-cli/page-2026-06-28T09-45-24-714Z.yml`
  - `.playwright-cli/console-2026-06-28T09-45-14-382Z.log`
  - `output/playwright/imagery-coverage-aoi12-before.png`
- Notes:
  - `next start` on a temporary Portless run returned a 404 for one generated Next chunk despite the file existing under `.next/static/chunks`; `npm run build` itself succeeded.
  - Starting a second Portless dev server with `imagery-coverage-dev` was blocked because an existing Next dev server for this repo was already running on port 4262. Final browser QA used the existing Portless mapping `https://field-usability.localhost`.
- Next recommended action:
  - Upload full z17-z18 tile pyramids to R2/CDN with S3-compatible sync, then validate representative AOI12/AOI02/AOI06/AOI08 tile URLs before deploying a pruned Vercel package.

### 2026-06-28 04:47 Local - Mobile Field Workflow Panel

- Objective: verify Priority 5 first-five-minutes usability and patch a high-impact mobile workflow blocker without aesthetic redesign.
- Files changed:
  - `src/components/OperationsConsole.tsx`
  - `src/app/globals.css`
  - `docs/OPERATIONAL_PROGRESS.md`
  - `qa/local-mobile-field-workflow.png`
- Commands run:
  - `npm run lint`
  - `npm run build`
  - `portless field-usability npm start` (failed because `next start` did not find a usable production build in `.next`)
  - `portless field-usability npm run dev`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh --session fieldqa open https://field-usability.localhost`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh --session fieldqa resize 390 844`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh --session fieldqa snapshot`
  - `bash ~/.codex/skills/playwright/scripts/playwright_cli.sh --session fieldqa click e72`
  - Playwright eval checks for selected id, map center, zoom, imagery mode, raster, Google Maps link, opacity, and popup clear.
- Functional change:
  - The right workflow rail is no longer hidden below 1120px. On tablet/mobile it becomes a scrollable bottom panel.
  - Priority is now directly after evidence in the rail, so mobile users can choose area, inspect a priority item, see evidence, open Google Maps, and return to the priority list.
  - Secondary right-rail panels are hidden only in the tablet/mobile bottom panel to keep the field workflow short; desktop keeps the full right rail.
- QA performed:
  - Mobile viewport `390x844`: priority list is visible in the bottom workflow panel.
  - Mobile priority tap on `ems_00050`: map selected `emsr884-aoi12-caraballeda__ems_00050`, centered at `10.6096660,-67.0144104`, zoom `18`, and evidence panel showed `dated_pre_event_comparison`, chip link, Google Maps link, and return-to-priority action.
  - Mobile opacity `0.52 -> 0.42`: selected id, center, and zoom stayed unchanged.
  - Mobile before/after toggle: `mode=before` showed `raster=before`, then returned to after.
  - Mobile outside click after AOI reset: popup text and focused id cleared.
  - Desktop viewport `1280x800`: right rail remains static in the normal three-column layout (`304px 648px 328px`) with evidence and priority visible.
- Evidence:
  - `qa/local-mobile-field-workflow.png`
  - `.playwright-cli/page-2026-06-28T09-43-30-859Z.yml`
  - `.playwright-cli/page-2026-06-28T09-45-07-236Z.yml`
- Result:
  - Priority 5 mobile workflow blocker fixed and verified locally through Portless dev URL `https://field-usability.localhost`.
- Blockers:
  - Durable desktop PNG capture through the wrapper was unavailable in this run; desktop verification is recorded through snapshot/eval output.
- Next recommended action:
  - Re-run this mobile script against the deployed public URL after the current working-tree changes are reviewed and deployed.

### 2026-06-28 - Documentation And Runbook Refresh

- Objective: make responder/operator docs match the current deployed and operational system without inventing capabilities.
- Files changed:
  - `README.md`
  - `docs/AOI12_ACTIVATION_RUNBOOK.md`
  - `docs/OPERATOR_HANDOFF_EN.md`
  - `docs/OPERATOR_HANDOFF_ES.md`
  - `docs/DEPLOYMENT_CHECKLIST.md`
  - `docs/ANALYTICS.md`
  - `docs/LOW_COST_INFRASTRUCTURE.md`
  - `docs/OPERATIONAL_PROGRESS.md`
- Commands run:
  - `sed -n '1,240p' docs/OPERATIONAL_LOOP_GOALS.md`
  - `sed -n '1,260p' docs/OPERATIONAL_PROGRESS.md`
  - `jq '{catalogVersion,generatedAt,areas:(.aois[] | {id,name,status,metrics,layers})}' public/data/catalog.json`
  - Targeted `rg` scan for stale AOI12-pending, old navigation, and AOI02/AOI06-only deployment wording in README and docs.
- Result:
  - README now states AOI12 v1 is already deployed and describes affected-area navigation, current public AOI/layer inventory, VLM review-type separation, and external prediction caveats.
  - AOI12 runbook now works as a rerun/repair/update runbook and records current AOI12 counts, EMS post-event imagery, Vantor/OpenData before reference, 107 before/after VLM reviews, and 13 skipped no-before records.
  - English and Spanish handoff docs now match on current area navigation, Vantor before-reference limits, VLM before/after vs post-event-only limits, AOI03 internal-only status, and do-not-overclaim warnings.
  - Deployment and analytics docs now test/report affected-area navigation and warn that analytics, VLM, MONIT01, and external predictions do not validate damage.
- QA performed:
  - Re-scanned targeted docs for stale AOI12-pending and old AOI-selector wording.
  - Compared docs against `public/data/catalog.json` metrics/layers rather than adding unverified capabilities.
  - No app build was run because this was a markdown-only patch.
- Next recommended action:
  - After deployment, run a short public spot check that the UI labels match the refreshed docs, especially AOI12 imagery labels and VLM review-type labels.

### 2026-06-28 04:55 Local - AOI03 Human Validation Compiler

- Objective: support cheap, auditable AOI03 human review without requiring live DB access or publishing unconfirmed OSM-candidate claims.
- Files changed:
  - `scripts/compile_aoi03_human_validation.py`
  - `ops/aoi03_internal_review_queue/adjudication/human_validation/README.md`
  - `ops/aoi03_internal_review_queue/README.md`
  - `ops/aoi03_internal_review_queue/adjudication/human_validation/compiled/human_validation_summary.json`
  - `ops/aoi03_internal_review_queue/adjudication/human_validation/compiled/human_validation_compiled.csv`
  - `ops/aoi03_internal_review_queue/adjudication/human_validation/compiled/human_validation_promoted.geojson`
  - `ops/aoi03_internal_review_queue/adjudication/human_validation/compiled/human_validation_promoted.kml`
- Commands run:
  - `python3 -m py_compile scripts/compile_aoi03_human_validation.py`
  - `python3 scripts/compile_aoi03_human_validation.py --input ops/aoi03_internal_review_queue/adjudication/human_validation/human_validation_template.csv`
  - Temp CSV header-only empty-template test
  - Temp JSONL negative test: `confirmed_damage` with blank `evidence_uri`
  - Temp JSONL positive test: `confirmed_damage` with reviewer, UTC timestamp, evidence URI, and source
  - `python3 scripts/validate_vlm_publication_guardrails.py`
- Result:
  - Current blank AOI03 template compiles successfully with 5 input rows, 0 reviewed rows, and 0 promoted rows.
  - Header-only empty CSV compiles successfully with 0 input rows, 0 reviewed rows, 0 promoted rows, and a stable compiled CSV header.
  - Static outputs are written under `ops/aoi03_internal_review_queue/adjudication/human_validation/compiled/`.
  - Positive JSONL test compiled 1 reviewed row into 1 promoted GeoJSON feature and preserved `audit_source=operator_photo`.
- Guardrail:
  - The compiler promotes only `human_status=confirmed_damage` rows with `reviewer_id`, `reviewed_at_utc`, and `evidence_uri`.
  - A `confirmed_damage` row without `evidence_uri` fails validation and emits no promoted output.
  - Unreviewed template rows are retained in the compiled CSV as `not_promoted` with `promotion_blockers=unreviewed`.
  - AOI03 public guardrail still passes: before/after reviewed 124, skipped no-before 13, post-event-only reviewed 309, and AOI03 public features remain 0.
- Next recommended action:
  - Have reviewers fill a copy of the AOI03 human-validation CSV/JSONL, run the compiler, and only consider `human_validation_promoted.geojson` for any static internal display or future public status indicator.

### 2026-06-28 05:20 Local - External Source Registry And Review Queue

- Objective: advance Priority 7 by recording recent useful external evidence without publishing unreviewed model predictions as operational damage.
- Files changed:
  - `public/data/sources/earthquake_source_review.json`
  - `ops/external_source_review/README.md`
  - `ops/external_source_review/review_queue.csv`
  - `scripts/validate_external_source_registry.py`
  - `docs/OPERATIONAL_PROGRESS.md`
- Commands run:
  - `curl -L --fail --silent 'https://data.humdata.org/api/3/action/package_show?id=venezuela-earthquakes-catia-la-mar'`
  - `curl -L --fail --silent 'https://data.humdata.org/api/3/action/package_show?id=hot_eq_ven'`
  - `curl -L --fail --silent 'https://data.humdata.org/api/3/action/package_search?q=%22Venezuela%20Earthquakes%3A%20Building%20Damage%20Assessment%22&rows=10'`
  - `curl -L --fail --silent 'https://mapping.emergency.copernicus.eu/activations/EMSR884/'`
  - `python3 -m json.tool public/data/sources/earthquake_source_review.json`
  - `python3 scripts/validate_external_source_registry.py`
  - `python3 scripts/validate_vlm_publication_guardrails.py`
- Source checks:
  - Confirmed the existing Microsoft AI for Good Lab / HDX Catia La Mar prediction layer is CC BY, external/non-official, and has an HDX caveat about orthorectification quality issues.
  - Confirmed three additional Microsoft AI for Good Lab / HDX prediction datasets exist for Caraballeda, Catia La Mar East, and La Guaira; all are recorded as queued review candidates only.
  - Confirmed HOT/HDX earthquake OSM/Overture context data licensing from HDX metadata: ODbL for OSM layers and CDLA Permissive 2.0 for Overture emergency facilities.
  - Recorded Copernicus EMSR884 as the official high-confidence reference source, with MONIT01 caveats preserved.
- QA performed:
  - External source registry validator passed for 6 source records.
  - Existing VLM publication guardrails still passed: `before_after_reviewed=124`, `before_after_skipped_no_before=13`, `post_event_only_reviewed=309`, `emsr884-aoi03-antimano_public_features=0`.
- Deployment:
  - Not deployed.
  - No new public AOI or layer was added to `public/data/catalog.json`.
- Result:
  - Priority 7 now has a source registry with URL, date accessed, data owner, license/terms, geography, confidence, and official status.
  - New external model-prediction datasets are queued for review instead of published.
- Blockers:
  - The queued Microsoft/HDX prediction layers still need overlap checks against EMS AOIs, threshold review, visual sample QA, and explicit UI distinction before any public layer can be considered.
- Next recommended action:
  - If Priority 7 continues, download queued HDX GPKGs into `ops/` only, produce feature counts by model threshold and AOI overlap, then decide whether a small internal review queue is useful. Do not add them to the public catalog until source confidence and caveats are reviewed.

## Next Recommended Loop

Run the next before/after VLM expansion loop:

1. Validate AOI02 on Vercel after deployment.
2. Search for better before imagery or alternative baselines for AOI06, AOI08, and AOI10 outside the current Vantor STAC collection.
3. For AOI03 Antimano, review the 19 internal VLM candidates before expanding further; do not publish them as official damage.
4. Add UI copy/metrics that surface AOI02's high uncertainty rate so users do not overread the VLM layer.

Do not run post-event-only VLM as if it were before/after comparison.

## Loop Entry Template

### YYYY-MM-DD HH:MM Local - Short Title

- Objective:
- Files changed:
- Commands run:
- QA performed:
- Screenshots/evidence:
- Deployment:
- Result:
- Blockers:
- Next recommended action:

### 2026-06-28 - R2 Tile Repair, Baseline Refresh, Toolbar Compression

- Objective:
  - Work down the four remaining operational gaps after the 8-priority agent loop: remote R2 tile 404s, missing before baselines for AOI06/AOI08/AOI10, AOI03 internal validation, and toolbar field usability.
- Files changed:
  - `scripts/upload_missing_remote_assets_from_report.py`
  - `src/components/OperationsConsole.tsx`
  - `src/app/globals.css`
  - `ops/remote_asset_validation/latest.json`
  - `ops/remote_asset_validation/latest.md`
  - `ops/baseline_inventory/pre_event_baseline_inventory.json`
  - `ops/baseline_inventory/pre_event_baseline_inventory.csv`
  - `ops/baseline_inventory/pre_event_baseline_suitability_report.md`
- Commands run:
  - `python3 -m py_compile scripts/upload_missing_remote_assets_from_report.py`
  - `python3 scripts/upload_missing_remote_assets_from_report.py`
  - `python3 scripts/validate_remote_asset_urls.py --sample-per-template 8 --sample-chips 16`
  - `python3 scripts/validate_remote_asset_urls.py --sample-per-template 20 --sample-chips 40`
  - `python3 scripts/inventory_pre_event_baselines.py`
  - `npm run lint`
  - `npm run build`
  - `python3 scripts/validate_vlm_publication_guardrails.py`
  - `python3 scripts/validate_external_source_registry.py`
  - `python3 scripts/compile_aoi03_human_validation.py`
- QA performed:
  - Uploaded 71 locally present tile objects that had returned public R2 404s in sampled validation reports.
  - Standard remote validation now passes: 56 checked, 0 failed.
  - Expanded remote validation now passes: 140 checked, 0 failed.
  - Baseline refresh still finds 0 building-level pre-event candidates for AOI06, AOI08, and AOI10.
  - AOI03 human validation compiler still reports 5 rows, 0 reviewed, 0 promoted.
  - Browser QA on `https://toolbar-qa.localhost` confirmed the compact toolbar renders with La Guaira active, priority list present, and a `Notas` disclosure; toolbar measured about 620x99 px on desktop.
- Result:
  - The known sampled R2 tile 404s are repaired, and the remote-asset validation report is green for a larger sample.
  - The app toolbar blocks less map area by moving long caveats into a compact notes disclosure while keeping base, before/after, opacity, and filter controls visible.
  - No new before/after VLM was run for AOI06/AOI08/AOI10 because the refreshed baseline inventory still does not support building-level comparison.
- Blockers:
  - R2 is much healthier, but this was still a sampled repair, not a complete 63k-object manifest audit.
  - AOI06/AOI08/AOI10 remain blocked for credible before/after VLM until a high-resolution pre-event baseline is found.
  - AOI03 cannot leave internal status until reviewers fill the validation template with evidence-backed decisions.
- Next recommended action:
  - Run or build a manifest-level R2 audit for every local tile key before deploying a fully pruned remote-asset package.
  - Have a human reviewer validate the 5 AOI03 urgent candidates, then rerun `python3 scripts/compile_aoi03_human_validation.py`.
  - Continue searching for licensed high-resolution pre-event baselines for AOI06/AOI08/AOI10; do not substitute Sentinel-2 or post-event-only VLM.
