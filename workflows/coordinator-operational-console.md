# Coordinator Operational Console

## Goal

Give coordinators a fast, low-noise operating surface for deciding what needs verification, routing, matching, escalation, follow-up, or closure.

This is not a general analytics dashboard. It is a triage and action queue for overloaded humans.

## Research Basis

This spec adapts lightweight pieces from incident management and humanitarian logistics practice:

- FEMA ICS 213RR resource requests track quantity, kind/type, detailed item description, requested delivery/reporting location, suitable substitutes/sources, priority, approvals, supplier/POC, and notes.
- FEMA ICS form descriptions emphasize status snapshots, resource status changes, check-ins, general messages, and activity logs for moving decision-support information where needed.
- Logistics Cluster guidance frames coordination and information management as support for operational decision-making, identifying critical gaps/bottlenecks, avoiding duplication, and clarifying roles/responsibilities.
- OCHA data responsibility guidance emphasizes common operational pictures, avoiding duplication, sensitive operational data handling, "do no harm", and transparency about limitations.

## Primary Users

- Logistics coordinators.
- Center-of-acopio operators.
- Trusted remote coordinators.
- Admins responsible for role, visibility, and export policy.

Field rescue teams are downstream consumers or escalation targets, not primary queue operators.

## Core Question

For each item, the console must help answer:

```text
What is this, where is it, how urgent is it, can we trust/share it, who should act, and what is the next safe action?
```

## Views

### 1. Action Queue

Default view. Shows items requiring human action.

Sections:

- Critical / life-safety
- Needs verification
- Possible duplicate
- Possible match
- Needs routing
- Stale / reconfirm
- Pending closure
- Sensitive / access restricted

### 2. Needs

Open needs grouped by category group, location, urgency, age, and status.

### 3. Offers And Resources

Available offers/resources grouped by category, location, freshness, sensitivity, and whether they can be shared.

### 4. Matches

Need/offer/resource match recommendations pending coordinator approval.

This view must include matches whose only blocker is missing coordinator approval. A missing approval must never make the dashboard look like there was no match.

Match recommendations pending coordinator approval should feel closer to a low-writing review queue than a raw table. The coordinator should be able to approve, reject, assign, request transport, or ask for more info from the card without writing unless a reason/note is needed.

The console must make accountability visible. If Luis, Gabriela, or another coordinator approves/rejects/fulfills a match, the detail view should show that actor and the timestamp from the audit trail.

### 5. Stale Data

Previously useful records whose freshness window has expired or is about to expire.

### 6. Tool Directory

Crisis tools, links, maps, forms, and contact points with status and last checked time.

### 7. Audit And Sensitive Access

Access history for exact locations, private contacts, exports, status changes, and admin overrides.

## Queue Card

Every action item should fit in one compact card.

Required visible fields:

- record id
- record type: need, offer, resource, update, closure
- category group and detail
- short summary
- approximate public location
- exact location availability indicator: hidden unless authorized
- urgency: inferred or confirmed
- verification status
- public visibility status
- sensitivity flags
- age: time since report
- freshness deadline or stale status
- source type: WhatsApp text, voice, image, location, admin, import
- trust level at creation
- follow-up allowed: yes, no, unknown
- duplicate candidates count
- match candidates count
- match approval state: none, pending, approved, rejected, fulfilled, expired
- approval blocker when applicable
- current owner or unassigned
- recommended next action

Do not show raw phone numbers, exact locations, or full messages in the compact card by default.

## Match Card

Each match card should show:

- need code and short public-safe summary
- offer/resource code and short public-safe summary
- matched item(s), especially for partial matches
- location fit: same zone, nearby, unclear, or far
- transport fit: available, needed, unclear, or blocked
- verification state of each side
- blocking gap
- latest match action actor and time, if any
- next safe action

Quick actions:

- Approve for internal routing
- Reject
- Need transport
- Ask more info
- Assign owner
- Mark fulfilled

Do not show raw phone numbers, exact locations, or full messages in the match card by default.

## Card Detail Drawer

When a coordinator opens a card, show:

- original message/media references
- exact location if coordinator role allows access
- reporter contact action if follow-up is allowed
- related records and duplicate candidates
- match recommendations
- update history
- audit history
- internal notes
- public-safe summary preview

Exact location and private contact views must be audited.

## Quick Actions

Each card should support:

