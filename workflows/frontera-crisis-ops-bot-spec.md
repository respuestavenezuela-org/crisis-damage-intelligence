# Frontera Crisis Ops Bot Spec

## Status

Implementable V1 workflow spec.

This spec consolidates the WhatsApp crisis coordination workflows into one build plan for Frontera.

## Product Summary

Build a WhatsApp-first crisis coordination bot inside Frontera.

The bot helps collect and coordinate logistics information during the Venezuela earthquake response. It is not a public map, not an official emergency service, and not a generic chatbot.

It receives WhatsApp messages from anyone, converts them into structured operational records, keeps sensitive details private, and gives coordinators a fast action queue for verification, routing, matching, and closure.

## V1 Scope

V1 runs inside Frontera only:

- WhatsApp intake.
- Conversation/message provenance.
- Crisis ops records.
- Coordinator action queue.
- Sensitive data controls.
- Basic matching.
- Coordinator match approval for internal routing.
- Tool/resource directory freshness.
- WhatsApp/admin responses.

No public map export is required for V1.

Map/static export is P1 after:

- confirmed records exist
- publication policy exists
- authority model exists
- redaction rules are validated

## V1 Battle-Test Gate

Do not expand into buttons, public export, or WhatsApp damage/data verification until this core loop works end to end:

1. A trusted or unknown user sends a natural-language WhatsApp message with a need or offer.
2. Frontera stores the raw message and creates one structured `OperationalRecord`.
3. The system creates explainable `MatchRecommendation` candidates against compatible needs/offers/resources.
4. If a match needs approval, the admin console shows a visible `CoordinatorAction(action_type=review_match)` or `approve_match_for_routing`; the match is not hidden or silently dropped.
5. A trusted coordinator can approve or reject an ordinary logistics/resource match for internal routing.
6. The bot sends only safe status copy unless a coordinator explicitly shares private details.
7. The bot reply follows the one-message-by-default [WhatsApp Response Contract](./whatsapp-response-contract.md): code, interpreted item, zone, status, coordination/privacy note, and one next action.

Buttons/menus remain a convenience layer after the natural-language loop passes this gate.

WhatsApp verification of existing map/data records is P2 and documented separately in [WhatsApp Data Verification](./whatsapp-data-verification.md).

## System Boundary

```text
WhatsApp
  -> Frontera WhatsApp webhook/backoffice
  -> Crisis Ops domain records
  -> Coordinator verification/routing/matching
  -> P1 optional static export
  -> Crisis public map
```

The public crisis map must not require Frontera at runtime.

## Existing Frontera Capabilities To Reuse

Reuse Frontera instead of building a new WhatsApp/backend stack.

Relevant files:

- `frontera/backend/app/api/routes/whatsapp.py`
- `frontera/backend/app/services/whatsapp.py`
- `frontera/backend/app/services/whatsapp_ops.py`
- `frontera/backend/app/services/chat.py`
- `frontera/backend/app/models/db.py`
- `frontera/frontend/src/app/admin/conversations/page.tsx`
- `frontera/frontend/src/app/portal/bots/page.tsx`
- `frontera/frontend/src/app/portal/bots/[slug]/channels/page.tsx`
- `frontera/frontend/src/app/portal/bots/[slug]/knowledge/page.tsx`

Reuse:

- WhatsApp webhook verification and inbound parsing.
- Message/status deduplication.
- Conversation continuity by phone number.
- Media handling.
- Outbound sanitization.
- 24-hour session/template behavior.
- Bot/channel model.
- Conversation/message storage.
- Admin inbox patterns.
- Handoff/takeover state.
- Health checks.

Replace commercial semantics:

| Frontera | Crisis Ops |
| --- | --- |
| Lead | OperationalRecord / CrisisContact |
| Lead score | urgency / risk / freshness |
| Sales qualification | resource/need classification |
| Appointment/demo | coordinator routing |
| Commercial KB | tool/resource directory |
| Sales handoff | logistics/coordinator handoff |

## Primary Users

Primary V1 users:

