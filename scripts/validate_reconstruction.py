#!/usr/bin/env python3
"""Validate the public aftermath reconstruction data contract."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "public" / "data" / "reconstruction" / "la-guaira-timeline.json"

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


def main() -> None:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    assert payload.get("version") == 1, "unsupported reconstruction version"
    parse_datetime(payload["updatedAt"], "updatedAt")
    origin = parse_datetime(payload["eventOrigin"], "eventOrigin")

    sources = payload.get("sources")
    events = payload.get("events")
    assert isinstance(sources, list) and sources, "sources must be non-empty"
    assert isinstance(events, list) and events, "events must be non-empty"

    source_ids = [source.get("id") for source in sources]
    assert all(isinstance(source_id, str) and source_id for source_id in source_ids), "source id missing"
    assert len(source_ids) == len(set(source_ids)), "duplicate source ids"
    for source in sources:
        assert str(source.get("url", "")).startswith("https://"), f"invalid source URL: {source.get('id')}"
        parse_datetime(source["publishedAt"], f"source {source['id']}.publishedAt")
        assert source.get("evidenceClass") in {"primary", "secondary", "derived"}

    event_ids: list[str] = []
    previous_start = origin
    for event in events:
        event_id = event.get("id")
        assert isinstance(event_id, str) and event_id, "event id missing"
        event_ids.append(event_id)
        starts_at = parse_datetime(event["startsAt"], f"event {event_id}.startsAt")
        assert starts_at >= origin, f"event {event_id} predates origin"
        assert starts_at >= previous_start, f"events are not chronological at {event_id}"
        previous_start = starts_at
        if event.get("endsAt"):
            ends_at = parse_datetime(event["endsAt"], f"event {event_id}.endsAt")
            assert ends_at >= starts_at, f"event {event_id} ends before it starts"
        require_localized(event.get("title"), f"event {event_id}.title")
        require_localized(event.get("summary"), f"event {event_id}.summary")
        assert event.get("confidence") in ALLOWED_CONFIDENCE, f"bad confidence on {event_id}"
        assert event.get("responseStage") in ALLOWED_STAGE, f"bad stage on {event_id}"
        event_sources = event.get("sourceIds")
        assert isinstance(event_sources, list) and event_sources, f"event {event_id} has no sources"
        unknown = sorted(set(event_sources) - set(source_ids))
        assert not unknown, f"event {event_id} has unknown sources: {unknown}"
        image = event.get("image")
        if image:
            assert str(image.get("src", "")).startswith("/data/"), f"event {event_id} image must be local public data"
            image_path = ROOT / "public" / str(image["src"]).lstrip("/")
            assert image_path.is_file(), f"event {event_id} image missing: {image_path}"
            require_localized(image.get("alt"), f"event {event_id}.image.alt")
            require_localized(image.get("caption"), f"event {event_id}.image.caption")

    assert len(event_ids) == len(set(event_ids)), "duplicate event ids"

    first72 = payload.get("first72Assessment", {})
    cutoff = parse_datetime(first72["cutoff"], "first72Assessment.cutoff")
    assert cutoff > origin, "first72 cutoff must follow origin"
    require_localized(first72.get("headline"), "first72Assessment.headline")
    require_localized(first72.get("summary"), "first72Assessment.summary")
    findings = first72.get("findings")
    assert isinstance(findings, list) and findings, "first72 findings missing"
    for finding in findings:
        finding_id = finding.get("id")
        require_localized(finding.get("title"), f"finding {finding_id}.title")
        require_localized(finding.get("body"), f"finding {finding_id}.body")
        assert finding.get("confidence") in ALLOWED_CONFIDENCE, f"bad finding confidence: {finding_id}"
        assert finding.get("status") in ALLOWED_STAGE, f"bad finding stage: {finding_id}"
        unknown = sorted(set(finding.get("sourceIds", [])) - set(source_ids))
        assert not unknown, f"finding {finding_id} has unknown sources: {unknown}"

    print(
        f"Reconstruction valid: {len(events)} events, "
        f"{len(sources)} sources, {len(findings)} first-72-hour findings."
    )


if __name__ == "__main__":
    main()
