# External Source Review Queue

This folder tracks external evidence that is useful but not safe to publish as operational damage without additional checks.

Review gates before any new public layer:

1. Confirm the source URL, data owner, access date, license/terms, geography, confidence, and official status in `public/data/sources/earthquake_source_review.json`.
2. Verify the source is authoritative enough for its intended use. Social or bookmark-derived sources are context only unless confirmed by an authoritative source.
3. For model predictions, inspect thresholds and sample features against imagery and official EMS products. Do not publish a blanket `damaged=1` layer if the source itself recommends stricter thresholding.
4. Confirm the layer is visually and textually distinct from official Copernicus EMS data.
5. Keep queued or rejected sources out of `public/data/catalog.json`.

The current queue documents three additional Microsoft AI for Good Lab HDX damage-prediction datasets discovered on 2026-06-28. They are not official EMS labels and were not added to the public catalog.
