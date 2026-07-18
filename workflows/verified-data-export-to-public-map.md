# Verified Data Export To Public Map

## Priority

P1. This is not required for V1.

V1 should work entirely inside WhatsApp/Frontera for intake and coordination. Export to the public map should wait until confirmed data and a publication policy exist.

## Loop

Every time verified operational information should become visible in the public static crisis platform.

## Goal

Publish safe, verified summaries from the WhatsApp coordination system into the static public map without making the map depend on the WhatsApp backend.

## Trigger

Event-triggered by:

- coordinator marks a record `public_summary` or `public_map`
- resource status changes from confirmed to stale/resolved

Schedule-triggered by:

- periodic static export job

## Primary Actors

- Coordinator.
- Export job.
- Public map user.

## Inputs

- Confirmed operational records with public visibility.
- Tool directory entries approved for public listing.
- Redaction policy.
- Existing static app catalog/data format.

## Output

Static JSON files under the public app data model, for example:

- `public/data/ops/resources.json`
- `public/data/ops/tools.json`
- `public/data/ops/status.json`

The exact path should follow the existing app data conventions at implementation time.

## Export Rules

Only export records when:

- `verification_status=confirmed`
- `public_visibility` is `public_summary` or `public_map`
- no blocking sensitivity flag exists
- last confirmed timestamp is within freshness window
- confirmation was made by a role allowed under the active authority policy

Do not export:

- private phone numbers
- private notes
- raw WhatsApp messages
- exact sensitive locations unless explicitly approved
- medical/missing-person details
- unverified records as facts

## Public Map Presentation

The public app may show:

- category
- approximate zone by default
- status
- last confirmed time
- source label: `coordinación verificada`, `pendiente`, or `desactualizado`
- no sensitive source details

Exact coordinates may only be exported if `location_access_level=approved_public_exact`, and that should be rare.

The map remains an optional view. The WhatsApp system remains the operational source for logistics.

## Failure Behavior

If the WhatsApp/Frontera backend is unavailable:

- existing static exports remain usable
- public map still loads existing EMS/static data
- app displays export timestamp and stale warning

## Checkpoint

Coordinator/admin approval required before any record becomes exportable. The exact confirming authority is TBD and must be configured before production use.

## Acceptance Criteria

- Export job produces static JSON without requiring runtime database access.
- Unverified records are excluded.
- Stale records are either excluded or labeled stale according to policy.
- Public app remains functional without WhatsApp backend.
- Export includes generated timestamp and schema version.
