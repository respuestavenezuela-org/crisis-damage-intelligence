# Agent Workflow

## Before Editing

1. Read `AGENTS.md`.
2. Read relevant Next docs under `node_modules/next/dist/docs/` before changing Next behavior.
3. Check `git status --short --branch`.
4. Treat existing dirty changes as user work; do not revert them.

## During Work

- Keep edits scoped.
- Prefer validators/docs/scripts over broad refactors when the risk is process or CI.
- Do not change operational data unless the task is explicitly data publication or validation.
- Add line-specific findings to audit docs when possible.
- Preserve Spanish default UX and low-bandwidth fallback paths.

## Before Handoff

Run the relevant commands and report exact failures:

```bash
npm run lint
npm run typecheck
npm run build
python3 scripts/validate_catalog_schema.py
python3 scripts/validate_mobile_performance_budget.py
```

If a command cannot run, state why and what risk remains.
