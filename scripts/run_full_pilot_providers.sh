#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="$ROOT/ops/data_acquisition_plan/full_pilot_temporal_grid/detail-250m"
PYTHON="${PYTHON:-/opt/homebrew/bin/python3.14}"
TARGET_CELLS=2283
HF_WORKERS="${HF_WORKERS:-8}"
MINIMAX_WORKERS="${MINIMAX_WORKERS:-8}"

mkdir -p "$PROFILE/runtime"
cd "$ROOT"

summary_value() {
  local path="$1"
  local key="$2"
  "$PYTHON" - "$path" "$key" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
key = sys.argv[2]
if not path.is_file():
    print(-1)
else:
    print(json.loads(path.read_text()).get(key, -1))
PY
}

run_hf() {
  if [[ -f "$HOME/.cache/huggingface/token" ]]; then
    export HF_TOKEN
    HF_TOKEN="$(<"$HOME/.cache/huggingface/token")"
  fi
  HF_ROUTER_RETRIES=8 \
  HF_ROUTER_RETRY_SECONDS=8 \
  HF_ROUTER_TIMEOUT_SECONDS=300 \
  HF_ROUTER_MAX_TOKENS=900 \
    "$PYTHON" scripts/run_full_pilot_vlm.py hf_router --workers "$HF_WORKERS" \
      >> "$PROFILE/runtime/hf_router.log" 2>&1
}

run_minimax() {
  MINIMAX_MAX_CALLS=2000 \
  MINIMAX_RETRIES=75 \
  MINIMAX_QUOTA_RETRY_SECONDS=300 \
    "$PYTHON" scripts/run_full_pilot_vlm.py minimax --workers "$MINIMAX_WORKERS" \
      >> "$PROFILE/runtime/minimax.log" 2>&1
}

while true; do
  stack_count="$(wc -l < "$PROFILE/stacks.jsonl" | tr -d ' ')"
  printf 'provider-cycle stacks=%s target=%s\n' "$stack_count" "$TARGET_CELLS" \
    | tee -a "$PROFILE/runtime/providers.log"

  run_hf &
  hf_pid=$!
  run_minimax &
  minimax_pid=$!
  wait "$hf_pid"
  wait "$minimax_pid"

  stack_count="$(wc -l < "$PROFILE/stacks.jsonl" | tr -d ' ')"
  hf_pending="$(summary_value "$PROFILE/hf_router_summary.json" pending)"
  minimax_pending="$(summary_value "$PROFILE/minimax_summary.json" pending)"
  printf 'provider-cycle-complete stacks=%s hf_pending=%s minimax_pending=%s\n' \
    "$stack_count" "$hf_pending" "$minimax_pending" \
    | tee -a "$PROFILE/runtime/providers.log"

  if [[ "$stack_count" -ge "$TARGET_CELLS" \
    && "$hf_pending" -eq 0 \
    && "$minimax_pending" -eq 0 ]]; then
    break
  fi
  sleep 15
done
