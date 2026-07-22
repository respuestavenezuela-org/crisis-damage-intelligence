#!/usr/bin/env python3
"""Build the bounded static public package for full-pilot response evidence."""

from __future__ import annotations

import json
import math
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "full_pilot_temporal_grid"
    / "detail-250m"
)
DOCUMENTARY = (
    ROOT
    / "ops"
    / "data_acquisition_plan"
    / "full_pilot_temporal_grid"
    / "documentary_sources.json"
)
PUBLIC_RECON = ROOT / "public" / "data" / "reconstruction"
PUBLIC_CHIPS = ROOT / "public" / "data" / "chips" / "full-pilot-response-evidence"
REMOTE_BASE = "https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev"


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text().splitlines()
        if line.strip()
    ]


def evidence_tier_rank(tier: str) -> int:
    return {
        "cross_model_positive_with_detector_delta": 4,
        "cross_model_positive": 3,
        "contested_positive_with_detector_delta": 2,
        "contested_positive": 1,
    }.get(tier, 0)


def mercator_to_lonlat(x: float, y: float) -> list[float]:
    longitude = x * 180 / 20037508.34
    latitude = math.degrees(
        2 * math.atan(math.exp(math.radians(y * 180 / 20037508.34)))
        - math.pi / 2
    )
    return [round(longitude, 7), round(latitude, 7)]


def bounds_polygon(bounds: list[float]) -> list[list[list[float]]]:
    west, south, east, north = bounds
    southwest = mercator_to_lonlat(west, south)
    southeast = mercator_to_lonlat(east, south)
    northeast = mercator_to_lonlat(east, north)
    northwest = mercator_to_lonlat(west, north)
    return [[southwest, southeast, northeast, northwest, southwest]]


def public_image_path(source: Path, role: str) -> tuple[str, str]:
    directory = PUBLIC_CHIPS / role
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / source.name
    if not destination.is_file() or destination.stat().st_size != source.stat().st_size:
        shutil.copy2(source, destination)
    relative = destination.relative_to(ROOT / "public")
    local_url = "/" + relative.as_posix()
    remote_url = f"{REMOTE_BASE}/{relative.as_posix()}"
    return local_url, remote_url


