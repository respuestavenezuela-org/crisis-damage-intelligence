# Rescue Operational Card

## Status

High-risk adjacent workflow.

This is related to the WhatsApp/Frontera crisis ops system, but it should not be mixed into the public map or silently added to the logistics V1 without an explicit safety decision.

## Core Insight

The feedback is not "we need more map." The feedback is:

Rescuers need a digested, updated, copyable WhatsApp card.

The map helps locate. The card helps act.

## Product Boundary

Do not turn the public crisis map into a public rescue CRM.

Separate:

- Public app: damage context, AOIs, official/triage layers, imagery, downloads, public-safe links, public-safe summaries.
- Private operational tool: rescue cards, person/building reports, contacts, last signal of life, event history, volunteer edits, verification workflow.
- Bridge: stable building/AOI IDs, public map links, and sanitized copy summaries.

## Users

- Coordinators.
- Volunteer transcribers/reviewers.
- Trusted rescue-support operators.
- Rescuers as downstream recipients of copyable summaries.

## Data Model

### RescueBuilding

- `id`
- `public_code`
- `name`
- `address_text`
- `location_lat`
- `location_lng`
- `location_precision`
- `location_access_level`
- `public_location_text`
- `map_link`
- `created_at`
- `updated_at`

### PersonReport

- `id`
- `building_id`
- `person_name_optional`
- `person_description`
- `contact_private`
- `last_signal_of_life`
- `last_signal_at`
- `status`: `new | in_review | sent_to_rescuers | attended | discarded | unknown`
- `verification_status`: `unverified | needs_verification | confirmed | rejected | stale`
- `sensitivity_flags`
- `created_at`
- `updated_at`

### RescueEvent

- `id`
- `building_id`
- `person_report_id`
- `timestamp`
- `description`
- `source_type`: `whatsapp | form | sheet | group | admin | import`
- `source_reference`
- `created_by`
- `verification_status`
- `created_at`

### RescueShareSummary

- `id`
- `building_id`
- `person_report_id`
- `summary_text`
- `included_fields`
- `redacted_fields`
- `approval_status`: `draft | approved | copied | sent | rejected`
- `created_at`
- `updated_at`

## Copyable WhatsApp Summary

The operational summary should be generated from the full private card.

Example:

```text
REPORTE ACTUALIZADO

Edificio: Jurel
Dirección: ...
Coordenadas: ...
Última señal de vida: ...
Última actualización: ...
Contacto / fuente: ...

Eventos recientes:
- ...
- ...

Estado: pendiente / en verificación / enviado a rescatistas

Link al mapa: ...
```

The summary must support field-level redaction before copying.

## Minimum Features

If implemented, the first usable slice is:

- private building/person rescue card
- event history
- last update timestamp
- last signal of life field
- copy WhatsApp summary button
- simple report form
- CSV/Sheet export or import
- status field
- source/verification field

## WhatsApp Bot Integration

The bot can support:

```text
RESUMEN edificio-jurel
REPORTAR señal de vida edificio-jurel ...
ACTUALIZAR edificio-jurel ...
EVENTOS edificio-jurel
```

If requester is authorized, bot returns a copyable operational card.

If requester is unknown, bot should not expose private person/contact/signal details.

## Public Map Integration

Public map may support:

- stable building/AOI IDs
- public map link
- public-safe copy summary
- "reportar/consultar por WhatsApp" link

Public map must not expose:

- names
- private contacts
- last signal of life
- unverified rescue reports
- raw event history
- exact sensitive locations unless explicitly approved

## Safety Rules

This workflow may include PII and life/death information.

Required:

- private by default
- strict role access
- audit access to exact location/contact/person details
- field-level redaction before copying
- no public exposure without explicit approval
- source and verification status visible
- no official rescue promise
- citizen-effort disclaimer for urgent/life-safety content

## Relationship To Logistics V1

This is not the same as the logistics intake MVP.

Shared infrastructure:

- Frontera WhatsApp webhook
- `CrisisContact`
- conversation/message provenance
- sensitive access audit
- coordinator action queue patterns
- copyable WhatsApp summaries

Different domain:

- buildings
- person reports
- last signal of life
- event history
- rescue-specific status

Do not add this to logistics V1 unless the project explicitly decides to support rescue-person reports and accepts the added safety burden.

## Open Decisions

- Is this part of V1, V1.1, or a separate private tool?
- Who can access full rescue cards?
- Who can copy/share summaries with PII?
- Which fields are included by default in a summary?
- Does this live in Frontera, a private Sheet/Supabase, or both?
- How are duplicates across other groups handled?

## Acceptance Criteria

- Rescue cards are private by default.
- A trusted operator can generate a copyable WhatsApp summary.
- Sensitive fields can be redacted before copy/share.
- Event history remains visible to authorized operators.
- Public map only exposes safe links or public summaries.
- Unknown users cannot retrieve person/contact/last-signal details.
