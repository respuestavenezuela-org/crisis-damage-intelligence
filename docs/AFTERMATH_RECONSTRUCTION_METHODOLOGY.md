# Aftermath Reconstruction Methodology

## Purpose

The public reconstruction at `/timeline` explains what can be established about
the June 24, 2026 Venezuela earthquakes and their aftermath in La Guaira,
Caraballeda, and Catia La Mar.

It is an evidence index, not a continuous recording and not an official finding
about response adequacy.

## Core Distinctions

The reconstruction keeps these response stages separate:

1. `announced`: an actor says help will be provided.
2. `mobilized`: people, supplies, or equipment are preparing or travelling.
3. `arrived-country`: arrival is documented in Venezuela.
4. `arrived-region`: arrival is documented in or near the affected region.
5. `observed-site`: dated visual or situated reporting places it at a site.
6. `operational`: a source documents that it was being used.

An airport landing is not a delivery. Movement toward La Guaira is not proof of
presence at every collapse site. A vehicle visible near rubble is not
automatically humanitarian, operational, or sufficient.

## Confidence

- `confirmed`: primary/official source or direct dated visual evidence.
- `corroborated`: at least two independent sources support the same general
  event.
- `single-source`: one credible source; further contrast is needed.
- `inferred`: conservative interpretation of imagery or structured data.

`Not observed` never means `did not happen`. The reconstruction only describes
an absence when a situated source reports a concrete gap.

## Image Review

The current public page displays only imagery already handled by the project:

- Copernicus EMS post-event products.
- Vantor Open Data pre-event reference under CC-BY-NC-4.0.

MapAction maps, field photographs, UN media, and journalism are linked when
reuse terms are unclear. They are not copied into the public package.

Vehicle and heavy-machinery observations are candidates unless a human can
resolve the object at the available ground sample distance. Models may propose
candidates but cannot determine ownership, activity, arrival time, intent, or
adequacy from a single image.

## Privacy

- Do not publish names, phone numbers, license plates, faces, or exact private
  shelter locations.
- Public shelter and distribution sites may be linked when already published by
  an official/humanitarian source.
- Vulnerable-population locations should be delayed, generalized, or withheld
  when publication could create a safety risk.

## Updating

Edit:

```text
public/data/reconstruction/la-guaira-timeline.json
```

Then run:

```bash
python3 scripts/validate_reconstruction.py
npm run lint
npm run typecheck
npm run build
npm run test:e2e
```

Every new event must:

- have a date or date range;
- identify time and location precision;
- cite one or more registered sources;
- use an allowed confidence level and response stage;
- preserve contradictory evidence and caveats;
- avoid converting a model detection into a factual claim.
