# AOI12 temporal response grid — human review report

Updated: 2026-07-21

## Decision

The publishable pass uses 250 m cells rendered at 768 × 768 pixels, or
approximately 0.326 m per output pixel. This is close to the useful 0.35–0.50 m
ground sampling distance of the source imagery. No super-resolution output was
used for detection, adjudication, or publication.

The earlier 500 m / 512 px pass (approximately 0.98 m per pixel) is retained as
calibration only. It produced too many object and context errors to support
site-level claims.

## Coverage and models

- Grid cells considered: 1,022
- Cells with usable temporal coverage: 734
- HF primary model: `Qwen/Qwen3-VL-30B-A3B-Instruct` on all 734 cells
- Primary likely signals: 16
- Primary possible signals: 171
- Priority cells sent to secondary review: 226
- HF secondary model: `Qwen/Qwen2.5-VL-72B-Instruct` on 206 cells
- Early secondary model: `CohereLabs/command-a-vision-07-2025` on 20 cells
- Cross-model positive agreements: 46
- Highest-signal or agreement cells checked by a human: 55
- MiniMax: not run because `MINIMAX_API_KEY` was unavailable

MiniMax remains useful as a selective third opinion on positive or disputed
cells. It should not run on all 734 cells, and its output should never be the
sole basis for publication.

## Published findings

### Caraballeda golf course

Cell: `aoi12_r018_c111`

The June 26 official image (+41 hours) shows a new organized concentration of
vehicles and rectangular objects on ground that was largely empty before the
earthquakes. Two June 29 Vantor acquisitions show a much more developed site
with temporary structures, vehicles, and organized areas. June 28 ground
reporting identifies the golf course as a hospital, helipad, and shelter;
later official reporting identifies an operations post there.

The imagery does not support a count of occupants or a sufficiency assessment.

### Estadio Jorge Luis García Carneiro

Cell: `aoi12_r013_c083`

The stadium field is largely open on June 26. By June 29 it is densely occupied
by temporary structures, vehicles, and organized internal areas. PAHO/WHO's
July 2 deployment map places a fixed Red Cross emergency medical team at the
stadium. The exact opening time is bounded only to the June 26–29 interval.

### Punta de Mulatos waterfront lot

Cell: `aoi12_r013_c073`

The lot has few objects on June 26 and rows of large white modules and vehicles
on June 29. The change is compatible with a medical, logistics, or
accommodation site. Exact function and operator remain unresolved.

### El Palmar Oeste track

Cell: `aoi12_r019_c103`

The track is essentially clear on June 26 and occupied by organized temporary
modules, tents, and vehicles on June 29. Response use is inferred from the
dated change and disaster context; function and operator remain unresolved.

### Los Corales vehicle lot

Cell: `aoi12_r019_c107`

About fifteen vehicle-scale objects appear in ordered rows by June 26 and
persist in a reorganized layout on June 29. The images do not support reliable
vehicle typing or a claim that the lot was a response staging area. This
observation remains unresolved.

## False-positive patterns

Human review rejected or downgraded many dual-model agreements:

- permanent container and truck yards interpreted as logistics staging;
- pre-existing construction equipment interpreted as emergency machinery;
- rubble, roof fragments, and shadows interpreted as tents or vehicles;
- ordinary airport aircraft and cargo interpreted as humanitarian movement;
- cloud and haze interpreted as smoke;
- newly visible destruction interpreted as organized response activity.

Four early agreements between the primary model and Command A Vision all
failed native-pixel review. Agreement is therefore a prioritization signal, not
verification.

## Remaining uncertainty

- The scan does not cover every street or every hour.
- A feature not visible in a dated image cannot be treated as absent.
- The imagery cannot reliably count people, determine whether people slept at
  a site, identify owners/operators, or measure whether assistance was
  sufficient.
- The July 5 official image is cloud-obscured or lacks useful pixels at most
  published response sites.
