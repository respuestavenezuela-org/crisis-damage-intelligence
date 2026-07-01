# Performance Audit Baseline

- Generated UTC: `2026-07-01T18:02:19.569204+00:00`
- Catalog: `65.1 KB` across `16` AOIs
- JS bundle in `.next/static`: `1.8 MB` across `24` files
- CSS bundle in `.next/static`: `71.7 KB` across `2` files
- `public/data`: `288.0 MB` across `74772` files
- `public/data/tiles`: `186.0 MB` across `73837` files
- `public/data/chips`: `88.5 MB` across `834` files
- Raw local production package safe: `False`
- Remote asset package required: `True`

## Initial Load Estimate

- AOI list before active AOI data: `65.1 KB`
- Default AOI vector/VLM plus catalog: `896.7 KB`
- Non-default damage/VLM bytes that would load if eager: `5.2 MB`
- Frontend eager-load pattern detected: `False`

## Production Package Pressure

- Local tiles/chips removable by remote-asset package: `274.5 MB`
- Public data remaining after remote tiles/chips are excluded: `13.5 MB`
- Local AOI files >= 5.0 MB: `0` files / `0 B`
- External-prediction large local files: `0 B`
- Local report large files: `0 B`

### Raw Local Package Unsafe Reasons

- public/data is 288.0 MB, above the raw package target 119.2 MB
- public/data/tiles is 186.0 MB, above the local tile target 71.5 MB
- public/data/chips is 88.5 MB, above the local chip target 38.1 MB

## AOI Data Pressure

| AOI | Status | AOI files | Tiles | Chips | GeoJSON features | VLM rows |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `emsr884-aoi02-caracas` | `official-vector` | 128.9 KB | 72.3 MB | 6.2 MB | 17 | 17 |
| `emsr884-aoi02-caracas-monitor01` | `official-monitor-points` | 54.0 KB | 0 B | 0 B | 20 | - |
| `emsr884-aoi03-antimano` | `imagery-only` | 341 B | 0 B | 0 B | 0 | - |
| `emsr884-aoi05-santa-cruz` | `official-monitor-points` | 5.3 KB | 0 B | 0 B | 3 | - |
| `emsr884-aoi06-moron` | `official-vector` | 564.9 KB | 10.9 MB | 9.8 MB | 129 | 129 |
| `emsr884-aoi06-moron-monitor01` | `official-monitor-points` | 243.7 KB | 0 B | 0 B | 96 | - |
| `emsr884-aoi08-san-felipe` | `official-vector` | 410.0 KB | 29.8 MB | 1.2 MB | 43 | 43 |
| `emsr884-aoi08-san-felipe-monitor01` | `official-monitor-points` | 288.2 KB | 0 B | 0 B | 183 | - |
| `emsr884-aoi10-guacara` | `imagery-only` | 340 B | 0 B | 0 B | 0 | - |
| `emsr884-aoi12-caraballeda` | `official-vector` | 1.9 MB | 73.0 MB | 71.3 MB | 120 | 107 |
| `emsr884-aoi12-caraballeda-monitor01` | `official-monitor-points` | 1.5 MB | 0 B | 0 B | 1004 | - |
| `external-msft-catia-la-mar-predicted-damage` | `external-prediction` | 4.9 MB | 0 B | 0 B | 9134 | - |
| `external-msft-caraballeda-east-predicted-damage` | `external-prediction` | 735.7 KB | 0 B | 0 B | 622 | - |
| `external-msft-catia-la-mar-east-predicted-damage` | `external-prediction` | 1.4 MB | 0 B | 0 B | 1209 | - |
| `external-msft-la-guaira-east-predicted-damage` | `external-prediction` | 141.4 KB | 0 B | 0 B | 119 | - |
| `external-hot-mapswipe-ems-gap-visual` | `external-gap` | 1.1 MB | 0 B | 0 B | 460 | - |
