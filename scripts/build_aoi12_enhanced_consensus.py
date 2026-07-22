#!/usr/bin/env python3
"""Synthesize enhanced AOI12 VLM and object-detector results into evidence queues.

This script is intentionally safe to run while provider batches are incomplete.
It keeps every source observation separate, uses agreement only for triage
priority, and never treats a negative screen as proof that an asset was absent.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "aoi12_temporal_response_grid"
)
PROFILE = BASE / "detail-250m-enhanced"
WALDO_PILOT = (
    BASE
    / "detail-250m-missing-scenes"
    / "waldo30-pilot"
    / "detections.jsonl"
)
WALDO_FULL = PROFILE / "waldo30-full" / "detections.jsonl"
WALDO_FULL_SUMMARY = PROFILE / "waldo30-full" / "summary.json"
EVENT_ORIGIN = datetime.fromisoformat("2026-06-24T18:04:33-04:00")
POSITIVE = {"likely_response_signal", "possible_response_signal"}
NEGATIVE = {"no_response_signal_visible"}
UNCERTAIN = {"uncertain_imagery_or_alignment"}
HEAVY_CLASSES = {"Digger", "Truck", "Bus", "Container"}
ASSET_LEXICON = {
    "heavy_machinery": (
        "excavator",
        "digger",
        "loader",
        "bulldozer",
        "backhoe",
        "crane",
        "heavy machinery",
        "heavy equipment",
        "earthmoving",
    ),
    "trucks_or_large_vehicles": (
        "truck",
        "dump truck",
        "cargo vehicle",
        "large vehicle",
        "bus",
        "convoy",
        "tanker",
    ),
    "temporary_shelter": (
        "tent",
        "shelter",
        "temporary structure",
        "camp",
        "tarpaulin",
        "tarp",
    ),
    "collection_or_staging": (
        "collection center",
        "distribution",
        "staging",
        "organized material",
        "stockpile",
        "supply",
        "gathering",
    ),
    "emergency_or_service_vehicle": (
        "ambulance",
        "fire vehicle",
        "emergency vehicle",
        "military vehicle",
        "utility vehicle",
    ),
    "debris_clearance": (
        "debris",
        "rubble",
        "clearance",
        "clearing",
        "excavated",
        "earthwork",
    ),
}


def read_jsonl(path: Path, key: str = "cellId") -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            records[record[key]] = record
    return records


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False) + "\n"
            for record in records
        )
    )


def bucket(response_class: Any) -> str:
    value = str(response_class or "")
    if value in POSITIVE:
        return "positive"
    if value in NEGATIVE:
        return "negative"
    if value in UNCERTAIN:
        return "uncertain"
    return "missing"


def model_view(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    result = record.get("vlm") or {}
    return {
        "provider": result.get("vlm_provider"),
        "model": result.get("vlm_model"),
        "responseClass": result.get("response_class"),
        "bucket": bucket(result.get("response_class")),
        "confidence": result.get("confidence"),
        "firstVisibleDate": result.get("first_visible_date"),
        "lastAbsentDate": result.get("last_absent_date"),
        "observedAssets": result.get("observed_assets") or [],
        "temporalChange": result.get("temporal_change"),
        "evidence": result.get("evidence"),
        "imageQuality": result.get("image_quality"),
        "alignmentQuality": result.get("alignment_quality"),
        "uncertaintyReason": result.get("uncertainty_reason"),
        "guardrailNotes": result.get("guardrailNotes")
        or record.get("guardrailNotes")
        or [],
    }


def consensus_label(
    hf_view: dict[str, Any] | None, minimax_view: dict[str, Any] | None
) -> str:
    buckets = [
        view["bucket"] for view in (hf_view, minimax_view) if view is not None
    ]
    if len(buckets) < 2:
        return "single_provider_only"
    if all(value == "positive" for value in buckets):
        return "both_positive"
    if all(value == "negative" for value in buckets):
        return "both_negative"
    if all(value == "uncertain" for value in buckets):
        return "both_uncertain"
    if "positive" in buckets and "negative" in buckets:
        return "positive_negative_disagreement"
    if "positive" in buckets and "uncertain" in buckets:
        return "positive_uncertain_disagreement"
    return "negative_uncertain_disagreement"


def exact_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or "/" in value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def hours_after_event(value: Any) -> float | None:
    timestamp = exact_datetime(value)
    if timestamp is None:
        return None
    return round((timestamp - EVENT_ORIGIN).total_seconds() / 3600, 2)


def asset_categories(view: dict[str, Any] | None) -> list[str]:
    if not view or view["bucket"] != "positive":
        return []
    excluded_phrases = (
        "already present",
        "pre-existing",
        "present in pre-event",
        "permanent feature",
        "permanent structure",
        "unchanged",
        "ordinary ",
        "cannot resolve",
        "cannot be resolved",
        "not distinguishable",
    )
    positive_items = []
    for item in view["observedAssets"]:
        text = str(item).strip().lower()
        if text.startswith(("no ", "none ", "absence of ", "without ")):
            continue
        if any(phrase in text for phrase in excluded_phrases):
            continue
        positive_items.append(text)
    text = " | ".join(positive_items)
    return sorted(
        category
        for category, terms in ASSET_LEXICON.items()
        if any(term in text for term in terms)
    )


def aggregate_waldo() -> dict[str, dict[str, Any]]:
    use_full = False
    if WALDO_FULL_SUMMARY.is_file():
        use_full = bool(json.loads(WALDO_FULL_SUMMARY.read_text()).get("coverageComplete"))
    source = WALDO_FULL if use_full else WALDO_PILOT
    scope = (
        "full enhanced priority queue"
        if use_full
        else "20-cell WALDO30 pilot only"
    )
    by_cell: dict[str, dict[str, Any]] = {}
    for row in read_jsonl_rows(source):
        cell = by_cell.setdefault(
            row["cellId"],
            {
                "scope": scope,
                "scenes": [],
                "preCounts": {},
                "postCounts": {},
            },
        )
        counts = Counter(row.get("detectionCounts") or {})
        phase_key = "preCounts" if row.get("phase") == "pre" else "postCounts"
        for label, count in counts.items():
            cell[phase_key][label] = max(
                cell[phase_key].get(label, 0),
                count,
            )
        cell["scenes"].append(
            {
                "sceneId": row.get("sceneId"),
                "acquisitionUtc": row.get("acquisitionUtc"),
                "phase": row.get("phase"),
                "chipPath": row.get("chipPath"),
                "detectionCounts": dict(counts),
            }
        )
    for cell in by_cell.values():
        cell["preCounts"] = dict(sorted(cell["preCounts"].items()))
        cell["postCounts"] = dict(sorted(cell["postCounts"].items()))
        cell["postHeavyClassCount"] = sum(
            cell["postCounts"].get(name, 0) for name in HEAVY_CLASSES
        )
        cell["preHeavyClassCount"] = sum(
            cell["preCounts"].get(name, 0) for name in HEAVY_CLASSES
        )
        cell["heavyClassIncrease"] = (
            cell["postHeavyClassCount"] - cell["preHeavyClassCount"]
        )
    return by_cell


def token_usage(records: dict[str, dict[str, Any]]) -> dict[str, int | float]:
    totals: Counter[str] = Counter()
    for record in records.values():
        usage = (record.get("vlmRaw") or {}).get("provider_usage") or {}
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = usage.get(key)
            if isinstance(value, (int, float)):
                totals[key] += value
    return dict(totals)


def main() -> int:
    stacks = read_jsonl(PROFILE / "stacks.jsonl")
    hf = read_jsonl(PROFILE / "hf_router.jsonl")
    minimax = read_jsonl(PROFILE / "minimax.jsonl")
    waldo = aggregate_waldo()
    target_ids = {
        cell_id
        for cell_id, stack in stacks.items()
        if stack.get("usesNewImagery")
    }
    all_result_ids = sorted((set(hf) | set(minimax)) & target_ids)
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    consensus_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    records: list[dict[str, Any]] = []

    for cell_id in all_result_ids:
        hf_record = hf.get(cell_id)
        minimax_record = minimax.get(cell_id)
        hf_view = model_view(hf_record)
        minimax_view = model_view(minimax_record)
        label = consensus_label(hf_view, minimax_view)
        consensus_counts[label] += 1
        if hf_view and minimax_view:
            matrix[hf_view["bucket"]][minimax_view["bucket"]] += 1

        hf_categories = asset_categories(hf_view)
        minimax_categories = asset_categories(minimax_view)
        categories = sorted(set(hf_categories) | set(minimax_categories))
        category_counts.update(categories)
        positive_dates = sorted(
            {
                str(view["firstVisibleDate"])
                for view in (hf_view, minimax_view)
                if view
                and view["bucket"] == "positive"
                and view.get("firstVisibleDate")
            }
        )
        first_date = min(
            (
                (date, hours_after_event(date))
                for date in positive_dates
                if hours_after_event(date) is not None
            ),
            key=lambda item: item[1],
            default=(None, None),
        )
        score = 0
        reasons: list[str] = []
        if label == "both_positive":
            score += 100
            reasons.append("Qwen and MiniMax both flag a possible response signal")
        elif "positive_" in label:
            score += 75
            reasons.append("providers disagree on a positive response signal")
        elif any(
            view and view["bucket"] == "positive"
            for view in (hf_view, minimax_view)
        ):
            score += 50
            reasons.append("one completed provider flags a possible response signal")
        if first_date[1] is not None and 0 <= first_date[1] <= 72:
            score += 25
            reasons.append("first flagged signal falls within 72 hours of the event")
        if "heavy_machinery" in categories:
            score += 25
            reasons.append("positive VLM observation mentions heavy machinery")
        if "trucks_or_large_vehicles" in categories:
            score += 20
            reasons.append("positive VLM observation mentions trucks or large vehicles")
        if {"temporary_shelter", "collection_or_staging"} & set(categories):
            score += 20
            reasons.append("positive VLM observation mentions shelter or staging")
        waldo_view = waldo.get(cell_id)
        if waldo_view and waldo_view["postHeavyClassCount"] > 0:
            score += 20
            reasons.append("WALDO30 pilot detects a post-event heavy-object class")
        if waldo_view and waldo_view["heavyClassIncrease"] > 0:
            score += 15
            reasons.append("WALDO30 heavy-object count is higher post-event than pre-event")

        source_record = hf_record or minimax_record or {}
        record = {
            "cellId": cell_id,
            "centerLon": source_record.get("centerLon"),
            "centerLat": source_record.get("centerLat"),
            "bounds3857": source_record.get("bounds3857"),
            "consensus": label,
            "priorityScore": score,
            "priorityReasons": reasons,
            "assetCategories": categories,
            "positiveFirstVisibleDates": positive_dates,
            "earliestExactPositiveDate": first_date[0],
            "earliestExactPositiveHoursAfterEvent": first_date[1],
            "models": {
                "hfQwen": hf_view,
                "minimax": minimax_view,
            },
            "waldo30": waldo_view,
            "scenes": source_record.get("scenes")
            or stacks.get(cell_id, {}).get("selectedScenes")
            or [],
            "evidencePolicy": (
                "Triage only. Inspect native source pixels before publication; "
                "negative screens do not prove absence."
            ),
        }
        records.append(record)

    records.sort(key=lambda item: item["cellId"])
    priority = sorted(
        (
            record
            for record in records
            if record["priorityScore"] > 0
            or record["consensus"].endswith("disagreement")
        ),
        key=lambda item: (-item["priorityScore"], item["cellId"]),
    )
    paired = len(set(hf) & set(minimax) & target_ids)
    summary = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "eventOrigin": EVENT_ORIGIN.isoformat(),
        "analysisType": "enhanced-vlm-consensus-with-waldo30-corroboration",
        "targetCellsUsingNewImagery": len(target_ids),
        "hfCoverage": len(set(hf) & target_ids),
        "minimaxCoverage": len(set(minimax) & target_ids),
        "pairedCoverage": paired,
        "hfPending": len(target_ids - set(hf)),
        "minimaxPending": len(target_ids - set(minimax)),
        "coverageComplete": paired == len(target_ids),
        "consensusCounts": dict(sorted(consensus_counts.items())),
        "hfVsMinimaxMatrix": {
            row: dict(sorted(values.items()))
            for row, values in sorted(matrix.items())
        },
        "positiveAssetCategoryCounts": dict(sorted(category_counts.items())),
        "waldo30Cells": len(waldo),
        "waldo30Scope": (
            next(iter(waldo.values()))["scope"] if waldo else "unavailable"
        ),
        "priorityQueueCount": len(priority),
        "usage": {
            "hf": token_usage(hf),
            "minimax": token_usage(minimax),
        },
        "guardrails": [
            "VLM and WALDO30 outputs are triage evidence, not official EMS facts.",
            "A negative screen cannot establish that help or an asset was absent.",
            (
                f"WALDO30 scope is {next(iter(waldo.values()))['scope'] if waldo else 'unavailable'}; "
                "detections may contain false positives."
            ),
            "First-visible time is bounded by image acquisitions, not actual arrival time.",
            "Native source pixels and acquisition metadata must be checked before publication.",
        ],
        "outputs": {
            "cellConsensus": str(
                (PROFILE / "enhanced_consensus.jsonl").relative_to(ROOT)
            ),
            "priorityQueue": str(
                (PROFILE / "enhanced_priority_queue.jsonl").relative_to(ROOT)
            ),
            "report": str(
                (PROFILE / "enhanced_consensus_report.md").relative_to(ROOT)
            ),
        },
    }
    write_jsonl(PROFILE / "enhanced_consensus.jsonl", records)
    write_jsonl(PROFILE / "enhanced_priority_queue.jsonl", priority)
    (PROFILE / "enhanced_consensus_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    report = [
        "# AOI12 enhanced imagery consensus",
        "",
        f"- Generated: `{summary['generatedAt']}`",
        f"- New-imagery target: `{len(target_ids)}` cells",
        f"- HF coverage: `{summary['hfCoverage']}`",
        f"- MiniMax coverage: `{summary['minimaxCoverage']}`",
        f"- Paired coverage: `{paired}`",
        f"- Priority evidence queue: `{len(priority)}`",
        f"- WALDO30 coverage: `{len(waldo)}` cells (`{summary['waldo30Scope']}`)",
        "",
        "## What this produces",
        "",
        "- Cross-provider agreement and disagreement per 250 m cell.",
        "- Exact first-visible acquisition bounds when models return a supplied timestamp.",
        "- Triage categories for heavy machinery, trucks, shelters, staging and debris clearance.",
        "- Separate WALDO30 pilot detections; they are never silently merged into VLM claims.",
        "",
        "## Guardrails",
        "",
        *[f"- {item}" for item in summary["guardrails"]],
        "",
        "Rerun this script at any point; it reads the current resumable provider outputs.",
        "",
    ]
    (PROFILE / "enhanced_consensus_report.md").write_text("\n".join(report))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
