# Respuesta Venezuela

Static-first, bilingual earthquake response and damage triage platform for public coordination in Venezuela.

Canonical public URL: `https://respuestavenezuela.org`

The Vercel project URL `https://crisis-damage-intelligence.vercel.app` remains attached to the project and is configured to redirect users to the canonical domain.

## What This Is

An operations-grade public map that can run close to zero cost:

- Next.js static frontend on Vercel free tier.
- Leaflet/OpenStreetMap-compatible map UI.
- AOI data loaded from static `public/data/**` exports.
- Affected-area navigation that groups operational layers by response area.
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
HF Spaces VLM provider setup lives in `docs/HF_SPACES_VLM.md`.

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

Current public operational data includes official EMS vectors for AOI02 Caracas, AOI06 Moron, AOI08 San Felipe, and AOI12 Caraballeda / La Guaira; MONIT01 point layers for AOI02/AOI06/AOI08; imagery-only navigation areas for AOI03 Antimano and AOI10 Guacara; and an external Microsoft AI4G Catia La Mar prediction layer. The external prediction layer is a triage-only candidate source, not official EMS damage confirmation.

For imagery-heavy La Guaira operations, prefer remote object storage URLs:

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

AOI12 v1 is already deployed. Use this flow for future EMS updates, reruns, or new AOIs:

1. Run `monitor_emsr884.py` for new or updated EMSR884 products.
2. Download the relevant product ZIP.
3. Run Copernicus EMS importer to produce CSV/GeoJSON/KML.
4. Upload exports to object storage/CDN.
5. Update `catalog.json`.
6. Run VLM only on high-value candidates first.
7. Publish VLM JSONL as a separate evidence layer with clear review type labels.

Do not mark an item as before/after VLM-reviewed unless both pre-event and post-event imagery were actually used. Treat pre-event reference imagery in three explicit classes:

- `Vantor usable for VLM`: dated pre-event reference may support building-level before/after VLM, subject to coverage and quality gaps.
- `Esri visual reference only`: operator-facing visual context only. Do not use it as cached evidence or as a VLM before source.
- `No before`: no suitable pre-event image is available; any VLM review must stay labeled post-event-only or candidate-only.

AOI12 has EMS post-event imagery and Vantor/OpenData pre-event reference with partial gaps. AOI02 has before/after evidence chips but high uncertainty. AOI06 and AOI08 currently have post-event-only VLM, not before/after VLM.

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

Historical acceptance behavior from this AOI02/AOI06 test:

- AOI02 and AOI06 loaded from real EMSR884 GRA vector products.
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

These explain affected-area navigation, severity filters, priority click behavior, exports, data confidence, deployed AOI12 operations, and the next safe actions for VLM expansion.

Live infrastructure:

- Vercel: `https://crisis-damage-intelligence.vercel.app`
- Canonical domain: `https://respuestavenezuela.org`
- GitHub: `https://github.com/takove/crisis-damage-intelligence`
- Public app remains static-first and does not require Supabase for viewing.

Operational warning:

- EMS `builtUpA` features may not be one building each.
- Official EMS labels are the source of record for this package.
- VLM/inferred labels are triage aids only.
- External predicted-damage layers are triage-only and must not be counted as official EMS damage.
- Google Maps links and Esri basemap imagery are external visual references only. They are not official evidence sources, are not cached by this project, and must not be cited as verification.
- Microsoft/HDX prediction layers are external model outputs for search and prioritization. Interpret them as candidate footprints or lead lists, not as confirmed damage, EMS labels, or response statistics.
- Absence of a marked feature is not proof of no damage.

## VLM Policy

VLM output is evidence, not authority.

- Official EMS labels are marked as confirmed source.
- Pixel heuristics are recall-oriented candidates.
- VLM is async second-pass prioritization.
- Before/after VLM means both dated pre-event and post-event imagery were reviewed. Post-event-only VLM has lower evidentiary value and must stay labeled separately.
- Esri/Google visual references must not be treated as cached VLM evidence. Vantor/OpenData before imagery is the current before source that can support VLM when coverage and quality are adequate.
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
- Batch VLM jobs through HF Spaces by default, never run every building by default.