- coordinators
- logistics operators
- center-of-acopio operators
- trusted remote coordinators

Secondary/downstream users:

- rescatistas/topos
- volunteers
- general public reporters

Rescuers should not be expected to feed the system during active operations. They may receive concise summaries forwarded by coordinators.

## Access Principle

The WhatsApp number is open for intake.

Anyone with the number can:

- report a need
- report an offer
- submit an update
- send voice/image/location/document evidence
- ask broad questions

Unknown users cannot:

- see exact sensitive locations
- see private phone/contact details
- confirm records
- close records directly
- publish records
- export records
- connect requester/provider directly

Trusted coordinators can approve ordinary logistics/resource records and matches for internal routing. That approval does not authorize public export, official damage claims, medical/missing-person handling, or broad sharing of sensitive details.

## Safety Principle

Accept reports easily. Share information carefully.

All new records default to:

- `verification_status=unverified`
- `public_visibility=private`
- exact submitted location as `location_access_level=private_sensitive`
- `trust_level_at_creation=unknown` unless sender is already known

## V1 Data Model

Reuse existing Frontera tables for provenance:

- `Organization`
- `Bot`
- `BotChannel`
- `Conversation`
- `Message`
- `WhatsAppWebhookEvent`
- existing admin/user model

Add seven V1 domain tables.

### CrisisContact

Purpose: represent a WhatsApp sender or authorized coordinator without asking for a name by default.

Fields:

- `id`
- `organization_id`
- `bot_id`
- `phone_hash`
- `phone_encrypted` or provider-native private phone reference
- `display_label`
- `trust_level`: `unknown | known_reporter | trusted_coordinator | admin`
- `role`: `reporter | coordinator | admin | blocked`
- `followup_allowed`: `unknown | yes | no`
- `is_blocked`
- `blocked_reason`
- `first_seen_at`
- `last_seen_at`
- `created_at`
- `updated_at`

Rules:

- Do not ask for reporter name by default.
- Raw phone must never appear in public views/exports.
- Unknown contacts can submit records but cannot confirm, close, publish, or access private details.

### OperationalRecord

Purpose: canonical current state for a need, offer, resource, tool, update target, or closure target.

Fields:

- `id`
- `public_code`, such as `REQ-184`, `OFF-057`, `RES-022`
- `organization_id`
- `bot_id`
- `conversation_id`
- `source_message_id`
- `created_by_contact_id`
- `record_type`: `need | offer | resource | tool | update | closure`
- `category_group`: `water_food | supplies | transport | tools_equipment | connectivity_energy | support_point | other`
- `category_detail`
- `raw_category_text`
- `category_confidence`: `low | medium | high`
- `title`
- `description`
- `location_text`
- `location_lat`
- `location_lng`
- `location_precision`: `exact | approximate | reference_only | unknown`
- `location_access_level`: `private_sensitive | coordinators_only | approved_public_approximate | approved_public_exact`
- `public_location_text`
- `quantity`
- `unit`
- `urgency`: `low | medium | high | critical | unknown`
- `urgency_source`: `inferred | reporter | coordinator`
- `verification_status`: `unverified | needs_verification | confirmed | stale | resolved | rejected | duplicate`
- `confirmation_scope`: `none | internal_routing | public_summary | public_map | official_claim`
- `public_visibility`: `private | coordinators_only | public_summary | public_map`
- `sensitivity_flags`: JSON/list
- `followup_allowed`: `unknown | yes | no`
- `trust_level_at_creation`: `unknown | known_reporter | trusted_coordinator | admin`
- `owner_user_id`
- `owner_contact_id`
- `related_record_ids`: JSON/list
- `duplicate_of_record_id`
- `last_confirmed_at`
- `expires_at`
- `created_at`
- `updated_at`

Rules:

- New records are private and unverified.
- Canonical fields are changed only by authorized coordinator/admin actions or approved updates.
- Exact location is stored for operations but hidden and audited.
- In V1, `confirmed` plus `confirmation_scope=internal_routing` means a trusted coordinator has accepted the record for logistics routing. It is not an official public claim.

