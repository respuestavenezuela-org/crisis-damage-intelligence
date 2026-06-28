# Puerto Cabello / Tucacas Data Gaps

Updated: 2026-06-28 18:02 UTC

## Current Status

- Puerto Cabello is EMSR884 AOI07, but both currently listed AOI07 products are `N = Not produced/not available` in the Copernicus EMSR884 dashboard.
- Tucacas / Falcon is not currently represented as an operational AOI layer in the app catalog.
- Tucacas has public incident reporting around La Mar Suites / Mar Suites collapse, but this is not yet a geospatial dataset and should not be mixed into official EMS damage counts.

## EMSR884 Evidence

- AOI07 Puerto Cabello GRA PRODUCT: `N`, not produced/not available, listed imagery `Legion 2026-06-26T14:03:00 EMSR884_AOI07_GRA_PRODUCT_LEGION_20260626_1403_ORTHO.tif`.
- AOI07 Puerto Cabello GRA MONIT01: `N`, not produced/not available, listed imagery `Legion 2026-06-27T15:16:00 EMSR884_AOI07_GRA_MONIT01_LEGION_20260627_1516_ORTHO.tif`.

## Public Leads To Review

- Tucacas / Falcon: reports identify collapse/rescue activity at La Mar Suites / Mar Suites. Treat as a high-priority geocoding and human-validation lead.
- Puerto Cabello: public video/reporting indicates building damage and evacuations, but no official EMS vector layer is available in the current product.

## Operational Next Steps

1. Add Puerto Cabello and Tucacas/Falcon as explicit data gaps in the app watchlist.
2. Search for public coordinates for La Mar Suites / Mar Suites in Tucacas and create a candidate incident row only after geocoding confidence is acceptable.
3. Search OSM/Overpass for likely building footprints around the candidate site.
4. Use aerial reference imagery for operator orientation only until dated pre/post imagery is available.
5. If Vantor/Copernicus/public imagery for Puerto Cabello or Tucacas becomes accessible, generate chips and run VLM as triage evidence with clear non-official labeling.

## Do Not Overclaim

- EMSR884 absence is not proof of no damage.
- News/social reports are not official building-level damage vectors.
- Tucacas/Falcon candidates must be labeled as report-derived/human-validation-needed until verified.
