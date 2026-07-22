#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="$ROOT/ops/data_acquisition_plan/full_pilot_temporal_grid/detail-250m"
PYTHON="${PYTHON:-/opt/homebrew/bin/python3.14}"
WALDO_PYTHON="${WALDO_PYTHON:-$ROOT/.venv-waldo/bin/python}"
TARGET_CELLS=2283

mkdir -p "$PROFILE/runtime" "$PROFILE/waldo30-full/runtime"
cd "$ROOT"

analysis_ready() {
  "$PYTHON" - "$PROFILE" "$TARGET_CELLS" <<'PY'
import json
import pathlib
import sys

profile = pathlib.Path(sys.argv[1])
target = int(sys.argv[2])
stacks = profile / "stacks.jsonl"
if not stacks.is_file():
    print("false")
    raise SystemExit
stack_count = sum(1 for line in stacks.open() if line.strip())
summaries = [profile / "hf_router_summary.json", profile / "minimax_summary.json"]
ready = stack_count >= target and all(
    path.is_file() and json.loads(path.read_text()).get("pending") == 0
    for path in summaries
)
print(str(ready).lower())
PY
}

while [[ "$(analysis_ready)" != "true" ]]; do
  sleep 60
done

"$PYTHON" scripts/validate_full_pilot_imagery.py --profile-dir "$PROFILE" --workers 8
"$PYTHON" scripts/build_full_pilot_consensus.py
while [[ -f "$PROFILE/waldo30-full/runtime/prepass.active" ]]; do
  sleep 60
done
"$WALDO_PYTHON" scripts/run_waldo_aoi12_priority.py \
  --profile-dir "$PROFILE" \
  --all-cells \
  --confidence 0.15 \
  >> "$PROFILE/waldo30-full/runtime/full.log" 2>&1
"$PYTHON" scripts/build_full_pilot_consensus.py
"$WALDO_PYTHON" scripts/generate_aoi12_evidence_crops.py \
  --profile-dir "$PROFILE" \
  --max-pairs 500 \
  --sr-pairs 100 \
  --min-confidence 0.25 \
  --max-per-scene 3
"$PYTHON" scripts/build_aoi12_response_timeline.py \
  --profile-dir "$PROFILE" \
  --scope "La Guaira-Caraballeda-Catia La Mar full 250 m pilot" \
  --scope-limit "Full three-city pilot extent; external Microsoft geometries define triage coverage only and are not official damage labels."
"$PYTHON" scripts/build_full_pilot_public_package.py
"$PYTHON" scripts/validate_full_pilot_public_package.py

ARCHIVE_DIR="$ROOT/output/full-pilot-publication"
ARCHIVE="$ARCHIVE_DIR/full-pilot-response-evidence.tar.gz"
mkdir -p "$ARCHIVE_DIR"
tar -czf "$ARCHIVE" \
  public/data/chips/full-pilot-response-evidence \
  public/data/reconstruction/full-pilot-response-evidence-summary.json \
  public/data/reconstruction/full-pilot-response-evidence.geojson \
  public/data/reconstruction/full-pilot-response-evidence.jsonl \
  public/data/reconstruction/full-pilot-response-evidence-crops.jsonl
shasum -a 256 "$ARCHIVE" > "$ARCHIVE.sha256"
printf 'Full-pilot publication archive: %s\n' "$ARCHIVE"
