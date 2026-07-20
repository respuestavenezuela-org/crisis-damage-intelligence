#!/usr/bin/env bash

set -euo pipefail

case "${VERCEL_ENV:-}" in
  production)
    python3 scripts/validate_remote_asset_urls.py \
      --report /tmp/cdi-remote-asset-validation.json
    python3 scripts/build_vercel_remote_asset_package.py \
      --prepare-package . \
      --prune-heavy
    ;;
  preview)
    python3 scripts/build_vercel_remote_asset_package.py \
      --prepare-package . \
      --prune-heavy \
      --skip-remote-validation-report
    ;;
  *)
    echo "Unsupported VERCEL_ENV=${VERCEL_ENV:-unset}" >&2
    exit 1
    ;;
esac

npm ci
