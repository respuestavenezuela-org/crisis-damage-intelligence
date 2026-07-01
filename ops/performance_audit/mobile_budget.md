# Mobile Performance Budget

- Generated UTC: `2026-07-01T18:02:19.878374+00:00`
- Result: `pass`
- Catalog: `65.1 KB` / `195.3 KB`
- Initial AOI list bytes: `65.1 KB` / `244.1 KB`
- Default AOI metadata+damage+VLM bytes: `896.7 KB` / `1.9 MB`
- Local public data: `288.0 MB` target `119.2 MB`
- Local tiles: `186.0 MB` target `71.5 MB`
- Local chips: `88.5 MB` target `38.1 MB`
- Raw local production package safe: `False`
- Remote asset package required: `True`
- Public data after excluding local tiles/chips: `13.5 MB` / `71.5 MB`
- Large local AOI files: `0` / `0 B`
- Eager all-AOI data detected: `False`

## Warnings

- public/data is above target (288.0 MB > 119.2 MB); use remote-asset package for production
- public/data/tiles is above target (186.0 MB > 71.5 MB); do not deploy raw local package to Vercel
- public/data/chips is above target (88.5 MB > 38.1 MB); verify R2/CDN mirror before pruning
- raw local public/data package is not production-safe; build and deploy the remote-asset package after remote URL validation
