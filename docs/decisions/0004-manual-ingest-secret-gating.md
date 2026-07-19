# Decision 0004: Gate optional ingest uploads without secrets in expressions

- Status: Accepted
- Date: 2026-07-19
- Commit: `Fix manual ingest secret gating`

## Context

GitHub rejected the existing manual EMSR884 ingest workflow before creating any
jobs because its upload step referenced `secrets.*` directly in an `if`
expression. GitHub Actions does not permit secrets to be referenced directly in
conditionals. The object-storage upload must remain optional because the ingest
and pull-request workflow should still work when S3/R2 credentials are absent.

## Decision

1. Add a configuration-probe step that maps the four optional object-storage
   secrets into that step's environment.
2. Check only whether every required value is non-empty.
3. Write a non-sensitive `configured=true|false` boolean to `GITHUB_OUTPUT`.
4. Gate the upload step on the probe output.
5. Map the actual secrets into the upload step separately, preserving their
   existing shell quoting and avoiding secret values in logs or outputs.

## Alternatives rejected

- Referencing `secrets.*` directly in `if`, which invalidates the workflow.
- Mapping the secrets at job scope, which would expose them to unrelated ingest
  and pull-request steps.
- Making object-storage credentials mandatory for the static ingest workflow.
- Printing secret values or partial values while diagnosing configuration.

## Consequences

- GitHub can parse and register the manual workflow.
- Ingest and pull-request creation remain usable without object storage.
- Upload runs only when the complete credential set is present.
- Two steps receive the optional secrets instead of the whole job.

## Validation

- YAML parsing and repository secret-pattern scan.
- GitHub Actions workflow registration on the follow-up `main` push.
- No secret value is written to `GITHUB_OUTPUT` or command output.