### OperationalEvent

Purpose: append-only timeline for every meaningful report/change.

Fields:

- `id`
- `organization_id`
- `bot_id`
- `record_id`
- `conversation_id`
- `source_message_id`
- `created_by_contact_id`
- `event_type`: `initial_report | update_suggestion | closure_suggestion | status_change | verification | routing | note | duplicate_link | match_action | system_extraction`
- `event_status`: `pending | applied | rejected | informational`
- `summary`
- `raw_text`
- `parsed_json`
- `previous_values_json`
- `proposed_values_json`
- `applied_by_user_id`
- `applied_by_contact_id`
- `applied_at`
- `rejected_reason`
- `created_at`

Rules:

- Unknown users can create update and closure suggestions.
- Unknown-user events do not overwrite canonical fields until reviewed.
- Every status change creates an event.

### CoordinatorAction

Purpose: queue item for human action.

Fields:

- `id`
- `organization_id`
- `bot_id`
- `record_id`
- `event_id`
- `action_type`: `verify | ask_more_info | route | apply_update | reject_update | review_closure | mark_duplicate | review_match | approve_match_for_routing | reject_match | confirm | mark_stale | resolve | reject | approve_public_summary | sensitive_review`
- `status`: `pending | in_progress | completed | rejected | cancelled`
- `priority`: `low | medium | high | critical`
- `recommended_by_system`
- `recommended_reason`
- `assigned_user_id`
- `assigned_contact_id`
- `due_at`
- `completed_by_user_id`
- `completed_at`
- `created_at`
- `updated_at`

Rules:

- New critical/sensitive/unverified records create actions.
- Dangerous actions require role authorization.
- Ordinary logistics `review_match`, `approve_match_for_routing`, and internal-routing confirmation may be available to `trusted_coordinator`.
- Public/export/official/sensitive actions require `admin` or a configured stronger role.
- Completed actions write an `OperationalEvent`.

### MatchRecommendation

Purpose: candidate connection between need and offer/resource.

Fields:

- `id`
- `organization_id`
- `bot_id`
- `need_record_id`
- `offer_or_resource_record_id`
- `match_score`
- `match_status`: `candidate | approved | rejected | fulfilled | expired`
- `category_fit`: `exact | group | weak | none`
- `location_fit`: `same_zone | nearby | unclear | far`
- `quantity_fit`: `full | partial | unknown | insufficient`
- `time_fit`: `current | stale_soon | stale | unknown`
- `blocking_gap`: `none | no_transport | contact_restricted | location_restricted | stale_offer | stale_need | quantity_unclear | needs_verification | coordinator_approval_pending`
- `risk_level`: `low | medium | high | critical`
- `recommendation`
- `approval_required_reason`
- `coordinator_action_id`
- `approved_by_user_id`
- `approved_at`
- `created_at`
- `updated_at`

Rules:

- Never auto-share private contacts/locations.
- Approved matches create coordinator actions/events.
- A candidate match must be visible in the coordinator queue even when one or both records are still `needs_verification`.
- Lack of coordinator approval is represented as `match_status=candidate`, `approval_required_reason`, and a pending `CoordinatorAction`; it is not treated as "no match".

### ToolDirectoryEntry

Purpose: current status of tools, links, maps, forms, contact points, and resource lists.

Fields:

- `id`
- `organization_id`
- `bot_id`
- `name`
- `purpose`
- `audience`: `coordinators | logistics | centers | rescuers | public | mixed`
- `category`: `rescue_support | logistics | supplies | map | connectivity | shelter | volunteer_coordination | official_source | external_reference | other`
- `url_or_contact_private`
- `public_url_or_summary`
- `owner_contact_id`
- `status`: `active | degraded | stale | down | unknown`
- `last_checked_at`
- `last_checked_by_user_id`
- `freshness_interval_hours`
- `sensitivity_flags`: JSON/list
- `internal_notes`
- `created_at`
- `updated_at`

Rules:

- New submitted tools default to `unknown`.
- Tools are not official unless marked by an authorized human.
- Stale tools are not presented as current.

### SensitiveAccessAudit

Purpose: audit access to sensitive fields.

Fields:

- `id`
- `organization_id`
- `bot_id`
- `actor_user_id`
- `actor_contact_id`
- `record_id`
- `event_id`
- `sensitive_type`: `exact_location | private_phone | private_contact | raw_media | private_notes | export | admin_override`
- `action`: `view | share | export | approve | deny`
- `reason`
- `target_surface`: `admin_ui | whatsapp | export | api | system`
- `created_at`

Rules:

- Viewing exact location or private contact creates audit row.
- Exporting sensitive data creates audit row.
- Admin overrides create audit row.

## Not V1

Do not build in V1:

- public map export
- WhatsApp verification of existing map/data records
- menu/button-first interaction before natural language works
- full authority/policy engine
- missing persons case management
- medical case management
- public publishing workflow
- autonomous assignment
- raw rescue dispatch promises
- separate WhatsApp backend
- separate admin inbox outside Frontera
- `OperationalBottleneck` table
- `PublicSafeSummary` table

Compute bottlenecks from records/actions/matches first. Public summaries are P1.

## Category UX

Use broad categories first, then subcategories only when needed.

First-level categories:

1. Agua/comida
2. Insumos
3. Transporte
4. Herramientas/equipos
5. Conectividad/energía
6. Centro o punto de apoyo
7. Otro

Example subcategories:

- Transporte: ambulancia, traslado de personas, traslado de insumos, camión/carga, combustible/gasoil, maquinaria pesada, otro.
- Insumos: médicos, construcción, higiene, limpieza/desinfección, ropa/mantas, protección personal, otro.
- Conectividad/energía: Starlink, Wi-Fi/internet, punto de carga, planta eléctrica, baterías/power banks, radios/comunicación, otro.

Rules:

- Do not show a long category list on the first screen.
- Free text always works.
- If the message is specific enough, classify automatically.
- Category uncertainty must not block record creation.

## WhatsApp Interaction Model

Support both free text and menus.

Free text is the fast path:

```text
NECESITO agua en Macuto
OFREZCO comida en Altamira
BUSCAR gasoil La Guaira
Hay Starlink abierto cerca de...
```

Menu appears only when useful:

```text
¿Qué quieres hacer?
1. Reportar necesidad
2. Reportar oferta/recurso
3. Buscar recurso
4. Actualizar caso
5. Marcar como resuelto
6. Ver herramientas útiles
```

Rules:

- Do not show menu after every message.
- Keep menus short.
- Numbered replies preferred.
- User can switch to natural language anytime.
- Bot must preserve already provided information during follow-ups.
- If the natural-language parser can create a usable record, do not force the user through buttons.

## Minimum Intake

To create a record, only require:

1. what is needed/offered
2. where it is

If need vs offer is unclear, ask:

```text
¿Esto es una necesidad o una oferta?
1. Necesidad
2. Oferta
```

Quantity, urgency, contact, photos, and details are optional.

If the user stops responding, create a partial `needs_verification` record.

## Contact Policy

Do not ask for reporter name by default.

Use WhatsApp number as private internal contact metadata.

Ask follow-up consent only when needed:

```text
¿Coordinación puede contactarte por este WhatsApp si hace falta aclarar algo?
1. Sí
2. No
```

Never expose reporter phone numbers in:

- public search
- public summaries
- broad coordinator digest
- map export

## Exact Location Policy

Exact locations may be stored because they can be operationally necessary.

Store as:

- `location_precision=exact`
- `location_access_level=private_sensitive`
- `public_visibility=private`

Public/broad outputs use approximate `public_location_text`, such as:

- Macuto
- La Guaira
- cerca de Altamira

Exact locations:

- hidden by default
- role-restricted
- audited on view/share/export
- never shown to unknown users
- never exported unless explicitly approved as `approved_public_exact`

Bot response to location pin:

```text
Recibí la ubicación. La guardo como dato privado para coordinación.
```

