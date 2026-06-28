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

## Known Gaps

1. Imagery is still active-area based. The map loads all vector features, but not all AOI imagery at once.
2. Vercel deployment package is too large because chips/tiles are still bundled.
3. Area ranking currently includes external prediction counts in the visible order; this is labeled, but needs better source-weighted ranking.
4. Public VLM before/after exists for AOI12 and AOI02 only. AOI03 has an internal OSM-candidate VLM pilot, but it is not public operational data.
5. Mobile end-to-end QA is incomplete.
6. Operator docs may be stale after the recent area-navigation and VLM before/after changes.
7. Human validation workflow is not implemented.
8. External bookmarked/social sources still need systematic review and ingestion only if trustworthy.

## Blockers

- More before imagery coverage is needed before running credible before/after VLM for AOI06, AOI08, and AOI10. AOI02 has coverage but poor comparison quality in many chips.
- AOI03 has before/after candidate chips, but current after imagery quality and non-official OSM candidates make it unsuitable for public damage claims.
- Moving assets to R2/CDN requires confirming public object URLs and updating catalog paths safely.
- Any social media/bookmark evidence requires source verification before it can be shown as operational data.

## Active Goal

Improve the crisis damage intelligence app, prioritizing more before/after VLM analysis. The markdown files are memory and guardrails for the loop; they are not the goal.

## Next Recommended Loop

Run the next before/after VLM expansion loop:

1. Validate AOI02 on Vercel after deployment.
2. Search for better before imagery or alternative baselines for AOI06, AOI08, and AOI10 outside the current Vantor STAC collection.
3. For AOI03 Antimano, only run VLM if credible candidate features are available; imagery alone is not enough.
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
