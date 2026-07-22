#!/usr/bin/env python3
"""Build an evidence-bounded response-arrival timeline for enhanced AOI12.

The output reports when a possible signal is first visible in supplied imagery.
It does not infer the actual arrival time of help and does not turn a model or
detector result into a verified fact.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "aoi12_temporal_response_grid"
    / "detail-250m-enhanced"
)
WALDO_DIR = PROFILE / "waldo30-full"
OUT_DIR = PROFILE / "response-timeline"
EVENT_ORIGIN = datetime.fromisoformat("2026-06-24T18:04:33-04:00")
POSITIVE_CONSENSUS = {
    "both_positive",
    "positive_negative_disagreement",
    "positive_uncertain_disagreement",
}
RESPONSE_DETECTOR_CLASSES = {"Digger", "Truck", "Bus", "Container", "Person"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-partial-detector", action="store_true")
    parser.add_argument(
        "--profile-dir",
        default=str(PROFILE),
        help="Directory containing consensus, detector, and crop outputs.",
    )
    parser.add_argument(
        "--scope",
        default="EMSR884 AOI12 Caraballeda / La Guaira enhanced imagery grid",
    )
    parser.add_argument(
        "--scope-limit",
        default=(
            "This AOI12 result does not cover the complete Catia La Mar full-pilot "
            "extent; Catia La Mar requires the separate 2,283-cell pilot expansion."
        ),
    )
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def exact_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or "/" in value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def hours_after_event(value: Any) -> float | None:
    timestamp = exact_time(value)
    if timestamp is None:
        return None
    return round((timestamp - EVENT_ORIGIN).total_seconds() / 3600, 2)


def time_window(hours: float | None) -> str:
    if hours is None:
        return "undated"
    if hours < 0:
        return "pre_event"
    if hours <= 24:
        return "0_24h"
    if hours <= 48:
        return "24_48h"
    if hours <= 72:
        return "48_72h"
    if hours <= 168:
        return "72h_7d"
    return "after_7d"


def main() -> int:
    global PROFILE, WALDO_DIR, OUT_DIR
    args = parse_args()
    profile_arg = Path(args.profile_dir).expanduser()
    PROFILE = profile_arg if profile_arg.is_absolute() else ROOT / profile_arg
    WALDO_DIR = PROFILE / "waldo30-full"
    OUT_DIR = PROFILE / "response-timeline"
    consensus = read_rows(PROFILE / "enhanced_consensus.jsonl")
    priority = {
        record["cellId"]: record
        for record in read_rows(PROFILE / "enhanced_priority_queue.jsonl")
    }
    detector_summary_path = WALDO_DIR / "summary.json"
    detector_summary = (
        json.loads(detector_summary_path.read_text())
        if detector_summary_path.is_file()
        else {}
    )
    if (
        not args.allow_partial_detector
        and not detector_summary.get("coverageComplete")
    ):
        raise SystemExit("WALDO30 full-run coverage is not complete.")
    detections = read_rows(WALDO_DIR / "detections.jsonl")
    detector_by_cell_date = {
        (record["cellId"], record.get("acquisitionUtc")): record
        for record in detections
    }
    changes = {
        record["cellId"]: record
        for record in (
            json.loads((WALDO_DIR / "cell_changes.json").read_text())
            if (WALDO_DIR / "cell_changes.json").is_file()
            else []
        )
    }
    crop_pairs = read_rows(PROFILE / "evidence-crops" / "manifest.jsonl")
    crops_by_cell_date: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for pair in crop_pairs:
        crops_by_cell_date[
            (pair["cellId"], pair.get("targetAcquisitionUtc"))
        ].append(
            {
                "pairId": pair["pairId"],
                "rank": pair["rank"],
                "targetDetection": pair["targetDetection"],
                "images": pair["images"],
            }
        )

    observations = []
    for record in consensus:
        if record.get("consensus") not in POSITIVE_CONSENSUS:
            continue
        cell_id = record["cellId"]
        first_date = record.get("earliestExactPositiveDate")
        hours = hours_after_event(first_date)
        detector_row = detector_by_cell_date.get((cell_id, first_date))
        change = changes.get(cell_id) or {}
        deltas = {
            key: value
            for key, value in (change.get("positiveMaxCountDeltas") or {}).items()
            if key in RESPONSE_DETECTOR_CLASSES and value > 0
        }
        exact_counts = {
            key: value
            for key, value in (
                (detector_row or {}).get("detectionCounts") or {}
            ).items()
            if key in RESPONSE_DETECTOR_CLASSES and value > 0
        }
        detector_support = bool(deltas and exact_counts)
        if record["consensus"] == "both_positive" and detector_support:
            tier = "cross_model_positive_with_detector_delta"
        elif record["consensus"] == "both_positive":
            tier = "cross_model_positive"
        elif detector_support:
            tier = "contested_positive_with_detector_delta"
        else:
            tier = "contested_positive"
        model_dates = {
            name: view.get("firstVisibleDate")
            for name, view in (record.get("models") or {}).items()
            if view and view.get("firstVisibleDate")
        }
        observations.append(
            {
                "cellId": cell_id,
                "centerLon": record.get("centerLon"),
                "centerLat": record.get("centerLat"),
                "bounds3857": record.get("bounds3857"),
                "coveredByAois": record.get("coveredByAois") or [],
                "stackStatus": record.get("stackStatus"),
                "firstVisibleAcquisitionUtc": first_date,
                "hoursAfterEvent": hours,
                "timeWindow": time_window(hours),
                "evidenceTier": tier,
                "consensus": record.get("consensus"),
                "priorityScore": (priority.get(cell_id) or {}).get("priorityScore", 0),
                "assetCategories": record.get("assetCategories") or [],
                "modelFirstVisibleDates": model_dates,
                "models": record.get("models"),
                "detector": {
                    "sameAcquisitionCounts": exact_counts,
                    "positiveMaxCountDeltas": deltas,
                    "supportStatus": (
                        "independent_triage_support"
                        if detector_support
                        else "no_independent_detector_support"
                    ),
                    "warning": (
                        "WALDO30 boxes and cross-date count deltas may be false positives."
                    ),
                },
                "scenes": record.get("scenes") or [],
                "evidenceCrops": crops_by_cell_date.get((cell_id, first_date), []),
                "publicationStatus": "native_pixel_review_required",
                "arrivalInterpretation": (
                    "This acquisition provides an earliest visible bound within the "
                    "available imagery, not the actual arrival time of assistance."
                ),
            }
        )

    observations.sort(
        key=lambda record: (
            record["hoursAfterEvent"] is None,
            record["hoursAfterEvent"]
            if record["hoursAfterEvent"] is not None
            else float("inf"),
            -int(record["priorityScore"] or 0),
            record["cellId"],
        )
    )
    by_time: dict[str, list[dict[str, Any]]] = defaultdict(list)
    undated = []
    for observation in observations:
        if observation["firstVisibleAcquisitionUtc"]:
            by_time[observation["firstVisibleAcquisitionUtc"]].append(observation)
        else:
            undated.append(observation)
    timeline = [
        {
            "acquisitionUtc": acquisition,
            "hoursAfterEvent": hours_after_event(acquisition),
            "timeWindow": time_window(hours_after_event(acquisition)),
            "candidateCells": len(items),
            "bothModelsPositive": sum(
                item["consensus"] == "both_positive" for item in items
            ),
            "detectorSupported": sum(
                item["detector"]["supportStatus"]
                == "independent_triage_support"
                for item in items
            ),
            "observations": sorted(
                items,
                key=lambda item: (-int(item["priorityScore"] or 0), item["cellId"]),
            ),
        }
        for acquisition, items in sorted(
            by_time.items(),
            key=lambda item: exact_time(item[0]) or datetime.max.replace(tzinfo=timezone.utc),
        )
    ]
    tier_counts = Counter(record["evidenceTier"] for record in observations)
    window_counts = Counter(record["timeWindow"] for record in observations)
    category_counts = Counter(
        category
        for record in observations
        for category in record["assetCategories"]
    )
    summary = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "eventOrigin": EVENT_ORIGIN.isoformat(),
        "scope": args.scope,
        "scopeLimit": args.scope_limit,
        "interpretation": (
            "Timeline dates are first-visible acquisition bounds for triage candidates, "
            "not verified arrival times."
        ),
        "positiveOrContestedCandidateCells": len(observations),
        "datedCandidateCells": len(observations) - len(undated),
        "undatedCandidateCells": len(undated),
        "withinFirst72Hours": sum(
            record["hoursAfterEvent"] is not None
            and 0 <= record["hoursAfterEvent"] <= 72
            for record in observations
        ),
        "evidenceTierCounts": dict(sorted(tier_counts.items())),
        "timeWindowCounts": dict(sorted(window_counts.items())),
        "assetCategoryCounts": dict(sorted(category_counts.items())),
        "detectorCoverage": detector_summary,
        "cropPairCount": len(crop_pairs),
        "guardrails": [
            "No model or detector observation is an official EMS fact.",
            "No negative screen is evidence that help or an asset was absent.",
            "First-visible acquisition time is not actual arrival time.",
            "Pre-existing industrial assets and ordinary activity are major confounders.",
            "Native pixels and source metadata require review before publication.",
            "Super-resolution images are visualization-only and may introduce artifacts.",
        ],
        "outputs": {
            "timeline": str((OUT_DIR / "timeline.json").relative_to(ROOT)),
            "observations": str((OUT_DIR / "observations.jsonl").relative_to(ROOT)),
            "undated": str((OUT_DIR / "undated_candidates.jsonl").relative_to(ROOT)),
            "report": str((OUT_DIR / "report.md").relative_to(ROOT)),
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "timeline.json").write_text(
        json.dumps(
            {
                "summary": summary,
                "events": timeline,
            },
            indent=2,
        )
        + "\n"
    )
    (OUT_DIR / "observations.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in observations)
    )
    (OUT_DIR / "undated_candidates.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in undated)
    )
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    report = [
        "# AOI12 response-arrival evidence timeline",
        "",
        f"- Generated: `{summary['generatedAt']}`",
        f"- Positive or contested-positive candidate cells: `{len(observations)}`",
        f"- Dated candidates: `{summary['datedCandidateCells']}`",
        f"- Within the first 72 hours: `{summary['withinFirst72Hours']}`",
        f"- Native/SR evidence pairs linked: `{len(crop_pairs)}`",
        "",
        "## Interpretation",
        "",
        summary["interpretation"],
        "",
        "## Scope limitation",
        "",
        summary["scopeLimit"],
        "",
        "## Evidence tiers",
        "",
        *[
            f"- `{key}`: `{value}`"
            for key, value in sorted(tier_counts.items())
        ],
        "",
        "## Acquisition timeline",
        "",
        *[
            (
                f"- `{event['acquisitionUtc']}` "
                f"(`{event['hoursAfterEvent']}` h): "
                f"`{event['candidateCells']}` candidates, "
                f"`{event['bothModelsPositive']}` both-model positive, "
                f"`{event['detectorSupported']}` with detector triage support"
            )
            for event in timeline
        ],
        "",
        "## Guardrails",
        "",
        *[f"- {item}" for item in summary["guardrails"]],
        "",
    ]
    (OUT_DIR / "report.md").write_text("\n".join(report))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
