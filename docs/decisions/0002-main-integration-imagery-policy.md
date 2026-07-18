# Decision 0002: Integrate main without weakening imagery or collaboration policy

- Status: Accepted
- Date: 2026-07-18
- Commit: `Merge origin/main into audit branch`

## Context

`origin/main` introduced updated Next.js instructions, collaborative-change
safety requirements, and a public imagery policy that caps source requests at
zoom 18 while permitting client-side overzoom. The audit branch simultaneously
contained map localization and operational-signal changes in the same areas.

## Decisions

1. Treat `origin/main` from
   `respuestavenezuela-org/crisis-damage-intelligence` as canonical. Retain the
   personal remote only for historical reference.
2. Combine the main and branch `AGENTS.md` rules. The project-specific static,
   privacy, imagery, mobile, and source-labeling rules remain authoritative,
   while the collaborative overlap-rationale requirement also applies.
3. Preserve main's imagery contract:
   - External Esri and approximate-reference sources stop requesting new source
     tiles above zoom 18.
   - The OpenLayers view may overzoom those source tiles.
   - Owned tile pyramids may later advertise a different validated maximum
     through catalog metadata rather than changing the external-source cap.
4. Preserve the branch's operational-signal rendering, localization, focus, and
   selection behavior while resolving the overlapping `MapPanel` changes.
5. Do not reduce imagery quality to resolve package or bandwidth pressure.
   Prefer tiling, range requests, caching, progressive delivery, and remote
   object storage.

## Alternatives rejected

- Hard-capping the map view itself at zoom 18.
- Requesting unlicensed or unavailable external source tiles above zoom 18.
- Applying one hard-coded maximum to both first-party and external imagery.
- Choosing either the main or branch control document wholesale and discarding
  the other.

## Consequences

- Users can inspect imagery beyond the native source zoom without creating
  invalid external requests.
- Future owned z19+ pyramids require catalog validation but no change to the
  external imagery rule.
- Collaborative changes that touch prior uncommitted or coworker work require an
  explicit preservation/adaptation/replacement rationale.

## Validation

- Main remains an ancestor of the consolidated branch.
- Current catalog tile pyramids remain z12-z18.
- External imagery sources retain a z18 source maximum.
- Map interaction, localization, and responsive E2E coverage continue to pass.
