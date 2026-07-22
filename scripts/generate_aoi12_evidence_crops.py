#!/usr/bin/env python3
"""Create paired native-pixel and labeled 2x SR crops for AOI12 evidence.

Native crops are lossless excerpts of the source chips. Swin2SR derivatives are
visualization aids only, include a visible warning banner, and are never used as
the sole basis for a detection or public claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageDraw
from transformers import Swin2SRForImageSuperResolution, Swin2SRImageProcessor


ROOT = Path(__file__).resolve().parents[1]
PROFILE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "aoi12_temporal_response_grid"
    / "detail-250m-enhanced"
)
DETECTIONS = PROFILE / "waldo30-full" / "detections.jsonl"
OUT_DIR = PROFILE / "evidence-crops"
MODEL_ID = "caidas/swin2SR-classical-sr-x2-64"
MODEL_REVISION = "cee1c923c6a37361c6e5650b65dcf4be821e5d52"
CLASS_PRIORITY = {
    "Digger": 100,
    "Truck": 90,
    "Bus": 80,
    "Container": 70,
    "Person": 40,
    "LightVehicle": 20,
    "Boat": 10,
}
EVENT_ORIGIN = datetime.fromisoformat("2026-06-24T18:04:33-04:00")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile-dir",
        default=str(PROFILE),
        help="Directory containing the priority queue and WALDO30 output.",
    )
    parser.add_argument("--max-pairs", type=int, default=250)
    parser.add_argument("--sr-pairs", type=int, default=50)
    parser.add_argument("--min-confidence", type=float, default=0.25)
    parser.add_argument("--max-per-scene", type=int, default=3)
    parser.add_argument("--device", default="")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scene_provenance(row: dict[str, Any]) -> tuple[str | None, str | None, str]:
    if row.get("sourceFamily") and row.get("license"):
        return row["sourceFamily"], row["license"], "recorded"
    text = " ".join(
        str(row.get(key) or "")
        for key in ("sceneId", "sensor", "chipPath", "sourceFamily")
    ).lower()
    if (
        "vantor" in text
        or "detail-250m-missing-scenes" in text
        or str(row.get("sceneId") or "").startswith("B")
    ):
        return "vantor_open_data", "CC-BY-NC-4.0", "derived_from_scene_identity"
    if "copernicus" in text or row.get("sensor") in {"Legion", "GeoEye-1"}:
        return (
            "copernicus_ems",
            "Copernicus EMS public product terms",
            "derived_from_scene_identity",
        )
    return row.get("sourceFamily"), row.get("license"), "unresolved"


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or "/" in value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def within_first_72h(value: Any) -> bool:
    timestamp = parse_time(value)
    if timestamp is None:
        return False
    hours = (timestamp - EVENT_ORIGIN).total_seconds() / 3600
    return 0 <= hours <= 72


def expanded_box(
    xyxyn: list[float],
    width: int,
    height: int,
    *,
    factor: float = 2.5,
    min_pixels: int = 96,
    max_pixels: int = 320,
) -> list[float]:
    x1, y1, x2, y2 = xyxyn
    center_x = (x1 + x2) / 2
    center_y = (y1 + y2) / 2
    box_pixels = max((x2 - x1) * width, (y2 - y1) * height)
    side_pixels = max(min_pixels, box_pixels * factor)
    side_pixels = min(max_pixels, side_pixels)
    side_x = side_pixels / width
    side_y = side_pixels / height
    nx1 = max(0.0, center_x - side_x / 2)
    ny1 = max(0.0, center_y - side_y / 2)
    nx2 = min(1.0, center_x + side_x / 2)
    ny2 = min(1.0, center_y + side_y / 2)
    return [round(value, 7) for value in (nx1, ny1, nx2, ny2)]


def crop_pixels(box: list[float], width: int, height: int) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    left = max(0, min(width - 1, round(x1 * width)))
    top = max(0, min(height - 1, round(y1 * height)))
    right = max(left + 1, min(width, round(x2 * width)))
    bottom = max(top + 1, min(height, round(y2 * height)))
    return left, top, right, bottom


def candidate_rows(
    queue: dict[str, dict[str, Any]],
    detections: list[dict[str, Any]],
    *,
    min_confidence: float,
    max_per_scene: int,
) -> list[dict[str, Any]]:
    candidates = []
    for row in detections:
        if row.get("phase") != "post" or row["cellId"] not in queue:
            continue
        per_scene = sorted(
            (
                detection
                for detection in row.get("detections") or []
                if float(detection.get("confidence") or 0) >= min_confidence
            ),
            key=lambda detection: (
                -CLASS_PRIORITY.get(detection.get("class"), 0),
                -float(detection.get("confidence") or 0),
            ),
        )[:max_per_scene]
        for detection in per_scene:
            priority = int(queue[row["cellId"]].get("priorityScore") or 0)
            consensus_bonus = (
                40 if queue[row["cellId"]].get("consensus") == "both_positive" else 0
            )
            first72_bonus = 30 if within_first_72h(row.get("acquisitionUtc")) else 0
            score = (
                priority
                + consensus_bonus
                + first72_bonus
                + CLASS_PRIORITY.get(detection.get("class"), 0)
                + round(float(detection.get("confidence") or 0) * 20)
            )
            candidates.append(
                {
                    "rankScore": score,
                    "queueRecord": queue[row["cellId"]],
                    "sceneRow": row,
                    "detection": detection,
                }
            )
    return sorted(
        candidates,
        key=lambda item: (
            -item["rankScore"],
            item["sceneRow"]["cellId"],
            str(item["sceneRow"].get("acquisitionUtc")),
            -float(item["detection"].get("confidence") or 0),
        ),
    )


def super_resolve(
    image: Image.Image,
    processor: Swin2SRImageProcessor,
    model: Swin2SRForImageSuperResolution,
    device: str,
) -> Image.Image:
    inputs = processor(images=image.convert("RGB"), return_tensors="pt")
    inputs = {key: value.to(device) for key, value in inputs.items()}
    with torch.inference_mode():
        output = model(**inputs).reconstruction
    array = (
        output.squeeze(0)
        .float()
        .cpu()
        .clamp(0, 1)
        .numpy()
        .transpose(1, 2, 0)
    )
    height = image.height * 2
    width = image.width * 2
    array = (array[:height, :width] * 255).round().astype(np.uint8)
    return Image.fromarray(array, mode="RGB")


def labeled_sr(image: Image.Image, label: str) -> Image.Image:
    banner_height = 34
    canvas = Image.new("RGB", (image.width, image.height + banner_height), "#121212")
    canvas.paste(image, (0, banner_height))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, canvas.width, banner_height), fill="#7a2600")
    draw.text((6, 2), "AI 2x ENHANCED", fill="white")
    draw.text((6, 17), "VISUALIZATION ONLY", fill="white")
    return canvas


def main() -> int:
    global PROFILE, DETECTIONS, OUT_DIR
    args = parse_args()
    profile_arg = Path(args.profile_dir).expanduser()
    PROFILE = profile_arg if profile_arg.is_absolute() else ROOT / profile_arg
    DETECTIONS = PROFILE / "waldo30-full" / "detections.jsonl"
    OUT_DIR = PROFILE / "evidence-crops"
    queue_rows = read_rows(PROFILE / "enhanced_priority_queue.jsonl")
    queue = {record["cellId"]: record for record in queue_rows}
    detections = read_rows(DETECTIONS)
    if not detections:
        raise SystemExit("No WALDO30 full-run detections are available.")
    expected = sum(len(record.get("scenes") or []) for record in queue_rows)
    if len(detections) < expected:
        raise SystemExit(
            f"WALDO30 coverage incomplete: {len(detections)}/{expected} scene images."
        )

    by_cell: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in detections:
        by_cell[row["cellId"]].append(row)
    selected = candidate_rows(
        queue,
        detections,
        min_confidence=args.min_confidence,
        max_per_scene=args.max_per_scene,
    )[: args.max_pairs]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    native_dir = OUT_DIR / "native"
    sr_dir = OUT_DIR / "swin2sr-x2-visualization-only"
    native_dir.mkdir(parents=True, exist_ok=True)
    sr_dir.mkdir(parents=True, exist_ok=True)

    device = args.device or ("mps" if torch.backends.mps.is_available() else "cpu")
    processor = None
    model = None
    if args.sr_pairs:
        processor = Swin2SRImageProcessor.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION
        )
        model = Swin2SRForImageSuperResolution.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION
        ).eval().to(device)

    manifest = []
    for pair_index, candidate in enumerate(selected, 1):
        target = candidate["sceneRow"]
        detection = candidate["detection"]
        source_path = ROOT / target["chipPath"]
        with Image.open(source_path) as source:
            source = source.convert("RGB")
            normalized_crop = expanded_box(
                detection["xyxyn"], source.width, source.height
            )
        comparator_rows = sorted(
            (
                row
                for row in by_cell[target["cellId"]]
                if row.get("phase") == "pre"
            ),
            key=lambda row: str(row.get("acquisitionUtc")),
        )
        image_rows = comparator_rows[:1] + [target]
        pair_images = []
        pair_id = f"pair_{pair_index:04d}_{target['cellId']}_{detection['class'].lower()}"
        for image_index, row in enumerate(image_rows, 1):
            role = "pre_comparator" if row.get("phase") == "pre" else "post_detection"
            source_family, license_name, provenance_status = scene_provenance(row)
            path = ROOT / row["chipPath"]
            with Image.open(path) as source:
                source = source.convert("RGB")
                pixel_box = crop_pixels(normalized_crop, source.width, source.height)
                native = source.crop(pixel_box)
            stem = (
                f"{pair_id}_{image_index}_{role}_{row['sceneId']}"
                .replace("/", "-")
                .replace(" ", "_")
            )
            native_path = native_dir / f"{stem}.png"
            native.save(native_path, format="PNG", compress_level=6)
            image_product = {
                "role": role,
                "sceneId": row.get("sceneId"),
                "acquisitionUtc": row.get("acquisitionUtc"),
                "sensor": row.get("sensor"),
                "sourceFamily": source_family,
                "license": license_name,
                "provenanceStatus": provenance_status,
                "sourceChipPath": row.get("chipPath"),
                "sourceChipSha256": sha256(path),
                "normalizedCropBox": normalized_crop,
                "pixelCropBox": list(pixel_box),
                "nativeCropPath": str(native_path.relative_to(ROOT)),
                "nativeCropSha256": sha256(native_path),
                "nativeCropSize": [native.width, native.height],
                "enhancedPath": None,
                "enhancedSha256": None,
            }
            if (
                pair_index <= args.sr_pairs
                and processor is not None
                and model is not None
            ):
                enhanced = super_resolve(native, processor, model, device)
                enhanced = labeled_sr(
                    enhanced,
                    "AI 2x ENHANCED - VISUALIZATION ONLY",
                )
                enhanced_path = sr_dir / f"{stem}_swin2sr_x2_visualization-only.png"
                enhanced.save(enhanced_path, format="PNG", compress_level=6)
                image_product["enhancedPath"] = str(enhanced_path.relative_to(ROOT))
                image_product["enhancedSha256"] = sha256(enhanced_path)
                image_product["enhancedContentSize"] = [
                    native.width * 2,
                    native.height * 2,
                ]
            pair_images.append(image_product)
        manifest.append(
            {
                "pairId": pair_id,
                "rank": pair_index,
                "rankScore": candidate["rankScore"],
                "cellId": target["cellId"],
                "centerLon": candidate["queueRecord"].get("centerLon"),
                "centerLat": candidate["queueRecord"].get("centerLat"),
                "consensus": candidate["queueRecord"].get("consensus"),
                "cellPriorityScore": candidate["queueRecord"].get("priorityScore"),
                "assetCategories": candidate["queueRecord"].get("assetCategories") or [],
                "targetDetection": detection,
                "targetAcquisitionUtc": target.get("acquisitionUtc"),
                "targetWithinFirst72Hours": within_first_72h(
                    target.get("acquisitionUtc")
                ),
                "images": pair_images,
                "policy": (
                    "The native crop is the evidence view. The Swin2SR image is "
                    "labeled visualization-only and cannot establish a feature."
                ),
            }
        )
        if pair_index % 10 == 0 or pair_index == len(selected):
            print(f"crops {pair_index}/{len(selected)}", flush=True)

    manifest_path = OUT_DIR / "manifest.jsonl"
    manifest_path.write_text(
        "".join(json.dumps(record) + "\n" for record in manifest)
    )
    summary = {
        "version": 1,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceDetector": "StephanST/WALDO30",
        "detectorSceneCoverage": len(detections),
        "candidateDetectionPairsAvailable": len(
            candidate_rows(
                queue,
                detections,
                min_confidence=args.min_confidence,
                max_per_scene=args.max_per_scene,
            )
        ),
        "selectedPairs": len(manifest),
        "nativeCropImages": sum(len(record["images"]) for record in manifest),
        "superResolutionPairs": min(args.sr_pairs, len(manifest)),
        "superResolutionImages": sum(
            1
            for record in manifest
            for image in record["images"]
            if image["enhancedPath"]
        ),
        "superResolutionModel": {
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "scale": 2,
            "role": "visualization-only",
        },
        "device": device,
        "minimumDetectionConfidence": args.min_confidence,
        "warnings": [
            "Detector boxes may be false positives.",
            "Super-resolution may introduce artifacts or plausible-looking detail.",
            "Every enhanced crop is paired with a lossless native-pixel crop.",
            "Only native source pixels may support a factual publication claim.",
        ],
        "outputs": {
            "manifest": str(manifest_path.relative_to(ROOT)),
            "nativeDirectory": str(native_dir.relative_to(ROOT)),
            "enhancedDirectory": str(sr_dir.relative_to(ROOT)),
        },
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
