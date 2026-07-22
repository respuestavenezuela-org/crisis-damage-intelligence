#!/usr/bin/env python3
"""Build cross-provider consensus for the full three-city imagery pilot."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_aoi12_enhanced_consensus import (  # noqa: E402
    asset_categories,
    consensus_label,
    hours_after_event,
    model_view,
    token_usage,
)

PROFILE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "full_pilot_temporal_grid"
    / "detail-250m"
)
WALDO = PROFILE / "waldo30-full" / "detections.jsonl"
WALDO_SUMMARY = PROFILE / "waldo30-full" / "summary.json"
HEAVY_CLASSES = {"Digger", "Truck", "Bus", "Container"}


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


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def aggregate_waldo() -> dict[str, dict[str, Any]]:
    if not WALDO.is_file():
        return {}
    by_cell: dict[str, dict[str, Any]] = {}
    for row in read_rows(WALDO):
        cell = by_cell.setdefault(
            row["cellId"],
            {"preCounts": {}, "postCounts": {}, "scenes": []},
        )
        phase_key = "preCounts" if row.get("phase") == "pre" else "postCounts"
        for label, count in (row.get("detectionCounts") or {}).items():
            cell[phase_key][label] = max(cell[phase_key].get(label, 0), count)
        cell["scenes"].append(
            {
                "sceneId": row.get("sceneId"),
                "acquisitionUtc": row.get("acquisitionUtc"),
                "phase": row.get("phase"),
                "detectionCounts": row.get("detectionCounts") or {},
            }
        )
    for cell in by_cell.values():
        cell["preCounts"] = dict(sorted(cell["preCounts"].items()))
        cell["postCounts"] = dict(sorted(cell["postCounts"].items()))
        cell["postHeavyClassCount"] = sum(
            cell["postCounts"].get(label, 0) for label in HEAVY_CLASSES
        )
        cell["preHeavyClassCount"] = sum(
            cell["preCounts"].get(label, 0) for label in HEAVY_CLASSES
        )
        cell["heavyClassIncrease"] = (
            cell["postHeavyClassCount"] - cell["preHeavyClassCount"]
        )
    return by_cell


def main() -> int:
    stacks = read_by_cell(PROFILE / "stacks.jsonl")
    hf = read_by_cell(PROFILE / "hf_router.jsonl")
    minimax = read_by_cell(PROFILE / "minimax.jsonl")
    waldo = aggregate_waldo()
    eligible = {
        cell_id
        for cell_id, stack in stacks.items()
        if stack.get("selectedScenes")
        and stack.get("stackStatus") != "no_usable_imagery"
    }
    record_ids = sorted((set(hf) | set(minimax)) & eligible)
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    consensus_counts: Counter[str] = Counter()
    category_counts: Counter[str] = Counter()
    area_counts: Counter[str] = Counter()
    records = []
    for cell_id in record_ids:
        stack = stacks[cell_id]
        hf_view = model_view(hf.get(cell_id))
        minimax_view = model_view(minimax.get(cell_id))
        label = consensus_label(hf_view, minimax_view)
        consensus_counts[label] += 1
        if hf_view and minimax_view:
            matrix[hf_view["bucket"]][minimax_view["bucket"]] += 1
        categories = sorted(
            set(asset_categories(hf_view)) | set(asset_categories(minimax_view))
        )
        category_counts.update(categories)
        area_counts.update(stack.get("coveredByAois") or [])
        positive_dates = sorted(
            {
                view.get("firstVisibleDate")
                for view in (hf_view, minimax_view)
                if view
                and view["bucket"] == "positive"
                and view.get("firstVisibleDate")
            }
        )
        dated = [
            (date, hours_after_event(date))
            for date in positive_dates
            if hours_after_event(date) is not None
        ]
        first_date, first_hours = min(
            dated,
            key=lambda item: item[1],
            default=(None, None),
        )
        score = 0
        reasons = []
        if label == "both_positive":
            score += 100
            reasons.append("Qwen and MiniMax both positive")
        elif label.startswith("positive_"):
            score += 75
            reasons.append("providers disagree on a positive signal")
        elif any(
            view and view["bucket"] == "positive"
            for view in (hf_view, minimax_view)
        ):
            score += 50
            reasons.append("one completed provider is positive")
        if first_hours is not None and 0 <= first_hours <= 72:
            score += 25
            reasons.append("first-visible bound is within 72 hours")
        if "heavy_machinery" in categories:
            score += 25
            reasons.append("positive observation mentions heavy machinery")
        if "trucks_or_large_vehicles" in categories:
            score += 20
            reasons.append("positive observation mentions trucks or large vehicles")
        if {"temporary_shelter", "collection_or_staging"} & set(categories):
            score += 20
            reasons.append("positive observation mentions shelter or staging")
        waldo_view = waldo.get(cell_id)
        if waldo_view and waldo_view["postHeavyClassCount"] > 0:
            score += 20
            reasons.append("WALDO30 detects a post-event heavy-object class")
        if waldo_view and waldo_view["heavyClassIncrease"] > 0:
            score += 15
            reasons.append("WALDO30 post-event maximum exceeds pre-event maximum")
        records.append(
            {
                "cellId": cell_id,
                "centerLon": stack["centerLon"],
                "centerLat": stack["centerLat"],
                "bounds3857": stack["bounds3857"],
                "coveredByAois": stack.get("coveredByAois") or [],
                "stackStatus": stack.get("stackStatus"),
                "consensus": label,
                "priorityScore": score,
                "priorityReasons": reasons,
                "assetCategories": categories,
                "positiveFirstVisibleDates": positive_dates,
                "earliestExactPositiveDate": first_date,
                "earliestExactPositiveHoursAfterEvent": first_hours,
                "models": {"hfQwen": hf_view, "minimax": minimax_view},
                "waldo30": waldo_view,
                "scenes": (hf.get(cell_id) or minimax.get(cell_id) or {}).get("scenes")
                or stack.get("selectedScenes")
                or [],
                "evidencePolicy": (
                    "AI triage only. Native source pixels and provenance must be "
                    "inspected before a factual publication claim."
                ),
            }
        )
    records.sort(key=lambda row: row["cellId"])
    priority = sorted(
        (
            record
            for record in records
            if record["priorityScore"] > 0
            or record["consensus"].endswith("disagreement")
        ),
        key=lambda row: (-row["priorityScore"], row["cellId"]),
    )
    paired = len(set(hf) & set(minimax) & eligible)
    waldo_complete = False
    if WALDO_SUMMARY.is_file():
        waldo_complete = bool(json.loads(WALDO_SUMMARY.read_text()).get("coverageComplete"))
    summary = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "La Guaira-Caraballeda-Catia La Mar full 250 m pilot",
        "fullPilotCells": len(stacks),
        "eligibleCells": len(eligible),
        "hfCoverage": len(set(hf) & eligible),
        "minimaxCoverage": len(set(minimax) & eligible),
        "pairedCoverage": paired,
        "coverageComplete": paired == len(eligible),
        "postEventOnlyCells": sum(
            stack.get("stackStatus") == "post_event_only" for stack in stacks.values()
        ),
        "consensusCounts": dict(sorted(consensus_counts.items())),
        "hfVsMinimaxMatrix": {
            key: dict(sorted(value.items())) for key, value in sorted(matrix.items())
        },
        "positiveAssetCategoryCounts": dict(sorted(category_counts.items())),
        "sourceAreaCoverageCounts": dict(sorted(area_counts.items())),
        "priorityQueueCount": len(priority),
        "waldo30Cells": len(waldo),
        "waldo30CoverageComplete": waldo_complete,
        "usage": {
            "hf": token_usage(hf),
            "minimax": token_usage(minimax),
        },
        "guardrails": [
            "Official EMS, external prediction, VLM and detector evidence remain separate.",
            "Post-event-only cells are not before/after evidence.",
            "No negative screen proves absence of response.",
            "First-visible dates are acquisition bounds, not actual arrival times.",
        ],
        "outputs": {
            "consensus": str((PROFILE / "enhanced_consensus.jsonl").relative_to(ROOT)),
            "priorityQueue": str(
                (PROFILE / "enhanced_priority_queue.jsonl").relative_to(ROOT)
            ),
        },
    }
    write_jsonl(PROFILE / "enhanced_consensus.jsonl", records)
    write_jsonl(PROFILE / "enhanced_priority_queue.jsonl", priority)
    (PROFILE / "enhanced_consensus_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    report = [
        "# Full-pilot imagery consensus",
        "",
        f"- Generated: `{summary['generatedAt']}`",
        f"- Grid cells: `{len(stacks)}`",
        f"- Eligible imagery stacks: `{len(eligible)}`",
        f"- Paired provider coverage: `{paired}`",
        f"- Post-event-only cells: `{summary['postEventOnlyCells']}`",
        f"- Priority queue: `{len(priority)}`",
        f"- WALDO30 coverage: `{len(waldo)}` (`{'complete' if waldo_complete else 'pending'})`",
        "",
        "All outputs are AI triage. First-visible acquisition bounds do not establish",
        "the actual arrival time of assistance, and negative screens do not establish absence.",
        "",
    ]
    (PROFILE / "enhanced_consensus_report.md").write_text("\n".join(report))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
