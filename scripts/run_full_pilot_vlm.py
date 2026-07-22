#!/usr/bin/env python3
"""Run resumable Qwen or MiniMax analysis on full-pilot temporal stacks.

Completed AOI12 analyses are reused by exact grid bounds. New calls are made
only for newly extracted cells with usable imagery. Post-event-only stacks are
explicitly prevented from being described as before/after comparisons.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from run_aoi12_temporal_response_grid import (  # noqa: E402
    SYSTEM,
    load_env,
    normalize_temporal_result,
    prompt_for,
)
from vlm_provider import call_vlm  # noqa: E402

PROFILE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "full_pilot_temporal_grid"
    / "detail-250m"
)
AOI12_BASE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "aoi12_temporal_response_grid"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("provider", choices=("hf_router", "minimax"))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--seed-only", action="store_true")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def read_by_cell(path: Path) -> dict[str, dict[str, Any]]:
    return {row["cellId"]: row for row in read_rows(path)}


def write_records(path: Path, records: dict[str, dict[str, Any]]) -> None:
    temporary = path.with_suffix(".jsonl.tmp")
    temporary.write_text(
        "".join(
            json.dumps(record) + "\n"
            for record in sorted(records.values(), key=lambda row: row["cellId"])
        )
    )
    temporary.replace(path)


def source_results(provider: str) -> dict[tuple[float, ...], tuple[dict[str, Any], str]]:
    if provider == "hf_router":
        paths = [
            (AOI12_BASE / "detail-250m-enhanced" / "hf_router.jsonl", "aoi12-enhanced-qwen"),
            (AOI12_BASE / "detail-250m" / "hf_primary.jsonl", "aoi12-original-qwen"),
        ]
    else:
        paths = [
            (AOI12_BASE / "detail-250m-enhanced" / "minimax.jsonl", "aoi12-enhanced-minimax"),
            (
                AOI12_BASE / "detail-250m" / "minimax_adjudication.jsonl",
                "aoi12-original-minimax",
            ),
        ]
    results: dict[tuple[float, ...], tuple[dict[str, Any], str]] = {}
    for path, label in reversed(paths):
        for record in read_rows(path):
            results[tuple(record["bounds3857"])] = (record, label)
    return results


def seed_reused(
    provider: str,
    stacks: dict[str, dict[str, Any]],
    records: dict[str, dict[str, Any]],
) -> int:
    sources = source_results(provider)
    seeded = 0
    for cell_id, stack in stacks.items():
        if cell_id in records or not stack.get("reusedFromCellId"):
            continue
        source = sources.get(tuple(stack["bounds3857"]))
        if not source:
            continue
        source_record, source_label = source
        copied = copy.deepcopy(source_record)
        copied.update(
            {
                "cellId": cell_id,
                "centerLon": stack["centerLon"],
                "centerLat": stack["centerLat"],
                "bounds3857": stack["bounds3857"],
                "coveredByAois": stack.get("coveredByAois") or [],
                "analysisReuseSource": source_label,
                "analysisReuseOriginalCellId": source_record["cellId"],
            }
        )
        records[cell_id] = copied
        seeded += 1
    return seeded


def usage(records: dict[str, dict[str, Any]], *, reused: bool) -> dict[str, int | float]:
    totals: Counter[str] = Counter()
    for record in records.values():
        if bool(record.get("analysisReuseSource")) != reused:
            continue
        provider_usage = (record.get("vlmRaw") or {}).get("provider_usage") or {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = provider_usage.get(key)
            if isinstance(value, (int, float)):
                totals[key] += value
    return dict(totals)


def estimated_hf_cost(token_usage: dict[str, int | float]) -> dict[str, Any]:
    """Report a transparent estimate using the current routed-provider rates."""

    input_per_million = float(os.environ.get("HF_INPUT_USD_PER_MILLION", "0.20"))
    output_per_million = float(os.environ.get("HF_OUTPUT_USD_PER_MILLION", "0.70"))
    prompt_tokens = float(token_usage.get("prompt_tokens") or 0)
    completion_tokens = float(token_usage.get("completion_tokens") or 0)
    estimated = (
        prompt_tokens * input_per_million
        + completion_tokens * output_per_million
    ) / 1_000_000
    return {
        "estimatedUsd": round(estimated, 4),
        "inputUsdPerMillionTokens": input_per_million,
        "outputUsdPerMillionTokens": output_per_million,
        "pricingCheckedAt": "2026-07-21",
        "billingNote": "Estimate only; the Hugging Face billing ledger is authoritative.",
    }


def main() -> int:
    load_env(ROOT / ".env")
    load_env(ROOT.parents[1] / ".env")
    args = parse_args()
    os.environ["VLM_PROVIDER"] = args.provider
    if args.provider == "hf_router":
        os.environ.setdefault("HF_VLM_MODEL", "Qwen/Qwen3-VL-30B-A3B-Instruct")
    PROFILE.mkdir(parents=True, exist_ok=True)
    output = PROFILE / f"{args.provider}.jsonl"
    records = read_by_cell(output)
    stacks = read_by_cell(PROFILE / "stacks.jsonl")
    seeded = seed_reused(args.provider, stacks, records)
    write_records(output, records)
    pending = [
        stack
        for cell_id, stack in stacks.items()
        if cell_id not in records
        and stack.get("reusedFromCellId") is None
        and stack.get("selectedScenes")
        and stack.get("stackStatus") != "no_usable_imagery"
    ]
    if args.limit:
        pending = pending[: args.limit]
    if args.seed_only:
        pending = []

    def analyze(stack: dict[str, Any]) -> dict[str, Any]:
        scenes = stack["selectedScenes"]
        paths = [ROOT / scene["chipPath"] for scene in scenes]
        post_only = stack.get("stackStatus") == "post_event_only"
        guardrail_prompt = (
            " No pre-event reference is supplied for this cell. This is post-event-only "
            "triage: do not describe a before/after change, do not infer last_absent_date, "
            "and do not treat non-visibility as evidence that an asset was absent."
            if post_only
            else " This stack includes one pre-event reference and the best usable image per post-event date."
        )
        metadata = {
            "cellId": stack["cellId"],
            "fullPilot": True,
            "stackStatus": stack.get("stackStatus"),
            "coveredByAois": stack.get("coveredByAois") or [],
            "sceneIds": [scene["sceneId"] for scene in scenes],
            "acquisitionUtc": [scene["acquisitionUtc"] for scene in scenes],
        }
        schema_attempts = max(1, int(os.environ.get("VLM_SCHEMA_RETRIES", "3")))
        raw = None
        for schema_attempt in range(1, schema_attempts + 1):
            try:
                raw = call_vlm(
                    SYSTEM,
                    prompt_for(stack, scenes)
                    + guardrail_prompt
                    + " Return every required JSON key, using null, an empty array, "
                    "or a short uncertainty explanation when evidence is unavailable.",
                    paths,
                    metadata=metadata,
                    review_type="temporal_response_comparison",
                )
                break
            except (KeyError, TypeError, ValueError) as exc:
                if schema_attempt == schema_attempts:
                    raise
                print(
                    f"{args.provider} {stack['cellId']}: malformed structured response "
                    f"({exc}); retrying {schema_attempt + 1}/{schema_attempts}",
                    flush=True,
                )
        if raw is None:
            raise RuntimeError(
                f"{args.provider} returned no usable structured result for {stack['cellId']}"
            )
        normalized, notes = normalize_temporal_result(raw, scenes)
        if post_only and normalized.get("last_absent_date") is not None:
            normalized["last_absent_date"] = None
            notes.append("last_absent_date removed because the stack is post-event-only")
        return {
            "cellId": stack["cellId"],
            "centerLon": stack["centerLon"],
            "centerLat": stack["centerLat"],
            "bounds3857": stack["bounds3857"],
            "coveredByAois": stack.get("coveredByAois") or [],
            "stackStatus": stack.get("stackStatus"),
            "scenes": scenes,
            "vlm": normalized,
            "vlmRaw": raw,
            "guardrailNotes": notes,
            "analysisReuseSource": None,
        }

    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(analyze, stack): stack["cellId"] for stack in pending
        }
        for index, future in enumerate(as_completed(futures), 1):
            cell_id = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                print(f"{args.provider} {cell_id}: ERROR {exc}", flush=True)
                continue
            with lock:
                records[cell_id] = record
                write_records(output, records)
            print(
                f"{args.provider} {index}/{len(pending)} {cell_id} "
                f"{record['vlm'].get('response_class')}",
                flush=True,
            )

    eligible = sum(
        bool(stack.get("selectedScenes"))
        and stack.get("stackStatus") != "no_usable_imagery"
        for stack in stacks.values()
    )
    reused_usage = usage(records, reused=True)
    expansion_usage = usage(records, reused=False)
    summary = {
        "version": 1,
        "provider": args.provider,
        "fullPilotStackCells": len(stacks),
        "eligibleStackCells": eligible,
        "completed": len(records),
        "pending": eligible - len(records),
        "reusedAnalyses": sum(bool(record.get("analysisReuseSource")) for record in records.values()),
        "newAnalyses": sum(not bool(record.get("analysisReuseSource")) for record in records.values()),
        "seededThisRun": seeded,
        "usage": {
            "reusedHistorical": reused_usage,
            "newExpansion": expansion_usage,
        },
        "output": str(output.relative_to(ROOT)),
        "guardrails": [
            "Post-event-only stacks are not labeled before/after.",
            "Non-visibility is never proof of absence.",
            "Reused analyses retain their original source scenes and provenance.",
        ],
    }
    if args.provider == "hf_router":
        summary["costEstimate"] = estimated_hf_cost(expansion_usage)
    else:
        summary["costEstimate"] = {
            "estimatedUsd": 0,
            "billingNote": "MiniMax requests use the user's subscription quota.",
        }
    (PROFILE / f"{args.provider}_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
