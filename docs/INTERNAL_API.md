# Closed Internal API Contract

`/api/internal/v1/*` is a closed, server-side API over the static public catalog and AOI files. It does not add a database, backend service, live VLM provider, or required analytics dependency.

## Enablement

The API is disabled unless `INTERNAL_API_ENABLED=true`.

When enabled, callers must send:

```http
Authorization: Bearer <token>
```

Set the token with `INTERNAL_API_TOKEN`. Disabled, missing-token, and invalid-token responses are HTTP `403`.

`INTERNAL_API_ALLOW_NO_TOKEN=true` exists only for local/E2E contract tests. Do not set it in production. Production deploys should leave the API disabled unless a private integration explicitly needs it.

## Response Envelope

Every successful response includes:

```json
{
  "version": "internal.v1",
  "generatedAt": "2026-06-30T00:00:00.000Z",
  "sourceLabels": {},
  "caveats": [],
  "data": {}
}
```

Every error response uses the same envelope and replaces `data` with:

```json
{
  "error": {
    "code": "invalid_query",
    "message": "Invalid search query.",
    "details": {}
  }
}
```

## Endpoints

- `GET /api/internal/v1/catalog`: catalog-derived AOI records with separated metrics and raw catalog metrics.
- `GET /api/internal/v1/aois`: compact AOI list.
- `GET /api/internal/v1/aois/:id`: one AOI record.
- `GET /api/internal/v1/aois/:id/features`: that AOI's GeoJSON, read server-side on request.
- `GET /api/internal/v1/features?aoi_id=:id`: alias for one AOI's GeoJSON, useful for clients that prefer query contracts.
- `GET /api/internal/v1/aois/:id/priority?limit=12`: ranked feature/evidence queue for one AOI, capped at `50`.
- `GET /api/internal/v1/priority?aoi_id=:id&limit=12`: alias for the ranked queue.
- `GET /api/internal/v1/search?q=...&limit=20`: catalog/watchlist search plus feature-id lookup when the query looks like a feature id, capped at `50`.
- `GET /api/internal/v1/summary`: aggregate totals with official EMS vectors, MONIT01 points, external predictions, imagery context, and VLM triage separated.
- `GET /api/internal/v1/health`: private health check.

## Source Separation Rules

`metrics` are separated into:

- `officialEmsVector`
- `officialEmsMonitorPoints`
- `externalPredictionTriage`
- `imageryOnlyContext`
- `vlmTriage`

`rawMetricsFromCatalog` is exposed for auditability, but clients should not aggregate raw metrics across source roles. External predictions must not be added to official EMS counts. MONIT01 point layers stay separate from official builtUpA polygon-vector counts. VLM evidence is triage only, and `post_event_only` records are not before/after evidence.

## Future Public Migration

Before making any endpoint public:

1. Keep `sourceLabels`, `caveats`, and separated metrics in the response contract.
2. Add public cache policy intentionally; current closed routes use `Cache-Control: no-store`.
3. Keep broad search metadata-only unless feature index size and latency are measured. Current feature search only runs for feature-id-like queries.
4. Review whether `/features` needs pagination, vector tiles, or FlatGeobuf for large external prediction layers.
5. Confirm that public exposure does not require Supabase, VLM providers, analytics, or private services.
