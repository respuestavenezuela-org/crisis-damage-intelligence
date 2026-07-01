# Mobile Low-Bandwidth Runbook

## Goal

Keep the app useful on 360-430 px Android-class devices with slow, lossy, or intermittent networks.

## Minimum Useful State

The user should see:

- AOI list;
- source/status/confidence label;
- KPIs from catalog metadata;
- downloads;
- last update;
- imagery availability warning;
- clear triage/official distinction.

This state must not require Supabase, VLM, analytics, or all AOI GeoJSON/JSONL.

## Field Checks

```bash
npm run build
python3 scripts/audit_asset_budget.py
python3 scripts/validate_mobile_performance_budget.py
npm run test:e2e -- --project=chromium
```

Automated Playwright coverage currently checks:

- default 390 px critical AOI workflow, lazy active-AOI data loading, mobile sheet controls, filters, before/after mode, and priority zoom;
- 360, 430, and 768 px viewport essentials with local raster stubs so tests do not depend on remote tiles or COGs;
- 360 px damage GeoJSON plus VLM JSONL failure, confirming visible error status, active AOI context, mobile operational brief, and CSV download reachability.

Manual viewport checks:

- 360 x 740;
- 390 x 844;
- 430 x 932;
- 768 x 1024.

Verify:

- AOI list is visible before heavy map interaction.
- Downloads remain reachable on mobile.
- Toolbar does not cover all operational context.
- AOI change does not crash if damage/VLM fetch fails.
- Priority click zooms to 18 when data is available.
- Before/after controls are disabled or labeled when imagery is missing.

Manual low-bandwidth checks still required:

- throttle a production-like build to Slow 3G/Fast 3G in Chrome DevTools and confirm the catalog-backed shell appears before imagery is usable;
- test on at least one modest Android device or Android emulator because Playwright viewport checks do not cover browser UI chrome, memory pressure, or touch latency;
- verify safe-area behavior with the mobile sheet open and closed at 360 px and 430 px;
- verify that failed first tiles or blocked COG requests do not hide AOI metadata, downloads, or the operational brief;
- confirm external Google/Esri references are not cached or bulk-downloaded during testing.

## Core Web Vitals Gaps

Core Web Vitals are not yet a blocking automated gate. Before production launch or a heavy asset change, capture a production-like Lighthouse or WebPageTest run for 360 px mobile with cache cold and warm:

- LCP for the static shell and first useful AOI context;
- CLS while the mobile sheet, toolbar, and map initialize;
- INP while opening controls, switching filters, and selecting priority rows;
- transferred bytes before the first active AOI metadata/downloads are usable;
- number and size of tile/chip/COG requests with remote assets enabled.

Record the run in `ops/performance_audit/` or the release handoff. Treat regressions in first useful shell, download reachability, or AOI metadata visibility as higher priority than visual polish.

## Poor Network Strategy

- Cache only owned app shell, catalog minimum, AOI metadata, and static exports if a future service worker is added.
- Do not cache third-party Esri/Google tiles.
- Heavy imagery should use R2/CDN cache headers and tile pyramids.
- If imagery fails, keep text metadata and downloads usable.
- If vector loading fails, show the AOI source/status and download links.
