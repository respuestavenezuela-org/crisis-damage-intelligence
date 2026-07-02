<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

## Collaborative Change Safety

When any collaborator, agent, or tool modifies or integrates files that already contain uncommitted user changes, collaborator changes, or coworker/agent changes from the current task, require an explicit overlap rationale before accepting the change.

The rationale must state:

- What prior change is being touched
- Why the new change is necessary
- Whether it preserves, adapts, or replaces the prior work
- Any conflict, regression, or ownership risk

Do not silently overwrite, revert, or subsume another collaborator's work. Keep the rationale in the agent output, handoff notes, final report, commit message, PR description, or review comment as appropriate.
