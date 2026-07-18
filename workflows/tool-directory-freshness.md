# Tool Directory Freshness

## Loop

Every time volunteers or coordinators need to know which crisis tools exist and whether they are still current.

## Goal

Maintain a lightweight directory of active tools, maps, forms, groups, dashboards, and resource lists so field teams do not waste time on stale links.

## Trigger

Event-triggered by:

- someone sends `HERRAMIENTAS`
- someone submits a new tool/link
- a coordinator marks a tool stale/down

Schedule-triggered by:

- freshness checks every 12 or 24 hours depending on tool type

## Primary Actors

- Tool submitter.
- Tool owner.
- Coordinator.
- Bot/system.

## Inputs

- Tool name.
- Tool URL/contact.
- Purpose.
- Audience.
- Owner/maintainer.
- Last update time.
- Current status.

## Output

Updated `ToolDirectoryEntry` and WhatsApp-safe tool list.

## Tool Categories

- rescue support
- logistics
- supplies
- map
- connectivity
- shelter
- volunteer coordination
- official source
- external reference

## Intake Flow

Submitter:

```text
HERRAMIENTA https://example.com mapa de centros de acopio
```

Bot:

```text
Recibido. Para registrarla necesito:
1. ¿Para quién sirve?
2. ¿Quién la mantiene o cuándo fue actualizada?
```

The tool is created as `unknown` until coordinator review.

## Freshness Flow

When a tool reaches its freshness interval:

1. System marks it `needs_check`.
2. If owner contact exists, system prepares a WhatsApp check-in message.
3. Coordinator approves or sends check-in.
4. Owner response updates status.
5. If no response, status becomes `stale`.

## Public Response

For `HERRAMIENTAS topos`:

```text
Herramientas activas para rescatistas:

1. [Nombre] - propósito - actualizado 15:10
2. [Nombre] - propósito - actualizado ayer

Nota: evita usar herramientas marcadas como desactualizadas.
```

## Checkpoint

Coordinator approval required before listing a tool as:

- active
- official
- recommended for field use

## Acceptance Criteria

- New tools can be submitted by WhatsApp.
- Tools have status and last-checked time.
- The bot can answer `HERRAMIENTAS`.
- Stale tools are not presented as current.
- Tool ownership and update source are visible to coordinators.
