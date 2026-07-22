#!/usr/bin/env python3
"""Validate full-pilot chip coverage, dimensions, readability, and hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "full_pilot_temporal_grid"
    / "detail-250m"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE))
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect(item: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    cell_id, scene = item
    relative = scene.get("chipPath")
    path = ROOT / relative if relative else None
    result = {
        "cellId": cell_id,
        "sceneId": scene.get("sceneId"),
        "chipPath": relative,
        "expectedSha256": scene.get("chipSha256"),
        "exists": bool(path and path.is_file()),
        "readable": False,
        "dimensions": None,
        "actualSha256": None,
        "errors": [],
    }
    if not path or not path.is_file():
        result["errors"].append("missing_file")
        return result
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            result["dimensions"] = list(image.size)
        result["readable"] = True
    except Exception as exc:  # validation report retains the concrete decoder error
        result["errors"].append(f"image_decode_error:{type(exc).__name__}:{exc}")
    actual = sha256(path)
    result["actualSha256"] = actual
    expected = scene.get("chipSha256")
    if expected and actual != expected:
        result["errors"].append("sha256_mismatch")
    if result["dimensions"] != [768, 802]:
        result["errors"].append("unexpected_dimensions")
    return result


def main() -> int:
    args = parse_args()
    profile_arg = Path(args.profile_dir).expanduser()
    profile = profile_arg if profile_arg.is_absolute() else ROOT / profile_arg
    stacks = [
        json.loads(line)
        for line in (profile / "stacks.jsonl").read_text().splitlines()
        if line.strip()
    ]
    items = [
        (stack["cellId"], scene)
        for stack in stacks
        for scene in stack.get("selectedScenes") or []
    ]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(executor.map(inspect, items))
    failures = [result for result in results if result["errors"]]
    status_counts = Counter(stack.get("stackStatus") for stack in stacks)
    dimension_counts = Counter(
        "x".join(map(str, result["dimensions"]))
        for result in results
        if result["dimensions"]
    )
    report = {
        "version": 1,
        "validatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not failures else "fail",
        "gridCells": len(stacks),
        "stackStatusCounts": dict(sorted(status_counts.items())),
        "sceneImageReferences": len(items),
        "uniqueSceneImagePaths": len(
            {result["chipPath"] for result in results if result["chipPath"]}
        ),
        "readableImages": sum(result["readable"] for result in results),
        "dimensionCounts": dict(sorted(dimension_counts.items())),
        "hashesChecked": sum(bool(result["actualSha256"]) for result in results),
        "hashesWithRecordedExpectedValue": sum(
            bool(result["expectedSha256"]) for result in results
        ),
        "failureCount": len(failures),
        "failures": failures[:100],
        "resolutionPolicy": {
            "gridCellWidthMetersApprox": 250,
            "nativeContentPixels": [768, 768],
            "labelBannerPixels": 34,
            "nominalOutputSamplingMetersPerPixel": 0.326,
            "warning": (
                "Output sampling preserves available detail but does not improve "
                "the source sensor ground sample distance."
            ),
        },
    }
    output = profile / "imagery_validation.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
