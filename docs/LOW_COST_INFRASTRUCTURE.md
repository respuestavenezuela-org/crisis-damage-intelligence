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

Apply once Supabase access is available:

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

Current status: schema and seed are ready, but live Supabase provisioning requires a Supabase access token or browser dashboard access.

## Object Storage

Recommended free/low-cost target: Cloudflare R2 or any S3-compatible bucket.

Bucket suggestion:

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
ems/qa-reports/
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

Current status: upload script and workflow hooks are ready. Live bucket creation/upload requires Cloudflare R2 login/API token.

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
