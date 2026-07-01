# Agent Control Center

## Mission

Respuesta Venezuela is a public, static-first crisis map for the June 24, 2026 Venezuela earthquake response. It presents Copernicus EMSR884 damage layers, open-source map context, before/after imagery where safely available, and VLM/evidence queues for triage. Primary users may be on modest Android phones, high latency, intermittent links, and low bandwidth.

The public app must remain useful when Supabase, VLM providers, analytics, R2/CDN, or optional services are unavailable. Image quality is operationally important: optimize tiling, caching, range requests, lazy loading, and progressive delivery before reducing visual quality.

## Source Repository

- Canonical GitHub repository: `https://github.com/respuestavenezuela-org/crisis-damage-intelligence`.
- Treat `origin/main` from `respuestavenezuela-org/crisis-damage-intelligence` as the source of truth.
- The old personal remote may exist locally as `takove` for historical reference only; do not open PRs or base new agent work against it unless explicitly instructed.
- New Codex/AI-agent branches should start from the current `origin/main` unless the user names a different base branch.

## Architecture

- Next.js App Router app in `src/app/**`.
- Public data is static under `public/data/**`; public viewing must not require Supabase.
- OpenLayers map lives in `src/components/map/MapPanel.tsx`.
- Operational console and AOI navigation live in `src/components/OperationsConsole.tsx`.
- Heavy tiles, chips, COGs, and future PMTiles belong in R2/CDN or another public object store when production deploy size matters.
- Supabase is optional for tracking/review workflows only.
- VLM is asynchronous evidence generation only; no public runtime VLM call is allowed.

## Next.js Rule

This is not assumed to match your training data. Before changing Next.js APIs, file conventions, config, routing, metadata, or build behavior, read the relevant guide in `node_modules/next/dist/docs/` and heed deprecation notices.

## Required Commands

Run the relevant subset before handing off:

```bash
npm ci
npm run lint
npm run typecheck
npm run build
python3 scripts/validate_catalog_schema.py
python3 scripts/audit_asset_budget.py
python3 scripts/validate_mobile_performance_budget.py
python3 scripts/validate_remote_asset_urls.py --allow-failures
```

If Playwright is present or you changed UI behavior:

```bash
npm run test:e2e
```

Use Portless for local app previews when starting a web server:

```bash
portless crisis-damage npm run dev
```

Share `https://crisis-damage.localhost` if Portless succeeds. If Portless is unavailable, fall back to the normal dev server and explicitly say why.

## Data Safety

- Copernicus EMS official vectors are the source of record.
- VLM, Microsoft AI4G/HDX, MONIT01, heuristics, OSM, and external predictions are triage/evidence only unless explicitly sourced as official EMS.
- Never claim absence of damage from absence of a feature.
- Do not mix external prediction counts into official destroyed/damaged metrics.
- `post_event_only` VLM must not be labeled before/after.
- Before/after VLM requires both dated pre-event and post-event evidence metadata plus chips/summary that pass validation.
- MONIT01 layers stay separate from GRA official vector counts.
- Google Maps and Esri imagery are external visual references, not cached evidence or official verification.

## Performance Rules

- Do not eager-load damage GeoJSON or VLM JSONL for all AOIs on first render.
- Load `catalog.json` first, then only the active AOI's heavy data.
- Cache already visited AOI data in memory when practical.
- Show loading/error states per AOI; if a layer fails, keep metadata, downloads, warnings, and AOI navigation usable.
- Do not parse large GeoJSON/JSONL in the render path.
- Consider Web Workers, PMTiles/MVT/FlatGeobuf, or zoom-simplified vectors only after measuring a real bottleneck.
- Do not commit heavy tiles/chips/rasters/PDFs without an operational reason and updated budget report.
- Do not make the browser load a full COG during initial public render when tiled imagery is available.

## Image Quality Rules

- Do not reduce evidence chips, tiles, or COG quality without a measured before/after report.
- Prefer tile pyramids, COG range requests, cache headers, responsive zooms, and progressive loading over destructive compression.
- Preserve access to original or high-quality imagery when publishing lower-cost previews.
- Versioned tiles/chips should be served with `Cache-Control: public, max-age=31536000, immutable`.
- Validate content type for `.webp`, `.png`, `.jsonl`, `.geojson`, `.kml`, and `.tif`.
- Validate COG Range support before relying on browser-side COG access.
- Never cache or bulk-download external Esri/Google tiles unless license terms explicitly allow it.

## Mobile And Accessibility

- Test at 360, 390, 430, and 768 px widths when changing layout.
- Keep core workflows usable with touch targets near 44 px where layout permits.
- Provide visible focus, semantic buttons/links, ARIA labels for map controls, and keyboard access for filters, language, before/after, downloads, and priority items.
- Do not rely only on color for severity; include labels or text context.
- Respect reduced-motion preferences.
- Safe areas and fixed rails/toolbars must not cover critical AOI metadata, downloads, or fallback text.
- Spanish is the default operational language; use correct accents where possible.

