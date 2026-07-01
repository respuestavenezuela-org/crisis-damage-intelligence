#!/usr/bin/env python3
"""Build pre-event imagery coverage manifests without bulk downloads."""

from __future__ import annotations

import csv
import json
import urllib.request
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "public" / "data" / "catalog.json"
OUT_DIR = ROOT / "ops" / "data_acquisition_plan"
VANTOR_COLLECTION = "https://vantor-opendata.s3.amazonaws.com/events/Venezuela-Earthquake-Jun-2026/collection.json"
MANIFEST = OUT_DIR / "pre_event_imagery_coverage.csv"
SUMMARY = OUT_DIR / "pre_event_imagery_coverage_summary.json"
SUMMARY_CSV = OUT_DIR / "pre_event_imagery_coverage_summary.csv"
USER_AGENT = "respuesta-venezuela-pre-event-coverage/1.0"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def request_status(url: str, method: str, headers: dict[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "",
        "content_type": "",
        "content_length": "",
        "accept_ranges": "",
        "error": "",
    }
    try:
        req = urllib.request.Request(url, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result["status"] = resp.status
            result["content_type"] = resp.headers.get("Content-Type", "")
            result["content_length"] = resp.headers.get("Content-Length", "")
            result["accept_ranges"] = resp.headers.get("Accept-Ranges", "")
    except HTTPError as exc:
        result["status"] = exc.code
        result["error"] = str(exc)
        result["content_type"] = exc.headers.get("Content-Type", "")
        result["content_length"] = exc.headers.get("Content-Length", "")
        result["accept_ranges"] = exc.headers.get("Accept-Ranges", "")
    except (URLError, TimeoutError) as exc:
        result["error"] = str(exc)
    return result


def validate_asset(url: str) -> dict[str, Any]:
    headers = {"User-Agent": USER_AGENT}
    head = request_status(url, "HEAD", headers)
    ranged = request_status(url, "GET", {**headers, "Range": "bytes=0-0"})
    return {
        "http_status": head["status"],
        "range_status": ranged["status"],
        "range_ok": ranged["status"] in (200, 206),
        "content_type": head["content_type"] or ranged["content_type"],
        "content_length": head["content_length"] or ranged["content_length"],
        "accept_ranges": head["accept_ranges"] or ranged["accept_ranges"],
        "error": head["error"] or ranged["error"],
    }


def aoi_bbox(aoi: dict[str, Any]) -> list[float]:
    # Catalog bounds are [[south, west], [north, east]].
    return [aoi["bounds"][0][1], aoi["bounds"][0][0], aoi["bounds"][1][1], aoi["bounds"][1][0]]


def intersects(a: list[float], b: list[float]) -> bool:
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def geom_bbox(geometry: dict[str, Any]) -> list[float] | None:
    coords: list[tuple[float, float]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and isinstance(value[0], (int, float)) and isinstance(value[1], (int, float)):
            coords.append((float(value[0]), float(value[1])))
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(geometry.get("coordinates", []))
    if not coords:
        return None
    return [min(x for x, _ in coords), min(y for _, y in coords), max(x for x, _ in coords), max(y for _, y in coords)]


def damage_layer_path(aoi: dict[str, Any]) -> Path | None:
    damage = (aoi.get("layers") or {}).get("damage")
    if not damage:
        return None
    path = ROOT / "public" / damage.lstrip("/")
    return path if path.exists() else None


def feature_count_inside(aoi: dict[str, Any], bbox: list[float]) -> tuple[int | None, str]:
    if aoi["id"] == "emsr884-aoi12-caraballeda" and (OUT_DIR / "aoi12_gra_v2_builtup.geojson").exists():
        path = OUT_DIR / "aoi12_gra_v2_builtup.geojson"
        source = "official_aoi12_gra_v2_ops"
    else:
        path = damage_layer_path(aoi)
        source = "public_catalog_damage_layer" if path else "none"
    if not path:
        return None, source
    data = json.loads(path.read_text())
    count = 0
    for feature in data.get("features", []):
        props = feature.get("properties") or {}
        lon = props.get("centroid_lon")
        lat = props.get("centroid_lat")
        if lon is None or lat is None:
            geometry_bbox = geom_bbox(feature.get("geometry") or {})
            if not geometry_bbox:
                continue
            lon = (geometry_bbox[0] + geometry_bbox[2]) / 2
            lat = (geometry_bbox[1] + geometry_bbox[3]) / 2
        if bbox[0] <= float(lon) <= bbox[2] and bbox[1] <= float(lat) <= bbox[3]:
            count += 1
    return count, source


def load_vantor_pre_items() -> list[dict[str, Any]]:
    collection = fetch_json(VANTOR_COLLECTION)
    links = sorted({link["href"] for link in collection.get("links", []) if link.get("rel") == "item" and link.get("href")})
    items = [fetch_json(url) for url in links]
    return [item for item in items if (item.get("properties") or {}).get("phase") == "pre"]


def gate_for_row(row: dict[str, Any]) -> str:
    pan_gsd = float(row["pan_gsd_m"]) if row["pan_gsd_m"] not in ("", None) else 999
    cloud_cover = float(row["cloud_cover"]) if row["cloud_cover"] not in ("", None) else 999
    if row["range_ok"] is not True:
        return "blocked_asset_not_range_readable"
    if row["features_covered"] in ("", None):
        return "coverage_only_no_official_features"
    if int(row["features_covered"]) <= 0:
        return "coverage_only_zero_current_features"
    if pan_gsd > 0.8:
        return "blocked_resolution_too_coarse"
    if cloud_cover > 25:
        return "conditional_cloud_review"
    return "eligible_after_chip_qa"


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    checked_at = utc_stamp()
    catalog = json.loads(CATALOG.read_text())
    aois = catalog["aois"]
    pre_items = load_vantor_pre_items()
    asset_validation: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []

    for item in pre_items:
        props = item.get("properties") or {}
        bbox = item.get("bbox") or geom_bbox(item.get("geometry") or {})
        if not bbox:
            continue
        asset_url = ((item.get("assets") or {}).get("visual") or {}).get("href") or ""
        if asset_url not in asset_validation:
            asset_validation[asset_url] = validate_asset(asset_url) if asset_url else {}
        validation = asset_validation[asset_url]
        for aoi in aois:
            abox = aoi_bbox(aoi)
            if not intersects(bbox, abox):
                continue
            features_covered, feature_source = feature_count_inside(aoi, bbox)
            row = {
                "checked_at": checked_at,
                "aoi_id": aoi["id"],
                "source": "vantor-open-data",
                "scene_id": item.get("id"),
                "phase": props.get("phase"),
                "acquisition_time": props.get("datetime"),
                "platform": props.get("vehicle_name"),
                "cloud_cover": props.get("eo:cloud_cover"),
                "pan_gsd_m": props.get("pan_gsd"),
                "multispectral_gsd_m": props.get("multispectral_gsd"),
                "off_nadir": props.get("view:off_nadir"),
                "sun_elevation": props.get("view:sun_elevation"),
                "bbox": json.dumps(bbox, separators=(",", ":")),
                "features_covered": features_covered if features_covered is not None else "",
                "feature_count_source": feature_source,
                "asset_url": asset_url,
                "content_length": validation.get("content_length", ""),
                "content_type": validation.get("content_type", ""),
                "http_status": validation.get("http_status", ""),
                "range_status": validation.get("range_status", ""),
                "range_ok": validation.get("range_ok", False),
                "license": "CC-BY-NC-4.0",
                "license_gate": "non_commercial_only_verify_before_public_derivatives",
                "building_vlm_gate": "",
                "error": validation.get("error", ""),
            }
            row["building_vlm_gate"] = gate_for_row(row)
            rows.append(row)

    fieldnames = [
        "checked_at",
        "aoi_id",
        "source",
        "scene_id",
        "phase",
        "acquisition_time",
        "platform",
        "cloud_cover",
        "pan_gsd_m",
        "multispectral_gsd_m",
        "off_nadir",
        "sun_elevation",
        "bbox",
        "features_covered",
        "feature_count_source",
        "asset_url",
        "content_length",
        "content_type",
        "http_status",
        "range_status",
        "range_ok",
        "license",
        "license_gate",
        "building_vlm_gate",
        "error",
    ]
    with MANIFEST.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    by_aoi: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_aoi[row["aoi_id"]].append(row)
    summary_rows: list[dict[str, Any]] = []
    for aoi in aois:
        items = by_aoi.get(aoi["id"], [])
        eligible = [row for row in items if row["building_vlm_gate"] == "eligible_after_chip_qa"]
        covered = sum(int(row["features_covered"] or 0) for row in eligible)
        summary_rows.append(
            {
                "aoi_id": aoi["id"],
                "pre_event_scene_count": len(items),
                "eligible_scene_count": len(eligible),
                "eligible_features_covered_sum": covered,
                "best_gate": "eligible_after_chip_qa" if eligible else (items[0]["building_vlm_gate"] if items else "no_vantor_pre_event_coverage"),
            }
        )
    with SUMMARY_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["aoi_id", "pre_event_scene_count", "eligible_scene_count", "eligible_features_covered_sum", "best_gate"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(summary_rows)

    summary = {
        "checked_at": checked_at,
        "vantor_pre_items": len(pre_items),
        "coverage_rows": len(rows),
        "aoi_count_with_coverage": sum(1 for row in summary_rows if row["pre_event_scene_count"]),
        "aoi_count_with_eligible_coverage": sum(1 for row in summary_rows if row["eligible_scene_count"]),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "summary_csv": str(SUMMARY_CSV.relative_to(ROOT)),
        "gate_counts": dict(defaultdict(int, {gate: sum(1 for row in rows if row["building_vlm_gate"] == gate) for gate in sorted({row["building_vlm_gate"] for row in rows})})),
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
