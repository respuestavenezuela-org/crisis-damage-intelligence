#!/usr/bin/env python3
"""Build a ranked review queue from blind before/after VLM calibration outputs."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CALIBRATION_ROOT = ROOT / "ops" / "hf_before_after_calibration"
MODE = "blind_multi_image_qc_v1"

CLASS_SCORE = {
    "no_change_visible": 0,
    "uncertain_comparison_problem": 1,
    "minor_visible_damage": 2,
    "possible_major_damage": 3,
    "likely_destroyed": 4,
}

FIELDNAMES = [
    "review_rank",
    "review_bucket",
    "aoi_id",
    "id",
    "official_ems_damage_gra",
    "baseline_damage_class",
    "blind_damage_class",
    "baseline_confidence",
    "blind_confidence",
    "baseline_action_priority",
    "blind_action_priority",
    "alignment_score",
    "target_visibility",
    "visible_change_score",
    "model_should_defer",
    "compare_chip",
    "google_maps_url",
    "change_evidence",
    "uncertainty_reason",
]


def score_class(name: str | None) -> int:
    return CLASS_SCORE.get(name or "", -1)


def review_bucket(record: dict[str, Any]) -> tuple[int, str]:
    vlm = record.get("vlm") or {}
    baseline = record.get("baseline_public_vlm") or {}
    baseline_class = baseline.get("damage_class")
    blind_class = vlm.get("damage_class")
    baseline_score = score_class(baseline_class)
    blind_score = score_class(blind_class)
    visible_change = float(vlm.get("visible_change_score") or 0)
    should_defer = bool(vlm.get("model_should_defer"))

    if baseline_class == "likely_destroyed" and blind_class in {"no_change_visible", "uncertain_comparison_problem"}:
        return 100 + baseline_score - blind_score, "critical_severity_disagreement"
    if baseline_score >= 3 and blind_class in {"no_change_visible", "uncertain_comparison_problem"}:
        return 90 + baseline_score - blind_score, "major_damage_disagreement"
    if should_defer or blind_class == "uncertain_comparison_problem":
        return 75 + max(baseline_score, 0), "quality_or_alignment_defer"
    if baseline_score > blind_score >= 0:
        return 65 + baseline_score - blind_score, "severity_downgrade"
    if blind_score >= 3 and visible_change >= 0.9:
        return 45 + blind_score, "calibration_confirmed_high_change"
    if blind_class == "no_change_visible":
        return 25, "calibration_deprioritize"
    return 10, "calibration_other"


def load_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(CALIBRATION_ROOT.glob(f"*/{MODE}.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            vlm = record.get("vlm") or {}
            if vlm.get("damage_class") == "uncertain_comparison_problem":
                vlm["model_should_defer"] = True
            record["vlm"] = vlm
            rank, bucket = review_bucket(record)
            record["review_rank"] = rank
            record["review_bucket"] = bucket
            records.append(record)
    return sorted(records, key=lambda item: (-int(item["review_rank"]), item.get("aoi_id", ""), item.get("id", "")))


def row(record: dict[str, Any]) -> dict[str, Any]:
    vlm = record.get("vlm") or {}
    baseline = record.get("baseline_public_vlm") or {}
    return {
        "review_rank": record.get("review_rank"),
        "review_bucket": record.get("review_bucket"),
        "aoi_id": record.get("aoi_id"),
        "id": record.get("id"),
        "official_ems_damage_gra": record.get("official_ems_damage_gra"),
        "baseline_damage_class": baseline.get("damage_class"),
        "blind_damage_class": vlm.get("damage_class"),
        "baseline_confidence": baseline.get("confidence"),
        "blind_confidence": vlm.get("confidence"),
        "baseline_action_priority": baseline.get("action_priority"),
        "blind_action_priority": vlm.get("action_priority"),
        "alignment_score": vlm.get("alignment_score"),
        "target_visibility": vlm.get("target_visibility"),
        "visible_change_score": vlm.get("visible_change_score"),
        "model_should_defer": vlm.get("model_should_defer"),
        "compare_chip": record.get("compare_chip"),
        "google_maps_url": record.get("google_maps_url"),
        "change_evidence": vlm.get("change_evidence"),
        "uncertainty_reason": vlm.get("uncertainty_reason"),
    }


def main() -> int:
    records = load_records()
    csv_path = CALIBRATION_ROOT / "review_queue.csv"
    json_path = CALIBRATION_ROOT / "review_queue.json"
    summary_path = CALIBRATION_ROOT / "review_queue_summary.json"

    rows = [row(record) for record in records]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    json_path.write_text(json.dumps(rows, ensure_ascii=True, separators=(",", ":")) + ("\n" if rows else ""))

    summary = {
        "records": len(records),
        "by_aoi": dict(Counter(record.get("aoi_id") for record in records)),
        "by_review_bucket": dict(Counter(record.get("review_bucket") for record in records)),
        "by_blind_damage_class": dict(Counter((record.get("vlm") or {}).get("damage_class") for record in records)),
        "warning": "Calibration review queue is for VLM QA and triage only; it is not official damage confirmation.",
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {len(records)} calibration review rows")
    print(f"CSV: {csv_path}")
    print(f"Summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
