#!/usr/bin/env python3
"""Compile filled AOI03 human-validation rows into static review artifacts.

This stays intentionally static and conservative: AOI03 rows are OSM-candidate
leads, not official EMS damage. Only rows with human_status=confirmed_damage,
reviewer/timestamp audit fields, and evidence_uri are promoted into GeoJSON/KML.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = (
    ROOT
    / "ops"
    / "aoi03_internal_review_queue"
    / "adjudication"
    / "human_validation"
    / "human_validation_template.csv"
)
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT.parent / "compiled"

AOI03_ID = "emsr884-aoi03-antimano"
WARNING = (
    "INTERNAL REVIEW ONLY. AOI03 rows are OpenStreetMap candidate leads, "
    "not official EMS damage. Static outputs promote only human-confirmed rows "
    "with independent evidence_uri."
)
ALLOWED_STATUSES = {
    "confirmed_damage",
    "false_positive",
    "needs_better_imagery",
    "needs_field_check",
    "duplicate_or_bad_footprint",
}
ALLOWED_DAMAGE_CLASSES = {
    "destroyed",
    "major_damage",
    "minor_damage",
    "no_visible_damage",
    "unknown",
}


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return [{key: as_text(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def read_jsonl(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line_number, raw in enumerate(path.read_text().splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSONL: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append({key: as_text(value) for key, value in data.items()})
    return rows


def read_rows(path: Path) -> list[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        return read_jsonl(path)
    raise ValueError(f"Unsupported input format {path.suffix!r}; use CSV or JSONL")


def candidate_id(row: dict[str, str]) -> str:
    return as_text(row.get("candidate_id") or row.get("id"))


def audit_source(row: dict[str, str]) -> str:
    return as_text(
        row.get("evidence_source")
        or row.get("review_source")
        or row.get("source")
        or row.get("evidence_uri")
    )


def parse_utc_timestamp(value: str, label: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{label}: reviewed_at_utc must be ISO-8601 UTC, got {value!r}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError(f"{label}: reviewed_at_utc must include UTC timezone, got {value!r}")
    return parsed


def validate_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[str]]:
    compiled: list[dict[str, Any]] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for index, row in enumerate(rows, start=1):
        cid = candidate_id(row)
        label = cid or f"row {index}"
        status = as_text(row.get("human_status"))
        damage_class = as_text(row.get("human_damage_class"))
        reviewer = as_text(row.get("reviewer_id"))
        reviewed_at = as_text(row.get("reviewed_at_utc"))
        evidence_uri = as_text(row.get("evidence_uri"))
        blockers: list[str] = []

        if not cid:
            errors.append(f"row {index}: missing candidate_id")
        elif cid in seen_ids:
            errors.append(f"{label}: duplicate candidate_id")
        seen_ids.add(cid)

        if status and status not in ALLOWED_STATUSES:
            errors.append(f"{label}: invalid human_status {status!r}")
        if damage_class and damage_class not in ALLOWED_DAMAGE_CLASSES:
            errors.append(f"{label}: invalid human_damage_class {damage_class!r}")

        if status:
            if not reviewer:
                errors.append(f"{label}: reviewed row is missing reviewer_id")
            if not reviewed_at:
                errors.append(f"{label}: reviewed row is missing reviewed_at_utc")
            else:
                try:
                    parse_utc_timestamp(reviewed_at, label)
                except ValueError as exc:
                    errors.append(str(exc))

        if status == "confirmed_damage":
            if not evidence_uri:
                errors.append(f"{label}: confirmed_damage requires evidence_uri")
                blockers.append("missing_evidence_uri")
            if not reviewer:
                blockers.append("missing_reviewer_id")
            if not reviewed_at:
                blockers.append("missing_reviewed_at_utc")
        elif not status:
            blockers.append("unreviewed")
        else:
            blockers.append(f"status_{status}")

        promoted = status == "confirmed_damage" and not blockers
        if promoted:
            try:
                float(as_text(row.get("centroid_lat")))
                float(as_text(row.get("centroid_lon")))
            except ValueError:
                errors.append(f"{label}: promoted row requires numeric centroid_lat and centroid_lon")
                promoted = False
                blockers.append("invalid_coordinates")

        compiled.append(
            {
                "row_number": index,
                "candidate_id": cid,
                "row": row,
                "human_status": status,
                "promoted": promoted,
                "blockers": blockers,
                "audit": {
                    "reviewer_id": reviewer,
                    "reviewed_at_utc": reviewed_at,
                    "source": audit_source(row),
                    "evidence_uri": evidence_uri,
                    "note": as_text(row.get("notes")),
                },
            }
        )

    return compiled, errors


def compiled_csv_rows(compiled: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in compiled:
        row = dict(item["row"])
        row.update(
            {
                "promotion_status": "promoted" if item["promoted"] else "not_promoted",
                "promotion_blockers": ";".join(item["blockers"]),
                "audit_reviewer_id": item["audit"]["reviewer_id"],
                "audit_reviewed_at_utc": item["audit"]["reviewed_at_utc"],
                "audit_source": item["audit"]["source"],
                "audit_note": item["audit"]["note"],
            }
        )
        rows.append(row)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    if not fields:
        fields = [
            "candidate_id",
            "promotion_status",
            "promotion_blockers",
            "audit_reviewer_id",
            "audit_reviewed_at_utc",
            "audit_source",
            "audit_note",
        ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def promoted_properties(item: dict[str, Any]) -> dict[str, Any]:
    row = item["row"]
    audit = item["audit"]
    return {
        "candidate_id": item["candidate_id"],
        "aoi_id": as_text(row.get("aoi_id") or AOI03_ID),
        "candidate_name": as_text(row.get("candidate_name") or row.get("name")),
        "human_status": item["human_status"],
        "human_damage_class": as_text(row.get("human_damage_class")),
        "human_confidence": as_text(row.get("human_confidence")),
        "evidence_uri": audit["evidence_uri"],
        "google_maps_url": as_text(row.get("google_maps_url")),
        "compare_chip": as_text(row.get("compare_chip")),
        "vlm_adjudicated_class": as_text(row.get("vlm_adjudicated_class")),
        "vlm_adjudicated_confidence": as_text(row.get("vlm_adjudicated_confidence")),
        "audit_reviewer_id": audit["reviewer_id"],
        "audit_reviewed_at_utc": audit["reviewed_at_utc"],
        "audit_source": audit["source"],
        "audit_note": audit["note"],
        "official_damage_source": False,
        "warning": WARNING,
    }


def feature_for(item: dict[str, Any]) -> dict[str, Any]:
    row = item["row"]
    return {
        "type": "Feature",
        "properties": promoted_properties(item),
        "geometry": {
            "type": "Point",
            "coordinates": [
                float(as_text(row.get("centroid_lon"))),
                float(as_text(row.get("centroid_lat"))),
            ],
        },
    }


def kml_for(promoted: list[dict[str, Any]]) -> str:
    placemarks = []
    for item in promoted:
        props = promoted_properties(item)
        desc = (
            f"<b>Warning:</b> {escape(WARNING)}<br/>"
            f"<b>Status:</b> {escape(props['human_status'])}<br/>"
            f"<b>Damage class:</b> {escape(props['human_damage_class'])}<br/>"
            f"<b>Evidence:</b> {escape(props['evidence_uri'])}<br/>"
            f"<b>Reviewer:</b> {escape(props['audit_reviewer_id'])}<br/>"
            f"<b>Reviewed at UTC:</b> {escape(props['audit_reviewed_at_utc'])}<br/>"
            f"<b>Note:</b> {escape(props['audit_note'])}<br/>"
            f"<b>Google Maps:</b> <a href='{escape(props['google_maps_url'])}'>open</a>"
        )
        row = item["row"]
        placemarks.append(
            f"""
    <Placemark>
      <name>{escape(props['candidate_id'])}</name>
      <description><![CDATA[{desc}]]></description>
      <Point><coordinates>{escape(as_text(row.get("centroid_lon")))},{escape(as_text(row.get("centroid_lat")))},0</coordinates></Point>
    </Placemark>"""
        )
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n"
        "  <Document>\n"
        "    <name>AOI03 Human-Confirmed Static Validation</name>\n"
        + "".join(placemarks)
        + "\n  </Document>\n</kml>\n"
    )


def write_outputs(compiled: list[dict[str, Any]], output_dir: Path, input_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    promoted = [item for item in compiled if item["promoted"]]
    reviewed = [item for item in compiled if item["human_status"]]
    unreviewed = [item for item in compiled if not item["human_status"]]

    summary = {
        "input": str(input_path),
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "warning": WARNING,
        "total_rows": len(compiled),
        "reviewed_rows": len(reviewed),
        "unreviewed_rows": len(unreviewed),
        "promoted_rows": len(promoted),
        "blocked_rows": len(compiled) - len(promoted),
        "status_counts": {},
        "promotion_guardrails": [
            "Only human_status=confirmed_damage can be promoted.",
            "confirmed_damage requires evidence_uri.",
            "Any reviewed row requires reviewer_id and reviewed_at_utc.",
            "AOI03 candidates remain non-official OSM leads.",
        ],
    }
    for item in compiled:
        status = item["human_status"] or "unreviewed"
        summary["status_counts"][status] = summary["status_counts"].get(status, 0) + 1

    (output_dir / "human_validation_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    write_csv(output_dir / "human_validation_compiled.csv", compiled_csv_rows(compiled))
    (output_dir / "human_validation_promoted.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "name": "aoi03_human_confirmed_static_validation",
                "warning": WARNING,
                "features": [feature_for(item) for item in promoted],
            },
            indent=2,
        )
        + "\n"
    )
    (output_dir / "human_validation_promoted.kml").write_text(kml_for(promoted))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Filled CSV or JSONL validation file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Directory for compiled static outputs")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rows = read_rows(args.input)
        compiled, errors = validate_rows(rows)
    except Exception as exc:
        print(f"Human validation compile failed: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("Human validation compile failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    write_outputs(compiled, args.output_dir, args.input)
    promoted_count = sum(1 for item in compiled if item["promoted"])
    reviewed_count = sum(1 for item in compiled if item["human_status"])
    print("Human validation compile passed")
    print(f"input_rows={len(compiled)}")
    print(f"reviewed_rows={reviewed_count}")
    print(f"promoted_rows={promoted_count}")
    print(f"output_dir={args.output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
