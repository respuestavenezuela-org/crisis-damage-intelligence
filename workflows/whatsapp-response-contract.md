# WhatsApp Response Contract

## Loop

Every time the crisis ops bot sends a WhatsApp reply after parsing or handling an inbound message.

This is the response loop. It applies after intake, search, update, closure, media handling, critical intake, duplicate checks, and coordinator-visible match routing.

## Goal

Send one concrete, readable WhatsApp message by default.

The message should preserve the operational context, confirm what the bot understood, state the current status, and ask for the next useful action without pretending to be a human typing several separate bubbles.

Human tone does not mean long, vague, or split across many bubbles. It means the reply sounds like a practical coordinator assistant: direct, warm enough, specific, and easy to act on.

## Trigger

Event-triggered when the system prepares an outbound WhatsApp message for:

- a newly registered need, offer, resource, update, or closure
- a missing-field follow-up
- a duplicate clarification
- a search result or restricted-result explanation
- a match/routing status update
- a coordinator command result
- a critical or life-safety escalation receipt

## Inputs

- Parsed user intent.
- Extracted resource/need text.
- Record code.
- Record type.
- Public-safe location text.
- Verification status.
- Sensitivity/privacy flags.
- Missing fields, if any.
- Match recommendation state, if any.
- Coordinator action state, if any.
- Follow-up consent state.

## Output

One WhatsApp message.

Multiple messages are allowed only when a single message would either exceed a real provider/product limit or force the bot to remove context needed for safe coordination. Splitting messages to feel more human is not a V1 goal.

## Default Message Shape

Use this order unless the specific workflow has a safety reason to override it. When parse confidence is high, prefer a natural first sentence over a rigid label block.

1. Conversational registration or result sentence.
2. Status.
3. Match, coordination, or privacy note.
4. One next action or question.

Example:

```text
Listo, registré tu oferta de sensores de calor en La Guaira como OFF-001.

Estado: pendiente de verificación.
Coordinación revisará si hace match con una necesidad antes de decirte a dónde llevarlo.

¿Pueden contactarte por este WhatsApp si hace falta coordinar?
Responde: SI CONTACTO o NO CONTACTO.
```

## Formatting Rules

- Prefer a natural first sentence plus short lines over long paragraphs.
- Use blank lines to separate receipt, coordination note, and next action.
- Keep the next action at the end.
- Use label-style lines when the reply has many details, low confidence, or a coordinator-facing summary; use conversational sentences when the intake is simple and clear.
- Use the original user wording when it carries important context, even if the internal category is broader.
- Do not expose private contact details, exact sensitive locations, or internal scoring.
- Do not include raw JSON, database field names, or internal policy names in the user-facing message.
- Do not show the main menu if the message already has enough meaning to process directly.

## Context Preservation

The response must not erase context just to become shorter.

If the inbound message says "sensores de calor en La Guaira", the reply should preserve "sensores de calor" in the user-visible summary, even if the structured category is `tools_equipment` or `equipos de rescate`.

If the message is too long, keep these elements first:

- record code
- interpreted need/offer/resource
- public-safe zone
- current status
- privacy/match constraint
- next action

Only optional explanation should be shortened.

## Missing-Field Replies

When required information is missing, still preserve what was understood:

```text
Listo, registré tu oferta de sensores de calor en La Guaira como OFF-001, pero falta aclarar algo para coordinar bien.

¿Los puedes entregar, prestar, o solo estás reportando que existen?

Responde con una frase corta, por ejemplo: "Puedo prestar 2 sensores hoy en La Guaira".
```

Ask for one missing thing at a time unless the missing pieces are tightly coupled.

## Match And Routing Replies

The bot may say that coordination will review a possible match.

It must not say where to take a resource, expose a requester/provider, or imply that routing is approved until an authorized coordinator approves the match.

Allowed:

```text
Coordinación revisará si hace match con una necesidad antes de indicar destino.
```

Not allowed:

```text
Llévalo a la dirección exacta de la persona que pidió ayuda.
```

## Acceptance Criteria

- A complete intake receipt fits in one WhatsApp message by default.
- The thermal-sensor offer example returns one message and does not ask what resource was offered.
- The reply includes code, interpreted resource, public-safe zone, status, and next action.
- The reply reads like a practical WhatsApp assistant, not a database receipt.
- Missing-field replies preserve already provided context.
- Match/routing copy never exposes private details before coordinator approval.
- Multi-message replies happen only for provider limits, safety/legal separation, or unusually large context that cannot be safely compressed.

## Open Grilling Question

Question: Should every intake receipt start with a conversational sentence instead of a label block when the bot is confident about what the user meant?

Recommended answer: Yes for V1. It feels more human while still keeping the same required information: code, interpreted item, zone, status, coordination/privacy note, and next action.