## Updates And Closures

Anyone can submit an update:

```text
ACTUALIZAR REQ-184 ya llegó un camión de agua
```

System behavior:

- create `OperationalEvent(event_type=update_suggestion, event_status=pending)`
- link to target record
- do not overwrite canonical record until reviewed

Anyone can suggest closure:

```text
RESUELTO REQ-184
```

If sender is not authorized:

```text
Recibido como actualización pendiente para REQ-184. Coordinación revisará antes de cerrar el caso.
```

Only authorized roles can directly change to:

- `resolved`
- `rejected`
- `duplicate`
- `stale`
- `confirmed`

## Critical / Life-Safety Intake

When a message appears urgent or life-safety related:

1. Create record immediately even if incomplete.
2. Set `urgency=critical`.
3. Add sensitivity flags.
4. Keep private.
5. Create critical `CoordinatorAction`.
6. Reply with citizen-effort disclaimer.

Required copy:

```text
Recibido. Lo registré como urgente para coordinación.

Importante: esto es un esfuerzo ciudadano de organización de información, no un servicio oficial de emergencia ni garantiza respuesta.

Código: REQ-184.
```

The bot must not:

- promise rescue
- claim official status
- say someone is on the way unless entered by authorized human
- publish critical reports by default
- diagnose medical conditions
- certify deaths/injuries

## Search Behavior

Unknown users may search, but receive only safe, broad, public-summary information.

Sensitive result response:

```text
Hay información relacionada, pero no puedo compartir detalles por aquí.
Dejo tu solicitud para coordinación. Código: REQ-184.
```

High-value resource response:

```text
Puedo registrar la necesidad de gasoil, pero la ubicación de recursos de combustible solo se comparte por coordinación verificada.
```

Never return to unknown users:

- private phone/contact
- exact locations
- fuel inventories
- Starlink exact locations
- tool/equipment inventories
- medical supplies details
- private notes
- raw media

## Coordinator Console

Build or adapt Frontera admin UI into an action queue, not a raw inbox.

Default sections:

- Critical / life-safety
- Needs verification
- Possible duplicate
- Possible match
- Needs routing
- Stale / reconfirm
- Pending closure
- Sensitive / restricted

Queue card fields:

- public code
- record type
- category group/detail
- short summary
- approximate public location
- exact location indicator, hidden unless authorized
- urgency
- verification status
- public visibility
- sensitivity flags
- age since report
- freshness/stale status
- source type
- trust level at creation
- follow-up allowed
- duplicate candidate count
- match candidate count
- current owner
- recommended next action

Do not show raw phone, exact location, or full message in compact card by default.

Detail drawer:

- original message/media references
- exact location if authorized
- reporter contact action if follow-up allowed
- related records
- duplicate candidates
- match recommendations
- update history
- audit history
- internal notes
- public-safe preview, P1/public export only

Quick actions:

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
- Keep private

Dangerous actions require role authorization and audit.

## Coordinator WhatsApp Commands

Support later in V1 if easy, otherwise V1.1.

Commands:

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
```

Dangerous commands require authorization and audit.

## Matching

On new or updated needs/offers/resources:

1. Compare category group/detail.
2. Compare location/zone.
3. Compare quantity if known.
4. Compare freshness.
5. Check sensitivity/privacy constraints.
6. Create `MatchRecommendation`.

Do not expose private contacts or exact locations automatically.

Match recommendation example:

```text
Possible match

Need: REQ-184 agua para 40 personas en Macuto
Offer: OFF-057 agua disponible en La Guaira hasta 18:00
Fit: high
Risk: medium
Blocking gap: transport not confirmed