def main() -> int:
    stack_summary = json.loads((PROFILE / "summary.json").read_text())
    imagery_validation = json.loads((PROFILE / "imagery_validation.json").read_text())
    consensus_summary = json.loads(
        (PROFILE / "enhanced_consensus_summary.json").read_text()
    )
    timeline_summary = json.loads((PROFILE / "response-timeline" / "summary.json").read_text())
    timeline = json.loads((PROFILE / "response-timeline" / "timeline.json").read_text())
    observations = read_rows(PROFILE / "response-timeline" / "observations.jsonl")
    crop_pairs = read_rows(PROFILE / "evidence-crops" / "manifest.jsonl")
    documentary = json.loads(DOCUMENTARY.read_text())
    crops_by_pair = {}
    public_crop_rows = []
    copied_native = 0
    copied_enhanced = 0
    for pair in crop_pairs:
        images = []
        for image in pair.get("images") or []:
            native_source = ROOT / image["nativeCropPath"]
            native_local, native_remote = public_image_path(native_source, "native")
            copied_native += 1
            enhanced_local = None
            enhanced_remote = None
            if image.get("enhancedPath"):
                enhanced_source = ROOT / image["enhancedPath"]
                enhanced_local, enhanced_remote = public_image_path(
                    enhanced_source, "enhanced-visualization-only"
                )
                copied_enhanced += 1
            images.append(
                {
                    "role": image.get("role"),
                    "sceneId": image.get("sceneId"),
                    "acquisitionUtc": image.get("acquisitionUtc"),
                    "sensor": image.get("sensor"),
                    "sourceFamily": image.get("sourceFamily"),
                    "license": image.get("license"),
                    "nativeImage": native_remote,
                    "nativeLocalFallback": native_local,
                    "nativeSha256": image.get("nativeCropSha256"),
                    "enhancedImage": enhanced_remote,
                    "enhancedLocalFallback": enhanced_local,
                    "enhancedSha256": image.get("enhancedSha256"),
                    "enhancementStatus": (
                        "display-only" if enhanced_remote else "not-generated"
                    ),
                }
            )
        public_pair = {
            "pairId": pair["pairId"],
            "rank": pair["rank"],
            "rankScore": pair["rankScore"],
            "cellId": pair["cellId"],
            "consensus": pair.get("consensus"),
            "assetCategories": pair.get("assetCategories") or [],
            "targetDetection": pair.get("targetDetection"),
            "targetAcquisitionUtc": pair.get("targetAcquisitionUtc"),
            "targetWithinFirst72Hours": pair.get("targetWithinFirst72Hours"),
            "images": images,
            "policy": pair.get("policy"),
        }
        public_crop_rows.append(public_pair)
        crops_by_pair[pair["pairId"]] = public_pair

    public_observations = []
    features = []
    for observation in observations:
        bounds = observation.get("bounds3857") or []
        cell_polygon = bounds_polygon(bounds) if len(bounds) == 4 else None
        pair_ids = [
            pair["pairId"]
            for pair in observation.get("evidenceCrops") or []
            if pair.get("pairId") in crops_by_pair
        ]
        public = {
            "cellId": observation["cellId"],
            "longitude": observation.get("centerLon"),
            "latitude": observation.get("centerLat"),
            "cellBoundsWgs84": cell_polygon[0] if cell_polygon else None,
            "coveredByAois": observation.get("coveredByAois") or [],
            "stackStatus": observation.get("stackStatus"),
            "firstVisibleAcquisitionUtc": observation.get("firstVisibleAcquisitionUtc"),
            "hoursAfterEvent": observation.get("hoursAfterEvent"),
            "timeWindow": observation.get("timeWindow"),
            "evidenceTier": observation.get("evidenceTier"),
            "consensus": observation.get("consensus"),
            "priorityScore": observation.get("priorityScore"),
            "assetCategories": observation.get("assetCategories") or [],
            "detector": observation.get("detector"),
            "cropPairIds": pair_ids,
            "publicationStatus": "ai-triage-native-review-required",
            "arrivalInterpretation": observation.get("arrivalInterpretation"),
        }
        public_observations.append(public)
        features.append(
            {
                "type": "Feature",
                "id": observation["cellId"],
                "geometry": {
                    "type": "Polygon" if cell_polygon else "Point",
                    "coordinates": cell_polygon
                    if cell_polygon
                    else [observation.get("centerLon"), observation.get("centerLat")],
                },
                "properties": {
                    key: value
                    for key, value in public.items()
                    if key
                    not in {
                        "longitude",
                        "latitude",
                        "cellBoundsWgs84",
                        "detector",
                    }
                },
            }
        )
    public_observations.sort(
        key=lambda row: (
            -evidence_tier_rank(str(row.get("evidenceTier"))),
            -int(row.get("priorityScore") or 0),
            row["cellId"],
        )
    )
    top = []
    for observation in public_observations[:24]:
        pair = (
            crops_by_pair.get(observation["cropPairIds"][0])
            if observation["cropPairIds"]
            else None
        )
        top.append(
            {
                **observation,
                "evidencePair": pair,
            }
        )
    window_counts = Counter(
        observation.get("timeWindow") or "undated" for observation in public_observations
    )
    area_counts = Counter(
        aoi
        for observation in public_observations
        for aoi in observation.get("coveredByAois") or []
    )
    summary = {
        "version": 1,
        "id": "full-pilot-response-evidence-2026",
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "status": "public-ai-triage",
        "scope": {
            "es": "La Guaira, Caraballeda y Catia La Mar",
            "en": "La Guaira, Caraballeda and Catia La Mar",
        },
        "eventOrigin": "2026-06-24T18:04:33-04:00",
        "imageryGrid": {
            "cellWidthMetersApprox": 250,
            "nativeContentPixels": [768, 768],
            "labeledAnalysisChipPixels": [768, 802],
            "nominalOutputSamplingMetersPerPixel": 0.326,
            "selectedDatedSceneImages": stack_summary["selectedSceneImages"],
            "validationStatus": imagery_validation["status"],
            "readableImages": imagery_validation["readableImages"],
            "hashesChecked": imagery_validation["hashesChecked"],
            "validationFailureCount": imagery_validation["failureCount"],
            "selectionPolicy": stack_summary["selectionPolicy"],
            "warning": (
                "Output sampling preserves available detail but does not improve "
                "the source sensor ground sample distance."
            ),
        },
        "coverage": {
            "gridCells": consensus_summary["fullPilotCells"],
            "eligibleImageryStacks": consensus_summary["eligibleCells"],
            "pairedVlmCoverage": consensus_summary["pairedCoverage"],
            "postEventOnlyCells": consensus_summary["postEventOnlyCells"],
            "candidateCells": len(public_observations),
            "withinFirst72Hours": timeline_summary["withinFirst72Hours"],
            "waldo30Cells": consensus_summary["waldo30Cells"],
            "cropPairs": len(public_crop_rows),
            "nativeCropImages": copied_native,
            "enhancedDisplayImages": copied_enhanced,
        },
        "evidenceTierCounts": timeline_summary["evidenceTierCounts"],
        "timeWindowCounts": dict(sorted(window_counts.items())),
        "assetCategoryCounts": timeline_summary["assetCategoryCounts"],
        "sourceAreaCandidateCounts": dict(sorted(area_counts.items())),
        "sourceAreaCoverageCounts": consensus_summary["sourceAreaCoverageCounts"],
        "timelineEvents": [
            {
                key: event[key]
                for key in (
                    "acquisitionUtc",
                    "hoursAfterEvent",
                    "timeWindow",
                    "candidateCells",
                    "bothModelsPositive",
                    "detectorSupported",
                )
            }
            for event in timeline["events"]
        ],
        "topObservations": top,
        "documentaryEvidence": documentary,
        "downloads": {
            "candidateGeoJson": "/data/reconstruction/full-pilot-response-evidence.geojson",
            "candidateJsonl": "/data/reconstruction/full-pilot-response-evidence.jsonl",
            "cropManifest": "/data/reconstruction/full-pilot-response-evidence-crops.jsonl",
        },
        "method": {
            "vlmProviders": ["Hugging Face Qwen3-VL", "MiniMax-M3"],
            "detector": "StephanST/WALDO30",
            "enhancement": "Swin2SR classical 2x; display-only",
            "arrivalRule": (
                "Dates are earliest visible bounds in available acquisitions, not "
                "actual arrival times."
            ),
            "absenceRule": "Not observed does not mean did not occur.",
        },
        "guardrails": timeline_summary["guardrails"],
    }
    PUBLIC_RECON.mkdir(parents=True, exist_ok=True)
    (PUBLIC_RECON / "full-pilot-response-evidence-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    )
    (PUBLIC_RECON / "full-pilot-response-evidence.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    (PUBLIC_RECON / "full-pilot-response-evidence.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in public_observations)
    )
    (PUBLIC_RECON / "full-pilot-response-evidence-crops.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in public_crop_rows)
    )
    result = {
        "version": 1,
        "candidateCells": len(public_observations),
        "cropPairs": len(public_crop_rows),
        "nativeImagesCopied": copied_native,
        "enhancedImagesCopied": copied_enhanced,
        "publicBytes": sum(
            path.stat().st_size
            for path in [
                PUBLIC_RECON / "full-pilot-response-evidence-summary.json",
                PUBLIC_RECON / "full-pilot-response-evidence.geojson",
                PUBLIC_RECON / "full-pilot-response-evidence.jsonl",
                PUBLIC_RECON / "full-pilot-response-evidence-crops.jsonl",
            ]
        ),
        "chipBytes": sum(path.stat().st_size for path in PUBLIC_CHIPS.rglob("*") if path.is_file()),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
