#!/usr/bin/env python3
"""Validate the bounded public full-pilot evidence package."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data" / "reconstruction"
PROFILE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "full_pilot_temporal_grid"
    / "detail-250m"
)
SUMMARY = PUBLIC / "full-pilot-response-evidence-summary.json"
GEOJSON = PUBLIC / "full-pilot-response-evidence.geojson"
OBSERVATIONS = PUBLIC / "full-pilot-response-evidence.jsonl"
CROPS = PUBLIC / "full-pilot-response-evidence-crops.jsonl"
REMOTE_PREFIX = (
    "https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev/"
    "data/chips/full-pilot-response-evidence/"
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def main() -> int:
    errors: list[str] = []
    for path in (SUMMARY, GEOJSON, OBSERVATIONS, CROPS):
        if not path.is_file():
            errors.append(f"missing:{path.relative_to(ROOT)}")
    if errors:
        raise SystemExit("\n".join(errors))

    summary = json.loads(SUMMARY.read_text())
    geojson = json.loads(GEOJSON.read_text())
    observations = read_jsonl(OBSERVATIONS)
    crops = read_jsonl(CROPS)
    coverage = summary.get("coverage") or {}

    if coverage.get("gridCells") != 2283:
        errors.append("coverage.gridCells must equal 2283")
    if coverage.get("pairedVlmCoverage") != coverage.get("eligibleImageryStacks"):
        errors.append("paired VLM coverage is incomplete")
    if coverage.get("candidateCells") != len(observations):
        errors.append("candidate observation count does not match summary")
    if coverage.get("cropPairs") != len(crops):
        errors.append("crop pair count does not match summary")
    features = geojson.get("features") or []
    if len(features) != len(observations):
        errors.append("GeoJSON feature count does not match observations")
    if len(summary.get("topObservations") or []) > 24:
        errors.append("topObservations exceeds the bounded 24-item payload")
    imagery_grid = summary.get("imageryGrid") or {}
    if imagery_grid.get("validationStatus") != "pass":
        errors.append("imagery validation did not pass")
    if imagery_grid.get("validationFailureCount") != 0:
        errors.append("imagery validation includes failures")
    if imagery_grid.get("selectedDatedSceneImages") != 9794:
        errors.append("unexpected selected dated scene count")

    native_images = 0
    enhanced_images = 0
    for pair in crops:
        for image in pair.get("images") or []:
            native_images += 1
            native = image.get("nativeImage") or ""
            if not native.startswith(REMOTE_PREFIX):
                errors.append(f"non-R2 native image:{pair.get('pairId')}")
            local = image.get("nativeLocalFallback") or ""
            if not local.startswith("/data/chips/full-pilot-response-evidence/"):
                errors.append(f"invalid local fallback:{pair.get('pairId')}")
            digest = image.get("nativeSha256") or ""
            if len(digest) != 64:
                errors.append(f"invalid native hash:{pair.get('pairId')}")
            if not image.get("license"):
                errors.append(f"missing image license:{pair.get('pairId')}")
            if image.get("enhancedImage"):
                enhanced_images += 1
                if not image["enhancedImage"].startswith(REMOTE_PREFIX):
                    errors.append(f"non-R2 enhanced image:{pair.get('pairId')}")
                if image.get("enhancementStatus") != "display-only":
                    errors.append(f"unlabeled enhanced image:{pair.get('pairId')}")
    if native_images != coverage.get("nativeCropImages"):
        errors.append("native crop image count does not match summary")
    if enhanced_images != coverage.get("enhancedDisplayImages"):
        errors.append("enhanced image count does not match summary")

    for source in (summary.get("documentaryEvidence") or {}).get("sources") or []:
        if not str(source.get("url") or "").startswith("https://"):
            errors.append(f"non-HTTPS documentary source:{source.get('id')}")
        if not source.get("claims") or not source.get("claimsEs"):
            errors.append(f"missing bilingual documentary claims:{source.get('id')}")

    serialized = "\n".join(
        path.read_text(errors="replace")
        for path in (SUMMARY, GEOJSON, OBSERVATIONS, CROPS)
    )
    for forbidden in ("/Users/", "HF_TOKEN", "MINIMAX_API_KEY"):
        if forbidden in serialized:
            errors.append(f"forbidden public value:{forbidden}")

    report = {
        "version": 1,
        "validatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "pass" if not errors else "fail",
        "errors": errors[:100],
        "gridCells": coverage.get("gridCells"),
        "pairedVlmCoverage": coverage.get("pairedVlmCoverage"),
        "candidateCells": len(observations),
        "geoJsonFeatures": len(features),
        "cropPairs": len(crops),
        "nativeCropImages": native_images,
        "enhancedDisplayImages": enhanced_images,
        "documentarySources": len(
            (summary.get("documentaryEvidence") or {}).get("sources") or []
        ),
    }
    (PROFILE / "public_package_validation.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
