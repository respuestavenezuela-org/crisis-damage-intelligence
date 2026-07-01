# Analytics Foundation

This app is a public bilingual crisis map. Analytics must measure whether responders and reviewers can find useful evidence without collecting personal data, exact user identity, or full external URLs.

## Measurement Readiness

Score: 86/100, measurement-ready for client instrumentation. Production provider verification remains required before operational decisions.

- Decision alignment: 20/25. Events map to crisis-response questions: which affected areas are used, which evidence paths matter, and which export formats are needed.
- Event model clarity: 19/20. Events use `object_action` names, flat properties, and distinguish intent, load health, and friction.
- Data accuracy: 18/20. Client events are wired, deduped for load failures, and covered by E2E assertions; production provider verification is still required.
- Conversion quality: 13/15. Evidence opens, data downloads, and external map opens define operational success paths; they remain intent signals, not damage validation.
- Attribution and context: 7/10. Page URLs and optional UTM context remain provider-owned; no custom attribution logic is added.
- Governance: 9/10. Taxonomy, deployment knobs, property allowlists, and privacy QA are documented here.

## Data Minimization

- Do not send names, emails, IPs, coordinates, free text, or full Google Maps/chip/download URLs from custom events.
- AOI ids, affected-area/city ids, language, selected mode, filter, basemap, file format, evidence surface, priority rank, source category, and coarse damage/VLM context are allowed.
- Priority events intentionally omit feature/building ids. Evidence chip events record `chip_kind`, not the chip path.
- `trackAnalytics` enforces a per-event property allowlist plus per-property validators: enums for language/mode/filter/basemap, coarse-id validators for AOI/city ids, bounded integer validators for counts/ranks/timers, token validators for surfaces/layers/statuses, and safe-label validators for coarse damage/VLM classes.
- Web Analytics pageviews are handled by Vercel's cookie-free script. Interaction events are queued locally and only sent to OpenPanel or Vercel custom events when explicitly configured with public environment variables.

## Event Taxonomy

| Event | Description | Properties | Trigger | Decision supported |
| --- | --- | --- | --- | --- |
| `app_loaded` | App shell and AOI catalog loaded | `language`, `default_aoi_id`, `aoi_count`, `default_basemap`, `default_mode`, `public_static` | First catalog load | Is the public app loading and what default context is seen? |
| `language_switched` | User changes ES/EN | `from_language`, `to_language`, `aoi_id` | Language segmented control | Which language needs better operational support? |
| `aoi_selected` | User selects an affected area or its active AOI layer | `aoi_id`, `city_id`, `aoi_status`, `language` | Affected-area navigation button | Which affected areas are being investigated? |
| `imagery_mode_changed` | User toggles before/after imagery | `aoi_id`, `mode`, `has_before_imagery`, `has_after_imagery` | Before/after buttons | Is before/after comparison useful where available? |
| `basemap_changed` | User toggles map/aerial base | `aoi_id`, `basemap` | Basemap buttons | Which base layer supports inspection? |
| `damage_filter_changed` | User changes damage/VLM filter | `aoi_id`, `filter` | Filter buttons | Which triage views are useful? |
| `priority_item_clicked` | User opens a priority evidence item | `aoi_id`, `rank`, `damage_class`, `has_vlm`, `vlm_review_type` | Priority list row | Are ranked evidence items driving review? |
| `google_maps_link_clicked` | User opens Google Maps | `aoi_id`, `surface`, `has_vlm` when available | Evidence panel or map popup link | Do users need external map context? |
| `data_download_clicked` | User downloads public data | `aoi_id`, `format`, `surface` | CSV/GeoJSON/KML and imagery links | Which public export formats matter? |
| `evidence_chip_clicked` | User opens an evidence chip | `aoi_id`, `chip_kind`, `surface`, `has_vlm` | Evidence preview or chip button | Are chips useful for visual confirmation? |
| `catalog_load_failed` | Static AOI catalog could not load | `surface`, `status` | `catalog.json` fetch failure | Is the static public shell failing before AOI data is available? |
| `layer_load_failed` | AOI data, imagery, or basemap layer failed | `aoi_id`, `layer`, `surface`, `status`, `mode`, `basemap` when available | Damage/VLM fetch failure or first map tile/image load error | Are users blocked by missing data or remote imagery failures? |
| `fallback_view_shown` | User sees a degraded but usable fallback state | `aoi_id`, `surface`, `status`, `catalog_status`, `damage_status`, `vlm_status` | Visible status/error alert appears | Are fallback states preserving usability when services/assets fail? |
| `filter_empty_result_seen` | Current filter leaves a loaded AOI with no visible features | `aoi_id`, `filter`, `mode`, `basemap`, `feature_count`, `status` | Damage layer is ready and selected filter returns zero visible features | Are users choosing filters that make the map look empty or confusing? |
| `map_empty_clicked` | User clicked/tapped the map without selecting a feature | `aoi_id`, `mode`, `filter`, `basemap` | Map click misses all visible damage features | Are users trying to inspect something the app does not make selectable? |
| `mobile_panel_opened` | User opens a mobile bottom-sheet panel | `aoi_id`, `surface`, `language`, `mode`, `filter`, `basemap` | Mobile About, Zone, Layers, or Evidence/Priority panel opens | Which mobile path creates or resolves navigation friction? |

