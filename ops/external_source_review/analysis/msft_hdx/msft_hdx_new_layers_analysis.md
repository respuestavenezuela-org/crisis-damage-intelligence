# Microsoft/HDX External Damage Layers Review

Generated: 2026-06-28.

## Decision

Keep these datasets. They are high-value public/OSS-adjacent external triage inputs, but do not publish them as confirmed damage and do not add their counts to official EMS totals. Use them as separate model-derived candidate layers after dedupe and visual QA.

## Why They Matter

The official EMS AOI12 layer has 120 built-up damage features. These Microsoft AI4G/HDX layers add broad model coverage around La Guaira, Catia La Mar, and Caraballeda, including areas outside or adjacent to the current EMS vector features. They are useful for routing human review and VLM before/after comparison where credible pre-event imagery exists.

## Layer Counts

| Layer | Features | damaged=1 | max damage >=25% | >=50% | >=75% | Bounds WGS84 |
|---|---:|---:|---:|---:|---:|---|
| `caraballeda_east` | 10392 | 622 | 498 | 334 | 255 | `[-66.8629357, 10.6002163, -66.8113256, 10.6211033]` |
| `catia_la_mar_east` | 24732 | 1209 | 769 | 457 | 307 | `[-67.0272747, 10.5212059, -66.9572208, 10.6147739]` |
| `la_guaira_east` | 5411 | 112 | 243 | 113 | 74 | `[-66.918586, 10.5849143, -66.8608767, 10.6132233]` |

## Overlap Risk

These are not independent official counts. Spatial overlap found:

| New layer | Intersects AOI12 official features | damaged=1 within AOI12 intersections | Intersects currently published Catia Microsoft layer | damaged=1 within Catia intersections |
|---|---:|---:|---:|---:|
| `caraballeda_east` | 1904 | 397 | 0 | 0 |
| `catia_la_mar_east` | 2152 | 300 | 4600 | 387 |
| `la_guaira_east` | 972 | 57 | 0 | 0 |

## Generated Review Artifacts

- Summary JSON: `ops/external_source_review/analysis/msft_hdx/summary.json`
- Overlap JSON: `ops/external_source_review/analysis/msft_hdx/overlap_summary.json`
- Reprojected GeoJSON copies for analysis: `ops/external_source_review/analysis/msft_hdx/*.sample.geojson`
- High-value candidate CSV: `ops/external_source_review/analysis/msft_hdx/high_value_external_triage_candidates.csv`
  - Rows: 1950
  - Inclusion rule: `damaged == 1` or max(`damage_pct_0m`, `damage_pct_10m`, `damage_pct_20m`) >= 0.50.

## Before Imagery Finding

Do not use Google Maps, Bing, Esri, or similar commercial basemap tiles as our downloadable/cacheable before imagery, VLM evidence, or exported chips. They can remain outbound human links only. For building-level before/after VLM, use dated, license-compatible sources such as Vantor Open Data where available. Current baseline inventory still blocks AOI06, AOI08, and AOI10 for true before/after VLM because only Sentinel-2/context-grade imagery was found there.

## Recommended Next Step

1. Normalize these HDX/Microsoft layers into an internal review queue, not public official counts.
2. Dedupe against AOI12 EMS and the existing Catia Microsoft layer.
3. Run before/after VLM only where Vantor/Open Data pre-event imagery covers the candidate.
4. Publish only with a clear label: `External model prediction / triage aid, not official EMS`.
