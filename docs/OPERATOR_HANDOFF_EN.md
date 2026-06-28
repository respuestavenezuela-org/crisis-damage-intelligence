# Operator Guide - First 5 Minutes

## Objective

Use the map to quickly locate official Copernicus EMSR884 damage polygons, prioritize inspection, and share coordinates/exports with response teams.

## How To Use

1. Open the app and confirm the active area is an operational Venezuela affected area, not the xBD demo.
2. Use affected-area navigation to switch between areas such as `La Guaira / Caraballeda / Catia La Mar`, `Moron`, `San Felipe`, `Caracas`, `Antimano`, and `Guacara`.
3. Read the indicators:
   - `features`: number of built-up polygons in the AOI.
   - `official destroyed/damaged`: `Destroyed` + `Damaged` from EMS.
   - `official possible`: `Possibly damaged` from EMS.
   - `MONIT01`: official EMS monitoring points when available.
   - `external candidates`: triage-only predictions when available.
4. Use filters:
   - `All`: every EMS polygon.
   - `Destroyed/Damaged`: only `Destroyed` + `Damaged`.
   - `VLM reviewed`: only items with VLM review, if present. Read the VLM review type before using it.
5. In `Priority`, click an item. The map centers the polygon at zoom 18 and opens the popup.
6. Use the `Google Maps` link to share the location with field teams.
7. Download CSV, GeoJSON, or KML for external analysis, QGIS, Google Earth, or dashboards.

## Data Confidence

- Official Copernicus EMS vector labels are the source of record for AOI02, AOI06, AOI08, and AOI12.
- MONIT01 point layers are official monitoring products, but they are separate from GRA `builtUpA` polygons.
- `Destroyed` and `Damaged` are treated as confirmed damage from the EMS product.
- `Possibly damaged` is shown separately. Do not count it as confirmed destroyed/damaged.
- VLM, when present, is supporting evidence for prioritization; it does not replace EMS or human validation.
- Before/after VLM exists publicly for AOI12 and AOI02 only. AOI12 is the canonical pattern; AOI02 has high uncertainty because many chips are dark, hazy, shadowed, or poorly centered.
- AOI06 and AOI08 currently have post-event-only VLM review. Do not describe those records as before/after comparisons.
- AOI03 Antimano has an internal OSM-candidate VLM review queue, but it is not public operational damage data.
- The `Catia La Mar - Microsoft AI4G Predicted Damage` layer comes from HDX/Microsoft AI for Good Lab. It is an external predicted-damage footprint layer for triage, not an official EMS label.
- Google Maps links and Esri basemap imagery are visual references only. They are not official evidence sources, are not cached by this project, and must not be cited as verification.

## Before Imagery Rules

- `Vantor usable for VLM`: dated pre-event imagery may support building-level before/after VLM when coverage, alignment, and visibility are adequate.
- `Esri visual reference only`: operator-facing context only. Use it to orient visually, not as cached evidence and not as the before image for VLM.
- `No before`: no suitable pre-event image is available. Keep VLM labels as post-event-only or candidate-only.

## Do Not Overclaim

- EMS `builtUpA` features may not represent one individual building each.
- Official EMS labels are the source of record for this package.
- VLM and inferred labels are triage aids, not official confirmation.
- External predicted-damage layers are leads only; do not quote them as official counts or confirmed damaged buildings.
- Microsoft/HDX layers are model prediction layers. Interpret them as external candidate footprints for prioritization, not as EMS labels, field confirmation, or response statistics.
- Do not describe Google or Esri views as official evidence, source-of-record imagery, or retained/cacheable before imagery.
- Absence of a marked polygon is not proof of no damage.

## Known Limitations

- AOI12 now includes the official EMS vector, EMS post-event imagery, and Vantor/OpenData pre-event reference imagery. The Vantor reference is not official EMS before imagery and has partial coverage/gaps; AOI12 VLM reviewed 107 comparisons and skipped 13 for missing/black before coverage.
- AOI02 has Vantor before reference in evidence chips only; no before map layer is published, and 15 of 17 before/after VLM records are uncertain comparison problems.
- AOI06 and AOI08 have after imagery and post-event-only VLM, but no high-resolution before imagery suitable for building-level before/after VLM in the current catalog.
- The external Microsoft/HDX layer has 9,134 predicted damaged candidates in Catia La Mar; use it as an additional lead, not as an official damage count.
- `builtUpA` polygons are official built-up assessment features; they are not guaranteed to be one building each.
- Large AOIs may require converting GeoJSON into PMTiles/vector tiles.
- National HOT/HDX buildings, roads, and POI datasets are useful context sources, but they are not loaded by default because they are large for the Vercel bundle.

## Newly Reviewed Sources

- Microsoft AI for Good Lab via HDX: `Venezuela Earthquakes: Building Damage Assessment in Catia La Mar`. Added as an external AOI with 9,134 `damaged=1` footprints.
- HOT via HDX: `Venezuela - M 7.5 Earthquake - June 2026 - OSM & Overture Data`. Documented as context source; not loaded by default because of size.
