# WhatsApp Resource Intake

## Loop

Every time a person sends a WhatsApp message that reports a need, offer, resource, update, or resolution.

## Goal

Convert messy WhatsApp input into a structured operational record with minimal user effort and enough information for a coordinator to verify or route it.

## Trigger

Event-triggered by an inbound WhatsApp message to the crisis ops number.

The number is open for intake. Any person who has the number may submit a report.

Accepted user intents:

- `NECESITO`
- `OFREZCO`
- `TENGO`
- `BUSCO`
- `ACTUALIZAR`
- `RESUELTO`
- natural-language equivalents such as "hace falta agua", "hay comida", "se acabó el gasoil", "ya lo resolvieron"

Free text should be accepted as the primary path. Menus should appear only when intent, category, or required minimum fields are unclear.

The July 1 implementation decision is explicit: battle-test natural language first. Buttons and menus are lower priority until this workflow can reliably parse, store, match, and queue coordinator approval from free-form WhatsApp messages.

## Primary Actors

- Reporter: person sending the WhatsApp message.
- Bot: Frontera-derived WhatsApp agent.
- Coordinator: human who reviews operational records.

Primary reporters for V1 are coordinators, logistics operators, center-of-acopio operators, and trusted volunteers relaying resource information. Active rescuers are not expected to feed this workflow except when they choose to send a minimal update.

Unknown reporters are allowed. Their reports are accepted but remain private/unverified until reviewed.

## Inputs

- WhatsApp text message.
- Optional voice note, image, document, location pin, or contact card.
- WhatsApp metadata: message id, phone number, timestamp.
- Existing records for duplicate detection.

## Output

One `OperationalRecord` in one of these types:

- `need`
- `offer`
- `resource`
- `update`
- `closure`

## Bot Behavior

1. Parse intent and category.
2. Extract location, quantity, urgency, time sensitivity, and any named contact.
3. Compare against recent records for likely duplicates.
4. Ask at most two follow-up questions if required fields are missing.
5. Confirm the interpreted record back to the reporter.
6. Store record as `unverified` or `needs_verification`.
7. Send a concise receipt with record id using [WhatsApp Response Contract](./whatsapp-response-contract.md).
8. Trigger matching and coordinator approval actions when compatible needs/offers/resources exist.

If the message appears critical or life-safety related, create/escalate the record immediately and use the citizen-effort disclaimer from [Critical Or Life-Safety Intake](./critical-urgent-intake.md).

## Required Fields By Record Type

### Need

- what is needed, or enough raw text to infer it later
- location_text
- record type should be inferred as `need` when possible

### Offer

- what is offered, or enough raw text to infer it later
- location_text or delivery scope
- record type should be inferred as `offer` when possible

### Resource

- category
- location_text
- access instructions if safe to share
- last-known status

### Update

- target record id or enough context to find a candidate record
- update text
- stored as append-only pending update unless sender has sufficient role

### Closure

- target record id or enough context to find a candidate record
- closure reason: resolved, invalid, duplicate, expired
- unknown users create a pending closure suggestion, not a direct state change

## Follow-Up Policy

The bot should ask for only the missing information needed to make the record usable.

Priority order:

1. What is needed/offered.
2. Where it is. Exact locations may be submitted, but are stored as private sensitive data by default.
3. Whether it is a need or offer, only if not clear from the message.

If the reporter does not answer, the bot still creates a partial record marked `needs_verification`.

Quantity, urgency, contact, photos, and extra details are optional follow-ups. They should not block record creation.

## Contact And Identity Policy

Do not ask for the reporter's name by default.

Use the WhatsApp number as private internal contact metadata. Non-sensitive views should use a hash or masked phone reference, not the raw phone number.

Ask for follow-up consent only when needed:

```text
¿Coordinación puede contactarte por este WhatsApp si hace falta aclarar algo?
1. Sí
2. No
```

If the user says no or does not answer, keep the report but set `followup_allowed=no` or `unknown`.

Never expose reporter phone numbers in public search results, public summaries, or map exports.

## Default Privacy

Every new intake record defaults to:

