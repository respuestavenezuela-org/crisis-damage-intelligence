# Performance Audit Baseline

- Generated UTC: `2026-06-29T08:20:46.406761+00:00`
- Catalog: `62.2 KB` across `15` AOIs
- JS bundle in `.next/static`: `1.7 MB` across `24` files
- CSS bundle in `.next/static`: `58.3 KB` across `2` files
- `public/data`: `268.9 MB` across `74613` files
- `public/data/tiles`: `186.0 MB` across `73837` files
- `public/data/chips`: `67.3 MB` across `681` files
- Raw local production package safe: `False`
- Remote asset package required: `True`

## Initial Load Estimate

- AOI list before active AOI data: `62.2 KB`
- Default AOI vector/VLM plus catalog: `978.2 KB`
- Non-default damage/VLM bytes that would load if eager: `7.5 MB`
- Frontend eager-load pattern detected: `False`

## Production Package Pressure

- Local tiles/chips removable by remote-asset package: `253.4 MB`
- Public data remaining after remote tiles/chips are excluded: `15.5 MB`
- Local AOI files >= 5.0 MB: `0` files / `0 B`
- External-prediction large local files: `0 B`
- Local report large files: `0 B`

### Raw Local Package Unsafe Reasons

- public/data is 268.9 MB, above the raw package target 119.2 MB
- public/data/tiles is 186.0 MB, above the local tile target 71.5 MB
- public/data/chips is 67.3 MB, above the local chip target 38.1 MB

## AOI Data Pressure

| AOI | Status | AOI files | Tiles | Chips | GeoJSON features | VLM rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `emsr884-aoi02-caracas` | `official-vector` | 140.3 KB | 72.3 MB | 6.2 MB | 17 | 17 |
| `emsr884-aoi02-caracas-monitor01` | `official-monitor-points` | 54.0 KB | 0 B | 0 B | 20 | - |
| `emsr884-aoi03-antimano` | `imagery-only` | 341 B | 0 B | 0 B | 0 | - |
| `emsr884-aoi05-santa-cruz` | `official-monitor-points` | 5.3 KB | 0 B | 0 B | 3 | - |
| `emsr884-aoi06-moron` | `official-vector` | 564.9 KB | 10.9 MB | 9.8 MB | 129 | 129 |
| `emsr884-aoi06-moron-monitor01` | `official-monitor-points` | 243.7 KB | 0 B | 0 B | 96 | - |
| `emsr884-aoi08-san-felipe` | `official-vector` | 410.0 KB | 29.8 MB | 1.2 MB | 43 | 43 |
| `emsr884-aoi08-san-felipe-monitor01` | `official-monitor-points` | 288.3 KB | 0 B | 0 B | 183 | - |
| `emsr884-aoi10-guacara` | `imagery-only` | 340 B | 0 B | 0 B | 0 | - |
| `emsr884-aoi12-caraballeda` | `official-vector` | 2.0 MB | 73.0 MB | 50.2 MB | 120 | 107 |
| `emsr884-aoi12-caraballeda-monitor01` | `official-monitor-points` | 1.5 MB | 0 B | 0 B | 1004 | - |
| `external-msft-catia-la-mar-predicted-damage` | `external-prediction` | 6.8 MB | 0 B | 0 B | 9134 | - |
| `external-msft-caraballeda-east-predicted-damage` | `external-prediction` | 1.1 MB | 0 B | 0 B | 622 | - |
| `external-msft-catia-la-mar-east-predicted-damage` | `external-prediction` | 2.1 MB | 0 B | 0 B | 1209 | - |
| `external-msft-la-guaira-east-predicted-damage` | `external-prediction` | 214.1 KB | 0 B | 0 B | 119 | - |
