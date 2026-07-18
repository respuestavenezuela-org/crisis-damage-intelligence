# Resource Verification And Routing

## Loop

Every time a new or updated operational record needs human review, confirmation, routing, or escalation.

## Goal

Give coordinators a small, decision-ready queue so they can verify records quickly and route them to the right group without reading raw chat threads.

Confirmation authority is intentionally unresolved. The workflow must support a future policy that defines who may mark which categories as `confirmed`.

V1 needs a provisional authority model so the matching/admin dashboard does not stall:

- trusted coordinators may confirm ordinary logistics/resource records for internal routing
- trusted coordinators may approve/reject ordinary need-offer matches
- admins are required for public/export, role changes, official damage claims, medical, missing-person, minors, security-sensitive resources, and other high-risk actions

## Trigger

Event-triggered by:

- new `OperationalRecord` with status `unverified` or `needs_verification`
- pending update or closure suggestion from any user
- duplicate candidate requiring decision
- match candidate requiring coordinator approval
- critical urgency
- sensitive category
- stale confirmed record requiring reconfirmation

## Primary Actors

- Coordinator.
- Bot/system.
- Optional domain lead: logistics, rescue, connectivity, supplies, tools.

Primary V1 operators are logistics coordinators and center-of-acopio coordinators. Rescue teams are downstream consumers or escalation targets, not expected queue managers.

## Inputs

- Operational records.
- Original source message and attachments.
- Duplicate candidates.
- Reporter conversation history.
- Current resource directory.

## Output

Record status transition and routing action.

Possible status transitions:

- `unverified` -> `needs_verification`
- `needs_verification` -> `confirmed`
- `needs_verification` -> `rejected`
- `confirmed` -> `stale`
- `confirmed` -> `resolved`
- any status -> `duplicate`

Possible routing actions:

- assign to coordinator
- approve match for internal routing
- reject match with reason
- send to logistics group
- send to rescue lead
- send to connectivity lead
- request more info from reporter
- mark no action needed
- apply pending update
- reject pending update

## Coordinator Brief

Each queue item shows:

- record id
- interpreted summary
- original source excerpt
- category group and detail
- location
- urgency
- duplicate candidates
- age and freshness
- sensitivity flags
- follow-up permission
- public visibility
- current owner
- recommended action
- one-tap decisions

Example:

```text
REQ-184
Need: agua para 40 personas
Zona: Macuto
Urgencia: alta
Fuente: WhatsApp, 14:32
Estado: needs_verification

Recomendación: confirmar disponibilidad o enrutar a logística.

Acciones:
- Confirmar
- Pedir más datos
- Enviar a logística
- Marcar duplicado
- Rechazar
- Corregir categoría
- Aplicar actualización
- Rechazar actualización
- Aprobar match
- Rechazar match
- Mantener privado
- Previsualizar resumen público
```

The full coordinator console is specified in [Coordinator Operational Console](./coordinator-operational-console.md).

## Safety Rules

Human review required for:

- critical urgency
- medical
- missing persons
- minors
- exact private locations
- public announcements
- official damage claims
- security-sensitive supply locations

The system must not autonomously mark high-risk records as confirmed.

Critical records must be treated as citizen coordination reports. The system should not imply official emergency authority or guarantee response.

Until a real authority model is configured, only an explicit admin override may set `confirmed`, and that action must be audited.

Exception for the V1 logistics loop: a configured `trusted_coordinator` may set `verification_status=confirmed` with `confirmation_scope=internal_routing` on ordinary logistics/resource records. This approval is for routing only and must not unlock public map export, official damage claims, medical/missing-person actions, or broad sensitive sharing.

Future authority policy should be able to vary by:

- category
- geography
- organization
- trust level
- urgency
- sensitivity flags
- public visibility

## Push Right

Before asking the coordinator, the system should:

- parse the record
- find likely duplicates
- find likely need-offer/resource matches
- identify missing fields
- propose category, urgency, and route
- prepare match approval/rejection actions when a match exists
- prepare one concise brief

The coordinator should not be asked to read full chat history unless needed.

## Frontera Leverage

Reuse:

- admin conversations page pattern
- handoff/takeover state
- message storage
- suggested actions

Adapt:

- sales owner to coordinator owner
- lead score to urgency/risk score
- conversation summary to verification brief

## Acceptance Criteria

- Every new unverified record appears in the coordinator queue.
- Coordinator can approve/reject/route from a brief.
- Every candidate match that needs approval appears in the coordinator queue.
- Lack of coordinator approval is displayed as pending, not as a failed or missing match.
- Every action writes an audit event.
- Sensitive records cannot become public without explicit approval.
- Duplicate decisions preserve source links.
- The implementation does not hard-code one universal confirmer role.
- Updates from unknown users are append-only until reviewed.
- Unknown users cannot directly close records.
