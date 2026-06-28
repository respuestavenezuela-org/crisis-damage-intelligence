# External Source Review Queue

This folder tracks external evidence that is useful but not safe to publish as operational damage without additional checks.

Review gates before any new public layer:

1. Confirm the source URL, data owner, access date, license/terms, geography, confidence, and official status in `public/data/sources/earthquake_source_review.json`.
2. Verify the source is authoritative enough for its intended use. Social or bookmark-derived sources are context only unless confirmed by an authoritative source.
3. For model predictions, inspect thresholds and sample features against imagery and official EMS products. Do not publish a blanket `damaged=1` layer if the source itself recommends stricter thresholding.
4. Confirm the layer is visually and textually distinct from official Copernicus EMS data.
5. Keep queued or rejected sources out of `public/data/catalog.json`.

Operational guardrails:

- Google Maps links and Esri basemap/satellite views are external visual references only. They are not official evidence sources, are not cached or redistributed by this project, and should not be used as VLM before imagery.
- Pre-event imagery has three allowed labels: `Vantor usable for VLM`, `Esri visual reference only`, and `No before`. Only the Vantor class may support before/after VLM, and only when coverage, alignment, and visibility are adequate.
- Microsoft/HDX damage-prediction layers are external model outputs. They may be used as candidate footprints or triage leads, but not as EMS labels, field-confirmed damage, or official response counts.
- Do not overclaim absence: a missing prediction, missing EMS polygon, or missing VLM flag is not proof of no damage.

The current queue documents three additional Microsoft AI for Good Lab HDX damage-prediction datasets discovered on 2026-06-28. They are not official EMS labels and were not added to the public catalog.
