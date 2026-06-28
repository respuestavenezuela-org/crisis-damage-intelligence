# Analytics Foundation

This app is a public bilingual crisis map. Analytics must measure whether responders and reviewers can find useful evidence without collecting personal data, exact user identity, or full external URLs.

## Measurement Readiness

Score: 76/100, usable with gaps.

- Decision alignment: 20/25. Events map to crisis-response questions: which AOIs are used, which evidence paths matter, and which export formats are needed.
- Event model clarity: 17/20. Events use `object_action` names and flat properties.
- Data accuracy: 14/20. Client events are wired, but production provider verification is still required.
- Conversion quality: 10/15. No hard conversion is defined yet; downloads and evidence opens are intent signals, not conversions.
- Attribution and context: 7/10. Page URLs and optional UTM context remain provider-owned; no custom attribution logic is added.
- Governance: 8/10. Taxonomy and deployment knobs are documented here.

## Data Minimization

- Do not send names, emails, IPs, coordinates, free text, or full Google Maps/chip/download URLs from custom events.
- AOI ids, city ids, language, selected mode, filter, basemap, file format, evidence surface, priority rank, and coarse damage/VLM context are allowed.
- Priority events intentionally omit feature/building ids. Evidence chip events record `chip_kind`, not the chip path.
- Web Analytics pageviews are handled by Vercel's cookie-free script. Interaction events are queued locally and only sent to Vercel when explicitly enabled.

## Event Taxonomy

| Event | Description | Properties | Trigger | Decision supported |
| --- | --- | --- | --- | --- |
| `app_loaded` | App shell and AOI catalog loaded | `language`, `default_aoi_id`, `aoi_count`, `default_basemap`, `default_mode`, `public_static` | First catalog load | Is the public app loading and what default context is seen? |
| `language_switched` | User changes ES/EN | `from_language`, `to_language`, `aoi_id` | Language segmented control | Which language needs better operational support? |
| `aoi_selected` | User selects a city/AOI | `aoi_id`, `city_id`, `aoi_status`, `language` | City/AOI button | Which affected areas are being investigated? |
| `imagery_mode_changed` | User toggles before/after imagery | `aoi_id`, `mode`, `has_before_imagery`, `has_after_imagery` | Before/after buttons | Is before/after comparison useful where available? |
| `basemap_changed` | User toggles map/aerial base | `aoi_id`, `basemap` | Basemap buttons | Which base layer supports inspection? |
| `damage_filter_changed` | User changes damage/VLM filter | `aoi_id`, `filter` | Filter buttons | Which triage views are useful? |
| `priority_item_clicked` | User opens a priority evidence item | `aoi_id`, `rank`, `damage_class`, `has_vlm`, `vlm_review_type` | Priority list row | Are ranked evidence items driving review? |
| `google_maps_link_clicked` | User opens Google Maps | `aoi_id`, `surface`, `has_vlm` when available | Evidence panel or map popup link | Do users need external map context? |
| `data_download_clicked` | User downloads public data | `aoi_id`, `format`, `surface` | CSV/GeoJSON/KML and imagery links | Which public export formats matter? |
| `evidence_chip_clicked` | User opens an evidence chip | `aoi_id`, `chip_kind`, `surface`, `has_vlm` | Evidence preview or chip button | Are chips useful for visual confirmation? |

## Deployment Notes

Vercel Web Analytics pageviews are enabled by rendering `@vercel/analytics/next` in the root layout. No client secrets are required.

Interaction events are provider-neutral by default:

- Every event is pushed to `window.crisisDamageAnalyticsQueue`.
- Every event dispatches a `crisis_damage_analytics` browser event.
- A future provider can attach `window.crisisDamageAnalytics.track(event)` without changing UI code.

Optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER` | unset | Set to `vercel` to send custom interaction events through `@vercel/analytics`. Leave unset for pageviews-only, no-cost operation. |
| `NEXT_PUBLIC_ANALYTICS_DEBUG` | `false` | Set to `true` to log sanitized events in the browser console during QA. |

Vercel custom events can require a paid plan or consume event quota. Keep `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER` unset unless the deployment owner has accepted that cost. The app remains static-first either way.

## Validation Checklist

1. Deploy or run locally with `NEXT_PUBLIC_ANALYTICS_DEBUG=true`.
2. Load the app and confirm one `app_loaded` event after `catalog.json` resolves.
3. Switch language, AOI, basemap, imagery mode, and filter; confirm each event fires once per state change.
4. Click a priority row, Google Maps link, evidence chip, and CSV/GeoJSON/KML download; confirm no full URL, feature id, coordinates, or free text appears in event properties.
5. If `NEXT_PUBLIC_ANALYTICS_EVENTS_PROVIDER=vercel` is enabled, verify events in the Vercel dashboard before using them for operational decisions.
