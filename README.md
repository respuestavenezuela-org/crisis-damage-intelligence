# Crisis Damage Intelligence

Static-first, bilingual earthquake damage intelligence platform for public response coordination.

## What This Is

An operations-grade public map that can run close to zero cost:

- Next.js static frontend on Vercel free tier.
- Leaflet/OpenStreetMap-compatible map UI.
- AOI data loaded from static `public/data/**` exports.
- Before/after image overlays with a simple toggle.
- Building damage GeoJSON/CSV/KML downloads.
- VLM evidence loaded lazily from JSONL.
- Optional Supabase/PostGIS for product tracking and human review.
- Batch/local/GitHub Actions processing instead of always-on workers.

Default language is Spanish, with English available in the UI.

## Local Run

```bash
npm install
npm run dev
```

Portless preview in this workspace:

```bash
portless crisis-damage npm run dev
```

## Production Deploy

Deploy the app shell to Vercel:

```bash
vercel
vercel --prod
```

Keep large rasters, chips, COGs, and PMTiles out of the Vercel repo. Store them in R2, Supabase Storage, or another CDN/object store, then point `public/data/catalog.json` layer URLs to those public CDN URLs.

Analytics setup and the privacy-safe event taxonomy live in `docs/ANALYTICS.md`.

## Data Model

The public app only requires static files:

```text
public/data/catalog.json
public/data/aoi/<aoi-id>/damage.geojson
public/data/aoi/<aoi-id>/damage.csv
public/data/aoi/<aoi-id>/damage.kml
public/data/aoi/<aoi-id>/vlm.jsonl
public/data/aoi/<aoi-id>/before.png or remote COG/tile URL
public/data/aoi/<aoi-id>/after.png or remote COG/tile URL
```

For real La Guaira operations, prefer remote object storage URLs:

```json
{
  "layers": {
    "damage": "https://cdn.example.org/aoi12/damage.geojson",
    "beforeImage": "https://cdn.example.org/aoi12/before.png",
    "afterImage": "https://cdn.example.org/aoi12/after.png",
    "vlm": "https://cdn.example.org/aoi12/vlm.jsonl"
  }
}
```

## Processing Strategy

1. Run `monitor_emsr884.py` until AOI12 is available.
2. Download AOI12 product ZIP.
3. Run Copernicus EMS importer to produce CSV/GeoJSON/KML.
4. Upload exports to object storage/CDN.
5. Update `catalog.json`.
6. Run VLM only on high-value candidates first.
7. Publish VLM JSONL as a separate evidence layer.

## EMSR884 Acceptance Test

The canonical path is Copernicus EMS GRA ZIP -> auto-detected GPKG -> `builtUpA` damage layer -> static CSV/GeoJSON/KML/catalog entries. xBD is kept only as a separate VLM benchmark fixture.

Commands validated on 2026-06-26:

```bash
python3 outputs/damage_pipeline/build_copernicus_ems_package.py \
  outputs/AOI02_Caracas_GRA_v1.zip \
  outputs/ems_acceptance_aoi02_from_zip

python3 outputs/damage_pipeline/build_copernicus_ems_package.py \
  outputs/AOI06_Moron_GRA_v1.zip \
  outputs/ems_acceptance_aoi06_from_zip

npm run lint
npm run build
```

Results:

| AOI | Layer | Features | Destroyed | Damaged | Possibly damaged |
| --- | --- | ---: | ---: | ---: | ---: |
| AOI02 Caracas | `builtUpA_v1` | 17 | 0 | 0 | 17 |
| AOI06 Moron | `builtUpA_v1` | 129 | 2 | 34 | 93 |

The counts match the EMS copied summary tables:

- `outputs/ems_acceptance_aoi02_from_zip/reports/EMSR884_AOI02_GRA_PRODUCT_summaryTable_v1.xlsx`
- `outputs/ems_acceptance_aoi06_from_zip/reports/EMSR884_AOI06_GRA_PRODUCT_summaryTable_v1.xlsx`

Browser QA evidence is in:

```text
outputs/ems_acceptance_qa/EMSR884_ACCEPTANCE_REPORT.md
outputs/ems_acceptance_qa/01-aoi02-all-final.png
outputs/ems_acceptance_qa/02-aoi06-severe-final.png
outputs/ems_acceptance_qa/06-aoi06-priority-zoom18-popup.png
```

Verified app behavior:

- AOI switching works for AOI02 and AOI06.
- Severity filters use real EMS `damage_gra` values.
- AOI06 severe filter returns 36 features: `Destroyed` + `Damaged`.
- Priority rows center the selected feature at zoom 18.
- Popups expose Google Maps links.

## Operator Handoff

Short response-operations guides:

- `docs/OPERATIONAL_LOOP_GOALS.md`
- `docs/OPERATIONAL_PROGRESS.md`
- `docs/OPERATOR_HANDOFF_ES.md`
- `docs/OPERATOR_HANDOFF_EN.md`
- `docs/DEPLOYMENT_CHECKLIST.md`
- `docs/AOI12_ACTIVATION_RUNBOOK.md`
- `docs/LOW_COST_INFRASTRUCTURE.md`

These explain AOI switching, severity filters, priority click behavior, exports, data confidence, and the exact next action when AOI12/La Guaira becomes available.

Live infrastructure:

- Vercel: `https://crisis-damage-intelligence.vercel.app`
- GitHub: `https://github.com/takove/crisis-damage-intelligence`
- Public app remains static-first and does not require Supabase for viewing.

Operational warning:

- EMS `builtUpA` features may not be one building each.
- Official EMS labels are the source of record for this package.
- VLM/inferred labels are triage aids only.
- Absence of a marked feature is not proof of no damage.

## VLM Policy

VLM output is evidence, not authority.

- Official EMS labels are marked as confirmed source.
- Pixel heuristics are recall-oriented candidates.
- VLM is async second-pass prioritization.
- Human validation can be added later with Supabase tables.

## Optional Supabase

Use Supabase only for tracking, review status, and jobs. The public map should keep working from static exports if Supabase is unavailable.

Schema: `supabase/schema.sql`

## Cost Controls

- No always-on model server.
- No paid map SDK.
- No heavy raster files in Vercel.
- Static AOI exports split by AOI/severity.
- CDN cache public read-only files aggressively.
- Batch VLM jobs, never run every building by default.
