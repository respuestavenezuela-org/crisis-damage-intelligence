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
EXPLORER_CELLS = PUBLIC / "full-pilot-evidence-cells"
EXPLORER_SUMMARY = PUBLIC / "full-pilot-evidence-explorer-summary.json"
MAPACTION_RESPONSE = PUBLIC / "mapaction-response-sites-la-guaira.json"
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
    for path in (
        SUMMARY,
        GEOJSON,
        OBSERVATIONS,
        CROPS,
        EXPLORER_SUMMARY,
        MAPACTION_RESPONSE,
    ):
        if not path.is_file():
            errors.append(f"missing:{path.relative_to(ROOT)}")
    if errors:
        raise SystemExit("\n".join(errors))

    summary = json.loads(SUMMARY.read_text())
    explorer_summary = json.loads(EXPLORER_SUMMARY.read_text())
    mapaction_response = json.loads(MAPACTION_RESPONSE.read_text())
    geojson = json.loads(GEOJSON.read_text())
    observations = read_jsonl(OBSERVATIONS)
    crops = read_jsonl(CROPS)
    coverage = summary.get("coverage") or {}
    observation_ids = {row.get("cellId") for row in observations}

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
    if "topObservations" in explorer_summary:
        errors.append("explorer summary must not embed top observations")
    explorer_metadata = explorer_summary.get("explorer") or {}
    if explorer_metadata.get("candidateCells") != len(observations):
        errors.append("explorer summary candidate count does not match observations")
    if explorer_metadata.get("cropPairs") != len(crops):
        errors.append("explorer summary crop pair count does not match manifest")
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

    detail_files = sorted(EXPLORER_CELLS.glob("*.json"))
    if len(detail_files) != len(observations):
        errors.append("explorer detail file count does not match observations")
    detail_pair_count = 0
    for path in detail_files:
        detail = json.loads(path.read_text())
        observation = detail.get("observation") or {}
        cell_id = observation.get("cellId")
        if path.stem != cell_id or cell_id not in observation_ids:
            errors.append(f"invalid explorer cell detail:{path.name}")
        pairs = detail.get("evidencePairs") or []
        detail_pair_count += len(pairs)
        if detail.get("pairCount") != len(pairs):
            errors.append(f"invalid explorer pair count:{path.name}")
        if any(pair.get("cellId") != cell_id for pair in pairs):
            errors.append(f"cross-cell explorer pair:{path.name}")
    if detail_pair_count != len(crops):
        errors.append("explorer detail pair total does not match crop manifest")

    for source in (summary.get("documentaryEvidence") or {}).get("sources") or []:
        if not str(source.get("url") or "").startswith("https://"):
            errors.append(f"non-HTTPS documentary source:{source.get('id')}")
        if not source.get("claims") or not source.get("claimsEs"):
            errors.append(f"missing bilingual documentary claims:{source.get('id')}")

    response_findings = mapaction_response.get("headlineFindings") or {}
    response_sites = mapaction_response.get("responseSites") or []
    if response_findings.get("mappedResponseSites") != 5 or len(response_sites) != 5:
        errors.append("MapAction response-site count must equal 5")
    if response_findings.get("annotatedSleepingAreas") != 13:
        errors.append("MapAction annotated sleeping-area count must equal 13")
    if response_findings.get("capacityLabeledShelters") != 9:
        errors.append("MapAction capacity-labelled shelter count must equal 9")
    if response_findings.get("printedCapacityPeopleTotal") != 3260:
        errors.append("MapAction printed capacity total must equal 3260")
    if response_findings.get("namedTemporaryWasteSites") != 14:
        errors.append("MapAction waste-site count must equal 14")
    if len({site.get("id") for site in response_sites}) != len(response_sites):
        errors.append("MapAction response-site IDs must be unique")
    for site in response_sites:
        if not str(site.get("datasetUrl") or "").startswith("https://"):
            errors.append(f"non-HTTPS MapAction source:{site.get('id')}")
        if not site.get("documentedAsOf"):
            errors.append(f"missing MapAction source date:{site.get('id')}")
        longitude = site.get("longitude")
        latitude = site.get("latitude")
        if not isinstance(longitude, (int, float)) or not -180 <= longitude <= 180:
            errors.append(f"invalid MapAction longitude:{site.get('id')}")
        if not isinstance(latitude, (int, float)) or not -90 <= latitude <= 90:
            errors.append(f"invalid MapAction latitude:{site.get('id')}")
        crosscheck = site.get("aerialCrosscheck") or {}
        if not crosscheck.get("nearestCandidate"):
            errors.append(f"missing aerial cross-check:{site.get('id')}")
    model_quality = mapaction_response.get("modelQuality") or {}
    if any(
        forbidden_key in json.dumps(model_quality)
        for forbidden_key in ("hfQwenRange", "minimaxRange")
    ):
        errors.append("unstable VLM unit-count ranges leaked into public package")
    if any(
        comparison.get("publicationDecision") != "withhold-visual-unit-count"
        for comparison in model_quality.get("campUnitCountComparisons") or []
    ):
        errors.append("MapAction visual unit-count publication guardrail missing")
    debris = mapaction_response.get("debrisManagement") or {}
    if len(debris.get("namedTemporaryDisposalAndSortingSites") or []) != 14:
        errors.append("MapAction named waste-site list must contain 14 sites")
    if len(debris.get("healthFacilityDistances") or []) != 5:
        errors.append("MapAction health-facility distance list must contain 5 sites")
    for source in mapaction_response.get("sources") or []:
        if not str(source.get("url") or "").startswith("https://"):
            errors.append(f"non-HTTPS MapAction evidence source:{source.get('id')}")

    serialized = "\n".join(
        path.read_text(errors="replace")
        for path in (
            SUMMARY,
            GEOJSON,
            OBSERVATIONS,
            CROPS,
            MAPACTION_RESPONSE,
        )
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
        "explorerDetailFiles": len(detail_files),
        "explorerDetailPairs": detail_pair_count,
        "explorerSummaryBytes": EXPLORER_SUMMARY.stat().st_size,
        "documentarySources": len(
            (summary.get("documentaryEvidence") or {}).get("sources") or []
        ),
        "mappedResponseSites": len(response_sites),
        "mapActionPublicBytes": MAPACTION_RESPONSE.stat().st_size,
    }
    PROFILE.mkdir(parents=True, exist_ok=True)
    (PROFILE / "public_package_validation.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
