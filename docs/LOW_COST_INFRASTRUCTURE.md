# Low-Cost Infrastructure

## Public App

- Vercel project: `takoves-projects/crisis-damage-intelligence`
- Public URL: `https://crisis-damage-intelligence.vercel.app`
- Source repo: `https://github.com/takove/crisis-damage-intelligence`
- Public viewing path: static Next.js + `public/data/**`
- Public viewing does not require Supabase, object storage, workers, or VLM.

## Supabase

Target use:

- Product/AOI tracking
- Ingestion job status
- Damage feature index
- VLM review queue status
- Human validation status
- Source confidence/audit history

Schema files:

- `supabase/migrations/0001_core_schema.sql`
- `supabase/seed.sql`

Live project:

- Organization: `la-memoria-de-venezuela`
- Project: `memoria-venezuela`
- Project ref: `gxepalgxlyohcgxzxcur`
- API endpoint: `https://gxepalgxlyohcgxzxcur.supabase.co`

Applied through Supabase SQL Editor:

- `supabase/migrations/0001_core_schema.sql`
- `supabase/seed.sql`

Verified live counts:

```text
aois                    3
products                2
ingestion_jobs          2
source_confidence_audit 3
vlm_review_queue        0
```

CLI path for future migrations:

```bash
npx supabase login --token <SUPABASE_ACCESS_TOKEN>
npx supabase link --project-ref <SUPABASE_PROJECT_REF>
npx supabase db push
npx supabase db execute --file supabase/seed.sql
```

Required GitHub/Vercel variables only if server-side DB automation is added later:

- `SUPABASE_ACCESS_TOKEN` for Supabase CLI in CI
- `SUPABASE_PROJECT_REF`
- `SUPABASE_DB_URL` or service role key only for private worker jobs, never client code

Current status: schema and seed are applied live. Public viewing still does not depend on Supabase.

## Object Storage

Active low-cost target: Cloudflare R2.

Bucket:

```text
crisis-damage-intelligence
```

Prefixes:

```text
ems/original-zips/
ems/generated/
ems/rasters/before/
ems/rasters/after/
ems/evidence-chips/
ems/vlm/
qa/reports/
qa/screenshots/
```

Upload helper:

```bash
python3 scripts/upload_to_object_storage.py LOCAL_PATH REMOTE_PREFIX
```

Required env for S3-compatible upload:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION=auto` for R2

Current status:

- R2 subscription enabled on the Cloudflare account.
- Bucket `crisis-damage-intelligence` created.
- Current AOI02/AOI06 static outputs uploaded.
- Original AOI02/AOI06 GRA ZIPs uploaded.
- AOI00 GRM ZIP uploaded from the monitor download.
- QA report and public screenshot uploaded.
- GitHub Actions R2 secrets configured.

Uploaded object manifest:

```text
ems/generated/catalog.json
ems/generated/emsr884-aoi02-caracas/damage.csv
ems/generated/emsr884-aoi02-caracas/damage.geojson
ems/generated/emsr884-aoi02-caracas/damage.kml
ems/generated/emsr884-aoi02-caracas/source_metadata.json
ems/generated/emsr884-aoi02-caracas/vlm_queue.jsonl
ems/generated/emsr884-aoi06-moron/damage.csv
ems/generated/emsr884-aoi06-moron/damage.geojson
ems/generated/emsr884-aoi06-moron/damage.kml
ems/generated/emsr884-aoi06-moron/source_metadata.json
ems/generated/emsr884-aoi06-moron/vlm_queue.jsonl
ems/original-zips/emsr884-aoi02-caracas/AOI02_Caracas_GRA_v1.zip
ems/original-zips/emsr884-aoi06-moron/AOI06_Moron_GRA_v1.zip
ems/original-zips/emsr884-aoi00-central-coastal-venezuela/AOI00_Central_Coastal_Venezuela_GRM_latest.zip
qa/screenshots/public-vercel-after-infra.png
qa/reports/EMSR884_ACCEPTANCE_REPORT.md
qa/reports/LOW_COST_INFRA_SETUP_REPORT.md
```

R2 token note:

- Active GitHub token name in Cloudflare: `crisis-damage-intelligence-github-actions-r2`
- Permission: `Object Read & Write`
- Scope: all R2 buckets on the account. This was used because the bucket-specific selector was unstable in the dashboard.
- It does not grant bucket admin permissions.

## GitHub Actions

Repo:

```text
https://github.com/takove/crisis-damage-intelligence
```

Workflows:

- `.github/workflows/monitor-emsr884.yml`
  - Scheduled every 30 minutes.
  - Manual dispatch supported.
  - Checks EMSR884 status and saves monitor artifacts.
- `.github/workflows/manual-ingest.yml`
  - Manual AOI ZIP ingest.
  - Downloads ZIP, runs importer, creates static outputs, builds VLM queue, uploads to object storage when secrets exist, opens PR.
- `.github/workflows/seed-vlm-queue.yml`
  - Builds prioritized VLM queue JSONL only.
  - Does not call a VLM.

Required GitHub secrets for object storage upload:

- `S3_ENDPOINT_URL`
- `S3_BUCKET`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

Current status: configured in GitHub repo secrets.

Optional future secrets:

- `SUPABASE_ACCESS_TOKEN`
- `SUPABASE_PROJECT_REF`
- `SUPABASE_DB_URL`
- `MINIMAX_API_KEY` for private worker jobs only

## VLM Queue Policy

- Do not run VLM on every feature by default.
- Queue priority:
  - `10`: official `Destroyed` / `Damaged`
  - `30`: official `Possibly damaged`
  - `90`: anything else
- Public output should be JSONL/static after review.
- VLM output is evidence only, not source-of-truth.

Current queue files:

- `public/data/aoi/emsr884-aoi02-caracas/vlm_queue.jsonl`
- `public/data/aoi/emsr884-aoi06-moron/vlm_queue.jsonl`

## Failure Recovery

If Vercel deploy fails:

```bash
npm ci
npm run lint
npm run build
vercel --prod --yes
```

If EMS monitor fails:

```bash
python3 ops/monitor_emsr884.py
```

If AOI ingest fails:

1. Confirm ZIP contains a `*_PRODUCT_v*.gpkg`.
2. Confirm a `builtUpA*` layer exists.
3. Re-run `scripts/emsr884-aoi12-ingest.sh`.
4. Compare metadata counts against EMS summary table.

If object storage upload fails:

1. Verify S3-compatible env vars.
2. Run `aws s3 ls --endpoint-url "$S3_ENDPOINT_URL" "s3://$S3_BUCKET"`.
3. Re-run `scripts/upload_to_object_storage.py`.

If Supabase is unavailable:

- Public app continues to work from static files.
- Continue publishing CSV/GeoJSON/KML/catalog through static exports.
