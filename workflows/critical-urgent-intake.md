# Critical Or Life-Safety Intake

## Loop

Every time a WhatsApp message appears to describe an urgent, life-safety, rescue, medical, structural, or critical humanitarian situation.

## Goal

Register the report, escalate it for citizen coordination review, and avoid implying that the bot or project is an official emergency service.

## Trigger

Event-triggered by messages mentioning:

- trapped people
- injured people
- immediate danger
- medical emergency
- collapsed structure
- fire
- flood
- blocked access
- no water/food for vulnerable people
- urgent rescue need
- other language indicating life-safety risk

## Required Bot Behavior

1. Create an `OperationalRecord` or critical update.
2. Mark `urgency=critical`.
3. Add relevant sensitivity flags.
4. Keep public visibility private.
5. Escalate to the critical coordinator queue.
6. Respond with a citizen-effort disclaimer.

## Required Response Copy

The bot should say:

```text
Recibido. Lo registré como urgente para coordinación.

Importante: esto es un esfuerzo ciudadano de organización de información, no un servicio oficial de emergencia ni garantiza respuesta.
```

If the record id exists:

```text
Código: REQ-184.
```

## Prohibited Bot Behavior

The bot must not:

- promise rescue
- promise delivery
- claim official status
- say "vamos en camino" unless an authorized human explicitly entered that update
- publish critical reports publicly by default
- expose exact locations broadly
- diagnose medical conditions
- certify deaths or injuries

## Checkpoint

Critical records require human review before:

- routing outside the coordinator queue
- sharing exact location
- marking confirmed
- sharing with a specific team
- publishing any public summary

## Acceptance Criteria

- Critical messages create records even if incomplete.
- The response clearly states this is a citizen coordination effort.
- The system does not promise action or rescue.
- Critical records are private and escalated.
