#!/usr/bin/env python3
"""Build an EMS-gap visual triage queue from HOT MapSwipe validation layers."""

from __future__ import annotations

import csv
import json
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from shapely.geometry import mapping, shape
from shapely.geometry.base import BaseGeometry


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "ops" / "data_acquisition_plan" / "hotosm_hf_dataset_manifest.csv"
OUT_CSV = ROOT / "ops" / "data_acquisition_plan" / "ems_gap_visual_queue.csv"
OUT_GEOJSON = ROOT / "ops" / "data_acquisition_plan" / "ems_gap_visual_queue.geojson"
OUT_SUMMARY = ROOT / "ops" / "data_acquisition_plan" / "ems_gap_visual_queue_summary.md"
USER_AGENT = "respuesta-venezuela-ems-gap-queue/1.0"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_geojson(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def safe_shape(geometry: dict[str, Any] | None) -> BaseGeometry | None:
    if not geometry:
        return None
    geom = shape(geometry)
    if geom.is_empty:
        return None
    if not geom.is_valid:
        geom = geom.buffer(0)
    return None if geom.is_empty else geom


def official_gra_features() -> list[dict[str, Any]]:
    catalog = json.loads((ROOT / "public" / "data" / "catalog.json").read_text())
    records: list[dict[str, Any]] = []
    for aoi in catalog["aois"]:
        if aoi.get("status") != "official-vector":
            continue
        path = ROOT / aoi["layers"]["damage"].lstrip("/")
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        for feature in data.get("features", []):
            geom = safe_shape(feature.get("geometry"))
            if geom is None:
                continue
            records.append({
                "aoi_id": aoi["id"],
                "source_feature_id": feature.get("properties", {}).get("id", ""),
                "damage": feature.get("properties", {}).get("damage_gra") or feature.get("properties", {}).get("damage_class") or "",
                "geometry": geom,
            })
    return records


def queue_sources() -> list[dict[str, str]]:
    with MANIFEST.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [
        row for row in rows
        if row["source_family"] == "validated_mapswipe"
        and row["path"].endswith("_human_validated_damage_polygons.geojson")
    ]


def triage_status(verdict: str, has_official_overlap: bool) -> str:
    if has_official_overlap:
        return "covered_by_official_gra"
    if verdict == "accepted":
        return "visual_confirmed_gap"
    if verdict == "uncertain":
        return "needs_human_review"
    return "discard_rejected"


def main() -> int:
    checked_at = utc_stamp()
    official = official_gra_features()
    rows: list[dict[str, Any]] = []
    features: list[dict[str, Any]] = []

    for source in queue_sources():
        data = fetch_geojson(source["download_url"])
        for index, feature in enumerate(data.get("features", []), start=1):
            props = feature.get("properties", {})
            verdict = str(props.get("verdict", ""))
            if verdict not in {"accepted", "uncertain"}:
                continue
            geom = safe_shape(feature.get("geometry"))
            if geom is None:
                continue
            overlaps = [
                item for item in official
                if item["geometry"].intersects(geom)
            ]
            rep = geom.representative_point()
            task_id = str(props.get("task_id") or f"row_{index}")
            candidate_id = f"hot_{source['area']}_{task_id}"
            status = triage_status(verdict, bool(overlaps))
            row = {
                "checked_at": checked_at,
                "candidate_id": candidate_id,
                "area": source["area"],
                "source_family": "hot_validated_mapswipe",
                "source_path": source["path"],
                "source_url": source["download_url"],
                "task_id": task_id,
                "verdict": verdict,
                "answer": props.get("answer", ""),
                "yes": props.get("yes", ""),
                "no": props.get("no", ""),
                "not_sure": props.get("not_sure", ""),
                "total_validators": props.get("total_validators", ""),
                "yes_share": props.get("yes_share", ""),
                "sources": props.get("sources", ""),
                "official_gra_overlap_count": len(overlaps),
                "official_gra_overlap_ids": ";".join(str(item["source_feature_id"]) for item in overlaps[:8]),
                "triage_status": status,
                "not_official_ems": "true",
                "lon": rep.x,
                "lat": rep.y,
                "imagery_tms": props.get("imagery_tms", ""),
            }
            rows.append(row)
            if status in {"visual_confirmed_gap", "needs_human_review"}:
                features.append({
                    "type": "Feature",
                    "geometry": mapping(geom),
                    "properties": row,
                })

    fieldnames = [
        "checked_at",
        "candidate_id",
        "area",
        "source_family",
        "source_path",
        "source_url",
        "task_id",
        "verdict",
        "answer",
        "yes",
        "no",
        "not_sure",
        "total_validators",
        "yes_share",
        "sources",
        "official_gra_overlap_count",
        "official_gra_overlap_ids",
        "triage_status",
        "not_official_ems",
        "lon",
        "lat",
        "imagery_tms",
    ]
    with OUT_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    OUT_GEOJSON.write_text(json.dumps({
        "type": "FeatureCollection",
        "features": features,
    }, indent=2) + "\n")

    by_status = Counter(row["triage_status"] for row in rows)
    by_area = Counter(row["area"] for row in rows)
    OUT_SUMMARY.write_text(
        "# EMS-Gap Visual Queue Summary\n\n"
        f"Checked: {checked_at}\n\n"
        "This queue is generated from HOT/MapSwipe human validation layers and intersects them with local official EMS GRA polygons. "
        "It is triage-only. Rows outside EMS are candidate visual gaps, not official damage counts.\n\n"
        "## Counts By Status\n\n"
        + "\n".join(f"- `{key}`: {value}" for key, value in sorted(by_status.items()))
        + "\n\n## Counts By Area\n\n"
        + "\n".join(f"- `{key}`: {value}" for key, value in sorted(by_area.items()))
        + "\n\n## Outputs\n\n"
        f"- `{OUT_CSV.relative_to(ROOT)}`\n"
        f"- `{OUT_GEOJSON.relative_to(ROOT)}`\n"
    )

    print(json.dumps({
        "checked_at": checked_at,
        "rows": len(rows),
        "geojson_features": len(features),
        "by_status": dict(sorted(by_status.items())),
        "by_area": dict(sorted(by_area.items())),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
