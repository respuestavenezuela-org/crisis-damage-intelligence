# Agent Disagreement Log

Updated: 2026-06-30

## Summary

Most agents agree on the operating plan: freeze broad VLM spending until official product freshness, AOI12 version mapping, high-resolution before imagery, candidate dedupe, chip QA, and licensing are handled.

The main disagreement is Copernicus live product state.

## High-Impact Disagreements

### Copernicus EMSR884 Live State

Finding:

- Claude Opus 4.8 claimed the live Copernicus API returned only 7 AOIs, all GRA v1, status W, empty download paths, no AOI00, no AOI08-AOI12, no GRM, no MONIT.
- Direct workspace verification against `https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884` on 2026-06-30 returned the fuller EMSR884 product set, including AOI00 GRM v2, AOI12 GRA v2, and MONIT updates.

Decision:

- Treat Claude's Copernicus-state finding as incorrect or from a transient/partial response.
- Keep Claude's non-Copernicus source notes where independently useful.
- Use direct raw API snapshots saved from this workspace as source of truth.

Impact:

- We should not relabel existing official EMS records as fabricated.
- We should still treat the local catalog as stale because AOI12 v2 and latest monitoring updates need ingestion/remap.

### Direct COG URL Availability

Finding:

- Gemini said direct COG URLs for updated products are missing.
- ChatGPT and local catalog identify current known post-event COG URLs for AOI02, AOI03, AOI05, AOI06, AOI08, AOI10, AOI12.

Decision:

- Current known COG URLs exist, but they are not yet fully bound to latest product versions.
- Keep this as a metadata/version-binding gap, not a total imagery gap.

Impact:

- Do not block all chip generation because URLs exist for several AOIs.
- Do block final broad VLM until COG-to-product-version binding and COG validation are recorded.

### Official Damage Vectors For Some AOIs

Finding:

- Agents agree official GRA polygons are absent/not produced for AOI01, AOI03, AOI04, AOI07, AOI09, AOI10, AOI11.
- Claude's broader claim that no official delivered vectors exist conflicts with verified local and live products.

Decision:

- Official GRA polygon products exist for AOI02, AOI06, AOI08, AOI12, and AOI05 has official point-style product data.
- Missing official polygons remain a real issue for imagery-only AOIs.

Impact:

- OSM/HOT/Microsoft candidates are appropriate only in no-official-vector AOIs or as external triage layers.

### AOI12 Existing VLM Reuse

Finding:

- All agents flag AOI12 v1 to v2 mapping as a blocker.
- Existing VLM rows may be reusable only if geometry/attribute mapping proves stable.

Decision:

- Treat AOI12 VLM as pending QA, not final.
- Build remap before more AOI12 VLM spend.

Impact:

- AOI12 is not the first place to spend new credits until remap is done.

### SAR Use

Finding:

- All agents agree SAR is useful for context, prioritization, or cloud fallback.
- No agent supports SAR as direct building-level optical VLM evidence.

Decision:

- Inventory SAR, use GEC and GRM products for context, do not run building VLM directly from SAR chips.

Impact:

- SAR can prioritize candidate sets but should not consume VLM budget as if it were optical before/after.

### LiDAR / DSM

Finding:

- All agents found no actionable public pre/post LiDAR or DSM change product.

Decision:

- Document checked providers and defer.

Impact:

- Do not block current optical/SAR pipeline on LiDAR.

## Consensus Items

- Need live Copernicus product manifest.
- Need AOI12 v1/v2 feature remap.
- Need official imagery manifest.
- Need Vantor/OpenAerialMap scene coverage mapping.
- Need OSM/HOT extracts for no-official-vector AOIs.
- Need Microsoft AI4G/HDX schema and dedupe.
- Need chip QA manifest before VLM.
- Need licensing matrix.
- Need human validation inventory for adjudication.

## Agent Reliability Notes

- Perplexity deep research: high value for missing artifact list and source categories.
- Gemini: high value for concise production blockers; less detailed on exact source URLs.
- Perplexity search: high value for table-style inventory and source endpoints.
- Claude Opus 4.8: mixed; useful external-source notes, unreliable Copernicus-state claim.
- ChatGPT 5.5 Pro: high value for operational schema, exact URL consolidation, remap rules, and chip QA gates.