- `verification_status=unverified`
- `public_visibility=private`
- `trust_level_at_creation=unknown` unless the sender is already known
- `followup_allowed=unknown` unless the user explicitly consents or declines
- exact submitted coordinates or addresses stored with `location_access_level=private_sensitive`

The bot should tell the reporter when sensitive details will remain private:

```text
Registrado. Mantendremos detalles sensibles privados hasta que coordinación los revise.
```

If the user sends a location pin:

```text
Recibí la ubicación. La guardo como dato privado para coordinación.
```

## Category UX

The bot must not show a long category list on the first screen.

Use broad first-level options:

```text
¿Qué tipo de recurso es?
1. Agua/comida
2. Insumos
3. Transporte
4. Herramientas/equipos
5. Conectividad/energía
6. Centro o punto de apoyo
7. Otro
```

Then show only relevant suboptions if needed.

If the user already wrote a specific item, classify it automatically and confirm only when ambiguous.

## Example Conversation

Reporter:

```text
NECESITO agua en Macuto para 40 personas
```

Bot:

```text
Listo, registré la solicitud de agua para 40 personas en Macuto como REQ-184.

Estado: pendiente de verificación.

¿Pueden contactarte por este WhatsApp si hace falta aclarar algo?
Responde: SI CONTACTO o NO CONTACTO.
```

Reporter:

```text
Sí
```

Bot:

```text
Listo. Coordinación podrá hacer seguimiento por este WhatsApp si hace falta.
```

## Duplicate Handling

If a similar record exists, the bot should not create a duplicate silently.

It should respond:

```text
Parece relacionado con REQ-171: agua en Macuto, actualizado hace 22 min.

¿Esto es una actualización de ese caso o una solicitud nueva?
1. Actualización
2. Nueva solicitud
```

If the reporter does not answer, create a new record linked to the candidate duplicate and mark `needs_verification`.

## Updates And Closures

Anyone may submit an update:

```text
ACTUALIZAR REQ-184 ya llegó un camión de agua
```

The system creates an append-only update event linked to `REQ-184`. It does not overwrite the canonical record unless a coordinator approves or applies it.

Unknown users may suggest closure:

```text
RESUELTO REQ-184
```

The system responds:

```text
Recibido como actualización pendiente para REQ-184. Coordinación revisará antes de cerrar el caso.
```

Only authorized roles can directly change a record to `resolved`, `rejected`, `duplicate`, or `stale`.

## Checkpoint

Coordinator review is required before:

- marking a record `confirmed`
- changing public visibility to `public_summary` or `public_map`
- routing critical records
- publishing exact resource locations
- using medical, missing-persons, minors, or security-sensitive information
- sharing private contacts or high-value resource details

## Acceptance Criteria

- The intake reply preserves the resource/need wording the user provided.
- The intake reply fits in one WhatsApp message by default.
- The reply includes code, interpreted item, public-safe zone, status, and one next action without sounding like a database receipt.
- The bot does not ask for the offered/needed resource again when it already inferred it confidently.
- applying updates from unknown users to canonical fields
- closing records based on third-party reports

For ordinary logistics/resource records, a trusted coordinator may approve internal routing in V1. Public/export/sensitive approval remains stricter.

## Frontera Leverage

Reuse:

- WhatsApp webhook route.
- Message deduplication.
- Conversation continuity by phone number.
- Media extraction.
- Outbound sanitization.
- 24-hour window handling.
- Admin conversation inbox.

Replace:

- Lead qualification with operational classification.
- Sales handoff with coordinator handoff.
- Commercial KB with crisis resource directory.

## Acceptance Criteria

- A free-form WhatsApp need/offer creates exactly one operational record.
- A free-form need/offer triggers matching without requiring a button flow.
- The bot asks no more than two follow-up questions before creating a partial record.
- Duplicate candidates are linked, not discarded.
- Reporter receives a stable record id.
- Coordinator can see the original message and derived fields.
- No record is marked confirmed without human action.
- V1 copy and prompts are written for logistics/coordinator users, not for rescatistas as primary data-entry operators.
