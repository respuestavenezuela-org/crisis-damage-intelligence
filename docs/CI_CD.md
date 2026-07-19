# CI/CD

## Workflows

- `ci.yml`: deterministic PR/push gate for npm install, lint, typecheck, build, and basic secret scan.
- `data-validation.yml`: catalog, VLM, external registry, asset audit, and mobile budget validation.
- `production-remote-assets.yml`: scheduled/manual remote URL validation plus a guarded, deployable production artifact; not a normal PR blocker.
- `performance-budget.yml`: PR budget report and artifact upload.
- `e2e.yml`: Chromium mobile smoke tests with screenshots/traces on failure. The smoke spec covers the critical path plus 360, 430, and 768 px low-bandwidth essentials with remote raster dependencies stubbed.

## Policy

- Ingest workflows may open PRs with generated static outputs.
- Ingest workflows must not auto-deploy official claims.
- Do not expose secrets to fork PRs.
- External network checks are separated from deterministic build/data checks.
- Dependency audit starts non-blocking except for clearly exploitable critical runtime issues.
- Core Web Vitals are not yet a blocking CI gate; record Lighthouse/WebPageTest evidence in release handoffs until a production-like mobile budget job exists.

## Local Preflight

```bash
npm ci
npm run lint
npm run typecheck
npm run build
python3 scripts/validate_catalog_schema.py
python3 scripts/audit_asset_budget.py
python3 scripts/validate_mobile_performance_budget.py
```
