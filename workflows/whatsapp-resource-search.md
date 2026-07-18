# WhatsApp Resource Search

## Loop

Every time someone asks WhatsApp where to find a resource, tool, or current operational information.

## Goal

Return the most current safe-to-share answer from verified or recently updated records without exposing sensitive details.

## Trigger

Event-triggered by inbound WhatsApp messages such as:

- `BUSCAR agua Macuto`
- `DONDE HAY gasoil`
- `HERRAMIENTAS topos`
- `STARLINK La Guaira`
- `centros de acopio activos`
- natural-language equivalents

## Primary Actors

- Searcher: person requesting information.
- Bot: WhatsApp responder.
- Coordinator: owner of records and visibility rules.

Primary V1 searchers are coordinators, logistics operators, and center-of-acopio operators. Rescuers may receive summarized results forwarded by coordinators.

Unknown searchers are allowed to ask, but receive only safe, broad, public-summary information or an intake path.

## Inputs

- Search query text.
- Optional location pin.
- Operational records.
- Tool directory entries.
- Visibility policy.
- Freshness/staleness timestamps.

## Output

A short WhatsApp answer with:

- direct answer when available
- status label
- last update time
- confidence/freshness
- next action
- record ids

## Search Policy

Search results prioritize:

1. `confirmed` records.
2. Recent `needs_verification` records clearly labeled as unverified.
3. Tool directory entries marked `active`.
4. Stale records only if no current record exists, clearly labeled.

Never return:

- private contact details unless explicit coordinator visibility allows it
- exact sensitive locations
- medical/missing-person details
- hidden admin notes
- high-value resource details such as fuel, generators, Starlink, tools, medical supplies, or inventories unless the user is authorized

## Category Search Behavior

Search should accept both broad and specific terms.

Examples:

- `BUSCAR transporte` returns ambulancias, traslados, carga, combustible, and related transport records.
- `BUSCAR ambulancia` narrows to `transporte > ambulancia`.
- `BUSCAR insumos médicos` narrows to `insumos > insumos médicos`.
- `BUSCAR Starlink` narrows to `conectividad/energía > Starlink`.

The bot should not require the searcher to know the taxonomy. It should infer likely group/detail from natural language.

## Response Format

Maximum one screen of WhatsApp text.

Example:

```text
Agua cerca de Macuto:

1. REQ-184 - Solicitud activa, alta urgencia, actualizada 14:32.
2. RES-022 - Punto de entrega confirmado, actualizado 13:50.

Nota: confirma disponibilidad antes de moverte. Responde VER REQ-184 para detalles permitidos.
```

If no result:

```text
No tengo un punto confirmado de gasoil para esa zona.

Puedo registrar una solicitud:
NECESITO gasoil en [zona]
```

If matching data exists but is sensitive:

```text
Hay información relacionada, pero no puedo compartir detalles por aquí.
Dejo tu solicitud para coordinación. Código: REQ-184.
```

Unknown users should get broad safe answers or a request-intake path, not private operational details.

## Staleness Policy

Default freshness windows:

- water/food: 6 hours
- gasoil/tools/machinery: 12 hours
- Starlink/connectivity: 6 hours
- centers of collection/distribution: 12 hours
- tools/websites: 24 hours

Records older than the freshness window are shown as `posiblemente desactualizado`.

## Checkpoint

No checkpoint is needed for low-risk, public-summary search answers.

Coordinator approval is required before first publication of:

- exact supply location
- private contact
- route/access instructions
- critical scarcity information
- any sensitive category

## Frontera Leverage

Reuse:

- Knowledge-base style retrieval.
- Conversation state.
- Sanitized outbound messages.
- Admin visibility.

Adapt:

- KB search to operational record search.
- FAQ answer generation to status-labeled operational answers.

## Acceptance Criteria

- `BUSCAR <resource> <zone>` returns only allowed fields.
- Stale data is labeled.
- Unverified data is labeled.
- No private phone numbers or exact sensitive addresses leak.
- The bot offers to create a need if no result exists.
