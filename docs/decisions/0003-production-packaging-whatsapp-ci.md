# Decision 0003: Gate production assets and publish only privacy-safe operations data

- Status: Accepted
- Date: 2026-07-18
- Commit: `Enforce remote-asset production and restore operational inputs`

## Context

The development checkout contains approximately 267 MiB under `public/data`,
including tens of thousands of local tiles and hundreds of evidence chips.
Production needs those assets on public object storage without allowing stale
validation, broken rewrites, or a silent loss of imagery. A local WhatsApp
export was also available for regeneration, while raw or exact message data was
not suitable for the public repository. CI drafts and deployment exclusions in
the stashes needed selective adaptation rather than wholesale restoration.

## Decisions

1. Keep the complete imagery set in the development checkout for offline and
   low-dependency testing, but deploy a validated remote-asset package.
2. Make production preparation fail closed:
   - Rerun public remote checks in production.
   - Require a green attestation no more than 24 hours old.
   - Require the attestation fingerprint to match all current tile/chip
     references.
   - Require nonzero tile, chip, and COG samples.
   - Verify status, content type, immutable cache headers, and COG byte-range
     behavior.
   - Refuse packages with local heavy directories, surviving local references,
     more than 15,000 files, or more than 250 MB.
3. Separate deployment modes. Production performs strict live network checks;
   previews run deterministic rewrite, prune, and package guards so transient
   external outages do not block ordinary PR previews.
4. Keep package preparation idempotent. A second preparation must not duplicate
   remote hostnames, and a generated rollback package may reuse prior sample
   paths only when its source fingerprint matches before refetching them.
5. Regenerate WhatsApp-derived public data only as aggregate zones. Record that
   the source is configured, but write no raw messages, exact points, free text,
   names, phones, addresses, or private local paths.
6. Restore deterministic CI for lint, typecheck, build, data validation,
   performance budgets, and Playwright. Keep scheduled/manual external network
   validation separate from normal PR gates.
7. Preserve every E2E assertion. Extend only the critical mobile test timeout
   where four-worker contention exceeded the prior global limit.
8. Reject stashed raw ZIPs, binaries, screenshots, PDFs, session drafts, logs,
   and large generated artifacts. Adapt the useful CI and deployment intent
   without committing workstation output.

## Alternatives rejected

- Deploying the raw 267 MiB public-data tree to Vercel.
- Trusting `.vercelignore` alone for every Git and CLI deployment path.
- Allowing an indefinitely old or zero-sample remote report.
- Running flaky third-party network checks on every PR.
- Publishing raw or exact WhatsApp data.
- Reducing tile or chip quality to meet a deployment limit.

## Consequences

- Production intentionally stops when R2/CDN evidence is unavailable or the
  source/attestation relationship cannot be proven.
- Preview builds can succeed during a remote outage, but remote imagery may be
  unavailable in that preview.
- The generated production package is about 21.8 MiB and 327 files, while the
  larger development dataset remains available locally.
- Representative remote validation is not exhaustive across every tile, so the
  scheduled package workflow and live production preflight remain necessary.

## Validation

- 72 tile, 32 chip, and 12 COG checks; 116 total with zero failures or quality
  warnings in the recorded attestation.
- Production, preview, rollback, fingerprint-mismatch, stale-attestation,
  zero-sample, idempotence, and exact package-count proofs.
- `npm ci`, lint, typecheck, production build, catalog/data/performance
  validators, and all 25 Playwright tests.
- Final independent Codex review reported no actionable findings.
