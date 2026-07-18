# Coordinator Handoff Digest

## Loop

Every time coordinators change shift, lose context, or need a compact operational summary.

## Goal

Produce a decision-ready digest of what changed, what is urgent, what is stale, and what needs human action.

## Trigger

Schedule-triggered:

- every 2 hours during active response
- every 6 hours during lower activity

Event-triggered:

- coordinator asks `RESUMEN`
- critical record appears
- too many unverified records accumulate

## Primary Actors

- Coordinator.
- Domain lead.
- Bot/system.

The first digest audience is logistics and center-of-acopio coordination, not field rescue teams.

## Inputs

- Operational records changed since previous digest.
- Match recommendations.
- Verification queue.
- Stale records.
- Tool directory updates.
- Public map export status.

## Output

`CoordinatorBrief` delivered to coordinator channel or admin inbox.

## Digest Sections

1. Critical new items.
2. Pending verification.
3. Possible need/offer matches.
4. Resolved items.
5. Stale records needing reconfirmation.
6. Tool directory changes.
7. Bottlenecks and gaps.
8. Recommended coordinator actions.

## Digest Format

```text
Resumen operativo 14:00-16:00

Crítico:
- REQ-184 agua Macuto, alta, sin confirmar.

Pendiente de verificar:
- 7 nuevas solicitudes
- 3 ofertas

Posibles matches:
- REQ-184 + OFF-057, requiere confirmar transporte.

Desactualizado:
- Starlink Maiquetía no confirmado desde 09:20.

Bottlenecks:
- 5 solicitudes de agua en Macuto sin oferta confirmada.
- 2 ofertas de comida sin transporte asignado.

Acciones sugeridas:
1. Verificar REQ-184.
2. Confirmar disponibilidad de OFF-057.
3. Revisar Starlink Maiquetía.
```

## Push Right

The digest should not dump raw data.

Before showing it, the system should:

- group duplicates
- rank urgency
- hide resolved noise
- identify owners when known
- include direct links to queue items

## Checkpoint

No checkpoint is required to generate a digest.

Coordinator action is required for each recommended decision.

## Acceptance Criteria

- Digest can be generated on schedule and on demand.
- Every digest item links back to source records.
- Critical items are listed first.
- Stale data is visible.
- The digest never presents unverified records as confirmed.
