# UI System

Respuesta Venezuela uses `shadcn/ui` as the default component foundation for reusable interface primitives: buttons, cards, badges, alerts, drawers, scroll areas, and separators.

The operational map shell keeps local CSS for layout-critical surfaces that are specific to this product: rails, map toolbar placement, mobile safe-area behavior, AOI carousels, dense priority rows, and OpenLayers popups.

Rules for future UI work:

- Prefer adding or reusing a local `src/components/ui/*` shadcn component before creating a bespoke primitive.
- Keep generated shadcn components only when they are imported by app code or an accepted near-term migration.
- Map-specific layout CSS should derive colors, borders, radius, and text colors from the shadcn tokens in `src/app/globals.css`.
- Do not reintroduce a second color/token system; legacy operational names such as `--panel`, `--line`, and `--black` are aliases for shadcn semantic tokens.
