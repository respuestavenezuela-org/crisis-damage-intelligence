# Frontera Crisis Ops Implementation Gap Issues

## Loop

Every time transcript/product intent is compared against the current Frontera crisis-ops implementation before coding.

## Goal

Keep the implementation backlog concrete enough that an implementer can build the missing crisis-ops workflow pieces without re-litigating the product intent.

## Source Context

The July 2 transcript clarified five product requirements:

- Matching is coordinator-reviewed candidate generation, not autonomous routing.
- A partial useful overlap should surface: if a need asks for water and machetes, an offer with only machetes may still be useful.
- Nearby zones should be shown as possible matches when operationally close enough for transport.
- Transport is a first-class routing bottleneck, not just another offer category.
- The system must keep an audit trail of who matched, approved, rejected, connected, fulfilled, or reassigned each case.

## Current Implementation Summary

Observed in the separate `frontera` repository on July 2, 2026:

- Crisis contact roles, trust levels, action assignment, sensitive access audit, records, events, and match tables exist.
- Unknown WhatsApp senders can create private/unverified operational records.
- Coordinator WhatsApp commands are restricted to trusted coordinator/admin contacts.
- `MatchRecommendation` rows are created for same `category_group` need/offer/resource pairs.
- Admin API can change a match status to `approved`, `rejected`, `fulfilled`, or `expired`.
- Approval stores `approved_by_user_id` and writes one `OperationalEvent(event_type=match_action)`.
- Rejected/fulfilled/expired match transitions are not clearly audited as actor events.
- Candidate matches do not create required `CoordinatorAction(action_type=review_match)` or `approve_match_for_routing`.
- Matching does not model nearby zones, partial item overlap, or triadic `need + offer + transport` routing.
- The admin E2E test renders match cards but does not click or verify `Aprobar match`.

## Issues

### CRISIS-MATCH-AUDIT-01: Audit Every Match Transition

Status: not fully implemented.

Priority: P0 for multi-coordinator operations.

Implement:

- Every match status transition writes an append-only `OperationalEvent(event_type=match_action)`.
- Event payload includes `match_id`, previous status, new status, actor user id/contact id, timestamp, need id, offer/resource id, optional transport id, and optional reason/note.
- `approved_by_user_id` remains for the approval shortcut, but audit must not depend only on that column.
- `rejected`, `fulfilled`, and `expired` are audited, not only `approved`.
- Admin detail view shows who made the latest match decision in human-readable form when available, such as "Aprobado por Gabriela" or "Rechazado por Luis".

Acceptance:

- Two coordinators acting on different matches produce distinct audit events.
- A fulfilled match shows who marked it fulfilled.
- A rejected match requires or stores a reason when provided.
- API tests assert events for `approved`, `rejected`, `fulfilled`, and `expired`.
- Playwright E2E clicks the match action and verifies the UI changes plus mocked request path.

### CRISIS-MATCH-ACTION-02: Put Candidate Matches In The Coordinator Queue

Status: not implemented.

Priority: P0.

Implement:

- Creating or updating a candidate `MatchRecommendation` creates or updates exactly one pending coordinator action.
- Action type is `review_match` or `approve_match_for_routing`.
- The action references the relevant record and the match id, either through a dedicated field or structured event/action metadata.
- The action recommended reason states the blocker: `coordinator_approval_pending`, `needs_verification`, `no_transport`, `quantity_unclear`, or `location_restricted`.
- If the match is approved/rejected/fulfilled/expired, close or update the pending action.

Acceptance:

- A need and compatible offer produce both `MatchRecommendation` and visible pending coordinator action.
- The admin action queue can filter to match-review actions.
- Missing approval never looks like "no match".

### CRISIS-MATCH-PARTIAL-03: Support Partial Item Overlap

Status: not implemented.

Priority: P1.

Implement:

- Parse and store multiple requested/offered resource tokens when a message lists several items.
- Generate a candidate when any operationally useful item overlaps, even if not all requested items are covered.
- Mark `quantity_fit=partial` or `category_fit=partial` and explain what matched.
- Do not hide partial candidates only because the score is below an arbitrary threshold.

