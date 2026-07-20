# Decision 0006: Use the neutral canvas behind desktop rails

- Status: Superseded by Decision 0007
- Date: 2026-07-20
- Commit: `Remove black rail gutters`

## Context

The desktop operations layout positions the left and right rails 14 pixels
inside the viewport. The rails already use light, translucent panels, but the
operations shell beneath them was solid black. That shell color appeared as a
heavy frame around both rails and competed visually with the map and planning
content.

## Decision

Use the existing page background token, `var(--bg)`, as the operations-shell
background at every breakpoint. Preserve the rail insets, borders, shadows,
translucency, scrolling, and the map's current bounds.

## Alternatives rejected

- Removing the rail insets, which would reduce useful visual separation.
- Extending the map behind both rails, which would require repositioning map
  controls and could reduce panel legibility over high-contrast imagery.
- Adding a new rail-only color token when the existing neutral canvas already
  matches the mobile layout and surrounding application chrome.

## Consequences

- The black gutters are replaced by the warm neutral canvas.
- The rails continue to read as floating operational surfaces.
- Mobile remains visually unchanged because it already used the same
  background token.
- No map, data-loading, interaction, or accessibility behavior changes.

## Validation

- Visual inspection at 375, 768, and 1440 pixel widths.
- Computed shell background: `rgb(231, 226, 216)` at all three widths.
- Document scroll width equals viewport width at all three widths.
- Lint, typecheck, production build, and all 25 Playwright tests.
