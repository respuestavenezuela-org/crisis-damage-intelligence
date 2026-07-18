# WhatsApp Voice And Media Intake

## Loop

Every time someone sends a WhatsApp voice note, photo, location pin, document, or contact card instead of structured text.

## Goal

Convert non-text WhatsApp inputs into structured records while preserving original evidence and requiring confirmation when transcription or interpretation is uncertain.

## Trigger

Event-triggered by inbound WhatsApp media:

- audio/voice note
- image
- document
- location
- contact card

## Primary Actors

- Reporter.
- Bot/system.
- Coordinator.

## Inputs

- WhatsApp media payload.
- Media metadata.
- Optional caption.
- Reporter conversation context.

## Output

- Media artifact reference.
- Extracted text or metadata.
- Candidate `OperationalRecord`.
- Confirmation prompt or coordinator queue item.

## Audio Flow

1. Download audio through WhatsApp media API.
2. Store artifact with access restricted to coordinators.
3. Transcribe locally or through approved provider.
4. Extract candidate intent, category, location, quantity, urgency.
5. Ask reporter to confirm:

```text
Entendí esto:
NECESITO agua en Macuto para 40 personas.

¿Está correcto?
1. Sí
2. Corregir
```

6. If no response, create partial record marked `needs_verification`.

## Image Flow

1. Store image artifact.
2. Do not infer sensitive facts automatically.
3. Use caption/text if available.
4. Ask reporter what the image represents if unclear.
5. Queue for coordinator review if it affects resource status or safety.

## Location Pin Flow

1. Store coordinates.
2. Ask what the location represents:

```text
Recibí una ubicación. ¿Qué representa?
1. Necesidad
2. Oferta/recurso
3. Centro de acopio
4. Punto de conectividad
5. Otro
```

3. Store coordinates with `location_precision=exact`.
4. Set `location_access_level=private_sensitive`.
5. Default public visibility to `private`.
6. Do not echo exact coordinates back into broad/shared summaries.

## Safety Rules

- Do not publish raw media publicly.
- Do not expose exact coordinates without approval.
- Do not use photos to certify damage, injury, death, official status, or identity.
- Voice transcription is evidence, not verification.
- Treat media as potentially sensitive even when the reporter did not label it sensitive.
- Do not ask media senders for names by default; keep WhatsApp contact metadata private.
- Exact location access must be role-restricted and audited.

## Frontera Leverage

Reuse:

- WhatsApp media handling.
- Message storage.
- Admin inbox.

Extend:

- audio transcription pipeline
- media artifact access policy
- confirmation prompt

## Acceptance Criteria

- Voice notes become candidate records or coordinator queue items.
- Location pins are private by default.
- Reporters can confirm or correct transcription.
- Original media remains linked to the derived record.
- Sensitive media is not published automatically.
