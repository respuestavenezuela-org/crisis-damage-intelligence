# Operational Progress

Update this after every work loop. Keep entries factual: what changed, how it was tested, where evidence lives, what remains blocked, and the next recommended action.

## Current Deployment

- Public app: https://crisis-damage-intelligence.vercel.app
- Package/repo path: `/Users/luisrosal/Documents/Codex/2026-06-26/he/outputs/crisis_damage_intelligence_platform`
- Primary app file: `src/components/OperationsConsole.tsx`
- Map implementation: `src/components/map/MapPanel.tsx`
- Catalog: `public/data/catalog.json`

## Current Operational Data State

- AOI12 La Guaira / Caraballeda:
  - Official EMSR884 vector: 120 features.
  - EMS post-event imagery: available.
  - Vantor pre-event reference: available with partial coverage/gaps.
  - VLM before/after comparisons: 107 reviewed, 13 skipped because before coverage was missing/black.
- AOI02 Caracas:
  - Official EMSR884 vector: 17 features.
  - MONIT01 points: 20.
  - Post-event imagery available.
- AOI06 Moron:
  - Official EMSR884 vector: 129 features.
  - MONIT01 points: 96.
  - Post-event imagery available.
- AOI08 San Felipe:
  - Official EMSR884 vector: 43 features.
  - MONIT01 points: 183.
  - Post-event imagery available.
- AOI03 Antimano:
  - Imagery available.
  - No official damage vector currently shown.
- AOI10 Guacara:
  - Imagery available.
  - No official damage vector currently shown.
- Catia La Mar:
  - Microsoft AI4G external prediction layer: 9,134 candidates.
  - This is triage-only and not official EMS confirmation.

## Recent Completed Work

### Before/After VLM For AOI12

- Added `scripts/run_minimax_ems_before_after_review.py`.
- AOI12 catalog now points to `vlm_before_after_review.jsonl`.
- Evidence panel prefers before/after comparison chip where available.
- Public QA verified `ems_00050` shows `dated_pre_event_comparison`.
- Deployment: https://crisis-damage-intelligence.vercel.app

Results:
- reviewed: 107
- skipped no-before/black-before: 13
- likely_destroyed: 26
- possible_major_damage: 33
- uncertain_comparison_problem: 32
- minor_visible_damage: 14
- no_change_visible: 2

QA evidence:
- `qa/local-before-after-vlm-qa.png`
- `qa/vercel-before-after-vlm-qa.png`

### Popup Clear On Background Click

- Map popup opens when clicking a feature.
- Clicking outside a polygon clears selected feature, popup, marker, and highlight.
- Public QA passed.

QA evidence:
- `qa/local-click-background-clears-popup.png`
- `qa/vercel-click-background-clears-popup.png`

### Affected Area Navigation

- Left navigation now shows affected areas instead of technical AOI/layer records.
- Label changed from `Ir a ciudad / AOI` to `Ir a zona afectada`.
- Areas are sorted by aggregated impact signal.
- Current order in Spanish:
  1. La Guaira / Caraballeda / Catia La Mar
  2. San Felipe
  3. Moron
  4. Caracas
  5. Antimano
  6. Guacara

QA evidence:
- `qa/local-city-nav-impact-order.png`
- `qa/vercel-city-nav-impact-order.png`

### Damage Opacity Behavior

- Damage opacity now applies to polygon and point outlines, not only fill.
- Moving opacity slider no longer refocuses the selected feature or forces zoom.
- Public QA passed with opacity `0.52 -> 0.05` and same focused feature.

QA evidence:
- `qa/local-opacity-slider-no-refocus.png`
- `qa/vercel-opacity-slider-no-refocus.png`

## Known Gaps

1. Imagery is still active-area based. The map loads all vector features, but not all AOI imagery at once.
2. Vercel deployment package is too large because chips/tiles are still bundled.
3. Area ranking currently includes external prediction counts in the visible order; this is labeled, but needs better source-weighted ranking.
4. VLM before/after exists for AOI12 only.
5. Mobile end-to-end QA is incomplete.
6. Operator docs may be stale after the recent area-navigation and VLM before/after changes.
7. Human validation workflow is not implemented.
8. External bookmarked/social sources still need systematic review and ingestion only if trustworthy.

## Blockers

- More before imagery coverage is needed before running credible before/after VLM outside AOI12.
- Moving assets to R2/CDN requires confirming public object URLs and updating catalog paths safely.
- Any social media/bookmark evidence requires source verification before it can be shown as operational data.

## Next Recommended Loop

Move large chips/tiles from Vercel to R2/CDN, update `public/data/catalog.json` to point to remote assets, run browser QA for AOI12 before/after chips and tiles, and confirm the deployment package shrinks.

## Loop Entry Template

### YYYY-MM-DD HH:MM Local - Short Title

- Objective:
- Files changed:
- Commands run:
- QA performed:
- Screenshots/evidence:
- Deployment:
- Result:
- Blockers:
- Next recommended action:
