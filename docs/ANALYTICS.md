# Analytics Foundation

This app is a public bilingual crisis map. Analytics must measure whether responders and reviewers can find useful evidence without collecting personal data, exact user identity, or full external URLs.

## Measurement Readiness

Score: 76/100, usable with gaps.

- Decision alignment: 20/25. Events map to crisis-response questions: which affected areas are used, which evidence paths matter, and which export formats are needed.
- Event model clarity: 17/20. Events use `object_action` names and flat properties.
- Data accuracy: 14/20. Client events are wired, but production provider verification is still required.
- Conversion quality: 10/15. No hard conversion is defined yet; downloads and evidence opens are intent signals, not conversions.
- Attribution and context: 7/10. Page URLs and optional UTM context remain provider-owned; no custom attribution logic is added.
- Governance: 8/10. Taxonomy and deployment knobs are documented here.

## Data Minimization

- Do not send names, emails, IPs, coordinates, free text, or full Google Maps/chip/download URLs from custom events.
- AOI ids, affected-area/city ids, language, selected mode, filter, basemap, file format, evidence surface, priority rank, source category, and coarse damage/VLM context are allowed.
- Priority events intentionally omit feature/building ids. Evidence chip events record `chip_kind`, not the chip path.
- Web Analytics pageviews are handled by Vercel's cookie-free script. Interaction events are queued locally and sent to OpenPanel by default with sanitized properties.

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

## Deployment Notes

Vercel Web Analytics pageviews are enabled by rendering `@vercel/analytics/next` in the root layout. No client secrets are required.

Interaction events remain provider-neutral at the app boundary:

- Every event is pushed to `window.crisisDamageAnalyticsQueue`.
- Every event dispatches a `crisis_damage_analytics` browser event.
- A future provider can attach `window.crisisDamageAnalytics.track(event)` without changing UI code.
- OpenPanel screen views, outgoing links, data-attribute events, and sanitized custom interaction events are enabled only when a public OpenPanel client id is configured.

Optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER` | `openpanel` | Sends screen views and custom interaction events through OpenPanel only when `NEXT_PUBLIC_OPENPANEL_CLIENT_ID` is set. Set to `disabled` to disable OpenPanel/custom forwarding. Set to `vercel` only if custom Vercel events are intentionally enabled. |
| `NEXT_PUBLIC_OPENPANEL_CLIENT_ID` | unset | Public OpenPanel client id. Required to enable OpenPanel network calls. |
| `NEXT_PUBLIC_OPENPANEL_API_URL` | unset | Optional OpenPanel API URL for self-hosted/proxied deployments. |
| `NEXT_PUBLIC_OPENPANEL_SCRIPT_URL` | unset | Optional OpenPanel script URL for self-hosted/proxied deployments. |
| `NEXT_PUBLIC_ANALYTICS_DEBUG` | `false` | Set to `true` to log sanitized events in the browser console during QA. |

OpenPanel is initialized only when `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=openpanel` and `NEXT_PUBLIC_OPENPANEL_CLIENT_ID` is set. Session replay, user identification, and profile ids remain disabled. Automatic outgoing-link tracking and `data-track` attribute tracking are enabled when OpenPanel is active. Vercel custom events can require a paid plan or consume event quota; use `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=vercel` only intentionally. The app remains static-first either way.

## Validation Checklist

1. Deploy or run locally with `NEXT_PUBLIC_ANALYTICS_DEBUG=true`.
2. Load the app and confirm one `app_loaded` event after `catalog.json` resolves.
3. Switch language, AOI, basemap, imagery mode, and filter; confirm each event fires once per state change.
4. Click a priority row, Google Maps link, evidence chip, and CSV/GeoJSON/KML download; confirm no full URL, feature id, coordinates, or free text appears in event properties.
5. Verify screen views and interaction events in OpenPanel before using them for operational decisions.
6. If `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=vercel` is enabled, verify events in the Vercel dashboard before using them for operational decisions.

## Interpretation Caveats

- Analytics events can show which affected areas, filters, exports, and evidence surfaces are used; they do not validate damage.
- Do not infer confirmed damage from clicks on VLM, imagery, MONIT01, or external prediction layers.
- Before/after VLM and post-event-only VLM must stay distinguishable in event properties and downstream dashboards.
- External Microsoft AI4G Catia La Mar prediction usage should be reported as triage-interest only, not as official EMS demand or confirmed damage.
