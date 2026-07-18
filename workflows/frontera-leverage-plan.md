# Frontera Leverage Plan

## Decision

Build the WhatsApp crisis coordination MVP by leveraging existing Frontera capabilities instead of creating a new bot/backoffice from scratch.

Frontera should be the WhatsApp and operations system of record. This crisis map repo should remain a static-first public viewer that can optionally consume redacted, verified exports.

## System Boundary

```text
WhatsApp
  -> Frontera WhatsApp webhook/backoffice
  -> Crisis Ops domain records
  -> Coordinator verification/routing
  -> Optional static export
  -> Crisis map public app
```

The public map must not require Frontera at runtime.

V1 does not need to export to the public map. The export path is P1 after there are confirmed records and a publication policy.

## Reuse From Frontera

### Backend

Reuse:

- WhatsApp webhook verification and inbound processing.
- Message/status deduplication.
- Conversation continuity by phone number.
- WhatsApp media handling.
- Outbound sanitization.
- 24-hour session window/template handling.
- Bot/channel model.
- Knowledge base model.
- Conversation/message persistence.
- Admin conversation inbox patterns.
- Handoff/takeover state.
- Health checks.

Known Frontera files to leverage:

- `frontera/backend/app/api/routes/whatsapp.py`
- `frontera/backend/app/services/whatsapp.py`
- `frontera/backend/app/services/whatsapp_ops.py`
- `frontera/backend/app/services/chat.py`
- `frontera/backend/app/models/db.py`

### Frontend/Admin

Reuse:

- bot/channel configuration UI patterns
- knowledge management UI patterns
- admin conversations page
- handoff/takeover workflow

Known Frontera files to leverage:

- `frontera/frontend/src/app/portal/bots/page.tsx`
- `frontera/frontend/src/app/portal/bots/[slug]/channels/page.tsx`
- `frontera/frontend/src/app/portal/bots/[slug]/knowledge/page.tsx`
- `frontera/frontend/src/app/admin/conversations/page.tsx`

## Replace Or Add

Replace commercial bot concepts with crisis ops concepts:

| Frontera Concept | Crisis Ops Concept |
| --- | --- |
| lead | operational record / reporter |
| lead score | urgency/risk/freshness |
| sales qualification | resource/need classification |
| appointment/demo | coordinator routing |
| commercial KB | tool/resource directory |
| sales handoff | logistics/coordinator handoff |
| customer conversation | reporter/coordinator conversation |

Add domain models:

- `CrisisContact`
- `OperationalRecord`
- `OperationalEvent`
- `CoordinatorAction`
- `MatchRecommendation`
- `ToolDirectoryEntry`
- `SensitiveAccessAudit`

Reuse existing `Conversation`, `Message`, and `WhatsAppWebhookEvent` as provenance/source objects.

Do not add `OperationalBottleneck` or `PublicSafeSummary` as V1 tables. Compute bottlenecks from records/actions/matches first; public summaries are P1 with map/export.

## MVP Architecture

### Frontera Crisis Ops Bot

Create a Crisis Ops bot/template inside Frontera with:

- Spanish-first prompts/copy.
- Free-text + menu interaction.
- Progressive category taxonomy.
- Minimal intake: what and where.
- Open intake from any WhatsApp number.
- Private/unverified default status.
- No reporter name by default.
- Follow-up consent.
- Sensitive location/contact controls.
- Critical citizen-effort disclaimer.

### Crisis Ops Admin Queue

Add or adapt admin UI to show:

- critical records
- needs verification
- possible duplicates
- possible matches
- stale data
- pending closure suggestions
- sensitive restricted records
- bottlenecks

### Static Export To Map

P1 only, not required for V1.

Export only safe records:

- confirmed or approved public summary
- redacted location by default
- no phone numbers
- no private notes
- no raw WhatsApp messages
- no exact location unless explicitly approved

Potential exports:

- `public/data/ops/resources.json`
- `public/data/ops/tools.json`
- `public/data/ops/status.json`

The export can be copied or pulled into this repo as static data.

## What Not To Build In This Repo

Do not build the WhatsApp webhook, admin inbox, conversation storage, or coordinator backend inside the public map app unless Frontera is unavailable.

This repo should only receive:

- workflow specs
- public/static data schema if needed
- map UI for redacted exports if needed
- documentation of safety boundaries

## Implementation Order

1. Create Crisis Ops bot/template in Frontera.
2. Add V1 crisis domain models from [V1 Data Model](./v1-data-model.md) while keeping existing message/conversation provenance.
3. Implement WhatsApp intake parser and deterministic rules before LLM behavior.
4. Add coordinator action queue.
5. Add sensitive access controls and audit.
6. P1: Add static export job after publication policy exists.
7. P1: Add optional map ingestion of exported public-safe JSON.

## Acceptance Criteria

- No duplicate WhatsApp webhook is built in this repo.
- A WhatsApp message can create an `OperationalRecord` in Frontera.
- Original `Conversation` and `Message` remain linked as evidence.
- Unknown users can submit reports but cannot see sensitive details.
- Coordinators can verify/route from an admin queue.
- Public map can consume static exports without runtime Frontera dependency.
- V1 works without any public map export.
