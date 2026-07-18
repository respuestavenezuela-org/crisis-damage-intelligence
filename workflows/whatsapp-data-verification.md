# WhatsApp Data Verification

## Priority

P2 / deferred.

Do not build this before the V1 routing loop is reliable. The immediate priority is routing volunteers, insumos, gasolina, maquinaria, and other resources to verified needs.

## Loop

Every time a trusted verifier or coordinator wants to check an existing operational record, map feature, tool entry, or exported summary through WhatsApp.

## Goal

Support manual verification work from WhatsApp without turning unreviewed chat replies into official claims or public map updates.

This workflow helps people verify data. It does not replace coordinator approval, official Copernicus EMS source labels, VLM caveats, or public export policy.

## Trigger

Event-triggered by:

- `VERIFICAR REQ-184`
- `VERIFICAR ems_00107`
- coordinator assigns a verification task to a trusted contact
- verifier replies to a verification request with text, photo, voice note, location, or status

## Primary Actors

- Trusted verifier.
- Coordinator.
- Bot/system.
- Optional admin for public/export-sensitive decisions.

Unknown users may submit corrections, but their updates stay pending until reviewed.

## Inputs

- Target record id or enough context to identify a candidate target.
- Source evidence from Frontera messages, operational records, tool directory, or static map feature ids.
- Verifier role/trust level.
- Optional media, location pin, voice note, and notes.

## Output

Append-only verification evidence:

- `OperationalEvent(event_type=verification, event_status=pending | applied | rejected)`
- linked `CoordinatorAction(action_type=verify | sensitive_review | approve_public_summary)` when human review is required
- proposed field changes stored in `proposed_values_json`
- no automatic public map update

## Bot Behavior

1. Identify the target record or ask one clarifying question.
2. Show a short verification brief with non-sensitive context.
3. Ask for a specific verification result, such as current, stale, resolved, wrong category, wrong location, or needs more review.
4. Accept text, voice, photo, document, or location evidence.
5. Store the verifier response as an event with provenance.
6. Apply directly only when the sender role is authorized for that target and the action is low risk.
7. Otherwise create a coordinator action for review.

Example:

```text
VERIFICAR REQ-184
```

Bot:

```text
REQ-184: agua para 40 personas, zona Macuto.
Estado actual: pendiente de verificación.

¿Qué confirmas?
1. Sigue vigente
2. Ya resuelto
3. Dato incorrecto
4. Necesita más revisión
```

## Safety Rules

- Do not ask unknown users to verify official damage labels.
- Do not let WhatsApp replies reclassify EMS official damage.
- Do not claim absence of damage from absence of reports.
- Do not label `post_event_only` VLM as before/after.
- Do not publish medical, missing-person, exact-location, or private-contact verification without stronger review.
- Do not expose private target details to unknown users.
- Official EMS remains the source of record for official damage counts.
- Verification of operational logistics is not the same as official damage verification.

## Interaction With V1 Routing

This workflow may update or close resource records after review, but it must not be required for the first routing MVP.

Allowed V1-adjacent use:

- coordinator asks a trusted contact to confirm whether a need/offer is still current
- verified response updates `last_confirmed_at`
- stale or resolved result creates a pending coordinator action

Deferred use:

- field validation of map damage layers
- public map publishing
- official source reconciliation
- large volunteer verification campaigns

## Checkpoint

Coordinator/admin review required before:

- changing public visibility
- exporting to the static map
- changing official-damage-related labels
- applying verification from unknown users
- applying sensitive or high-risk verification

## Acceptance Criteria

- Verification replies are append-only and preserve source message provenance.
- Unknown-user verification cannot overwrite canonical fields directly.
- Trusted coordinator verification can update ordinary logistics/resource freshness for internal routing.
- Public/export changes require explicit stronger approval.
- WhatsApp data verification is feature-gated or otherwise separable from V1 routing.
