#!/usr/bin/env python3
"""Inventory public pre-event imagery candidates for EMSR884 AOIs.

The output is intentionally conservative. It separates very-high-resolution
candidate baselines that can support building-level VLM from lower-resolution
context imagery that should not be used for building damage calls.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "ops" / "baseline_inventory"
CATALOG = ROOT / "public" / "data" / "catalog.json"

VANTOR_COLLECTION = "https://vantor-opendata.s3.amazonaws.com/events/Venezuela-Earthquake-Jun-2026/collection.json"
AWS_STAC_SEARCH = "https://earth-search.aws.element84.com/v1/search"
OAM_SEARCH = "https://api.openaerialmap.org/meta"

TARGET_AOIS = {
    "emsr884-aoi03-antimano",
    "emsr884-aoi05-santa-cruz",
    "emsr884-aoi06-moron",
    "emsr884-aoi08-san-felipe",
    "emsr884-aoi10-guacara",
}


def fetch_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    if method == "POST":
        response = requests.post(url, json=payload, timeout=60)
    else:
        response = requests.get(url, timeout=60)
    response.raise_for_status()
    return response.json()


def intersects(a: list[float], b: list[float]) -> bool:
    # [minlon, minlat, maxlon, maxlat]
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def aoi_bbox(aoi: dict[str, Any]) -> list[float]:
    return [aoi["bounds"][0][1], aoi["bounds"][0][0], aoi["bounds"][1][1], aoi["bounds"][1][0]]


def geom_bbox(geometry: dict[str, Any]) -> list[float] | None:
    coords: list[tuple[float, float]] = []

    def walk(value: Any) -> None:
        if isinstance(value, list) and value and isinstance(value[0], (int, float)) and len(value) >= 2:
            coords.append((float(value[0]), float(value[1])))
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(geometry.get("coordinates", []))
    if not coords:
        return None
    return [min(x for x, _ in coords), min(y for _, y in coords), max(x for x, _ in coords), max(y for _, y in coords)]


def feature_count_inside(aoi: dict[str, Any], bbox: list[float]) -> int | None:
    damage = aoi.get("layers", {}).get("damage")
    if not damage:
        return None
    path = ROOT / "public" / damage.lstrip("/")
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    count = 0
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        lat = props.get("centroid_lat")
        lon = props.get("centroid_lon")
        if lat is None or lon is None:
            continue
        if bbox[0] <= float(lon) <= bbox[2] and bbox[1] <= float(lat) <= bbox[3]:
            count += 1
    return count


def source_judgement(source: str, gsd_m: float | None) -> tuple[str, bool]:
    if source == "vantor-open-data" and gsd_m is not None and gsd_m <= 1.0:
        return "candidate_building_level", True
    if gsd_m is not None and gsd_m <= 1.0:
        return "candidate_building_level_if_license_allows", True
    if gsd_m is not None and gsd_m <= 5.0:
        return "context_only_too_coarse_for_building_vlm", False
    return "context_only_not_building_level", False


def inventory_vantor(aois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collection = fetch_json(VANTOR_COLLECTION)
    links = [link["href"] for link in collection.get("links", []) if link.get("rel") == "item"]
    items = [fetch_json(url) for url in links]
    rows: list[dict[str, Any]] = []
    for item in items:
        props = item.get("properties", {})
        if props.get("phase") != "pre":
            continue
        bbox = geom_bbox(item.get("geometry", {}))
        if not bbox:
            continue
        for aoi in aois:
            abox = aoi_bbox(aoi)
            if not intersects(bbox, abox):
                continue
            hits = feature_count_inside(aoi, bbox)
            gsd = 0.5
            judgement, usable = source_judgement("vantor-open-data", gsd)
            rows.append({
                "aoi_id": aoi["id"],
                "source": "vantor-open-data",
                "item_id": item.get("id"),
                "datetime": props.get("datetime"),
                "platform": props.get("vehicle_name"),
                "cloud_cover": props.get("eo:cloud_cover"),
                "gsd_m": gsd,
                "phase": props.get("phase"),
                "bbox": bbox,
                "features_covered": hits,
                "asset_url": item.get("assets", {}).get("visual", {}).get("href"),
                "license": "CC-BY-NC-4.0",
                "judgement": judgement,
                "usable_for_building_vlm": usable,
            })
    return rows


def inventory_aws_sentinel_2(aois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for aoi in aois:
        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": aoi_bbox(aoi),
            "datetime": "2026-01-01T00:00:00Z/2026-06-24T23:59:59Z",
            "limit": 8,
            "query": {"eo:cloud_cover": {"lt": 30}},
            "sortby": [{"field": "properties.eo:cloud_cover", "direction": "asc"}],
        }
        try:
            data = fetch_json(AWS_STAC_SEARCH, method="POST", payload=payload)
        except Exception as exc:
            rows.append({
                "aoi_id": aoi["id"],
                "source": "aws-earth-search-sentinel-2-l2a-cogs",
                "item_id": "ERROR",
                "datetime": None,
                "platform": "Sentinel-2",
                "cloud_cover": None,
                "gsd_m": 10,
                "features_covered": None,
                "asset_url": None,
                "license": "Copernicus Sentinel data terms",
                "judgement": f"query_error: {exc}",
                "usable_for_building_vlm": False,
            })
            continue
        for item in data.get("features", []):
            props = item.get("properties", {})
            gsd = 10
            judgement, usable = source_judgement("sentinel-2", gsd)
            rows.append({
                "aoi_id": aoi["id"],
                "source": "aws-earth-search-sentinel-2-l2a-cogs",
                "item_id": item.get("id"),
                "datetime": props.get("datetime"),
                "platform": props.get("platform", "Sentinel-2"),
                "cloud_cover": props.get("eo:cloud_cover"),
                "gsd_m": gsd,
                "phase": "pre",
                "bbox": item.get("bbox"),
                "features_covered": feature_count_inside(aoi, item.get("bbox", [])) if item.get("bbox") else None,
                "asset_url": item.get("assets", {}).get("visual", {}).get("href") or item.get("assets", {}).get("red", {}).get("href"),
                "license": "Copernicus Sentinel data terms / AWS Open Data Registry",
                "judgement": judgement,
                "usable_for_building_vlm": usable,
            })
    return rows


def inventory_oam(aois: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for aoi in aois:
        bbox = aoi_bbox(aoi)
        params = {
            "bbox": ",".join(str(v) for v in bbox),
            "limit": 10,
        }
        try:
            response = requests.get(OAM_SEARCH, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            rows.append({
                "aoi_id": aoi["id"],
                "source": "openaerialmap",
                "item_id": "ERROR",
                "datetime": None,
                "platform": None,
                "cloud_cover": None,
                "gsd_m": None,
                "features_covered": None,
                "asset_url": None,
                "license": None,
                "judgement": f"query_error: {exc}",
                "usable_for_building_vlm": False,
            })
            continue
        results = data.get("results", data if isinstance(data, list) else [])
        for item in results[:10]:
            props = item.get("properties", item)
            gsd = props.get("gsd") or props.get("resolution")
            try:
                gsd = float(gsd) if gsd is not None else None
            except (TypeError, ValueError):
                gsd = None
            judgement, usable = source_judgement("openaerialmap", gsd)
            rows.append({
                "aoi_id": aoi["id"],
                "source": "openaerialmap",
                "item_id": item.get("_id") or item.get("uuid") or item.get("id"),
                "datetime": props.get("acquisition_start") or props.get("created_at") or props.get("date"),
                "platform": props.get("provider") or props.get("platform"),
                "cloud_cover": props.get("cloud_cover"),
                "gsd_m": gsd,
                "phase": "unknown",
                "bbox": props.get("bbox"),
                "features_covered": None,
                "asset_url": props.get("tms") or props.get("url") or props.get("download_url"),
                "license": props.get("license"),
                "judgement": judgement,
                "usable_for_building_vlm": usable,
            })
    return rows


def write_outputs(rows: list[dict[str, Any]]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warning": "Only rows with usable_for_building_vlm=true should be considered for building-level before/after VLM. Context-only imagery must not be used as damage evidence.",
        "rows": rows,
    }
    (OUT_DIR / "pre_event_baseline_inventory.json").write_text(json.dumps(payload, indent=2) + "\n")
    fieldnames = [
        "aoi_id", "source", "item_id", "datetime", "platform", "cloud_cover", "gsd_m",
        "features_covered", "license", "judgement", "usable_for_building_vlm", "asset_url",
    ]
    with (OUT_DIR / "pre_event_baseline_inventory.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    write_suitability_report(rows)


def write_suitability_report(rows: list[dict[str, Any]]) -> None:
    by_aoi: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_aoi.setdefault(row["aoi_id"], []).append(row)

    names = {
        "emsr884-aoi03-antimano": "AOI03 Antimano",
        "emsr884-aoi05-santa-cruz": "AOI05 Santa Cruz",
        "emsr884-aoi06-moron": "AOI06 Moron",
        "emsr884-aoi08-san-felipe": "AOI08 San Felipe",
        "emsr884-aoi10-guacara": "AOI10 Guacara",
    }
    order = [aoi for aoi in TARGET_AOIS if aoi in by_aoi]
    order.sort()

    lines = [
        "# Pre-Event Baseline Suitability Report",
        "",
        "Generated from `ops/baseline_inventory/pre_event_baseline_inventory.json`.",
        "",
        "Only imagery marked `usable_for_building_vlm=true` should be used for building-level before/after VLM. Sentinel-2 and unknown-date/context-only basemaps are acceptable as visual context only, not building damage comparison.",
        "",
        "## Summary",
        "",
        "| AOI | Building-level baseline | Total candidates | Usable feature coverage | Decision |",
        "|---|---:|---:|---:|---|",
    ]
    for aoi_id in order:
        items = by_aoi.get(aoi_id, [])
        usable = [row for row in items if row.get("usable_for_building_vlm")]
        covered = sum(int(row.get("features_covered") or 0) for row in usable)
        if aoi_id == "emsr884-aoi03-antimano" and usable:
            decision = "usable pilot only; internal candidates, not official vectors"
        elif aoi_id in {"emsr884-aoi05-santa-cruz", "emsr884-aoi06-moron", "emsr884-aoi08-san-felipe"}:
            decision = "blocked: only 10 m Sentinel-2 context baseline found"
        elif aoi_id == "emsr884-aoi10-guacara":
            decision = "blocked: no official damage vector and only context baseline found"
        else:
            decision = "blocked for before/after building VLM"
        lines.append(f"| `{aoi_id}` | {len(usable)} | {len(items)} | {covered} | {decision} |")

    lines.extend(["", "## AOI Detail", ""])
    for aoi_id in order:
        items = by_aoi.get(aoi_id, [])
        usable = [row for row in items if row.get("usable_for_building_vlm")]
        context = [row for row in items if not row.get("usable_for_building_vlm")]
        lines.extend([f"### {names.get(aoi_id, aoi_id)}", ""])
        if usable:
            lines.append("Building-level candidate baselines:")
            for row in usable:
                lines.append(
                    f"- {row['source']} `{row['item_id']}`; datetime {row.get('datetime')}; "
                    f"gsd {row.get('gsd_m')} m; cloud {row.get('cloud_cover')}; "
                    f"features covered {row.get('features_covered')}; license {row.get('license')}"
                )
        else:
            lines.append("No high-resolution building-level pre-event baseline found in the current public inventory.")
        if context:
            lines.extend(["", "Context-only candidates found:"])
            for row in context[:10]:
                lines.append(
                    f"- {row['source']} `{row['item_id']}`; datetime {row.get('datetime')}; "
                    f"gsd {row.get('gsd_m')}; features covered {row.get('features_covered')}; "
                    f"judgement `{row.get('judgement')}`"
                )
        lines.append("")

    lines.extend([
        "## Operational Rule",
        "",
        "- Do not run or publish before/after building VLM for AOI05, AOI06, AOI08, or AOI10 until a high-resolution pre-event baseline is found.",
        "- Post-event-only VLM may remain available as lower-confidence triage evidence, but it must stay labeled separately from before/after comparison.",
        "- AOI03 VLM remains internal because it is based on OSM candidates, not official EMS damage features.",
    ])
    (OUT_DIR / "pre_event_baseline_suitability_report.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    catalog = json.loads(CATALOG.read_text())
    aois = [aoi for aoi in catalog["aois"] if aoi["id"] in TARGET_AOIS]
    rows: list[dict[str, Any]] = []
    rows.extend(inventory_vantor(aois))
    rows.extend(inventory_aws_sentinel_2(aois))
    rows.extend(inventory_oam(aois))
    rows.sort(key=lambda row: (row["aoi_id"], not row.get("usable_for_building_vlm", False), row.get("source") or "", row.get("cloud_cover") if row.get("cloud_cover") is not None else 999))
    write_outputs(rows)
    by_aoi: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_aoi.setdefault(row["aoi_id"], []).append(row)
    for aoi_id, items in by_aoi.items():
        usable = [row for row in items if row.get("usable_for_building_vlm")]
        print(f"{aoi_id}: {len(usable)} building-level candidates, {len(items)} total rows")
        for row in usable[:5]:
            print(f"  {row['source']} {row['item_id']} {row['datetime']} cloud={row['cloud_cover']} covered={row['features_covered']}")
    print(f"Wrote {OUT_DIR / 'pre_event_baseline_inventory.json'}")
    print(f"Wrote {OUT_DIR / 'pre_event_baseline_inventory.csv'}")


if __name__ == "__main__":
    sys.exit(main())
