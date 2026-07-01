# Pre-Event Baseline Suitability Report

Generated from `ops/baseline_inventory/pre_event_baseline_inventory.json`.

Only imagery marked `usable_for_building_vlm=true` should be used for building-level before/after VLM. Sentinel-2 and unknown-date/context-only basemaps are acceptable as visual context only, not building damage comparison.

## Summary

| AOI | Building-level baseline | Total candidates | Usable feature coverage | Decision |
|---|---:|---:|---:|---|
| `emsr884-aoi03-antimano` | 4 | 21 | 0 | usable pilot only; internal candidates, not official vectors |
| `emsr884-aoi05-santa-cruz` | 0 | 8 | 0 | blocked: only 10 m Sentinel-2 context baseline found |
| `emsr884-aoi06-moron` | 0 | 3 | 0 | blocked: only 10 m Sentinel-2 context baseline found |
| `emsr884-aoi08-san-felipe` | 0 | 3 | 0 | blocked: only 10 m Sentinel-2 context baseline found |
| `emsr884-aoi10-guacara` | 0 | 8 | 0 | blocked: no official damage vector and only context baseline found |

## AOI Detail

### AOI03 Antimano

Building-level candidate baselines:
- vantor-open-data `B160001100FD1910`; datetime 2026-03-20T14:46:55.249591Z; gsd 0.5 m; cloud 1; features covered 0; license CC-BY-NC-4.0
- vantor-open-data `B160001100FF4510`; datetime 2026-03-21T14:31:32.374596Z; gsd 0.5 m; cloud 3; features covered 0; license CC-BY-NC-4.0
- vantor-open-data `B1400011000BDF10`; datetime 2026-02-09T12:03:36.37465Z; gsd 0.5 m; cloud 5; features covered 0; license CC-BY-NC-4.0
- vantor-open-data `B120001100513B10`; datetime 2026-04-07T15:14:46.124708Z; gsd 0.5 m; cloud 12; features covered 0; license CC-BY-NC-4.0

Context-only candidates found:
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PGM_20260212_0_L2A`; datetime 2026-02-12T14:59:58.291000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PGM_20260205_0_L2A`; datetime 2026-02-05T15:09:51.842000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PGM_20260302_0_L2A`; datetime 2026-03-02T15:09:57.444000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PGM_20260131_0_L2A`; datetime 2026-01-31T15:09:55.504000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PGM_20260121_0_L2A`; datetime 2026-01-21T15:09:57.001000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PGM_20260428_0_L2A`; datetime 2026-04-28T15:00:05.149000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PGM_20260322_0_L2A`; datetime 2026-03-22T15:09:58.971000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PGM_20260327_0_L2A`; datetime 2026-03-27T15:09:54.747000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- openaerialmap `6a3f353290cf21f32ffb7471`; datetime None; gsd None; features covered None; judgement `context_only_not_building_level`
- openaerialmap `6a3f378090cf21f32ffb7cec`; datetime None; gsd None; features covered None; judgement `context_only_not_building_level`

### AOI05 Santa Cruz

No high-resolution building-level pre-event baseline found in the current public inventory.

Context-only candidates found:
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PFM_20260205_0_L2A`; datetime 2026-02-05T15:09:57.182000Z; gsd 10; features covered 3; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260121_0_L2A`; datetime 2026-01-21T15:10:02.380000Z; gsd 10; features covered 3; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260322_0_L2A`; datetime 2026-03-22T15:10:04.740000Z; gsd 10; features covered 3; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260302_0_L2A`; datetime 2026-03-02T15:10:03.095000Z; gsd 10; features covered 3; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260131_0_L2A`; datetime 2026-01-31T15:10:00.807000Z; gsd 10; features covered 3; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260210_0_L2A`; datetime 2026-02-10T15:10:03.780000Z; gsd 10; features covered 3; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PFM_20260327_0_L2A`; datetime 2026-03-27T15:10:00.369000Z; gsd 10; features covered 3; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PFM_20260506_0_L2A`; datetime 2026-05-06T15:09:59.485000Z; gsd 10; features covered 3; judgement `context_only_not_building_level`

### AOI06 Moron

No high-resolution building-level pre-event baseline found in the current public inventory.

Context-only candidates found:
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PEM_20260205_0_L2A`; datetime 2026-02-05T15:10:00.674000Z; gsd 10; features covered 129; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PEM_20260322_0_L2A`; datetime 2026-03-22T15:10:08.303000Z; gsd 10; features covered 129; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PEM_20260121_0_L2A`; datetime 2026-01-21T15:10:05.888000Z; gsd 10; features covered 129; judgement `context_only_not_building_level`

### AOI08 San Felipe

No high-resolution building-level pre-event baseline found in the current public inventory.

Context-only candidates found:
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PEM_20260205_0_L2A`; datetime 2026-02-05T15:10:00.674000Z; gsd 10; features covered 43; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PEM_20260322_0_L2A`; datetime 2026-03-22T15:10:08.303000Z; gsd 10; features covered 43; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PEM_20260121_0_L2A`; datetime 2026-01-21T15:10:05.888000Z; gsd 10; features covered 43; judgement `context_only_not_building_level`

### AOI10 Guacara

No high-resolution building-level pre-event baseline found in the current public inventory.

Context-only candidates found:
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PFM_20260205_0_L2A`; datetime 2026-02-05T15:09:57.182000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260121_0_L2A`; datetime 2026-01-21T15:10:02.380000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260322_0_L2A`; datetime 2026-03-22T15:10:04.740000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260302_0_L2A`; datetime 2026-03-02T15:10:03.095000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260131_0_L2A`; datetime 2026-01-31T15:10:00.807000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2C_19PFM_20260210_0_L2A`; datetime 2026-02-10T15:10:03.780000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PFM_20260327_0_L2A`; datetime 2026-03-27T15:10:00.369000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`
- aws-earth-search-sentinel-2-l2a-cogs `S2B_19PFM_20260506_0_L2A`; datetime 2026-05-06T15:09:59.485000Z; gsd 10; features covered 0; judgement `context_only_not_building_level`

## Operational Rule

- Do not run or publish before/after building VLM for AOI05, AOI06, AOI08, or AOI10 until a high-resolution pre-event baseline is found.
- Post-event-only VLM may remain available as lower-confidence triage evidence, but it must stay labeled separately from before/after comparison.
- AOI03 VLM remains internal because it is based on OSM candidates, not official EMS damage features.
