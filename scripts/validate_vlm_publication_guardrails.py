#!/usr/bin/env python3
"""Validate public VLM outputs do not overstate before/after evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CATALOG = PUBLIC / "data" / "catalog.json"
AOI03_ID = "emsr884-aoi03-antimano"
BEFORE_AFTER_REVIEW_TYPE = "dated_pre_event_comparison"
POST_EVENT_REVIEW_TYPE = "post_event_only"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSONL record: {exc}") from exc
    return records


def public_path(value: str | None) -> Path | None:
    if not value or urlparse(value).scheme:
        return None
    return PUBLIC / value.lstrip("/")


def metric(metrics: dict[str, Any], key: str) -> int:
    value = metrics.get(key) or 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def require_file(errors: list[str], label: str, value: str | None) -> Path | None:
    path = public_path(value)
    if path is None:
        errors.append(f"{label}: expected local public path, got {value!r}")
        return None
    if not path.exists():
        errors.append(f"{label}: missing file {path}")
        return None
    return path


def validate_before_after(
    errors: list[str],
    aoi: dict[str, Any],
    downloads: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[int, int]:
    aoi_id = str(aoi.get("id"))
    reviewed = metric(metrics, "vlmBeforeAfterReviewed")
    skipped_no_before = metric(metrics, "vlmBeforeAfterSkippedNoBefore")
    has_before_after_download = any(str(key).startswith("vlm_before_after") for key in downloads)

    if reviewed <= 0 and not has_before_after_download:
        for key, value in metrics.items():
            if key.startswith("vlmBeforeAfter") and metric(metrics, key) != 0:
                errors.append(f"{aoi_id}: {key} is nonzero without before/after downloads")
        return 0, 0

    if reviewed <= 0:
        errors.append(f"{aoi_id}: before/after downloads exist but vlmBeforeAfterReviewed is {reviewed}")

    before_imagery = (aoi.get("imagery") or {}).get("before")
    after_imagery = (aoi.get("imagery") or {}).get("after")
    if not before_imagery:
        errors.append(f"{aoi_id}: before/after VLM is published without imagery.before metadata")
    if not after_imagery:
        errors.append(f"{aoi_id}: before/after VLM is published without imagery.after metadata")

    jsonl_path = require_file(errors, f"{aoi_id} vlm_before_after_jsonl", downloads.get("vlm_before_after_jsonl"))
    summary_path = require_file(errors, f"{aoi_id} vlm_before_after_summary", downloads.get("vlm_before_after_summary"))
    if jsonl_path is None or summary_path is None:
        return 0, skipped_no_before

    records = read_jsonl(jsonl_path)
    summary = read_json(summary_path)
    summary_reviewed = int(summary.get("reviewed") or 0)
    if summary.get("review_type") != BEFORE_AFTER_REVIEW_TYPE:
        errors.append(f"{aoi_id}: summary review_type is {summary.get('review_type')!r}")
    if summary_reviewed != reviewed or len(records) != reviewed:
        errors.append(
            f"{aoi_id}: before/after count mismatch catalog={reviewed} "
            f"summary={summary_reviewed} jsonl={len(records)}"
        )
    if not summary.get("before_source"):
        errors.append(f"{aoi_id}: before/after summary is missing before_source")

    for index, record in enumerate(records, start=1):
        record_id = record.get("id") or f"record-{index}"
        prefix = f"{aoi_id}/{record_id}"
        vlm = record.get("vlm") or {}
        if record.get("aoi_id") != aoi_id:
            errors.append(f"{prefix}: aoi_id mismatch {record.get('aoi_id')!r}")
        if vlm.get("review_type") != BEFORE_AFTER_REVIEW_TYPE:
            errors.append(f"{prefix}: review_type is {vlm.get('review_type')!r}")
        if not vlm.get("before_source"):
            errors.append(f"{prefix}: missing vlm.before_source")
        for chip_key in ("before_event_chip", "post_event_chip", "compare_chip"):
            chip = record.get(chip_key)
            chip_path = public_path(chip)
            if not chip:
                errors.append(f"{prefix}: missing {chip_key}")
            elif chip_path is not None and not chip_path.exists():
                errors.append(f"{prefix}: {chip_key} file does not exist: {chip_path}")

    return len(records), skipped_no_before


def validate_post_event_only(
    errors: list[str],
    aoi: dict[str, Any],
    downloads: dict[str, Any],
    metrics: dict[str, Any],
) -> int:
    aoi_id = str(aoi.get("id"))
    jsonl_value = downloads.get("vlm_jsonl")
    if not jsonl_value:
        return 0

    jsonl_path = require_file(errors, f"{aoi_id} vlm_jsonl", jsonl_value)
    summary_path = require_file(errors, f"{aoi_id} vlm_summary", downloads.get("vlm_summary"))
    if jsonl_path is None:
        return 0

    records = read_jsonl(jsonl_path)
    reviewed = metric(metrics, "vlmPostEventReviewed")
    if reviewed != len(records):
        errors.append(f"{aoi_id}: post-event count mismatch catalog={reviewed} jsonl={len(records)}")
    if not metric(metrics, "vlmBeforeAfterReviewed") and metric(metrics, "vlmReviewed") != 0:
        errors.append(f"{aoi_id}: legacy vlmReviewed is nonzero for post-event-only VLM")

    if summary_path is not None:
        summary = read_json(summary_path)
        if summary.get("review_type") != POST_EVENT_REVIEW_TYPE:
            errors.append(f"{aoi_id}: post-event summary review_type is {summary.get('review_type')!r}")
        if int(summary.get("reviewed") or 0) != len(records):
            errors.append(f"{aoi_id}: post-event summary reviewed does not match JSONL count")

    for index, record in enumerate(records, start=1):
        record_id = record.get("id") or f"record-{index}"
        prefix = f"{aoi_id}/{record_id}"
        vlm = record.get("vlm") or {}
        if vlm.get("review_type") != POST_EVENT_REVIEW_TYPE:
            errors.append(f"{prefix}: post-event JSONL review_type is {vlm.get('review_type')!r}")
        if record.get("before_event_chip") or record.get("compare_chip"):
            errors.append(f"{prefix}: post-event-only record contains before/compare chip fields")
        chip_path = public_path(record.get("post_event_chip"))
        if not record.get("post_event_chip"):
            errors.append(f"{prefix}: missing post_event_chip")
        elif chip_path is not None and not chip_path.exists():
            errors.append(f"{prefix}: post_event_chip file does not exist: {chip_path}")

    return len(records)


def validate_aoi03_public_guardrail(errors: list[str], aoi: dict[str, Any]) -> None:
    metrics = aoi.get("metrics") or {}
    downloads = aoi.get("downloads") or {}
    forbidden_downloads = sorted(key for key in downloads if str(key).startswith("vlm"))
    if forbidden_downloads:
        errors.append(f"{AOI03_ID}: public catalog exposes VLM downloads {forbidden_downloads}")
    for key in ("features", "destroyed", "damagedConfirmed", "possibleDamage", "vlmReviewed"):
        if metric(metrics, key) != 0:
            errors.append(f"{AOI03_ID}: public metric {key} is {metrics.get(key)!r}, expected 0")

    geojson_path = public_path(downloads.get("geojson"))
    if geojson_path and geojson_path.exists():
        feature_count = len((read_json(geojson_path).get("features") or []))
        if feature_count != 0:
            errors.append(f"{AOI03_ID}: public damage GeoJSON contains {feature_count} features")


def main() -> int:
    catalog = read_json(CATALOG)
    errors: list[str] = []
    before_after_records = 0
    skipped_no_before = 0
    post_event_records = 0

    for aoi in catalog.get("aois", []):
        downloads = aoi.get("downloads") or {}
        metrics = aoi.get("metrics") or {}
        reviewed, skipped = validate_before_after(errors, aoi, downloads, metrics)
        before_after_records += reviewed
        skipped_no_before += skipped
        post_event_records += validate_post_event_only(errors, aoi, downloads, metrics)
        if aoi.get("id") == AOI03_ID:
            validate_aoi03_public_guardrail(errors, aoi)

    if errors:
        print("VLM publication guardrail validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VLM publication guardrails passed")
    print(f"before_after_reviewed={before_after_records}")
    print(f"before_after_skipped_no_before={skipped_no_before}")
    print(f"post_event_only_reviewed={post_event_records}")
    print(f"{AOI03_ID}_public_features=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
