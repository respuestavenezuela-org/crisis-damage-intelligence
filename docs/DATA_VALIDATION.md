# Data Validation

## Commands

```bash
python3 scripts/validate_catalog_schema.py
python3 scripts/validate_vlm_publication_guardrails.py
python3 scripts/validate_external_source_registry.py
python3 scripts/validate_remote_asset_urls.py --allow-failures
python3 scripts/audit_asset_budget.py
```

## Catalog Rules

- AOI ids must be unique and URL-safe.
- Bounds are `[[lat, lon], [lat, lon]]`; centers must be valid coordinates.
- Status must be one of the values documented in `AGENTS.md`.
- Local downloads/layers must exist under `public/data/**`.
- No local absolute paths, `file://`, localhost/private URLs, or secret-looking strings.
- Public text data under `public/data/**` is scanned for local absolute paths and secret-looking strings, not just `catalog.json`.
- External predictions must not publish official destroyed/damaged metrics.
- VLM before/after requires before and after imagery metadata plus matching VLM downloads.
- Post-event-only VLM must stay separate from before/after metrics.
- Remote asset validation samples tile/chip URLs for HTTP status, content type, immutable cache headers, and samples COG URLs for byte-range support.

## Failure Response

- Fix `errors` before merge.
- Warnings can ship only with a written operational reason in the PR.
- For external remote failures, attach the remote validation report and avoid production remote-asset deploy until failures are resolved.
