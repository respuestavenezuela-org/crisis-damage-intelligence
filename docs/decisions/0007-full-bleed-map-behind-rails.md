# Decision 0007: Make the rail outline visually disappear into the map

- Status: Accepted
- Date: 2026-07-20
- Commit: `Remove visible rail outline`
- Supersedes: Decision 0006

## Context

Decision 0006 changed the operations-shell gutter from black to the neutral page
canvas. That removed the black color but left a visible solid outline around the
inset left and right rails. The clarified requirement is to remove the outline
itself, not recolor it.

The rails are intended to float over the operational map. Their 14-pixel inset,
rounded corners, and shadows are useful, but the shell should not appear as a
separate frame behind them.

## Decision

1. Extend the map stage to every edge of the desktop and tablet operations
   shell so map imagery appears behind the rail insets.
2. Keep the rails above the map with their existing translucent surfaces,
   borders, shadows, scrolling, and spacing.
3. Offset the map toolbar into the unobstructed center:
   - 346 pixels from the left on desktop and tablet.
   - 382 pixels from the right on wide desktop, where the right rail is full
     height.
   - 14 pixels from the right below 1120 pixels, where the right rail becomes a
     bottom inspector.
4. Preserve the existing mobile flow, where the map stage remains in normal
   document layout beneath the compact header.

## Alternatives rejected

- Keeping the neutral gutter from Decision 0006, because it still reads as a
  visible frame.
- Removing rail insets and rounded corners, which would make the operational
  panels heavier and reduce map context.
- Making the rail surfaces themselves transparent, which would reduce text
  legibility over variable imagery.
- Allowing the full-bleed map toolbar to sit beneath the rails.

## Consequences

- The black outline disappears rather than changing color.
- Map context remains visible around all four sides of each floating rail.
- The map renders a larger area, but no additional data source or eager payload
  is introduced.
- Rail and toolbar interactions remain above the map.

## Validation

- Visual inspection at 375, 768, and 1440 pixel widths.
- Confirm no horizontal overflow, toolbar/rail collision, clipped content, or
  mobile regression.
- Lint, typecheck, production build, and the Playwright suite.
