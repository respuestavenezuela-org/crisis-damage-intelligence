# Decision 0005: Keep Vercel deployment policy in a versioned install wrapper

- Status: Accepted
- Date: 2026-07-20
- Commit: `Fix Vercel production deployment configuration`

## Context

The first production deployments after the consolidation never reached the
application build. Vercel rejected `vercel.json` during schema validation
because its inline `installCommand` was longer than the platform's 256-character
limit. GitHub CI still passed because the failure was specific to Vercel's
project-configuration parser. The previous production deployment therefore
continued serving `respuestavenezuela.org`.

The rejected command contained important deployment policy: production must
perform live remote-asset validation and prune local heavy assets; previews
must prepare the same pruned package without a flaky live-network gate.

## Decision

1. Replace the long inline `installCommand` with
   `bash scripts/vercel_install.sh`.
2. Move the existing production, preview, unsupported-environment, and
   `npm ci` behavior into that versioned wrapper without weakening any gate.
3. Keep `vercel.json` limited to short platform configuration and keep the
   operational policy reviewable and testable as ordinary shell code.
4. Continue failing closed for unknown or missing `VERCEL_ENV` values.

## Alternatives rejected

- Shortening or removing remote validation to fit the JSON field, which would
  weaken the production asset-safety policy.
- Moving the command into Vercel dashboard settings, which would hide important
  deployment behavior outside version control.
- Deploying the raw local asset tree to bypass package preparation.
- Manually aliasing the prior build, which would leave the consolidated changes
  absent from production.

## Consequences

- Vercel can accept the project configuration and start the production build.
- Production and preview preparation retain their prior behavior.
- Deployment logic can be shell-syntax checked independently.
- Changes to the wrapper require the same review as other deployment code.

## Validation

- Parse `vercel.json` and verify the install command remains below Vercel's
  256-character limit.
- Run `bash -n scripts/vercel_install.sh`.
- Verify missing or unsupported `VERCEL_ENV` fails closed.
- Run the standard repository validation suite.
- Confirm the resulting Vercel deployment is ready and
  `respuestavenezuela.org` serves the new production build.
