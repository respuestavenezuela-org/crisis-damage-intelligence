# Full-pilot aerial response analysis

## Public purpose

This pilot reconstructs what can be seen in dated aerial imagery after the June
24, 2026 earthquakes across La Guaira, Caraballeda, and Catia La Mar. It looks
for response-related signals such as heavy machinery, trucks, debris clearance,
temporary shelters, and collection or staging areas.

The output is public AI triage, not an official damage or response inventory.
Every claim must remain bounded by the date, place, source pixels, and limits of
the evidence that supports it.

## Spatial and image resolution

- The complete pilot contains 2,283 square grid cells, each approximately 250 m
  wide in EPSG:3857.
- The coverage envelope combines one official EMS corridor and four external
  Microsoft/HDX triage footprints. The external footprints define where to
  inspect imagery; they are not official damage labels.
- Each selected scene is extracted as a 768 × 768 pixel native evidence chip.
  This provides a nominal sampling interval of about 0.33 m per output pixel.
- The output sampling interval does not improve the ground sample distance of
  the source sensor. It avoids throwing away useful detail but cannot create
  detail that the source image did not record.
- Swin2SR 2× images are generated only for display and navigation. They are
  clearly labeled `visualization-only` and cannot replace the native crop for
  verification.
- High-quality native chips, SHA-256 hashes, source scene IDs, acquisition
  times, sensors, and licenses are preserved in the evidence manifest.

## Temporal selection

For every grid cell, the extraction process selects:

1. the best usable pre-event comparator available to the project; and
2. the best usable post-event image for each available acquisition date.

This removes redundant overlaps while preserving the temporal sequence. A
`post_event_only` stack is never described as a before/after comparison.

The source inventory contains 17 distinct acquisitions: four pre-event and 13
post-event. After per-date quality selection, the analysis corpus contains
9,794 unique cell-date image chips.

The event origin used for elapsed-time calculations is
`2026-06-24T18:04:33-04:00`. A first-visible image date means only that the
signal was visible no later than that acquisition. It is not the real arrival
time of a truck, machine, shelter, or response team.

## Analysis pipeline

1. Qwen3-VL-30B-A3B-Instruct, routed through Hugging Face, reviews every
   eligible temporal stack.
2. MiniMax independently reviews the same temporal stacks.
3. Cross-model consensus separates joint positives, contested positives,
   uncertain results, and negatives.
4. WALDO30 runs across every eligible dated scene as an independent
   object-detection signal for recognizable classes such as diggers, trucks,
   buses, and containers. Its coverage does not depend on a VLM-positive result.
5. Detector count changes are treated as triage signals. They are not proof
   that an object arrived after the event, because view angle, occlusion,
   source quality, and false detections can change counts.
6. The highest-priority candidates receive native before/post evidence crops.
7. A public timeline groups candidate cells by their earliest dated positive
   acquisition and keeps undated observations separate.

The public browser loads only the bounded summary, top evidence pairs, and
download links. The full analysis is asynchronous and no public page makes a
live VLM request.

## Documentary cross-checks

The aerial evidence is interpreted alongside dated field and operational
sources. These sources can establish observations that imagery may not resolve,
but they do not turn an image-screening result into a verified fact.

- [El Diario, June 25](https://eldiario.com/2026/06/25/la-guaira-edificios-colapsados-y-hospitales-saturados-terremotos/)
- [EFE in Catia La Mar, June 26](https://efe.com/mundo/2026-06-26/saqueos-terremotos-venezuela/)
- [World Food Programme, June 26](https://es.wfp.org/historias/wfp-apoya-la-respuesta-al-terremoto-en-venezuela-con-alimentos-y-otra-asistencia)
- [Logistics Working Group, June 26](https://logcluster.org/sites/default/files/public/2026-06/venezuelagrupo-de-trabajo-de-logistica_0260626.pdf)
- [EFE at Playa Grande, June 29](https://efe.com/mundo/2026-06-29/esperanza-busqueda-rescate-personas-la-guaira-terremotos-venezuela/)
- [UNDP debris assessment, June 29](https://www.undp.org/es/venezuela/comunicados-de-prensa/el-pnud-estima-12-millones-de-toneladas-de-escombros-en-la-guaira-tras-los-terremotos-en-venezuela)
- [Logistics situation report, July 2](https://logcluster.org/es/documents/venezuela-respuesta-terremotos-reporte-situacional-1-2-julio-2026)
- [Logistics meeting minutes, July 2](https://logcluster.org/es/documents/venezuela-minutas-de-la-reunion-respuesta-al-terremoto-caracas-2-julio-de-2026)

## Interpretation rules

- “Not observed” never means “did not occur.”
- A regional arrival does not establish delivery to every neighborhood.
- A site-specific gap cannot be generalized to all of La Guaira.
- Pre-existing industrial or transport activity is a major confounder.
- Official Copernicus EMS data, external predictions, VLM observations, and
  detector outputs remain separate.
- Super-resolution images are visualization-only.
- Native pixels and provenance require review before a candidate becomes a
  factual publication claim.

## Public outputs

- `/data/reconstruction/full-pilot-response-evidence-summary.json`
- `/data/reconstruction/full-pilot-response-evidence.geojson`
- `/data/reconstruction/full-pilot-response-evidence.jsonl`
- `/data/reconstruction/full-pilot-response-evidence-crops.jsonl`
- `/timeline#full-pilot-evidence`

Large evidence images are published to the project's public R2 object store
with immutable caching. The page keeps its narrative, metadata, and downloads
usable if an image host is temporarily unavailable.