Recommended action:
Contact logistics coordinator to confirm transport before sharing details.
```

## Tool Directory

Support `HERRAMIENTAS` and current tool/resource listing.

Tool states:

- `active`
- `degraded`
- `stale`
- `down`
- `unknown`

New submitted tools default to `unknown`.

Freshness matters. Stale tools must not be presented as current.

Example:

```text
HERRAMIENTAS topos
```

Response should include only tools safe to share and marked active/recent.

## Role Model V1

Use simple roles:

- `unknown`
- `known_reporter`
- `trusted_coordinator`
- `admin`

Capabilities:

| Capability | unknown | known_reporter | trusted_coordinator | admin |
| --- | --- | --- | --- | --- |
| submit report | yes | yes | yes | yes |
| submit update | yes | yes | yes | yes |
| search broad info | yes | yes | yes | yes |
| see private contact | no | no | role-gated | yes |
| see exact location | no | no | role-gated + audit | yes + audit |
| confirm | no | no | maybe/TBD | yes |
| close directly | no | no | maybe/TBD | yes |
| publish/export | no | no | no/TBD | yes |
| change roles | no | no | no | yes |

Confirmation authority remains TBD. Until configured, dangerous actions require admin override.

## Audit Requirements

Audit:

- status changes
- visibility changes
- confirmations
- accepted/rejected updates
- accepted/rejected closures
- exact location access
- private contact access
- exports
- admin overrides
- match approval
- role changes

## Deterministic Parser Before LLM

Implement deterministic rules first. Use LLM only as optional classifier/summarizer.

Detect:

- `NECESITO`
- `OFREZCO`
- `TENGO`
- `BUSCO`
- `ACTUALIZAR`
- `RESUELTO`
- `HERRAMIENTAS`
- critical/life-safety phrases
- categories/subcategories
- locations
- quantities
- possible duplicate references

If LLM is unavailable, V1 should still work for core commands.

## Implementation Order

1. Create Crisis Ops bot/template in Frontera.
2. Add V1 data model/migrations.
3. Add deterministic WhatsApp crisis parser.
4. Create `CrisisContact` on inbound messages.
5. Create `OperationalRecord` and `OperationalEvent` from text intake.
6. Add privacy defaults and sensitive location/contact handling.
7. Add coordinator action queue.
8. Add update/closure suggestion behavior.
9. Add critical/life-safety escalation copy.
10. Add basic match recommendations.
11. Add tool directory entries and `HERRAMIENTAS` response.
12. Add sensitive access audit hooks.
13. Add admin UI cards/detail drawer.
14. Add tests with mocked WhatsApp payloads.

P1:

- static export to crisis map
- public-safe summary approval flow
- configurable authority policy
- richer bottleneck detection
- coordinator WhatsApp command set

## Test Cases

### Intake

- `NECESITO agua en Macuto` creates `OperationalRecord(record_type=need)`.
- `OFREZCO comida en Altamira` creates `OperationalRecord(record_type=offer)`.
- Unknown reporter does not need to provide name.
- Missing location creates partial record and asks location.

### Privacy

- New records are private/unverified.
- Location pin stores exact location as `private_sensitive`.
- Unknown user cannot retrieve exact location.
- Viewing exact location creates `SensitiveAccessAudit`.

### Updates

- `ACTUALIZAR REQ-184 ...` creates pending `OperationalEvent`.
- Unknown `RESUELTO REQ-184` creates closure suggestion, not state change.

### Critical

- Critical language sets `urgency=critical`.
- Bot returns citizen-effort disclaimer.
- Critical record creates `CoordinatorAction(priority=critical)`.

### Matching

- Need and offer in same category/zone create `MatchRecommendation`.
- Private details are not shared automatically.

### Coordinator

- Unverified record appears in action queue.
- Coordinator can apply/reject update.
- Dangerous actions require authorization.

## Acceptance Criteria

V1 is done when:

- Existing Frontera WhatsApp webhook creates crisis records.
- Every crisis record links back to source conversation/message.
- Anyone can submit via WhatsApp number.
- No reporter name is required.
- Contact and exact location are private by default.
- Unknown users cannot access sensitive details.
- Critical reports are registered/escalated with citizen-effort disclaimer.
- Updates and closures from unknown users are append-only pending review.
- Coordinators can work from an action queue.
- Matching recommendations exist but do not auto-share private details.
- Sensitive access is audited.
- Public map/export is not required.
