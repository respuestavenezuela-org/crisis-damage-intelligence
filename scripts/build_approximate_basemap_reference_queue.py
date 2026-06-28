#!/usr/bin/env python3
"""Build a clearly labeled approximate aerial-reference review queue.

This queue exists for speed when no dated high-resolution pre-event baseline is
available. It does not download or redistribute commercial basemap tiles. It
stores live reference URLs and caveats so operators/VLM runners can keep these
records separate from true before/after evidence.
"""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "public" / "data" / "catalog.json"
OUT_DIR = ROOT / "ops" / "approximate_basemap_reference_queue"
ZOOM = 18
TARGET_STATUSES = {"official-vector"}


def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    n = 2.0**zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def load_features(aoi: dict[str, Any]) -> list[dict[str, Any]]:
    layer = aoi.get("layers", {}).get("damage")
    if not layer:
        return []
    path = ROOT / "public" / layer.lstrip("/")
    if not path.exists():
        return []
    return json.loads(path.read_text()).get("features", [])


def severity_rank(props: dict[str, Any]) -> int:
    damage = str(props.get("damage_gra") or props.get("damage_class") or "").lower()
    pct = float(props.get("damage_percent") or props.get("damage_score") or 0)
    if "destroyed" in damage:
        return 1000 + int(pct)
    if "damaged" in damage:
        return 800 + int(pct)
    if "possible" in damage:
        return 500 + int(pct)
    return int(pct)


def main() -> None:
    catalog = json.loads(CATALOG.read_text())
    rows: list[dict[str, Any]] = []
    for aoi in catalog.get("aois", []):
        if aoi.get("status") not in TARGET_STATUSES:
            continue
        layers = aoi.get("layers", {})
        if layers.get("beforeTiles") or layers.get("beforeImage"):
            continue
        approximate = aoi.get("imagery", {}).get("approximateReference")
        if not approximate:
            continue
        for feature in load_features(aoi):
            props = feature.get("properties", {})
            lat = props.get("centroid_lat")
            lon = props.get("centroid_lon")
            if lat is None or lon is None:
                continue
            lat_f = float(lat)
            lon_f = float(lon)
            x, y = lonlat_to_tile(lon_f, lat_f, ZOOM)
            tile_url = approximate["urlTemplate"].replace("{z}", str(ZOOM)).replace("{x}", str(x)).replace("{y}", str(y))
            rows.append({
                "aoi_id": aoi["id"],
                "aoi_name_en": aoi["name"]["en"],
                "aoi_name_es": aoi["name"]["es"],
                "feature_id": props.get("id") or props.get("source_feature_id"),
                "damage_gra": props.get("damage_gra") or props.get("damage_class") or "unknown",
                "damage_percent": props.get("damage_percent") or props.get("damage_score") or "",
                "centroid_lat": lat_f,
                "centroid_lon": lon_f,
                "google_maps_url": props.get("google_maps_url") or f"https://www.google.com/maps/search/?api=1&query={lat_f},{lon_f}",
                "approx_reference_source": approximate["label"],
                "approx_reference_tile_z": ZOOM,
                "approx_reference_tile_x": x,
                "approx_reference_tile_y": y,
                "approx_reference_tile_url": tile_url,
                "evidence_mode": "approximate_aerial_reference_not_dated_before",
                "vlm_use": "triage_only_if_no_dated_before_baseline_exists",
                "do_not_overclaim": approximate["limitations"],
                "_rank": severity_rank(props),
            })
    rows.sort(key=lambda r: (-r["_rank"], r["aoi_id"], str(r["feature_id"])))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "warning": "This is not true before/after evidence. It uses approximate aerial basemap references only when no dated high-resolution pre-event baseline exists.",
        "rows": [{k: v for k, v in row.items() if k != "_rank"} for row in rows],
    }
    (OUT_DIR / "queue.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    with (OUT_DIR / "queue.jsonl").open("w") as handle:
        for row in rows:
            handle.write(json.dumps({k: v for k, v in row.items() if k != "_rank"}, ensure_ascii=False) + "\n")
    fieldnames = [k for k in rows[0].keys() if k != "_rank"] if rows else [
        "aoi_id", "feature_id", "damage_gra", "centroid_lat", "centroid_lon", "approx_reference_tile_url"
    ]
    with (OUT_DIR / "queue.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: v for k, v in row.items() if k != "_rank"})
    readme = [
        "# Approximate Basemap Reference Queue",
        "",
        "This queue is for speed when no dated high-resolution pre-event imagery exists.",
        "",
        "- It is not official EMS evidence.",
        "- It is not guaranteed to be pre-event for every tile.",
        "- It must not be merged into official EMS counts.",
        "- VLM outputs from this queue must be labeled `approximate_aerial_reference_not_dated_before`.",
        "- Do not bulk-download or redistribute basemap tiles without reviewing provider terms.",
        "",
        f"Generated records: {len(rows)}",
    ]
    (OUT_DIR / "README.md").write_text("\n".join(readme) + "\n")
    print(json.dumps({"out_dir": str(OUT_DIR), "records": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
