# Decision 0008: Let button variants own their foreground color

- Status: Accepted
- Date: 2026-07-20
- Commit: `Fix active button text contrast`

## Context

The active “Priorizar” planning-lens button rendered nearly black text on a
black background. Its design-system classes correctly requested
`text-primary-foreground`, but the unlayered global rule
`button { color: inherit; }` took precedence over Tailwind's layered utility.

Several older active-button selectors happened to set `color: white`
explicitly, masking the same cascade problem. The planning-lens selector did
not, exposing a contrast ratio of approximately 1.05:1 instead of the WCAG AA
minimum of 4.5:1 for normal text.

## Decision

1. Scope inherited button color to native buttons that do not use the shared
   design-system component.
2. Give the shared Button component an explicit `text-foreground` base color
   and expose its semantic variant as `data-variant`.
3. Let each Button variant override that base through its existing semantic
   foreground token and an unlayered attribute rule:
   - Primary buttons use `text-primary-foreground`.
   - Secondary buttons use `text-secondary-foreground`.
   - Destructive and link buttons keep their semantic colors.
   - Outline and ghost buttons use the base foreground.
4. Keep the attribute rules outside Tailwind's cascade layers so an unlayered
   application rule cannot silently override semantic contrast again.
5. Retain the existing focus ring, keyboard behavior, pressed-state semantics,
   disabled styling, and native-button inheritance.

## Alternatives rejected

- Adding only `.planning-lens-switch .active { color: white; }`, which would
  leave the shared cascade bug in place.
- Using `!important`, which would make semantic variant and theme overrides
  harder to maintain.
- Removing native-button inheritance entirely, which could regress the
  hand-authored lightweight console controls.

## Consequences

- “Priorizar” and future primary Button instances consistently use the intended
  foreground token.
- Existing one-off active-state rules remain compatible but are no longer
  required to rescue the shared component.
- Button contrast follows the design-system tokens in light and dark themes.

## Validation

- Automated contrast audit at 375, 768, and 1440 pixel widths.
- Visual inspection of active planning, map, language, filter, and operational
  signal controls.
- Verify the active planning-lens foreground/background pair meets WCAG AA.
- Lint, typecheck, production build, and the Playwright suite.
