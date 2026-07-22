#!/usr/bin/env python3
"""Run resumable WALDO30 detection across the AOI12 enhanced evidence queue.

Detections are independent triage observations. They are stored per dated
scene, never summed into a claim about simultaneous asset totals, and never
treated as factual verification without inspection of the native pixels.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch
from huggingface_hub import hf_hub_download
from PIL import Image
from ultralytics import YOLO


ROOT = Path(__file__).resolve().parents[1]
PROFILE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "aoi12_temporal_response_grid"
    / "detail-250m-enhanced"
)
OUT_DIR = PROFILE / "waldo30-full"
TARGET_CLASSES = {
    "LightVehicle",
    "Person",
    "Boat",
    "Container",
    "Truck",
    "Digger",
    "Bus",
}
HEAVY_CLASSES = {"Container", "Truck", "Digger", "Bus"}
MODEL_ID = "StephanST/WALDO30"
MODEL_FILENAME = "WALDO30_yolov8l-p2_1024x1024.pt"
MODEL_REVISION = "6ad69ea1c69696d50333a1339925614688615edf"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile-dir",
        default=str(PROFILE),
        help="Directory containing enhanced_priority_queue.jsonl.",
    )
    parser.add_argument("--confidence", type=float, default=0.15)
    parser.add_argument("--device", default="")
    parser.add_argument("--min-score", type=int, default=0)
    parser.add_argument("--max-cells", type=int, default=0)
    parser.add_argument(
        "--all-cells",
        action="store_true",
        help="Run on every consensus cell instead of only the VLM priority queue.",
    )
    parser.add_argument(
        "--all-stacks",
        action="store_true",
        help="Run independently on every extracted stack before VLM consensus is ready.",
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


def scene_key(cell_id: str, scene_id: str) -> str:
    return f"{cell_id}::{scene_id}"


def write_products(
    queue: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    *,
    device: str,
    confidence: float,
) -> dict[str, Any]:
    queue_by_id = {record["cellId"]: record for record in queue}
    by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    totals: Counter[str] = Counter()
    for row in rows:
        by_cell[row["cellId"]].append(row)
        totals.update(row.get("detectionCounts") or {})

    changes = []
    for cell_id in sorted(queue_by_id):
        scene_rows = sorted(
            by_cell.get(cell_id, []),
            key=lambda row: (str(row.get("acquisitionUtc")), row.get("sceneId", "")),
        )
        pre_rows = [row for row in scene_rows if row.get("phase") == "pre"]
        post_rows = [row for row in scene_rows if row.get("phase") == "post"]
        pre_max: Counter[str] = Counter()
        post_max: Counter[str] = Counter()
        for label in TARGET_CLASSES:
            pre_max[label] = max(
                (row.get("detectionCounts", {}).get(label, 0) for row in pre_rows),
                default=0,
            )
            post_max[label] = max(
                (row.get("detectionCounts", {}).get(label, 0) for row in post_rows),
                default=0,
            )
        positive_deltas = {
            label: post_max[label] - pre_max[label]
            for label in sorted(TARGET_CLASSES)
            if post_max[label] - pre_max[label] > 0
        }
        dated_heavy = [
            {
                "sceneId": row.get("sceneId"),
                "acquisitionUtc": row.get("acquisitionUtc"),
                "counts": {
                    label: row.get("detectionCounts", {}).get(label, 0)
                    for label in sorted(HEAVY_CLASSES)
                    if row.get("detectionCounts", {}).get(label, 0) > 0
                },
            }
            for row in post_rows
            if any(
                row.get("detectionCounts", {}).get(label, 0) > 0
                for label in HEAVY_CLASSES
            )
        ]
        changes.append(
            {
                "cellId": cell_id,
                "priorityScore": queue_by_id[cell_id].get("priorityScore"),
                "consensus": queue_by_id[cell_id].get("consensus"),
                "assetCategories": queue_by_id[cell_id].get("assetCategories") or [],
                "sceneCoverage": len(scene_rows),
                "preSceneMaxCounts": {
                    key: value for key, value in sorted(pre_max.items()) if value
                },
                "postSceneMaxCounts": {
                    key: value for key, value in sorted(post_max.items()) if value
                },
                "positiveMaxCountDeltas": positive_deltas,
                "datedPostHeavyDetections": dated_heavy,
                "warning": (
                    "Detector boxes may be false positives. Max-count deltas compare "
                    "different sensors and acquisitions and are triage signals only."
                ),
            }
        )

    expected_scenes = sum(len(record.get("scenes") or []) for record in queue)
    runtime_log = OUT_DIR / "runtime" / "full.log"
    nms_warnings = (
        runtime_log.read_text(errors="replace").count("NMS time limit")
        if runtime_log.is_file()
        else 0
    )
    summary = {
        "version": 1,
        "model": f"{MODEL_ID}/{MODEL_FILENAME}",
        "modelRevision": MODEL_REVISION,
        "device": device,
        "confidenceThreshold": confidence,
        "queueCells": len(queue),
        "expectedSceneImages": expected_scenes,
        "completedSceneImages": len(rows),
        "coverageComplete": len(rows) == expected_scenes,
        "cellsWithCompletedScenes": len(by_cell),
        "nmsTimeLimitWarnings": nms_warnings,
        "totalDetectionCountsAcrossAllDates": dict(sorted(totals.items())),
        "targetClasses": sorted(TARGET_CLASSES),
        "heavyClasses": sorted(HEAVY_CLASSES),
        "licenseNote": (
            "Modified MIT; civilian disaster analysis use. See model card for restrictions."
        ),
        "status": "triage-only",
        "warnings": [
            "Detections are not verified assets and may contain false positives.",
            "Counts from different dates are never simultaneous asset totals.",
            "Sensor, angle, haze and resolution differences limit count comparability.",
            (
                f"Ultralytics reported {nms_warnings} NMS time-limit warnings in dense scenes; "
                "those scenes may have incomplete boxes."
            ),
            "Native source pixels must be inspected before any public claim.",
        ],
        "outputs": {
            "detections": str((OUT_DIR / "detections.jsonl").relative_to(ROOT)),
            "cellChanges": str((OUT_DIR / "cell_changes.json").relative_to(ROOT)),
        },
    }
    (OUT_DIR / "cell_changes.json").write_text(
        json.dumps(changes, indent=2) + "\n"
    )
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main() -> int:
    global PROFILE, OUT_DIR
    args = parse_args()
    if args.all_cells and args.all_stacks:
        raise SystemExit("--all-cells and --all-stacks are mutually exclusive.")
    profile_arg = Path(args.profile_dir).expanduser()
    PROFILE = profile_arg if profile_arg.is_absolute() else ROOT / profile_arg
    OUT_DIR = PROFILE / "waldo30-full"
    if args.all_stacks:
        source_name = "stacks.jsonl"
        queue = [
            {
                **record,
                "scenes": record.get("selectedScenes") or [],
                "priorityScore": 0,
                "consensus": "independent_detector_prepass",
            }
            for record in read_rows(PROFILE / source_name)
            if record.get("selectedScenes")
        ]
    else:
        source_name = (
            "enhanced_consensus.jsonl"
            if args.all_cells
            else "enhanced_priority_queue.jsonl"
        )
        queue = [
            record
            for record in read_rows(PROFILE / source_name)
            if int(record.get("priorityScore") or 0) >= args.min_score
        ]
    if args.max_cells:
        queue = queue[: args.max_cells]
    if not queue:
        raise SystemExit("No enhanced priority cells matched the requested scope.")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUT_DIR / "detections.jsonl"
    existing_rows = read_rows(output)
    completed = {
        scene_key(row["cellId"], row["sceneId"]) for row in existing_rows
    }
    pending = [
        (record, scene)
        for record in queue
        for scene in record.get("scenes") or []
        if scene.get("chipPath")
        and scene_key(record["cellId"], scene["sceneId"]) not in completed
    ]

    checkpoint = hf_hub_download(
        MODEL_ID,
        MODEL_FILENAME,
        revision=MODEL_REVISION,
    )
    model = YOLO(checkpoint)
    device = args.device or (
        "mps" if torch.backends.mps.is_available() else "cpu"
    )
    with output.open("a") as sink:
        for index, (record, scene) in enumerate(pending, 1):
            path = ROOT / scene["chipPath"]
            with Image.open(path) as image:
                native_width, native_height = image.size
            prediction = model.predict(
                path,
                imgsz=1024,
                conf=args.confidence,
                device=device,
                verbose=False,
            )[0]
            detections = []
            for xyxy, confidence, class_id in zip(
                prediction.boxes.xyxyn.cpu().tolist(),
                prediction.boxes.conf.cpu().tolist(),
                prediction.boxes.cls.cpu().tolist(),
            ):
                label = prediction.names[int(class_id)]
                if label not in TARGET_CLASSES:
                    continue
                detections.append(
                    {
                        "class": label,
                        "confidence": round(float(confidence), 4),
                        "xyxyn": [round(float(value), 5) for value in xyxy],
                    }
                )
            row = {
                "cellId": record["cellId"],
                "priorityScore": record.get("priorityScore"),
                "consensus": record.get("consensus"),
                "sceneId": scene.get("sceneId"),
                "acquisitionUtc": scene.get("acquisitionUtc"),
                "phase": scene.get("phase"),
                "sensor": scene.get("sensor"),
                "sourceFamily": scene.get("sourceFamily"),
                "license": scene.get("license"),
                "panGsdM": scene.get("panGsdM"),
                "chipPath": scene.get("chipPath"),
                "nativeWidth": native_width,
                "nativeHeight": native_height,
                "inferenceImageSize": 1024,
                "detections": detections,
                "detectionCounts": dict(
                    sorted(Counter(item["class"] for item in detections).items())
                ),
            }
            sink.write(json.dumps(row) + "\n")
            sink.flush()
            existing_rows.append(row)
            if index % 25 == 0 or index == len(pending):
                summary = write_products(
                    queue,
                    existing_rows,
                    device=device,
                    confidence=args.confidence,
                )
                print(
                    f"waldo {index}/{len(pending)} new scenes; "
                    f"{summary['completedSceneImages']}/"
                    f"{summary['expectedSceneImages']} total",
                    flush=True,
                )

    summary = write_products(
        queue,
        existing_rows,
        device=device,
        confidence=args.confidence,
    )
    summary["queueSource"] = source_name
    summary["allConsensusCells"] = args.all_cells
    summary["independentStackPrepass"] = args.all_stacks
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
