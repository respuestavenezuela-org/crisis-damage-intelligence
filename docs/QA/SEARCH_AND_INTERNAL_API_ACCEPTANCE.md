# Search, Priority Actions, And Internal API QA Acceptance

These checks are implemented in `tests/e2e/search-usability.spec.ts` and `tests/e2e/internal-api-contract.spec.ts`. They are contract-driven until the Search/UX and internal API work lands.

## Search UX Contract

Required stable selectors and semantics:

- `data-testid="global-search-input"` on the visible search input. It should be a keyboard-focusable `input` with an accessible Spanish label such as `Buscar`.
- `data-testid="global-search-results"` on the result container. Use `role="listbox"` when results are open.
- `data-testid="search-result-<stable-id>"` on each result. Use `role="option"` and include enough visible text to identify the city, AOI, source id, or priority feature id.
- Search must find:
  - active city/AOI text such as `La Guaira`, `Caraballeda`, and `emsr884-aoi12-caraballeda`;
  - priority/source ids such as `ems_00003`.
- Selecting a feature result should set the existing map attributes: `.map-node[data-focused-id="ems_00003"]`, `data-map-zoom="18"`, and `data-map-center="<lat>,<lon>"`.
- On mobile widths `360`, `390`, and `430`, search must not cover or disable the existing dock buttons: `mobile-zona-toggle`, `mobile-capas-toggle`, and `mobile-inspector-toggle`.
- `Escape` closes results without trapping focus. `Tab` after closing results should move to another visible input, button, or link, not to a hidden result.

## Priority Action Contract

Required stable selectors and behavior:

- `data-testid="copy-coordinates"` on the coordinate copy action in the selected evidence panel.
- The copied text format should be `lat,lon` using decimal degrees, for example `10.6017854,-67.0311953`.
- The Google Maps evidence link should remain visible and use `https://www.google.com/maps/search/?api=1&query=<lat>,<lon>`.
- Priority sort controls should use:
  - `data-testid="priority-sort"` on the chip group;
  - `data-testid="priority-sort-response-value"` for the default response-value order;
  - `data-testid="priority-sort-source"` for source/id order.
- Sort chips must expose `aria-pressed`. Focusing or hovering an unselected chip must not reorder rows; clicking it may reorder rows.

## Internal API Contract

Base path: `/api/internal/v1`.

Runtime env contract for tests and deployment:

- `INTERNAL_API_ENABLED=false` means every contract endpoint returns `403`.
- `INTERNAL_API_ENABLED=true` enables the API.
- `INTERNAL_API_ALLOW_NO_TOKEN=true` allows unauthenticated local/CI API reads.
- `INTERNAL_API_ALLOW_NO_TOKEN=false` with `INTERNAL_API_TOKEN=<token>` requires `Authorization: Bearer <token>`.

Contract endpoints:

- `GET /catalog`
- `GET /aois`
- `GET /aois/:id`
- `GET /features?aoi_id=<aoi-id>&limit=<n>`
- `GET /priority?aoi_id=<aoi-id>&limit=<n>`
- `GET /search?q=<query>&limit=<n>`
- `GET /summary`
- Later production health check: `GET /health`

Response payloads may be direct JSON objects/arrays or enveloped as `{ "data": ... }`. Shape expectations:

- catalog includes `updatedAt` and `aois[]`;
- AOIs include `id`, localized `name`, `status`, `center`, `bounds`, `layers`, and `metrics`;
- features are GeoJSON `Feature` objects with `properties.id` and `properties.aoi_id`;
- priority rows include `id`, `aoi_id`, and `google_maps_url`;
- search results include `id`, `type`, and `label`, and must find AOIs/cities and feature ids;
- summary includes `updatedAt` plus at least one numeric, array, or object summary field.

## Commands

Local focused runs after `npm run build`:

```bash
npx playwright test tests/e2e/search-usability.spec.ts --workers=1
npx playwright test tests/e2e/internal-api-contract.spec.ts --workers=1
```

Production smoke:

```bash
npm run smoke:production
npm run smoke:production -- --api-enabled --api-token "$INTERNAL_API_TOKEN"
```

Expected status on unintegrated `origin/main`: Search/UX tests fail because the search input, sort chips, and copy-coordinate action are not implemented yet. Internal API tests fail with `404` until `/api/internal/v1/**` exists.
