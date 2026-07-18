# Need Offer Matching

## Loop

Every time a need or offer is created or updated, the system checks whether it can connect it to a compatible counterpart.

## Goal

Surface likely matches between needs and offers so coordinators can act faster without the system making unsafe autonomous commitments.

The matcher recommends candidates; it does not decide routes. A coordinator decides whether a partial overlap, nearby zone, or transport bridge is actually useful.

## Trigger

Event-triggered by:

- new `need`
- new `offer`
- update to quantity, location, urgency, or availability
- confirmed resource becoming available

## Primary Actors

- Coordinator.
- Reporter/requester.
- Offer provider.
- Bot/system.

## Inputs

- Need records.
- Offer records.
- Resource records.
- Transport capability records.
- Location text/coordinates.
- Category and quantity.
- Parsed item tokens when one message contains multiple requested/offered items.
- Availability windows.
- Verification status.

## Output

A match recommendation card.

Fields:

- `match_id`
- `need_record_id`
- `offer_record_id`
- optional `transport_record_id`
- `matched_items`
- `match_score`
- `category_match`
- `location_match`
- `quantity_fit`
- `time_fit`
- `verification_fit`
- `risk_level`
- `recommended_action`
- `requires_human_approval`
- `approval_required_reason`
- `coordinator_action_id`
- `blocking_gap`: `none | no_transport | contact_restricted | location_restricted | stale_offer | stale_need | quantity_unclear | needs_verification | coordinator_approval_pending`

## Matching Rules

Score positively when:

- same category detail
- compatible category group when detail is unknown
- one or more matched item tokens in a multi-item need/offer
- compatible zone
- nearby zone when transport could plausibly bridge the route
- offer quantity can satisfy need quantity
- availability window is current
- both records are confirmed or one is confirmed and the other is recent
- no sensitivity flags block sharing

Score negatively when:

- stale data
- conflicting location
- incompatible quantity/unit
- no overlap between any requested/offered item
- sensitive contact details required
- either side is rejected/resolved

## Candidate Creation Rules

The matcher should create a `MatchRecommendation` when a plausible route exists, even if coordinator approval is still missing.

Recommended V1 behavior:

- `confirmed` records with `confirmation_scope=internal_routing` can produce normal candidate matches.
- `needs_verification` records can produce candidate matches with `blocking_gap=needs_verification` and `requires_human_approval=true`.
- `unverified` records from unknown users can produce review-only candidates, but the bot must not tell either party that a resource is available and the route must not proceed until a coordinator validates the contact/record.
- `rejected`, `resolved`, `duplicate`, and expired/stale records should not produce new active matches unless a coordinator reopens them.
- Every candidate match creates or updates one coordinator action: `review_match` or `approve_match_for_routing`.
- A partial overlap should still surface if it can help operations. Example: a need for "agua y machetes" can match an offer of "machetes" with `quantity_fit=partial` or `category_fit=partial`.
- If zones are nearby rather than identical, set `location_match=nearby` and show the distance/proximity explanation to the coordinator.
- If a need and offer/resource are useful but no trusted transport is available, create the match with `blocking_gap=no_transport` instead of suppressing it.

The admin console must never infer "no match" from "approval missing." Missing approval is a visible pending state.

## Coordinator Brief

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

If approval is the only blocker, the brief must say that directly:

```text
Possible match

Need: REQ-184 agua para 40 personas en Macuto
Offer: OFF-057 agua disponible en La Guaira hasta 18:00
Fit: high
Risk: medium
Blocking gap: coordinator approval pending

Recommended action:
Approve match for internal routing or reject with reason.
```

## Automation Boundary

The bot may tell a reporter:

```text
Encontré una posible opción, pendiente por confirmar con coordinación.
```

The bot must not expose private offer contact/details until a coordinator approves.

## Checkpoint

Coordinator approval required before:

- connecting two private parties
- sharing phone numbers
- sharing exact resource location
- telling someone to move toward a supply point
- marking a match as fulfilled

Every match transition must be auditable:

- candidate created
- approved
- rejected
- fulfilled
- expired
- connected/contacted parties, when that action is represented in the system

Each audit event must record actor, timestamp, previous status, new status, linked need, linked offer/resource, optional linked transport, and optional reason/note.

Trusted coordinators may approve ordinary logistics/resource matches for internal routing in V1. Admin approval is still required before public/export/sensitive sharing.

## Acceptance Criteria

- Creating a need checks open offers/resources.
- Creating an offer checks open needs.
- Matches are explainable.
- Candidate matches are visible even when coordinator approval is pending.
- Missing approval creates a coordinator queue action instead of breaking the match path.
- No private details are shared automatically.
- Coordinator can mark a match as accepted, rejected, fulfilled, or duplicate.
- Partial overlaps and nearby-zone candidates are visible as such, not presented as exact fits.
- Transport gaps appear as `blocking_gap=no_transport`.
- The UI/API can answer "who matched this?" for each approved/rejected/fulfilled transition.
