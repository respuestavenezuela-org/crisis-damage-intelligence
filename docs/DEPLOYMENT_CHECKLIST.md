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
- The current operational app includes AOI12 imagery/VLM assets and local chip/tile references. Keep large chips, tiles, rasters, COGs, and PMTiles out of the Vercel deploy package where possible; use R2/CDN remote assets after URL validation passes.

For the imagery-enabled package, generate a remote-asset deploy copy first:

```bash
python3 scripts/validate_remote_asset_urls.py
python3 scripts/build_vercel_remote_asset_package.py --force
cd ../crisis_damage_intelligence_vercel_remote_assets
npm install
npm run build
```

The remote asset validator writes:

```text
ops/remote_asset_validation/latest.json
ops/remote_asset_validation/latest.md
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
- Environment variables: none required for static public viewing. Analytics provider variables are optional; see `docs/ANALYTICS.md`.
- Canonical domain: `respuestavenezuela.org`
- Redirects configured in `next.config.ts`:
  - `crisis-damage-intelligence.vercel.app/*` -> `https://respuestavenezuela.org/*`
  - `www.respuestavenezuela.org/*` -> `https://respuestavenezuela.org/*`

## Domain DNS

The Vercel project is `takoves-projects/crisis-damage-intelligence`.

Required DNS records for the purchased domain:

| Type | Name | Value | Proxy |
| --- | --- | --- | --- |
| A | `@` | `76.76.21.21` | Currently proxied through Cloudflare |
| A | `www` | `76.76.21.21` | Currently proxied through Cloudflare |

If Vercel certificate validation ever fails, switch both records to DNS-only temporarily, wait for validation, then re-enable the proxy only after smoke testing.

Validation commands:

```bash
dig +short A respuestavenezuela.org
dig +short A www.respuestavenezuela.org
vercel domains inspect respuestavenezuela.org
vercel domains inspect www.respuestavenezuela.org
curl -I https://respuestavenezuela.org
curl -I https://crisis-damage-intelligence.vercel.app
```

## Before Publishing

- Confirm `public/data/catalog.json` contains only operational AOIs or clearly labeled demos.
- Confirm no `.env`, API keys, service-role keys, or local-only secrets are included.
- Confirm `node_modules` and `.next` are not committed or zipped for handoff.
- Confirm CSV/GeoJSON/KML links resolve under `/data/aoi/<aoi-id>/`.
- Confirm large rasters are not committed to Vercel; use object storage/CDN if imagery becomes large.
- If using the remote-asset package, confirm `public/data/catalog.json` tile/chip URLs point to R2/CDN and not local `/data/tiles` or `/data/chips`.

## Smoke Test After Deploy

Automated static smoke:

```bash
npm run smoke:production
```

If the internal API is intentionally enabled, also run:

```bash
npm run smoke:production -- --api-enabled --api-token "$INTERNAL_API_TOKEN"
```

1. Open the deployed URL.
2. Confirm default AOI is official EMSR884 data.
3. Check affected-area navigation. Current expected Spanish order after source-aware ranking is La Guaira / Caraballeda / Catia La Mar, Moron, San Felipe, Caracas, Antimano, Guacara.
4. Check filters:
   - AOI02 all = 17, Destroyed/Damaged = 0.
   - AOI06 all = 129, Destroyed/Damaged = 36.
   - AOI08 all = 43, Destroyed/Damaged = 8.
   - AOI12 all = 120, Destroyed/Damaged = 96.
5. Click first priority item and confirm zoom 18 + popup + Google Maps link.
6. Confirm AOI12 imagery labels show EMS post-event imagery and Vantor/OpenData before reference, with partial-coverage caveats.
7. Confirm VLM labels distinguish before/after review from post-event-only review.
8. Confirm Catia La Mar Microsoft AI4G predictions are labeled external/triage-only and are not counted as official EMS damage.
9. Download CSV, GeoJSON, and KML for operational AOIs.

## Do Not Overclaim

- EMS `builtUpA` features may not be one building each.
- Official EMS labels are the source of record for this package.
- VLM/inferred labels are triage aids only.
- Post-event-only VLM is not before/after VLM.
- External prediction layers are not official EMS confirmation.
- Absence of a marked feature is not proof of no damage.
