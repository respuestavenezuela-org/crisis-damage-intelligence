# Decision 0001: Consolidate the low-bandwidth operations experience

- Status: Accepted
- Date: 2026-07-18
- Commit: `Consolidate low-bandwidth operations work`

## Context

The branch contained overlapping work for the public crisis map, a lightweight
view, operational impact zones, first-visit/install prompts, language handling,
and WhatsApp-oriented response workflows. The work had to be integrated without
making Supabase, analytics, VLM providers, or another private service mandatory
for public viewing.

## Decisions

1. Keep the public application static-first. Load the catalog first and only
   fetch active-AOI detail; failures in optional services must not remove AOI
   metadata, downloads, or fallback guidance.
2. Add `/lite` as a catalog-first route for low-bandwidth users. It provides
   public priority context and a path back to the full operational console
   without initializing the full map workflow.
3. Publish community evidence only as aggregate impact envelopes. Never publish
   raw messages, free text, exact report points, names, phone numbers, or
   addresses. Require minimum report and distinct-time thresholds before a
   community aggregate is visible.
4. Preserve source precedence. Copernicus EMS official vectors remain the source
   of record; MONIT01, VLM, external predictions, and community signals remain
   separately labeled triage evidence.
5. Let the desktop map own the viewport between fixed information rails, while
   mobile retains compact map-first controls and reachable AOI/layer/priority
   actions.
6. Coordinate the first-visit acknowledgement and install prompt so they do not
   compete for attention. Persist language and dismissal state when storage is
   available, with Spanish and in-memory/session fallbacks when it is not.
7. Keep the WhatsApp and coordinator material under `workflows/` as operating
   specifications. Do not turn those documents into a required public-runtime
   backend.

## Alternatives rejected

- Loading all AOI vectors and VLM records at startup.
- Publishing individual community or WhatsApp report locations.
- Mixing external prediction counts into official EMS metrics.
- Replacing the full console with the lite route instead of offering both.
- Allowing simultaneous first-visit and install prompts.

## Consequences

- The public surface remains useful on constrained phones and intermittent
  links, but two interfaces must be maintained and tested.
- Impact envelopes intentionally trade point-level precision for privacy and
  operational safety.
- Workflow specifications can evolve independently from the public static app.
- Responsive behavior and storage-denial fallbacks require dedicated browser
  coverage.

## Validation

- Mobile critical-path and fallback tests.
- First-visit dismissal, storage-denial, and language-persistence tests.
- Desktop map-ownership and planning-lens tests.
- Low-bandwidth checks at 360, 430, and 768 pixels.
- Analytics privacy assertions and public-data validation.
