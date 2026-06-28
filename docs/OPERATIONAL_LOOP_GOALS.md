# Operational Loop Goals

Use this document as the source of truth for the app-improvement loop. The goal is not to maintain documents; the goal is to improve the operational damage intelligence app. These documents exist so each loop stays grounded, remembers what was already done, and does not drift or hallucinate priorities.

Current top priority: expand credible before/after VLM analysis.

## Loop Protocol

1. Read this file.
2. Read `docs/OPERATIONAL_PROGRESS.md`.
3. Pick the highest-leverage unchecked objective that is not blocked, starting with before/after VLM analysis unless there is a concrete reason it cannot proceed.
4. Implement the smallest complete improvement that can be tested.
5. Run build and browser QA.
6. Update `docs/OPERATIONAL_PROGRESS.md` with commands, results, screenshots, blockers, and next recommendation.
7. Commit and deploy only when the change is verified and operationally useful.

## Product Principle

This is an emergency-response damage intelligence platform. It should be fast, simple, bilingual, static-first, cheap to host, and careful about confidence. Never imply that VLM or external predictions are official damage confirmations.

## Priority 1: VLM Before/After Expansion

Goal: use VLM to compare credible pre-event and post-event imagery for more high-value candidates, while clearly labeling source confidence.

Acceptance criteria:
- AOI12 before/after VLM remains the canonical VLM pattern.
- No feature is labeled as before/after reviewed unless both images were actually used.
- Areas with only post-event imagery are not treated as before/after VLM comparisons.
- VLM outputs include evidence chips, prompt/model metadata, source imagery dates, and triage warning.
- Run VLM first on high-value candidates, not every feature by default.
- The app exposes VLM before/after results clearly in the evidence panel and downloads.

Immediate work order:
1. Inventory all areas with usable post-event imagery.
2. Find or generate acceptable pre-event baselines for AOI02, AOI06, AOI08, AOI03, and AOI10.
3. Generate before/after chips where pre-event coverage is nonblank and aligned enough.
4. Run VLM on prioritized candidates:
   - official EMS destroyed/damaged first,
   - then official possibly damaged / MONIT01,
   - then AOI12/Catia La Mar external prediction candidates near populated/high-density zones.
5. Publish per-area VLM JSONL/CSV/summary outputs.
6. Update catalog and UI so VLM comparison coverage is visible.

Candidate next work:
- Identify acceptable pre-event baselines for AOI02, AOI06, AOI08, AOI03, and AOI10.
- Generate before/after chips only where before coverage is nonblank.
- Add per-area VLM coverage metrics: reviewed, skipped no-before, uncertain comparison, likely destroyed.
- Run a small pilot first, compare outputs, then batch the rest.
- AOI03 now has an internal OSM-candidate pilot: 95 VLM-reviewed comparisons and 19 review candidates. Review those candidates before publishing or expanding claims.

## Priority 2: Imagery Loading And Coverage

Goal: make available imagery useful across all affected areas without making the public app slow.

Acceptance criteria:
- The map clearly shows whether each affected area has after imagery, before imagery, both, or only basemap reference imagery.
- AOI12 uses EMS post-event imagery and Vantor pre-event reference where available, clearly labeled.
- Imagery-only AOIs such as Antimano and Guacara are easy to navigate to and do not appear as damage-confirmed areas.
- The app does not attempt to load every heavy raster at once.
- At high zoom, tiles load from pre-generated WebP/COG-derived tiles or object storage/CDN where possible.

Preferred implementation:
- Keep one active imagery area at a time.
- Load all vector features for operational context.
- Lazy-load raster/tile layers only when the user navigates to a zone or the viewport intersects that area.
- Move large tiles/chips out of Vercel to R2/CDN when possible.

## Priority 3: Operational Ranking By Severity And Source

Goal: order affected areas and priority items by response value, not raw feature count alone.

Acceptance criteria:
- Area ranking distinguishes official EMS damaged/destroyed features from MONIT01 points, VLM findings, and external predictions.
- External predictions never dominate official EMS counts without being clearly labeled.
- Suggested ranking weight:
  - Official destroyed/damaged: highest
  - Official possibly damaged / MONIT01: high
  - VLM before-after likely destroyed / possible major: medium-high
  - External prediction candidates: medium, triage-only
  - Imagery-only: low, navigation/context only
- The UI copy explains the ranking source in Spanish and English.

## Priority 4: Static/Free-Tier Performance

Goal: keep the public app fast and deployable on free/low-cost infrastructure.

Acceptance criteria:
- Vercel deployment package is not dominated by chips/tiles/raster assets.
- Large assets live in R2/Supabase Storage or another CDN/object store.
- Public viewing still works if Supabase is down.
- CSV/GeoJSON/KML remain static exports.
- GitHub Actions/manual scripts can regenerate and upload outputs.

Candidate next work:
- Move `public/data/chips` and `public/data/tiles` to R2.
- Update `public/data/catalog.json` URLs to public CDN/R2 paths.
- Keep only small manifests and GeoJSON in the Vercel repo.
- Add a script that validates remote asset URLs before deploy.

## Priority 5: Mobile And Field Usability

Goal: responders can use the platform in the first five minutes on desktop or mobile.

Acceptance criteria:
- Spanish and English are not mixed inside the same language mode.
- Area navigation is understandable without EMS jargon.
- Priority list items center the map reliably and open evidence.
- Click outside polygons clears the popup.
- Damage opacity changes fill and outline without zooming or refocusing.
- Before/after toggle is obvious and does not imply unavailable imagery exists.
- Mobile supports: choose area, inspect priority item, switch before/after, open Google Maps, return to priority list.

Candidate next work:
- Run a full mobile QA script and capture screenshots.
- Fix only functional usability issues first; defer aesthetic redesign unless explicitly requested.

## Priority 6: Documentation And Runbooks

Goal: docs match the current deployed system.

Acceptance criteria:
- README links to current operational loop, runbooks, QA reports, and deployment notes.
- AOI12 runbook reflects that AOI12 v1 is already deployed.
- Operator handoff docs mention current area navigation, AOI12 Vantor before reference, VLM before/after limits, and external prediction caveats.
- "Do not overclaim" warnings are present in English and Spanish.

## Priority 7: External Sources And Validation

Goal: ingest recent, useful external evidence without lowering trust.

Acceptance criteria:
- New external sources are recorded with URL, date accessed, data owner, license/terms if known, geography, confidence, and whether they are official.
- Social/bookmark-derived sources are never treated as official unless confirmed by an authoritative source.
- Added external layers are visually and textually distinct from EMS official data.

## Priority 8: Human Validation Workflow

Goal: support cheap, auditable human review when multiple people help.

Acceptance criteria:
- A reviewer can mark a feature as confirmed, false positive, needs review, or urgent field check.
- Validation status is exportable as static JSONL/CSV.
- The public app can display validation status without requiring live DB access.
- Audit trail records reviewer, timestamp, source, and note when available.

## Current Highest-Leverage Recommendation

Run the next before/after VLM expansion loop. First human-review the 19 AOI03 internal candidates or find stronger pre-event baselines for AOI06/AOI08/AOI10; only then expand VLM batches. Move chips/tiles to R2/CDN immediately after or during that work if deployment weight blocks publishing new VLM outputs.
