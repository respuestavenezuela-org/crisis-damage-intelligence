# WhatsApp Interaction Model

## Goal

Support both fast free-text reporting and guided menu interaction without making overloaded users learn a rigid command system.

## Principle

Free text first, menus when useful.

The initial implementation should not spend time polishing button flows until free text can create records, trigger matching, and surface coordinator approval reliably.

Outbound replies must follow [WhatsApp Response Contract](./whatsapp-response-contract.md): one concrete, well-formatted message by default, preserving context and asking for one next action. The tone should feel like a practical WhatsApp coordinator assistant, not a rigid form. Do not split replies into several WhatsApp bubbles just to feel more human.

The bot should understand direct messages like:

```text
NECESITO agua en Macuto
OFREZCO comida en Altamira
BUSCAR gasoil La Guaira
Hay Starlink abierto cerca de...
```

But it should also offer menus when:

- the user sends "hola"
- the intent is unclear
- required minimum info is missing
- the category is ambiguous
- the user asks "qué puedo hacer"
- a confirmation is needed

## Greeting

When the user sends a short greeting or asks for help, respond with one human, concrete guidance message:

```text
Hola, este WhatsApp ayuda a coordinar necesidades y ofertas.

Escríbeme normal qué necesitas u ofreces y en qué zona. Por ejemplo:
"Necesito agua en Macuto"
"Ofrezco sensores de calor en La Guaira"
"Busco gasolina en Catia La Mar"

No compartimos datos privados sin revisión de coordinación.
```

Do not create an operational record from this greeting alone.

## Main Menu

When needed, show:

```text
¿Qué quieres hacer?
1. Reportar necesidad
2. Reportar oferta/recurso
3. Buscar recurso
4. Actualizar caso
5. Marcar como resuelto
6. Ver herramientas útiles
```

Do not show the main menu after every message.

Do not show this menu just because a message mentions a resource. If the message has enough meaning, process it directly and send a receipt.

## Free-Text Rules

If the user provides enough information, do not force a menu.

Examples:

```text
NECESITO agua en Macuto
```

creates a record directly.

```text
BUSCAR ambulancia en Catia La Mar
```

performs a safe search or creates a request path if details are restricted.

## Menu Rules

- Use numbered options.
- Keep menus to 6 options or fewer when possible.
- Never require exact command spelling.
- Always allow "otro" or free text.
- Do not restart the flow if the user answers naturally.

## Recovery Rules

If the bot is unsure:

```text
No estoy seguro de qué quieres hacer.

1. Reportar necesidad
2. Reportar oferta/recurso
3. Buscar recurso
```

If a message is incomplete:

```text
¿Dónde está o cuál es la referencia?
Puedes responder con zona, punto de referencia o ubicación de WhatsApp.
```

## Response Contract

Every processed message should produce a concise receipt or follow-up that includes the context the user already gave.

Default intake receipt order:

```text
Listo, registré tu oferta de sensores de calor en La Guaira como OFF-001.

Estado: pendiente de verificación.
Coordinación revisará si hace match con una necesidad antes de decirte a dónde llevarlo.

¿Pueden contactarte por este WhatsApp si hace falta coordinar?
Responde: SI CONTACTO o NO CONTACTO.
```

Use multiple messages only when a single message would exceed a real WhatsApp/provider limit or would force removal of context needed for safe coordination.

## Acceptance Criteria

- Direct free-text messages work without menu navigation.
- The core need/offer routing loop passes without using buttons.
- Menus appear only when helpful.
- The user can switch from menu to natural language at any time.
- The bot never loses already provided information when asking follow-ups.
- Bot replies follow the one-message-by-default response contract.