## Analytics And Privacy

- Do not collect PII, names, emails, free text, exact user location, feature ids in analytics, or full external URLs.
- Allowed event properties are coarse: AOI id, city id, language, mode, filter, basemap, file format, chip kind, surface, rank, status, and triage class.
- Analytics providers are optional. The app must work when analytics scripts are disabled or blocked.
- Automatic outgoing-link tracking must stay disabled unless a privacy review proves URLs are sanitized.

## CI/CD Rules

- CI must keep build/lint/typecheck/data validation separate from flaky external network checks.
- Remote asset validation may run on schedule or manual dispatch and upload reports; it should not block ordinary PRs because public R2/CDN can have transient failures.
- Ingest workflows may open PRs with generated static outputs, but must not auto-publish official claims without human review.
- Do not use secrets on PRs from forks.
- Upload build/test artifacts on CI failure where useful.

## AI Coworker Delegation

For complex, ambiguous, multi-file, test-sensitive, debugging-heavy, or architecturally risky tasks, Codex may delegate bounded subtasks to external AI coworker CLIs such as `claude -p`, `claude-main -p`, `claude-alt -p`, and `opencode run` when available.

There are two modes:

- Advisory Mode: coworkers propose plans, reviews, candidate patches, tests, debugging hypotheses, architecture critiques, or docs.
- Executor Mode: coworkers may perform real implementation work, but only in isolated git worktrees/branches assigned to them.

Core rule: `Coworkers may implement in isolation. Codex integrates.`

Codex remains the lead engineer. Codex must inspect the repo, send only minimal safe context, capture outputs/logs, check completion markers, review diffs, integrate accepted changes, validate locally, and report what was accepted, adapted, rejected, incomplete, or failed.

Use a local mailbox: `.codex/coworkers/tasks/`, `.codex/coworkers/outputs/`, `.codex/coworkers/logs/`, `.codex/coworkers/worktrees/`.

Every coworker task must request `COMPLETED_COWORKER_TASK: yes`. Missing markers, quota errors, abrupt endings, non-zero exits, auth errors, or incomplete code blocks mean the output is partial and untrusted.

Coworkers must not directly modify the main working tree by default. Coworkers must not commit, push, delete branches, run destructive commands, modify secrets, or alter production deployment settings unless explicitly authorized.

## Forbidden Changes

- Do not add a mandatory database, paid map SDK, live VLM call, or private service to public runtime.
- Do not commit `.env`, service role keys, tokens, R2/Supabase/Vercel credentials, local absolute paths, or private URLs.
- Do not reclassify external predictions as official EMS damage.
- Do not hide uncertainty, source labels, or "triage only" warnings.
- Do not shrink imagery quality as a cosmetic optimization.
- Do not add repo-level Portless config unless explicitly requested.

## Adding A New AOI Safely

1. Generate CSV/GeoJSON/KML from official EMS products or label the AOI as imagery-only/external-triage.
2. Put small public metadata under `public/data/aoi/<aoi-id>/`.
3. Put heavy chips/tiles/rasters in R2/CDN where possible.
4. Add a catalog entry with source, status, bounds, center, downloads, layers, imagery metadata, and metrics.
5. Keep official, MONIT01, external prediction, and VLM metrics separate.
6. Run:

```bash
python3 scripts/validate_catalog_schema.py
python3 scripts/audit_asset_budget.py
python3 scripts/validate_mobile_performance_budget.py
python3 scripts/validate_remote_asset_urls.py --allow-failures
```

7. Update docs if operational caveats, imagery coverage, or licensing changed.

## Updating Image Assets Safely

- Record source, acquisition time, sensor, license/terms, bytes, and SHA256 when available.
- Validate R2/CDN 200, Range, content type, and cache headers.
- If tiles/chips are mirrored, run remote validation before deploying a pruned Vercel package.
- Keep high-zoom tiles needed for inspection; use low-zoom previews only as progressive UX, not as replacement for final quality.

## PR Checklist

- [ ] Public app works without Supabase, VLM, or analytics.
- [ ] No secrets, local absolute paths, or private URLs.
- [ ] Official vs triage labels remain clear.
- [ ] No first-render loading of all AOI GeoJSON/JSONL.
- [ ] Mobile fallback shows AOI metadata/downloads if imagery or vectors fail.
- [ ] Image quality is preserved or any reduction is documented with visual QA.
- [ ] `npm run lint`, `npm run typecheck`, `npm run build`, and Python validators were run or explicitly reported as not run.
- [ ] CI changes do not deploy official claims automatically.

## Agent Output

In final handoff, include: changed files, commands run with results, P0/P1/P2 risks, performance baseline, remaining work, and any uncertainty. Be precise; cite file paths and lines when reporting findings.