Acceptance:

- `NECESITO agua y machetes en Guatire` plus `OFREZCO machetes en Guarenas` creates a candidate.
- The match card says the overlap is `machetes`, not the whole request.
- Coordinator can reject partial matches quickly if they are not useful.

### CRISIS-MATCH-PROXIMITY-04: Show Nearby Zones

Status: not implemented.

Priority: P1.

Implement:

- Add a V1 zone/proximity resolver for common crisis zones and aliases.
- Set `location_fit` to `same_zone`, `nearby`, `unclear`, or `far`.
- Expose "nearby" in the admin match card with enough context for a coordinator to decide.
- Do not send nearby-routing instructions to WhatsApp users before coordinator approval.

Acceptance:

- Guatire/Guarenas-style nearby examples can produce `location_fit=nearby`.
- Same-zone matches still outrank nearby matches.
- Unknown or ambiguous zones stay `unclear` and require review.

### CRISIS-TRANSPORT-05: Model Transport As The Third Routing Piece

Status: not implemented.

Priority: P1.

Implement:

- Treat transport as a routing capability that can bridge a need and an offer/resource.
- Match cards can show `need`, `offer/resource`, and optional `transport`.
- If need and offer match but no transport is known, set `blocking_gap=no_transport`.
- If transport exists, show approximate from/to zones and transport mode when safe.
- Transport actors are manually trusted/waitlisted before they can receive routing tasks.

Acceptance:

- Need in one zone plus offer in another zone creates a candidate with `no_transport` if no trusted transport exists.
- Adding a trusted moto/car/camion transport option updates the candidate or creates a stronger route candidate.
- Coordinator approves the route before any private details are shared.

### CRISIS-TRUST-ROSTER-06: Separate Open Intake From Trusted Routing

Status: partially implemented.

Priority: P0 policy issue before pilot.

Implement:

- Keep a manual trusted roster for coordinators, rescatistas/topos/medical requesters, centros de acopio/donors, and transport.
- Unknown senders may still be accepted as review-only intake if the operator chooses the open/closed hybrid.
- Unknown records remain private/unverified and should not be routable without coordinator validation.
- Store who added or promoted a contact, when, and optionally who vouched for them.
- Admin can label contact role/capability: `need_actor`, `offer_actor`, `transport_actor`, `coordinator`, or equivalent.

Acceptance:

- A trusted coordinator can see commands and queue summaries.
- Unknown contacts cannot receive operational details or be used as trusted route endpoints without review.
- Admin can explain why a contact is trusted from the audit trail.

### CRISIS-CONSOLE-CARD-07: Low-Writing Match Review UI

Status: partially implemented.

Priority: P2 after audit and queue action are in place.

Implement:

- Show compact match cards with approve, reject, need transport, ask more info, and assign owner actions.
- Keep required writing to optional notes/reasons.
- Show item overlap, location fit, verification state, transport gap, and latest actor/action.
- Photo/media support can remain deferred because provider storage limits matter.

Acceptance:

- A coordinator can process a match without typing unless rejecting with a reason or sending follow-up.
- Match cards do not expose private phones or exact locations by default.

### CRISIS-E2E-08: Add Missing E2E Coverage

Status: partially implemented.

Priority: P0 for regressions.

Implement tests for:

- WhatsApp intake creates candidate match plus coordinator action.
- Admin approves a match and the actor appears in audit/history.
- Admin rejects a match and the rejection is audited.
- Admin marks a match fulfilled and the fulfillment actor is audited.
- Unknown vs trusted contact behavior for routing/search/commands.
- Nearby/partial/transport match examples once those features exist.

Acceptance:

- Backend tests cover database events.
- Playwright covers the admin match action.
- Provider smoke remains a separate go-live gate.

## Open Grilling Question

Question: Should V1 be closed for routing even if it remains open for review-only intake?

Recommended answer: Yes. Let unknown people submit reports, but only manually trusted contacts and coordinator-approved records should participate in routing, matching, transport assignment, or outbound operational details.
