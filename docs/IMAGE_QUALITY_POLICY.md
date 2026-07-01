# Image Quality Policy

## Non-Negotiables

- Evidence chips and inspection tiles must remain useful for human review.
- Never lower quality as a blind byte-size optimization.
- Preserve original/high-quality imagery access when publishing previews or tiles.
- Official EMS imagery, Vantor/OpenData before imagery, Esri visual reference, Google Maps links, and external predictions must remain clearly labeled.

## Preferred Optimizations

- Tile pyramids over large one-shot raster loads.
- COG range requests only after Range and content-type validation.
- CDN/R2 cache headers: `public, max-age=31536000, immutable` for versioned tiles/chips.
- Low-zoom first, high-zoom later, without replacing final high-quality detail.
- Lazy-load evidence chips only after feature selection.

## Required QA For Quality Changes

Document:

- old bytes and new bytes;
- visual before/after screenshots or contact sheet;
- affected AOIs and zoom levels;
- quality factor or generation settings;
- operational risk;
- rollback path and original asset location.

## What Not To Cache

Do not bulk-download, cache, or redistribute Esri/Google/external basemap tiles unless license terms explicitly allow it.
