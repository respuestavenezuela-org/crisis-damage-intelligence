# Performance Budgets

Budgets are staged. Current local assets exceed production-package targets, so the first stage blocks first-render regressions and single-file blowups while making raw package pressure explicit for reviewers.

## Stage 1 Gates

Run:

```bash
python3 scripts/audit_asset_budget.py
python3 scripts/validate_mobile_performance_budget.py
python3 scripts/validate_remote_asset_urls.py --allow-failures
```

Hard budgets:

- `public/data/catalog.json` <= 200 KB.
- Initial AOI list before active data <= 250 KB.
- Default AOI catalog + damage GeoJSON + VLM JSONL <= 2 MB.
- No detected eager loading of all AOI damage GeoJSON or VLM JSONL.
- No single local AOI file >= 50 MB. Large reports, GeoJSON, KML, or JSONL must be moved to remote storage or represented as vector tiles/FlatGeobuf before crossing this threshold.

Warnings:

- `public/data` target <= 125 MB.
- `public/data/tiles` target <= 75 MB.
- `public/data/chips` target <= 40 MB.
- Any local AOI file >= 5 MB is listed by AOI id, status, role, source, and catalog refs.
- External-prediction local payloads are called out separately from official EMS vectors and must never be mixed into official destroyed/damaged metrics.
- Local report PDFs are called out because they can make a raw deploy unsafe even when first-render mobile bytes remain acceptable.
- `python3 scripts/validate_mobile_performance_budget.py --strict` treats warnings as failures for production-package checks.
- Missing `.next` build means JS/CSS bundle numbers are incomplete.
- Remote asset failures do not block ordinary PRs, but a pruned Vercel package must not ship until representative remote tile/chip/COG checks pass.

## Raw Package Rule

The current repository checkout is a development package, not a safe production package. `public/data/tiles` and `public/data/chips` exceed the local targets and make `scripts/build_vercel_remote_asset_package.py` required before production deploys.

Review `ops/performance_audit/latest.md` and `ops/performance_audit/mobile_budget.md` on every PR that changes `public/data/**`. The reports identify:

- raw local package safety;
- bytes removable by the remote-asset package;
- public data that remains after local tiles/chips are excluded;
- large local AOI files grouped by status/source;
- large external-prediction GeoJSON/KML payloads;
- large local EMS report PDFs.

## Image Budgets

- Do not sacrifice building/damage legibility to hit byte targets.
- Use tile pyramids, cache immutable headers, and progressive loading first.
- Track median and p95 tile size by zoom when changing imagery generation.
- Keep thumbnails/previews separate from full-quality evidence chips.
- Any quality-factor change needs visual QA, old/new size, affected zooms, operational risk, and original access path.

## PR Acceptance

- No PR should increase local heavy assets without an audit report and reason.
- If local tiles/chips are needed for development, production deploy must use remote-asset packaging once R2/CDN validation passes.
- Lighthouse/Playwright mobile reports can be non-blocking initially, but failures must upload artifacts.
