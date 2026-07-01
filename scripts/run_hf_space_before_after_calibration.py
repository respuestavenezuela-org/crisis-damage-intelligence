#!/usr/bin/env python3
"""Run blind, multi-image before/after VLM calibration without public writes."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any

import run_minimax_ems_before_after_review as base
from vlm_provider import call_vlm


ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "ops" / "hf_before_after_calibration"
REVIEW_TYPE = "dated_pre_event_comparison"
CALIBRATION_MODE = "blind_multi_image_qc_v1"

SYSTEM = (
    "You are assisting emergency earthquake damage triage by comparing pre-event and post-event aerial/satellite imagery. "
    "You will receive three images for one mapped feature: image 1 is the before chip, image 2 is the after chip, and image 3 is a labeled side-by-side compare panel. "
    "The red/white reticle marks the target centroid. A yellow/black outline, when visible, marks the target footprint or mapped geometry. "
    "You must be blind to official damage labels: do not assume the feature is damaged, and do not infer official status from the AOI or feature id. "
    "Be conservative. VLM output is a triage aid, not official confirmation. Never claim absence of damage solely because no damage is visible. "
    "Return only valid JSON with keys damage_class, damage_percent, confidence, change_evidence, before_observation, after_observation, "
    "image_alignment, image_quality, action_priority, uncertainty_reason, alignment_score, target_visibility, visible_change_score, model_should_defer. "
    "damage_class must be one of no_change_visible, minor_visible_damage, possible_major_damage, likely_destroyed, uncertain_comparison_problem. "
    "action_priority must be one of urgent_review, review, deprioritize. "
    "target_visibility must be one of clear, partial, poor, not_visible. "
    "alignment_score and visible_change_score must be numbers from 0 to 1. model_should_defer must be boolean. "
    "If alignment, resolution, obstruction, black/missing before content, or scene mismatch prevents fair comparison, return uncertain_comparison_problem and set model_should_defer true."
)

REQUIRED_EXTRA_KEYS = (
    "alignment_score",
    "target_visibility",
    "visible_change_score",
    "model_should_defer",
)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key == "HF-TOKEN":
            key = "HF_TOKEN"
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("aoi_id")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--ids", default="", help="Comma-separated feature ids to run instead of priority offset/limit selection")
    return parser.parse_args()


def selected_features(aoi_id: str, limit: int, offset: int, ids: str) -> list[dict[str, Any]]:
    geojson_path = ROOT / "public" / "data" / "aoi" / aoi_id / "damage.geojson"
    data = json.loads(geojson_path.read_text())
    features = sorted(data.get("features", []), key=base.priority)
    if ids:
        wanted = {item.strip() for item in ids.split(",") if item.strip()}
        return [feature for feature in features if feature["properties"]["id"] in wanted]
    if offset:
        features = features[offset:]
    if limit:
        features = features[:limit]
    return features


def load_public_vlm(aoi_id: str) -> dict[str, dict[str, Any]]:
    path = ROOT / "public" / "data" / "aoi" / aoi_id / "vlm_before_after_review.jsonl"
    if not path.exists():
        return {}
    records: dict[str, dict[str, Any]] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        records[record["id"]] = record
    return records


def ensure_chips(aoi_id: str, feature: dict[str, Any]) -> tuple[Path, Path, Path] | None:
    props = feature["properties"]
    fid = props["id"]
    before_chip = base.chip_path(aoi_id, fid, "before_event")
    after_chip = base.chip_path(aoi_id, fid, "after_event")
    compare_chip = base.chip_path(aoi_id, fid, "before_after_compare")
    before_cog = base.LOCAL_BEFORE_COGS[aoi_id]
    after_cog = base.LOCAL_AFTER_COGS[aoi_id]
    if not before_chip.exists() and not base.make_chip(before_cog, feature, before_chip):
        return None
    if not after_chip.exists() and not base.make_chip(after_cog, feature, after_chip):
        return None
    if not compare_chip.exists():
        base.make_compare_chip(before_chip, after_chip, compare_chip)
    return before_chip, after_chip, compare_chip


def validate_calibration_result(result: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_EXTRA_KEYS if key not in result]
    if missing:
        raise ValueError(f"Calibration response missing required keys: {', '.join(missing)}")
    for key in ("alignment_score", "visible_change_score"):
        value = result.get(key)
        if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
            raise ValueError(f"Calibration response {key} must be numeric 0..1; got {value!r}")
    if result.get("target_visibility") not in {"clear", "partial", "poor", "not_visible"}:
        raise ValueError(f"Unexpected target_visibility={result.get('target_visibility')!r}")
    if not isinstance(result.get("model_should_defer"), bool):
        raise ValueError(f"model_should_defer must be boolean; got {result.get('model_should_defer')!r}")


def normalize_calibration_result(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("damage_class") == "uncertain_comparison_problem":
        result["model_should_defer"] = True
    for key in ("alignment_score", "visible_change_score"):
        if isinstance(result.get(key), (int, float)):
            result[key] = float(result[key])
    return result


def run_feature(aoi_id: str, feature: dict[str, Any], public_vlm: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    chips = ensure_chips(aoi_id, feature)
    if chips is None:
        return None
    before_chip, after_chip, compare_chip = chips
    props = feature["properties"]
    fid = props["id"]
    prompt = (
        "Run blind before/after damage triage for the target feature. "
        "Image 1 is the before chip, image 2 is the after chip, and image 3 is the side-by-side compare panel. "
        "Use the reticle and any yellow/black outline to identify the target. "
        f"AOI: {aoi_id}. Feature id: {fid}. "
        f"Before source: {base.BEFORE_SOURCE_LABEL[aoi_id]}. "
        "Do not use official EMS damage labels; they are intentionally withheld for calibration. "
        "First judge whether before/after alignment and target visibility are good enough. "
        "Then classify only visible physical change: new rubble, roof loss, collapse, footprint distortion, exposed floors, debris fields, shadow/height loss, or clear disappearance. "
        "If the evidence is ambiguous, defer with uncertain_comparison_problem rather than overcalling damage."
    )
    metadata = {
        "aoi_id": aoi_id,
        "id": fid,
        "calibration_mode": CALIBRATION_MODE,
        "before_source_label": base.BEFORE_SOURCE_LABEL[aoi_id],
    }
    result = call_vlm(SYSTEM, prompt, [before_chip, after_chip, compare_chip], metadata, REVIEW_TYPE)
    validate_calibration_result(result)
    result = normalize_calibration_result(result)
    result["before_source"] = base.BEFORE_SOURCE_LABEL[aoi_id]
    result["calibration_mode"] = CALIBRATION_MODE
    baseline = public_vlm.get(fid, {})
    baseline_vlm = baseline.get("vlm") or {}
    return {
        "id": fid,
        "aoi_id": aoi_id,
        "google_maps_url": props.get("google_maps_url"),
        "official_ems_damage_gra": props.get("damage_gra"),
        "official_ems_damage_percent": props.get("damage_percent"),
        "before_event_chip": base.public_chip(before_chip),
        "post_event_chip": base.public_chip(after_chip),
        "compare_chip": base.public_chip(compare_chip),
        "baseline_public_vlm": {
            "damage_class": baseline_vlm.get("damage_class"),
            "confidence": baseline_vlm.get("confidence"),
            "action_priority": baseline_vlm.get("action_priority"),
            "vlm_provider": baseline_vlm.get("vlm_provider"),
            "vlm_model": baseline_vlm.get("vlm_model"),
        },
        "vlm": result,
    }


def output_paths(aoi_id: str) -> tuple[Path, Path, Path]:
    out_dir = OUT_ROOT / aoi_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return (
        out_dir / f"{CALIBRATION_MODE}.jsonl",
        out_dir / f"{CALIBRATION_MODE}_summary.json",
        out_dir / f"{CALIBRATION_MODE}_summary.csv",
    )


def load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    for record in records:
        if isinstance(record.get("vlm"), dict):
            normalize_calibration_result(record["vlm"])
    return records


def write_outputs(aoi_id: str, records: list[dict[str, Any]]) -> None:
    jsonl_path, summary_path, csv_path = output_paths(aoi_id)
    records = sorted(records, key=lambda record: record["id"])
    jsonl_path.write_text("\n".join(json.dumps(record, ensure_ascii=True, separators=(",", ":")) for record in records) + ("\n" if records else ""))
    class_counts: dict[str, int] = {}
    priority_counts: dict[str, int] = {}
    visibility_counts: dict[str, int] = {}
    deferred = 0
    disagreements = 0
    for record in records:
        vlm = record.get("vlm") or {}
        baseline = record.get("baseline_public_vlm") or {}
        class_counts[vlm.get("damage_class", "unknown")] = class_counts.get(vlm.get("damage_class", "unknown"), 0) + 1
        priority_counts[vlm.get("action_priority", "unknown")] = priority_counts.get(vlm.get("action_priority", "unknown"), 0) + 1
        visibility_counts[vlm.get("target_visibility", "unknown")] = visibility_counts.get(vlm.get("target_visibility", "unknown"), 0) + 1
        deferred += 1 if vlm.get("model_should_defer") else 0
        disagreements += 1 if baseline.get("damage_class") and baseline.get("damage_class") != vlm.get("damage_class") else 0
    summary = {
        "aoi_id": aoi_id,
        "calibration_mode": CALIBRATION_MODE,
        "reviewed": len(records),
        "damage_classes": class_counts,
        "action_priorities": priority_counts,
        "target_visibility": visibility_counts,
        "deferred": deferred,
        "baseline_class_disagreements": disagreements,
        "warning": "Calibration outputs are for prompt/model QA only and are not public evidence.",
    }
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "id",
                "official_ems_damage_gra",
                "baseline_damage_class",
                "blind_damage_class",
                "confidence",
                "action_priority",
                "alignment_score",
                "target_visibility",
                "visible_change_score",
                "model_should_defer",
                "change_evidence",
                "uncertainty_reason",
                "before_observation",
                "after_observation",
                "compare_chip",
                "google_maps_url",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        for record in records:
            vlm = record.get("vlm") or {}
            baseline = record.get("baseline_public_vlm") or {}
            writer.writerow(
                {
                    "id": record.get("id"),
                    "official_ems_damage_gra": record.get("official_ems_damage_gra"),
                    "baseline_damage_class": baseline.get("damage_class"),
                    "blind_damage_class": vlm.get("damage_class"),
                    "confidence": vlm.get("confidence"),
                    "action_priority": vlm.get("action_priority"),
                    "alignment_score": vlm.get("alignment_score"),
                    "target_visibility": vlm.get("target_visibility"),
                    "visible_change_score": vlm.get("visible_change_score"),
                    "model_should_defer": vlm.get("model_should_defer"),
                    "change_evidence": vlm.get("change_evidence"),
                    "uncertainty_reason": vlm.get("uncertainty_reason"),
                    "before_observation": vlm.get("before_observation"),
                    "after_observation": vlm.get("after_observation"),
                    "compare_chip": record.get("compare_chip"),
                    "google_maps_url": record.get("google_maps_url"),
                }
            )


def main() -> int:
    load_env(ROOT / ".env")
    load_env(ROOT.parents[1] / ".env")
    args = parse_args()
    if args.aoi_id not in base.LOCAL_BEFORE_COGS:
        raise SystemExit(f"No before/after VLM configuration for {args.aoi_id}")
    features = selected_features(args.aoi_id, args.limit, args.offset, args.ids)
    jsonl_path, _, _ = output_paths(args.aoi_id)
    existing = load_existing(jsonl_path)
    by_id = {record["id"]: record for record in existing}
    if args.force:
        for feature in features:
            by_id.pop(feature["properties"]["id"], None)
    pending = [feature for feature in features if args.force or feature["properties"]["id"] not in by_id]
    public_vlm = load_public_vlm(args.aoi_id)
    reviewed = 0
    skipped = 0
    lock = Lock()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(run_feature, args.aoi_id, feature, public_vlm): feature for feature in pending}
        for future in as_completed(futures):
            feature = futures[future]
            fid = feature["properties"]["id"]
            record = future.result()
            if record is None:
                skipped += 1
                print(f"{args.aoi_id} {fid} skipped: missing/black before reference", flush=True)
                continue
            with lock:
                by_id[record["id"]] = record
                reviewed += 1
                write_outputs(args.aoi_id, list(by_id.values()))
            vlm = record["vlm"]
            baseline = record.get("baseline_public_vlm") or {}
            print(
                f"{args.aoi_id} {fid} blind={vlm.get('damage_class')} baseline={baseline.get('damage_class')} "
                f"align={vlm.get('alignment_score')} visible_change={vlm.get('visible_change_score')} defer={vlm.get('model_should_defer')}",
                flush=True,
            )
            time.sleep(0.25)
    write_outputs(args.aoi_id, list(by_id.values()))
    print(f"Calibration reviewed {reviewed}; skipped {skipped}; total records {len(by_id)}")
    print(f"Output: {jsonl_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
