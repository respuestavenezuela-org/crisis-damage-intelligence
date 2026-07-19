# Copilot Instructions

Read `AGENTS.md` first. It is the canonical control document for this crisis-response map.

Critical rules:

- Public runtime must stay static-first and work without Supabase, VLM, or analytics.
- Do not overclaim: EMS official vectors are source of record; VLM, MONIT01, Microsoft/HDX, OSM, and heuristics are triage/evidence only.
- Do not eager-load all AOI GeoJSON/JSONL on first render.
- Do not commit secrets, `.env`, local absolute paths, or private URLs.
- Do not reduce image/chip/tile quality without measured visual QA and preserved access to originals.
- Run `npm run lint`, `npm run typecheck`, `npm run build`, `python3 scripts/validate_catalog_schema.py`, and `python3 scripts/validate_mobile_performance_budget.py` before handoff when relevant.
