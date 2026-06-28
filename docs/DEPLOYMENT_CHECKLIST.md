# Vercel Deployment Checklist

## Preflight

Run from the package root:

```bash
npm ci
npm run lint
npm run build
```

Expected result:

- Build command: `npm run build`
- Framework preset: Next.js
- Output: Next.js static/prerendered route for `/`
- Public data served from `public/data/**`
- No database required for public viewing
- No object storage required for current AOI02/AOI06 vector-only package

For the imagery-enabled package, generate a remote-asset deploy copy first:

```bash
python3 scripts/build_vercel_remote_asset_package.py --force
cd ../crisis_damage_intelligence_vercel_remote_assets
npm install
npm run build
```

Do not deploy the remote-asset package until these URLs return HTTP 200:

```text
https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/tiles/<aoi>/<kind>/<z>/<x>/<y>.webp
https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/data/chips/<aoi>/<chip>.png
```

## Vercel Settings

- Root directory: repository/package root
- Install command: `npm ci`
- Build command: `npm run build`
- Output directory: leave default for Next.js
- Environment variables: none required for public AOI02/AOI06 viewing

## Before Publishing

- Confirm `public/data/catalog.json` contains only operational AOIs or clearly labeled demos.
- Confirm no `.env`, API keys, service-role keys, or local-only secrets are included.
- Confirm `node_modules` and `.next` are not committed or zipped for handoff.
- Confirm CSV/GeoJSON/KML links resolve under `/data/aoi/<aoi-id>/`.
- Confirm large rasters are not committed to Vercel; use object storage/CDN if imagery becomes large.
- If using the remote-asset package, confirm `public/data/catalog.json` tile/chip URLs point to R2/CDN and not local `/data/tiles` or `/data/chips`.

## Smoke Test After Deploy

1. Open the deployed URL.
2. Confirm default AOI is official EMSR884 data.
3. Switch AOI02/AOI06.
4. Check filters:
   - AOI02 all = 17, Destroyed/Damaged = 0.
   - AOI06 all = 129, Destroyed/Damaged = 36.
5. Click first priority item and confirm zoom 18 + popup + Google Maps link.
6. Download CSV, GeoJSON, and KML for each AOI.

## Do Not Overclaim

- EMS `builtUpA` features may not be one building each.
- Official EMS labels are the source of record for this package.
- VLM/inferred labels are triage aids only.
- Absence of a marked feature is not proof of no damage.
