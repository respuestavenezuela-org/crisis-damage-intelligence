#!/usr/bin/env python3
"""Validate the external source registry required fields and guardrails."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "public" / "data" / "sources" / "earthquake_source_review.json"
CATALOG = ROOT / "public" / "data" / "catalog.json"

REQUIRED_SOURCE_FIELDS = {
    "id",
    "title",
    "url",
    "dateAccessed",
    "dataOwner",
    "licenseOrTerms",
    "geography",
    "official",
    "confidence",
    "sourceType",
    "status",
    "reviewStatus",
    "resources",
    "caveat",
}


def valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def main() -> int:
    registry = json.loads(REGISTRY.read_text())
    catalog = json.loads(CATALOG.read_text())
    errors: list[str] = []

    if not registry.get("publicationPolicy", {}).get("doNotTreatSocialOrBookmarkSourcesAsOfficial"):
        errors.append("publicationPolicy.doNotTreatSocialOrBookmarkSourcesAsOfficial must be true")
    if not registry.get("publicationPolicy", {}).get("doNotPublishUnlessSourceTermsConfidenceAreClear"):
        errors.append("publicationPolicy.doNotPublishUnlessSourceTermsConfidenceAreClear must be true")

    source_ids = set()
    for index, source in enumerate(registry.get("sources", []), start=1):
        missing = sorted(REQUIRED_SOURCE_FIELDS - source.keys())
        if missing:
            errors.append(f"source #{index} missing required fields: {', '.join(missing)}")
            continue

        source_id = source["id"]
        if source_id in source_ids:
            errors.append(f"duplicate source id: {source_id}")
        source_ids.add(source_id)

        if not valid_http_url(source["url"]):
            errors.append(f"{source_id}: url is not a valid http(s) URL")
        if not isinstance(source["official"], bool):
            errors.append(f"{source_id}: official must be boolean")
        if not source["dateAccessed"]:
            errors.append(f"{source_id}: dateAccessed is empty")
        if not source["dataOwner"]:
            errors.append(f"{source_id}: dataOwner is empty")
        if not source["licenseOrTerms"]:
            errors.append(f"{source_id}: licenseOrTerms is empty")
        if not source["confidence"]:
            errors.append(f"{source_id}: confidence is empty")

        geography = source["geography"]
        if not isinstance(geography, dict) or not geography.get("label"):
            errors.append(f"{source_id}: geography.label is required")
        if geography.get("bounds") is not None:
            bounds = geography["bounds"]
            if (
                not isinstance(bounds, list)
                or len(bounds) != 2
                or any(not isinstance(point, list) or len(point) != 2 for point in bounds)
            ):
                errors.append(f"{source_id}: geography.bounds must be [[lat, lon], [lat, lon]] or null")

        for resource in source.get("resources", []):
            if not resource.get("url") or not valid_http_url(resource["url"]):
                errors.append(f"{source_id}: resource {resource.get('name', '<unnamed>')} has invalid URL")

    catalog_ids = {aoi.get("id") for aoi in catalog.get("aois", [])}
    queued_public_ids = [
        source["id"]
        for source in registry.get("sources", [])
        if source.get("reviewStatus") == "queued_for_source_review" and source["id"].replace("hdx-msft-", "external-msft-") in catalog_ids
    ]
    if queued_public_ids:
        errors.append(f"queued sources appear to have matching public catalog entries: {', '.join(queued_public_ids)}")

    if errors:
        print("External source registry validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(registry.get('sources', []))} external source records in {REGISTRY.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
