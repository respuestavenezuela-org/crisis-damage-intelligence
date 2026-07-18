# WhatsApp Crisis Ops Workflow Suite

These workflows describe the WhatsApp-first operational coordination system for the Venezuela earthquake response.

The suite is intentionally split into small recurring loops instead of one large "chatbot" workflow. The bot is the interface; the workflows are the operating system.

For implementation, start from [Frontera Crisis Ops Bot Spec](./frontera-crisis-ops-bot-spec.md).

## Workflows

1. [Frontera Crisis Ops Bot Spec](./frontera-crisis-ops-bot-spec.md)
2. [Rescue Operational Card](./rescue-operational-card.md)
3. [WhatsApp Resource Intake](./whatsapp-resource-intake.md)
4. [WhatsApp Resource Search](./whatsapp-resource-search.md)
5. [Resource Verification And Routing](./resource-verification-routing.md)
6. [Need Offer Matching](./need-offer-matching.md)
7. [Tool Directory Freshness](./tool-directory-freshness.md)
8. [Coordinator Handoff Digest](./coordinator-handoff-digest.md)
9. [WhatsApp Voice And Media Intake](./whatsapp-voice-media-intake.md)
10. [Verified Data Export To Public Map](./verified-data-export-to-public-map.md)
11. [Category Taxonomy And Progressive Disclosure](./category-taxonomy.md)
12. [Security Threat Model](./security-threat-model.md)
13. [Critical Or Life-Safety Intake](./critical-urgent-intake.md)
14. [WhatsApp Interaction Model](./whatsapp-interaction-model.md)
15. [Coordinator Operational Console](./coordinator-operational-console.md)
16. [Frontera Leverage Plan](./frontera-leverage-plan.md)
17. [V1 Data Model](./v1-data-model.md)
18. [WhatsApp Data Verification](./whatsapp-data-verification.md)
19. [WhatsApp Response Contract](./whatsapp-response-contract.md)
20. [Frontera Crisis Ops Implementation Gap Issues](./frontera-crisis-ops-implementation-gap-issues.md)

## Shared Principles

- WhatsApp is the primary operator interface.
- The public crisis map remains optional support, not the operational source of truth.
- Primary users for data entry and operations are coordinators, logistics operators, and center-of-acopio operators. Rescuers should receive concise outputs, not be expected to feed the system during active response.
- The WhatsApp number is open for intake: anyone with the number can submit reports. Permissions only tighten when the user tries to view sensitive details, confirm, route, export, or contact-match records.
- Anyone may submit an update against a record, but updates are append-only evidence until reviewed. Unknown users cannot directly close or overwrite records.
- Do not ask for reporter names by default. Use the WhatsApp number as private internal contact metadata and ask permission before follow-up.
- Exact submitted locations should be stored for operations, but secured as sensitive data. Public outputs use approximate zones unless explicitly approved.
- Category selection must use progressive disclosure: a small first-level menu, then subcategories only when needed.
- Every structured record must preserve source, timestamp, actor, and verification status.
- The system recommends, structures, and routes; humans verify high-impact information.
- Default statuses are conservative: `unverified`, `needs_verification`, `confirmed`, `stale`, `resolved`, `rejected`.
- Confirmation authority is a configurable governance policy, not a hard-coded assumption. Until named operators are defined, the implementation must support role/category rules and default to "no public confirmation without explicit admin approval."
- Assume some users may act maliciously. Accept reports with low friction, but keep new records private/unverified and restrict sensitive search results by default.
- Critical/life-safety reports are registered and escalated, but the bot must state this is a citizen information coordination effort, not an official emergency service and not a response guarantee.
- Rescue-person/building fichas are a separate high-risk workflow: private by default, redacted before sharing, and not public map data.
- Support both free text and menus. Free text is the fast path; menus are used when intent is unclear or the user asks for guidance.
- Battle-test the natural-language routing loop before investing in buttons: intake, match recommendation, coordinator approval, and safe route/response must work first.
- Bot replies should follow the WhatsApp Response Contract: one concrete, human-but-structured message by default; preserve context; split into multiple messages only when necessary for provider limits, safety, or unusually large context.
- Coordinators need an action queue, not a raw inbox: critical items, needs verification, duplicates, matches, stale data, sensitive access, and next safe action.
- Missing coordinator approval is a queue state, not an invisible blocker. A match that needs approval must create a visible `review_match` or `approve_match_for_routing` action.
- Trusted coordinators may approve ordinary logistics/resource records and matches for internal routing in V1. Admin approval remains required for public/export, role changes, official damage claims, medical/missing-person items, and other sensitive cases.
- Sensitive categories require human review before broad sharing: medical, missing persons, exact private locations, minors, security risks, public claims, official damage counts.
- The first implementation should leverage Frontera's WhatsApp webhook, message deduplication, conversation model, media handling, admin inbox, handoff state, templates, and sanitization.
- Frontera is the preferred WhatsApp/backoffice system of record. This static crisis map repo should consume only safe exports and must not depend on Frontera at public runtime.
- V1 scope is WhatsApp/Frontera intake and coordination only. Public map/static export is P1, not required for V1.
- WhatsApp data verification is P2/deferred. It may support manual verification later, but it must not delay routing volunteers, insumos, gasolina, maquinaria, or other resources to verified needs.
- Latest routing decision: V1 may remain open for review-only intake, but operational routing should be closed around a manually trusted roster until a coordinator validates the record/contact.

## Shared Data Objects

### OperationalRecord

- `id`
- `public_code`
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
- `urgency`: `low | medium | high | critical`
- `source_channel`: `whatsapp | admin | import | map | manual`
- `source_message_id`
- `source_actor_id`
- `source_actor_display`
- `source_phone_hash`
- `followup_allowed`: `unknown | yes | no`
- `source_timestamp`
- `verification_status`: `unverified | needs_verification | confirmed | stale | resolved | rejected`
- `verified_by`
- `verified_at`
- `last_confirmed_at`
- `expires_at`
- `public_visibility`: `private | coordinators_only | public_summary | public_map`
- `sensitivity_flags`
- `trust_level_at_creation`: `unknown | known_reporter | trusted_coordinator | admin`
- `related_record_ids`
- `notes_for_coordinators`

See [V1 Data Model](./v1-data-model.md) for the full Frontera-side domain model.

### ToolDirectoryEntry

- `id`
- `name`
- `purpose`
- `audience`
- `url_or_contact`
- `owner_name`
- `owner_contact_private`
- `status`: `active | degraded | stale | down | unknown`
- `last_checked_at`
- `last_checked_by`
- `freshness_interval_hours`
- `public_summary`
- `internal_notes`

### CoordinatorBrief

- `id`
- `brief_type`
- `timeframe_start`
- `timeframe_end`
- `summary`
- `critical_items`
- `new_items`
- `resolved_items`
- `stale_items`
- `recommended_actions`
- `source_record_ids`
- `created_at`

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
