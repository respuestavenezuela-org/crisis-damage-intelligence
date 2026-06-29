# Remote Asset Validation

- Generated UTC: `2026-06-29T08:21:05.606197+00:00`
- Remote base: `https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev`
- Result: `pass`

## Package Pressure

- `public/data`: 74613 files, 268.9 MB
- `public/data/chips`: 681 files, 67.3 MB
- `public/data/tiles`: 73837 files, 186.0 MB

### Largest Bundled Files

- `public/data/aoi/external-msft-catia-la-mar-predicted-damage/damage.geojson`: 4.3 MB
- `public/data/aoi/external-msft-catia-la-mar-predicted-damage/damage.csv`: 2.4 MB
- `public/data/aoi/external-msft-catia-la-mar-east-predicted-damage/damage.geojson`: 1.1 MB
- `public/data/aoi/external-msft-catia-la-mar-east-predicted-damage/damage.kml`: 768.7 KB
- `public/data/aoi/emsr884-aoi12-caraballeda-monitor01/damage.kml`: 647.6 KB
- `public/data/aoi/emsr884-aoi12-caraballeda-monitor01/damage.geojson`: 637.2 KB
- `public/data/aoi/emsr884-aoi12-caraballeda/damage.geojson`: 605.1 KB
- `public/data/aoi/emsr884-aoi12-caraballeda/data/ems_builtup_damage.geojson`: 605.1 KB
- `public/data/aoi/external-msft-caraballeda-east-predicted-damage/damage.geojson`: 569.7 KB
- `public/data/aoi/external-msft-caraballeda-east-predicted-damage/damage.kml`: 395.4 KB

## Supabase-Free Static Data

- Local `/data/aoi` references checked: 90
- Missing local static references: 0

## Pruned Deploy Gate

- Ready for pruned remote-asset package: `True`
- COG Range requirement: COG fallback URLs must honor Range: bytes=0-0 with HTTP 206 and a Content-Range header starting with 'bytes 0-0/'.
- COG content-type requirement: COG fallback URLs must return a GeoTIFF-compatible content type; binary/octet-stream is accepted for EMS/Vantor/Sentinel public S3 COGs when byte ranges work.
- Sampled COG URLs: `12`

## Remote Asset Checks

- Checks run: 116
- OK: 116
- Failed: 0
- Quality errors: 0
- Quality warnings: 0
