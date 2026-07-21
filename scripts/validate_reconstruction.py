#!/usr/bin/env python3
"""Validate the reconstruction catalog and every published evidence packet."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "public" / "data" / "reconstruction"
CATALOG_PATH = DATA_DIR / "catalog.json"
AERIAL_EVIDENCE_PATH = DATA_DIR / "aerial-response-evidence-la-guaira.json"

ALLOWED_CONFIDENCE = {"confirmed", "corroborated", "single-source", "inferred"}
ALLOWED_STAGE = {
    "impact",
    "announced",
    "reported",
    "mobilized",
    "arrived-country",
    "arrived-region",
    "observed-site",
    "operational",
    "assessment",
    "recovery",
}


def parse_datetime(value: str, label: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AssertionError(f"{label} is not ISO-8601: {value}") from exc


def require_localized(value: object, label: str) -> None:
    assert isinstance(value, dict), f"{label} must be an object"
    assert isinstance(value.get("es"), str) and value["es"].strip(), f"{label}.es missing"
    assert isinstance(value.get("en"), str) and value["en"].strip(), f"{label}.en missing"


def validate_image(image: dict[str, Any], label: str) -> None:
    src = str(image.get("src", ""))
    assert src.startswith("/data/"), f"{label} image must be local public data"
    image_path = ROOT / "public" / src.lstrip("/")
    assert image_path.is_file(), f"{label} image missing: {image_path}"
    require_localized(image.get("alt"), f"{label}.image.alt")
    require_localized(image.get("caption"), f"{label}.image.caption")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_aerial_evidence(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    prefix = path.name
    assert payload.get("version") == 1, f"{prefix}: unsupported version"
    assert payload.get("aoiId") == "emsr884-aoi12-caraballeda", f"{prefix}: wrong AOI"
    parse_datetime(payload["updatedAt"], f"{prefix}.updatedAt")
    parse_datetime(payload["acquisitionAt"], f"{prefix}.acquisitionAt")

    inventory = payload.get("inventory", {})
    assert inventory.get("url") == "/data/imagery/emsr884-acquisitions.json", f"{prefix}: imagery inventory missing"
    assert inventory.get("officialAois") == 13, f"{prefix}: official AOI count mismatch"
    assert inventory.get("localOpticalAois") == 12, f"{prefix}: local optical AOI count mismatch"
    assert inventory.get("opticalProductRecords") >= inventory.get("distinctOpticalAcquisitions", 0)
    assert inventory.get("publiclyReadableOpticalCogs") >= inventory.get("distinctOpticalAcquisitions", 0)
    require_localized(inventory.get("countingNote"), f"{prefix}.inventory.countingNote")

    temporal_review = payload.get("temporalReview", {})
    assert temporal_review.get("status") == "human-reviewed", f"{prefix}: temporal review status missing"
    require_localized(temporal_review.get("summary"), f"{prefix}.temporalReview.summary")
    official_july5 = temporal_review.get("officialJuly5", {})
    assert official_july5.get("candidateLocationsChecked") == 26
    assert official_july5.get("publishedSitesChecked") == 5
    assert official_july5.get("publishedSitesUsableForObjectComparison") == 0
    require_localized(official_july5.get("finding"), f"{prefix}.temporalReview.officialJuly5.finding")
    external_followup = temporal_review.get("externalFollowup", {})
    assert external_followup.get("publishedSitesChecked") == 5
    assert external_followup.get("usableComparisons") == 5
    require_localized(external_followup.get("finding"), f"{prefix}.temporalReview.externalFollowup.finding")

    review = payload.get("review", {})
    require_localized(review.get("method"), f"{prefix}.review.method")
    require_localized(review.get("summary"), f"{prefix}.review.summary")
    require_localized(review.get("absenceCaveat"), f"{prefix}.review.absenceCaveat")
    candidate_ids = review.get("candidateIds")
    assert isinstance(candidate_ids, list) and candidate_ids, f"{prefix}: candidateIds missing"
    assert len(candidate_ids) == len(set(candidate_ids)), f"{prefix}: duplicate candidate ids"
    assert review.get("candidateRecords") == len(candidate_ids), f"{prefix}: candidate count mismatch"

    enhancement = payload.get("enhancement", {})
    assert enhancement.get("status") == "display-only", f"{prefix}: enhancement must be display-only"
    assert enhancement.get("scale") == 2, f"{prefix}: only reviewed 2x derivatives are allowed"
    require_localized(enhancement.get("method"), f"{prefix}.enhancement.method")
    require_localized(enhancement.get("acceptanceRule"), f"{prefix}.enhancement.acceptanceRule")

    benchmarks = payload.get("modelBenchmarks")
    assert isinstance(benchmarks, list) and benchmarks, f"{prefix}: model benchmarks missing"
    accepted = [item for item in benchmarks if item.get("result") == "accepted-display-only"]
    assert len(accepted) == 1, f"{prefix}: exactly one display-only model must be accepted"
    for benchmark in benchmarks:
        assert benchmark.get("result") in {"accepted-display-only", "rejected"}
        require_localized(benchmark.get("note"), f"{prefix}: benchmark {benchmark.get('modelId')}.note")

    observations = payload.get("observations")
    assert isinstance(observations, list) and observations, f"{prefix}: observations missing"
    observation_ids = [item.get("id") for item in observations]
    assert len(observation_ids) == len(set(observation_ids)), f"{prefix}: duplicate observations"
    likely_count = 0
    unresolved_count = 0
    for observation in observations:
        observation_id = observation.get("id")
        chip_id = observation.get("chipId")
        assert chip_id in candidate_ids, f"{prefix}: {observation_id} was not in the review queue"
        assert observation.get("status") in {"likely-response-related", "unresolved"}
        likely_count += observation.get("status") == "likely-response-related"
        unresolved_count += observation.get("status") == "unresolved"
        assert observation.get("confidence") == "inferred", f"{prefix}: imagery observations must be inferred"
        assert observation.get("category") in {"heavy-machinery", "large-vehicles", "site-use"}
        require_localized(observation.get("title"), f"{prefix}: {observation_id}.title")
        require_localized(observation.get("finding"), f"{prefix}: {observation_id}.finding")
        for image_key, hash_key in (
            ("nativeImage", "nativeSha256"),
            ("enhancedImage", "enhancedSha256"),
        ):
            src = str(observation.get(image_key, ""))
            assert src.startswith("/data/"), f"{prefix}: {observation_id}.{image_key} must be public data"
            image_path = ROOT / "public" / src.lstrip("/")
            assert image_path.is_file(), f"{prefix}: missing image {image_path}"
            assert file_sha256(image_path) == observation.get(hash_key), (
                f"{prefix}: hash mismatch for {observation_id}.{image_key}"
            )
        assert str(observation.get("mapUrl", "")).startswith("https://www.google.com/maps/")
        followup = observation.get("temporalFollowup", {})
        parse_datetime(followup["acquisitionAt"], f"{prefix}: {observation_id}.temporalFollowup.acquisitionAt")
        assert followup.get("sourceRole") == "external-triage"
        assert followup.get("reviewStatus") in {
            "weakens-response-attribution",
            "supports-object-persistence",
            "not-discernible-in-followup",
        }
        require_localized(followup.get("finding"), f"{prefix}: {observation_id}.temporalFollowup.finding")
        require_localized(followup.get("limitations"), f"{prefix}: {observation_id}.temporalFollowup.limitations")
        for image_key, hash_key in (
            ("nativeImage", "nativeSha256"),
            ("enhancedImage", "enhancedSha256"),
            ("compareImage", "compareSha256"),
        ):
            src = str(followup.get(image_key, ""))
            assert src.startswith("/data/"), (
                f"{prefix}: {observation_id}.temporalFollowup.{image_key} must be public data"
            )
            image_path = ROOT / "public" / src.lstrip("/")
            assert image_path.is_file(), f"{prefix}: missing temporal image {image_path}"
            assert file_sha256(image_path) == followup.get(hash_key), (
                f"{prefix}: temporal hash mismatch for {observation_id}.{image_key}"
            )

    assert review.get("publishedSites") == len(observations), f"{prefix}: published site count mismatch"
    assert review.get("likelyResponseSites") == likely_count, f"{prefix}: likely site count mismatch"
    assert review.get("unresolvedSites") == unresolved_count, f"{prefix}: unresolved site count mismatch"
    return {
        "candidates": len(candidate_ids),
        "observations": len(observations),
        "likely": likely_count,
    }


def validate_packet(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    prefix = path.name
    assert payload.get("version") == 1, f"{prefix}: unsupported reconstruction version"
    assert isinstance(payload.get("id"), str) and payload["id"], f"{prefix}: id missing"
    parse_datetime(payload["updatedAt"], f"{prefix}.updatedAt")
    origin = parse_datetime(payload["eventOrigin"], f"{prefix}.eventOrigin")

    coverage = payload.get("coverage", {})
    require_localized(coverage.get("geography"), f"{prefix}.coverage.geography")
    require_localized(coverage.get("note"), f"{prefix}.coverage.note")
    parse_datetime(coverage["startsAt"], f"{prefix}.coverage.startsAt")
    parse_datetime(coverage["endsAt"], f"{prefix}.coverage.endsAt")
    parse_datetime(coverage["latestEvidenceAt"], f"{prefix}.coverage.latestEvidenceAt")
    parse_datetime(coverage["latestOpenSatelliteAt"], f"{prefix}.coverage.latestOpenSatelliteAt")

    sources = payload.get("sources")
    events = payload.get("events")
    assert isinstance(sources, list) and sources, f"{prefix}: sources must be non-empty"
    assert isinstance(events, list) and events, f"{prefix}: events must be non-empty"

    source_ids = [source.get("id") for source in sources]
    assert all(isinstance(source_id, str) and source_id for source_id in source_ids), f"{prefix}: source id missing"
    assert len(source_ids) == len(set(source_ids)), f"{prefix}: duplicate source ids"
    source_id_set = set(source_ids)
    for source in sources:
        assert str(source.get("url", "")).startswith("https://"), f"{prefix}: invalid source URL: {source.get('id')}"
        parse_datetime(source["publishedAt"], f"{prefix}: source {source['id']}.publishedAt")
        assert source.get("evidenceClass") in {"primary", "secondary", "derived"}

    event_ids: list[str] = []
    previous_start = origin
    image_event_count = 0
    for event in events:
        event_id = event.get("id")
        assert isinstance(event_id, str) and event_id, f"{prefix}: event id missing"
        event_ids.append(event_id)
        starts_at = parse_datetime(event["startsAt"], f"{prefix}: event {event_id}.startsAt")
        assert starts_at >= origin, f"{prefix}: event {event_id} predates origin"
        assert starts_at >= previous_start, f"{prefix}: events are not chronological at {event_id}"
        previous_start = starts_at
        if event.get("endsAt"):
            ends_at = parse_datetime(event["endsAt"], f"{prefix}: event {event_id}.endsAt")
            assert ends_at >= starts_at, f"{prefix}: event {event_id} ends before it starts"
        require_localized(event.get("title"), f"{prefix}: event {event_id}.title")
        require_localized(event.get("summary"), f"{prefix}: event {event_id}.summary")
        assert event.get("confidence") in ALLOWED_CONFIDENCE, f"{prefix}: bad confidence on {event_id}"
        assert event.get("responseStage") in ALLOWED_STAGE, f"{prefix}: bad stage on {event_id}"
        event_sources = event.get("sourceIds")
        assert isinstance(event_sources, list) and event_sources, f"{prefix}: event {event_id} has no sources"
        unknown = sorted(set(event_sources) - source_id_set)
        assert not unknown, f"{prefix}: event {event_id} has unknown sources: {unknown}"
        image = event.get("image")
        if image:
            image_event_count += 1
            validate_image(image, f"{prefix}: event {event_id}")

    assert len(event_ids) == len(set(event_ids)), f"{prefix}: duplicate event ids"

    first72 = payload.get("first72Assessment", {})
    cutoff = parse_datetime(first72["cutoff"], f"{prefix}.first72Assessment.cutoff")
    assert cutoff > origin, f"{prefix}: first72 cutoff must follow origin"
    require_localized(first72.get("headline"), f"{prefix}.first72Assessment.headline")
    require_localized(first72.get("summary"), f"{prefix}.first72Assessment.summary")
    findings = first72.get("findings")
    assert isinstance(findings, list) and findings, f"{prefix}: first72 findings missing"
    finding_ids: list[str] = []
    for finding in findings:
        finding_id = finding.get("id")
        assert isinstance(finding_id, str) and finding_id, f"{prefix}: finding id missing"
        finding_ids.append(finding_id)
        require_localized(finding.get("title"), f"{prefix}: finding {finding_id}.title")
        require_localized(finding.get("body"), f"{prefix}: finding {finding_id}.body")
        assert finding.get("confidence") in ALLOWED_CONFIDENCE, f"{prefix}: bad finding confidence: {finding_id}"
        assert finding.get("status") in ALLOWED_STAGE, f"{prefix}: bad finding stage: {finding_id}"
        finding_sources = finding.get("sourceIds")
        assert isinstance(finding_sources, list) and finding_sources, f"{prefix}: finding {finding_id} has no sources"
        unknown = sorted(set(finding_sources) - source_id_set)
        assert not unknown, f"{prefix}: finding {finding_id} has unknown sources: {unknown}"
        if finding.get("image"):
            validate_image(finding["image"], f"{prefix}: finding {finding_id}")
    assert len(finding_ids) == len(set(finding_ids)), f"{prefix}: duplicate finding ids"

    return {
        "id": payload["id"],
        "events": len(events),
        "sources": len(sources),
        "findings": len(findings),
        "imageEvents": image_event_count,
    }


def main() -> None:
    aerial_result = validate_aerial_evidence(AERIAL_EVIDENCE_PATH)
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    assert catalog.get("version") == 1, "unsupported catalog version"
    parse_datetime(catalog["updatedAt"], "catalog.updatedAt")
    entries = catalog.get("entries")
    assert isinstance(entries, list) and entries, "catalog entries missing"

    slugs = [entry.get("slug") for entry in entries]
    ids = [entry.get("id") for entry in entries]
    assert len(slugs) == len(set(slugs)), "duplicate catalog slug"
    assert len(ids) == len(set(ids)), "duplicate catalog id"
    assert catalog.get("defaultSlug") in slugs, "defaultSlug is not in catalog"

    results = []
    for entry in entries:
        require_localized(entry.get("geography"), f"catalog {entry.get('slug')}.geography")
        require_localized(entry.get("description"), f"catalog {entry.get('slug')}.description")
        gaps = entry.get("gaps")
        assert isinstance(gaps, list), f"catalog {entry.get('slug')}.gaps must be a list"
        for index, gap in enumerate(gaps):
            require_localized(gap, f"catalog {entry.get('slug')}.gaps[{index}]")
        data_path = str(entry.get("dataPath", ""))
        assert data_path.startswith("/data/reconstruction/"), f"bad dataPath for {entry.get('slug')}"
        packet_path = ROOT / "public" / data_path.lstrip("/")
        assert packet_path.is_file(), f"missing packet: {packet_path}"
        result = validate_packet(packet_path)
        assert result["id"] == entry["id"], f"catalog id mismatch for {entry['slug']}"
        for field, result_key in (
            ("eventCount", "events"),
            ("sourceCount", "sources"),
            ("imageEventCount", "imageEvents"),
        ):
            assert entry.get(field) == result[result_key], (
                f"catalog {entry['slug']}.{field}={entry.get(field)} "
                f"does not match packet {result[result_key]}"
            )
        results.append((entry["slug"], result))

    summary = ", ".join(
        f"{slug}: {result['events']} events/{result['sources']} sources"
        for slug, result in results
    )
    print(
        f"Reconstruction catalog valid ({len(results)} packets): {summary}. "
        f"Aerial review valid ({aerial_result['candidates']} candidates/"
        f"{aerial_result['observations']} published/{aerial_result['likely']} likely response sites)."
    )


if __name__ == "__main__":
    main()
