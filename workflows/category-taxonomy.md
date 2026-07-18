# Category Taxonomy And Progressive Disclosure

## Goal

Keep the first WhatsApp interaction simple while still allowing coordinators to capture useful detail.

Users may be overloaded, injured, exhausted, multitasking, or relaying information under pressure. The system must avoid showing a large category list up front.

## Principle

Use progressive disclosure:

1. Ask for a broad category.
2. Then show only the relevant subcategories.
3. Allow free text at every step.
4. Never block record creation because the category is imperfect.

## First-Level Categories

The first screen should show the smallest practical set:

1. Agua / comida
2. Insumos
3. Transporte
4. Herramientas / equipos
5. Conectividad / energía
6. Centro o punto de apoyo
7. Otro

These labels are intentionally broad. They are doors into more specific options, not final taxonomy limits.

## Second-Level Categories

### Agua / comida

- agua potable
- hielo
- comida preparada
- alimentos no perecederos
- comida para bebés
- cocina / preparación
- otro

### Insumos

- insumos médicos
- insumos de construcción
- higiene personal
- limpieza / desinfección
- ropa / mantas
- protección personal
- otro

### Transporte

- ambulancia
- traslado de personas
- traslado de insumos
- camión / carga
- combustible / gasoil
- maquinaria pesada
- otro

### Herramientas / equipos

- herramientas manuales
- herramientas eléctricas
- equipos de rescate
- iluminación
- generadores
- bombas / extracción de agua
- otro

### Conectividad / energía

- Starlink
- Wi-Fi / internet
- punto de carga
- planta eléctrica
- baterías / power banks
- radios / comunicación
- otro

### Centro o punto de apoyo

- centro de acopio
- punto de comida
- punto de agua
- punto de atención médica
- punto de descanso
- punto de conectividad
- otro

## Free Text Handling

If the user writes a specific thing directly, the bot should classify it without forcing menu navigation.

Examples:

- "Necesito ambulancia" -> `transporte > ambulancia`
- "Ofrezco gasoil" -> `transporte > combustible/gasoil`
- "Hay Starlink abierto" -> `conectividad/energía > Starlink`
- "Necesitan palas y picos" -> `herramientas/equipos > herramientas manuales`

The bot should confirm only when ambiguity matters:

```text
¿Esto entra como transporte?
1. Ambulancia
2. Traslado de insumos
3. Combustible/gasoil
4. Otro
```

## UI And Prompt Rules

- Do not show more than 7 first-level options.
- Do not show more than 7 second-level options.
- Always allow `Otro`.
- Always allow the user to type naturally instead of choosing.
- Do not force category selection when natural language is already specific enough.
- Use short labels.
- Prefer numbered replies over long prose.
- If the user gives enough information, do not ask them to categorize manually.
- Create a partial record if the user stops responding.

## Data Model

Operational records should store both:

- `category_group`: broad first-level category.
- `category_detail`: second-level category or free-text detail.

They should also keep:

- `raw_category_text`: what the user actually wrote.
- `category_confidence`: `low | medium | high`.

## Acceptance Criteria

- First prompt never displays a long category list.
- Broad categories can contain multiple specific item types.
- Free text still works.
- Category uncertainty does not block intake.
- Coordinators can later correct category group/detail.