- Confirm
- Mark needs verification
- Ask reporter for more info
- Assign owner
- Route to logistics
- Route to center-of-acopio
- Route to connectivity
- Route to tools/equipment
- Mark possible duplicate
- Merge duplicate
- Apply update
- Reject update
- Approve match
- Reject match
- Mark stale
- Mark resolved
- Reject / invalid
- Approve public summary
- Keep private

The UI should only show actions allowed by the coordinator's role and the record's sensitivity flags.

In V1, trusted coordinators can approve/reject ordinary logistics/resource matches for internal routing. Admin approval remains required for public/export/official/sensitive actions.

## Filters

Minimum filters:

- status
- urgency
- category group
- category detail
- location text / zone
- age
- stale soon
- sensitivity flag
- source type
- owner
- follow-up allowed
- has duplicates
- has matches
- public visibility

## Sorting

Default sort:

1. Critical urgency.
2. Sensitive records requiring review.
3. Oldest unverified high/medium urgency.
4. Records with match candidates.
5. Stale soon.
6. Newest low-risk records.

Coordinators can switch to:

- newest first
- stale first
- by zone
- by category
- unassigned first

## WhatsApp Coordinator Commands

The console should have web/admin UI, but coordinators may also need WhatsApp commands.

Supported commands:

```text
RESUMEN
PENDIENTES
CRITICOS
VER REQ-184
ASIGNAR REQ-184 @logistica
PEDIR REQ-184 ubicación más precisa
CONFIRMAR REQ-184
STALE REQ-184
RESOLVER REQ-184
PRIVADO REQ-184
PUBLICAR RESUMEN REQ-184
```

Dangerous commands such as `CONFIRMAR`, `RESOLVER`, and `PUBLICAR` require role authorization and audit.

## What Coordinators Need Most

### Situation Snapshot

They need a current, compact snapshot:

- open critical items
- open needs by category/zone
- available offers/resources by category/zone
- stale or conflicting data
- active bottlenecks
- pending decisions

### Bottlenecks

The system should surface bottlenecks such as:

- many needs but no matching offers
- offers available but no transport
- resource exists but location cannot be shared
- match exists but coordinator approval is pending
- many unverified reports in one zone
- center reports capacity full
- tool/resource list stale

### Decision Support

The system should recommend, not decide:

- likely route
- likely duplicate
- likely match
- missing minimum field
- safety/privacy warning
- suggested public-safe summary

Every recommendation must link to source records.

## Public-Safe Summary Preview

Before publishing or forwarding, show exactly what will be visible:

```text
Agua: necesidad activa en Macuto, alta prioridad, pendiente por coordinación.
Última actualización: 14:32.
```

The preview must omit:

- exact location unless approved
- private phone
- private notes
- raw media
- sensitive inventory details

## Data Model Additions

### CoordinatorAction

- `id`
- `record_id`
- `action_type`
- `status`: `pending | completed | rejected | cancelled`
- `recommended_by_system`
- `assigned_to`
- `created_at`
- `completed_at`
- `source_evidence_ids`
- `audit_event_id`

Required match action types:

- `review_match`
- `approve_match_for_routing`
- `reject_match`

These actions are created from `MatchRecommendation` rows and must appear in the default action queue when pending.

Match action completion must write an audit event with actor and timestamp. The console should not rely only on current status fields because coordinators need to know who made the decision.

### OperationalBottleneck

- `id`
- `bottleneck_type`: `no_supply | no_transport | no_verifier | stale_data | sensitive_access | duplicate_cluster | capacity_full | unclear_owner`
- `summary`
- `category_group`
- `location_text`
- `related_record_ids`
- `severity`
- `recommended_action`
- `status`: `open | mitigated | resolved | rejected`
- `created_at`
- `updated_at`

### PublicSafeSummary

- `id`
- `record_id`
- `summary_text`
- `redacted_fields`
- `approved_by`
- `approved_at`
- `expires_at`

## Access Control

Role permissions should control:

- who can see exact locations
- who can see private reporter contact
- who can confirm
- who can close
- who can publish summaries
- who can export map data
- who can change roles

Until a final authority model exists, dangerous actions require admin override.

## Acceptance Criteria

- Coordinator can process a new record from queue card to route/verify/reject without reading raw chat first.
- Exact location/private contact access is hidden by default and audited when opened.
- Queue clearly separates unverified, confirmed, stale, and resolved records.
- The console surfaces duplicates, matches, and bottlenecks.
- Match cards expose partial overlap, nearby-zone fit, transport gap, and latest accountable actor.
- Public-safe summary preview exists before any sharing/export.
- WhatsApp commands provide at least summary and single-record lookup for coordinators on mobile.
