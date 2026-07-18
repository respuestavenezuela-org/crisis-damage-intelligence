# V1 Data Model

## Decision

V1 should add a small crisis-ops domain model inside Frontera while reusing Frontera's existing WhatsApp/conversation infrastructure.

Do not create a separate backend or duplicate WhatsApp message storage.

## Reused Frontera Tables

Use existing Frontera concepts as source/provenance:

- `Organization`
- `Bot`
- `BotChannel`
- `Conversation`
- `Message`
- `WhatsAppWebhookEvent`
- existing admin/user model

Inbound WhatsApp messages remain the raw evidence. Crisis ops records point back to `Conversation`, `Message`, and webhook event ids.

## New V1 Tables

V1 needs seven new domain tables.

### 1. CrisisContact

Represents a WhatsApp sender or authorized coordinator without asking for a name by default.

Purpose:

- track trust/role by phone number
- allow open intake while restricting privileged actions
- store follow-up permission
- support coordinator WhatsApp commands later

Fields:

- `id`
- `organization_id`
- `bot_id`
- `phone_hash`
- `phone_encrypted` or provider-native private phone reference
- `display_label`: optional internal label, not required from reporter
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

- Do not ask for name by default.
- Raw phone must never appear in public views/exports.
- Unknown contacts can submit records but cannot confirm, close, publish, or access private details.

### 2. OperationalRecord

Canonical current state for a need, offer, resource, tool, update target, or closure target.

Purpose:

- one row per operational thing coordinators may act on
- safe current state for queue, search, matching, and handoff

Fields:

- `id`
- `public_code`: human-readable code such as `REQ-184`, `OFF-057`, `RES-022`
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

- New records default to `unverified`, `private`, and `private_sensitive` for exact submitted locations.
- Exact location exists for operations but is hidden and audited.
- Canonical fields are changed only by authorized coordinator/admin actions or approved updates.
- In V1, trusted coordinators may set `verification_status=confirmed` with `confirmation_scope=internal_routing` for ordinary logistics/resource records. This does not authorize public export or official claims.

### 3. OperationalEvent

Append-only timeline for every meaningful change or report related to an operational record.

Purpose:

- preserve updates without overwriting canonical state
- support pending closure suggestions
- provide audit trail and source provenance
- allow coordinators to accept/reject updates

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

- Unknown users can create `update_suggestion` and `closure_suggestion`.
- Unknown-user events do not overwrite canonical `OperationalRecord` fields until reviewed.
- Every status change should create an `OperationalEvent`.

### 4. CoordinatorAction

Work queue item for a coordinator.

Purpose:

- power the action queue
- avoid raw inbox triage
- track ownership, pending decisions, and next safe action

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

- New critical/sensitive/unverified items should create coordinator actions.
- Dangerous actions require role authorization.
- Completed actions should write an `OperationalEvent`.
- Match candidates requiring approval create `review_match` or `approve_match_for_routing` actions.
- Lack of approval is represented by a pending action, not by suppressing the match.

### 5. MatchRecommendation

Candidate connection between a need and an offer/resource.

Purpose:

- help coordinators connect demand and supply without auto-sharing private details
- keep match review auditable

Fields:

- `id`
- `organization_id`
- `bot_id`
- `need_record_id`
- `offer_or_resource_record_id`
- optional `transport_record_id`
- `matched_items`: JSON/list of user-facing item strings that caused the match
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
- `last_decision_by_user_id`
- `last_decision_at`
- `created_at`
- `updated_at`

Rules:

- Match recommendations do not share private contacts/locations automatically.
- Approved, rejected, fulfilled, expired, and contact/connection actions create auditable `OperationalEvent(event_type=match_action)` entries.
- Candidate matches may exist before both records are fully confirmed, but they remain blocked by `needs_verification` and coordinator approval.
- Candidate matches must be visible in the admin queue.
- Partial matches and nearby-zone matches are valid candidates when clearly labeled for coordinator review.
- Transport can be linked directly or represented as a blocking gap; do not hide useful need/offer matches solely because transport is missing.

### 6. ToolDirectoryEntry

Current status of useful tools, forms, maps, contact points, and resource lists.

Purpose:

- answer "which tools/resources are actually current?"
- avoid sending stale links to coordinators or field teams

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
- Tools are not called official unless an authorized human marks them so.
- Stale tools should not be presented as current.

### 7. SensitiveAccessAudit

Audit trail for access to sensitive fields.

Purpose:

- protect exact locations, raw phone/contact data, private notes, media, and exports
- support "cover our backs and protect people"

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

- Viewing exact location or private contact creates an audit row.
- Exporting sensitive data creates an audit row.
- Admin overrides create audit rows.

## Not V1

Do not add separate tables for these in V1:

- `OperationalBottleneck`: compute from records/actions/matches first.
- `PublicSafeSummary`: generate on demand or store in `OperationalEvent` until P1 export exists.
- Full role/authority policy engine: start with simple roles and make it configurable later.
- Public map export tables: P1.
- Missing persons or medical case management: out of scope without a separate safety design.

## Minimal V1 Creation Flow

1. Inbound WhatsApp message arrives through existing Frontera webhook.
2. Existing Frontera stores `Conversation`, `Message`, and `WhatsAppWebhookEvent`.
3. Crisis parser creates or updates `CrisisContact`.
4. Parser creates `OperationalRecord`.
5. Parser creates `OperationalEvent` linked to source message.
6. If review is needed, create `CoordinatorAction`.
7. If a compatible need/offer exists, create `MatchRecommendation`.
8. If a match requires approval, create `CoordinatorAction(action_type=review_match)` or `approve_match_for_routing`.
9. If a coordinator changes a match status, create `OperationalEvent(event_type=match_action)` with actor, previous status, new status, and linked records.
10. If exact location/contact is viewed later, create `SensitiveAccessAudit`.

## Acceptance Criteria

- Every `OperationalRecord` links back to original Frontera message evidence.
- Unknown WhatsApp users can create records without names.
- Updates and closures are append-only until reviewed.
- Exact location and raw phone/contact access are audited.
- Coordinator queue can be built from `CoordinatorAction`.
- Need/offer matching can be reviewed without exposing private details automatically.
- Candidate matches needing approval appear in the coordinator queue.
- Every match decision can answer who did it and when.
- Tool freshness can be tracked without building a separate app.