## Operational Funnels

Use these as decision funnels, not vanity totals:

| Question | Funnel |
| --- | --- |
| Do people reach useful evidence? | `app_loaded` → `aoi_selected` or default AOI → `map_ready` → `priority_item_clicked` → `evidence_chip_clicked` or `google_maps_link_clicked` |
| Do people get usable files? | `app_loaded` → `aoi_selected` → `data_download_clicked` |
| Is poor connectivity blocking use? | `app_loaded` → `catalog_load_failed` / `layer_load_failed` / missing `first_tile_loaded` → `fallback_view_shown` |
| Are filters or map affordances confusing? | `damage_filter_changed` → `filter_empty_result_seen`; `map_ready` → repeated `map_empty_clicked` without `priority_item_clicked` |
| Is mobile navigation too indirect? | `mobile_panel_opened` sequences before `priority_item_clicked`, `evidence_chip_clicked`, or `data_download_clicked` |

## Deployment Notes

Vercel Web Analytics pageviews are enabled by rendering `@vercel/analytics/next` in the root layout. No client secrets are required.

Interaction events remain provider-neutral at the app boundary:

- Every event is pushed to `window.crisisDamageAnalyticsQueue`.
- Every event dispatches a `crisis_damage_analytics` browser event.
- A future provider can attach `window.crisisDamageAnalytics.track(event)` without changing UI code.
- OpenPanel screen views and sanitized custom interaction events are enabled only when a public OpenPanel client id is configured. Automatic outgoing-link and attribute tracking stay disabled to avoid collecting full external URLs.
- Unknown event properties are discarded before local queueing, browser event dispatch, OpenPanel forwarding, or Vercel custom-event forwarding.
- New dimensions must be added in two places: the event allowlist and the property validator table. Pick the narrowest validator that preserves the intended aggregate dimension; do not bypass sanitization for one-off debugging values.

Optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER` | `disabled` | Sends screen views and custom interaction events through OpenPanel only when set to `openpanel` and `NEXT_PUBLIC_OPENPANEL_CLIENT_ID` is set. Set to `vercel` only if custom Vercel events are intentionally enabled. |
| `NEXT_PUBLIC_OPENPANEL_CLIENT_ID` | unset | Public OpenPanel client id. Required to enable OpenPanel network calls. |
| `NEXT_PUBLIC_OPENPANEL_API_URL` | unset | Optional OpenPanel API URL for self-hosted/proxied deployments. |
| `NEXT_PUBLIC_OPENPANEL_SCRIPT_URL` | unset | Optional OpenPanel script URL for self-hosted/proxied deployments. |
| `NEXT_PUBLIC_ANALYTICS_DEBUG` | `false` | Set to `true` to log sanitized events in the browser console during QA. |

OpenPanel is initialized only when `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=openpanel` and `NEXT_PUBLIC_OPENPANEL_CLIENT_ID` is set. Session replay, user identification, profile ids, automatic outgoing-link tracking, and data-attribute tracking remain disabled. Vercel custom events can require a paid plan or consume event quota; use `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=vercel` only intentionally. The app remains static-first either way.

## Validation Checklist

1. Deploy or run locally with `NEXT_PUBLIC_ANALYTICS_DEBUG=true`.
2. Load the app and confirm one `app_loaded` event after `catalog.json` resolves.
3. Switch language, AOI, basemap, imagery mode, and filter; confirm each event fires once per state change.
4. On a mobile viewport, open About, Zone, Layers, and Evidence/Priority; confirm `mobile_panel_opened` contains only coarse surface/context fields.
5. Click an empty map area and choose any filter that returns no visible features; confirm `map_empty_clicked` and `filter_empty_result_seen` omit coordinates and feature ids.
6. Click a priority row, Google Maps link, evidence chip, and CSV/GeoJSON/KML download; confirm no full URL, feature id, coordinates, or free text appears in event properties.
7. Simulate failed AOI data/imagery requests and confirm `layer_load_failed` plus `fallback_view_shown` fire once per AOI/layer fallback state.
8. Run `npm run test:e2e`; the analytics privacy test listens to `crisis_damage_analytics` and checks coarse payloads.
9. Verify screen views and interaction events in OpenPanel before using them for operational decisions.
10. If `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=vercel` is enabled, verify events in the Vercel dashboard before using them for operational decisions.

## Interpretation Caveats

- Analytics events can show which affected areas, filters, exports, and evidence surfaces are used; they do not validate damage.
- Do not infer confirmed damage from clicks on VLM, imagery, MONIT01, or external prediction layers.
- Before/after VLM and post-event-only VLM must stay distinguishable in event properties and downstream dashboards.
- External Microsoft AI4G Catia La Mar prediction usage should be reported as triage-interest only, not as official EMS demand or confirmed damage.
