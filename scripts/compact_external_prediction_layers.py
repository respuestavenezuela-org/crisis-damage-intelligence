#!/usr/bin/env python3
"""Compact external prediction GeoJSON layers for mobile map rendering.

External model layers are triage leads, not official damage polygons. The public
map only needs a lightweight point at each candidate centroid; full footprints
remain available through the source GPKG/HDX references in metadata.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CATALOG = PUBLIC / "data" / "catalog.json"

COMPACT_FIELDS = (
    "id",
    "damage_class",
    "damage_percent",
    "not_official_ems",
    "centroid_lat",
    "centroid_lon",
    "triage_only",
)
MAP_PAYLOAD_NOTE = (
    "damage.geojson is a compact browser map payload with point geometry, "
    "centroid coordinates, and trimmed properties; use CSV or the HDX source "
    "GPKG for full footprint/attribute review."
)


def public_path(value: str | None) -> Path | None:
    if not value or not value.startswith("/"):
        return None
    return PUBLIC / value.lstrip("/")


def as_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_points(value: Any, points: list[tuple[float, float]]) -> None:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        points.append((float(value[0]), float(value[1])))
        return
    if isinstance(value, list):
        for item in value:
            collect_points(item, points)


def centroid_from_geometry(geometry: dict[str, Any] | None) -> tuple[float, float] | None:
    if not geometry:
        return None
    if geometry.get("type") == "Point":
        coords = geometry.get("coordinates")
        if isinstance(coords, list) and len(coords) >= 2:
            lon = as_float(coords[0])
            lat = as_float(coords[1])
            if lat is not None and lon is not None:
                return lat, lon

    points: list[tuple[float, float]] = []
    collect_points(geometry.get("coordinates"), points)
    if not points:
        return None
    lon = sum(point[0] for point in points) / len(points)
    lat = sum(point[1] for point in points) / len(points)
    return lat, lon


def compact_feature(aoi_id: str, feature: dict[str, Any]) -> dict[str, Any]:
    props = dict(feature.get("properties") or {})
    lat = as_float(props.get("centroid_lat"))
    lon = as_float(props.get("centroid_lon"))
    if lat is None or lon is None:
        derived = centroid_from_geometry(feature.get("geometry"))
        if derived is None:
            raise ValueError(f"{aoi_id}: feature {props.get('id') or '<missing-id>'} has no centroid")
        lat, lon = derived

    props["centroid_lat"] = round(lat, 7)
    props["centroid_lon"] = round(lon, 7)
    props["aoi_id"] = props.get("aoi_id") or aoi_id
    props["triage_only"] = True
    props["not_official_ems"] = True
    compact_props = {key: props[key] for key in COMPACT_FIELDS if key in props}
    return {
        "type": "Feature",
        "properties": compact_props,
        "geometry": {
            "type": "Point",
            "coordinates": [props["centroid_lon"], props["centroid_lat"]],
        },
    }


def update_metadata(path: Path | None, before_bytes: int, after_bytes: int, feature_count: int) -> None:
    if path is None or not path.exists():
        return
    data = json.loads(path.read_text())
    data["map_payload"] = MAP_PAYLOAD_NOTE
    data["map_payload_geometry"] = "Point"
    data["map_payload_bytes_before"] = before_bytes
    data["map_payload_bytes_after"] = after_bytes
    data["map_payload_features"] = feature_count
    path.write_text(json.dumps(data, indent=2) + "\n")


def compact_layer(aoi: dict[str, Any]) -> dict[str, Any] | None:
    layers = aoi.get("layers") or {}
    damage_path = public_path(layers.get("damage"))
    if damage_path is None or not damage_path.exists():
        return None

    before_bytes = damage_path.stat().st_size
    data = json.loads(damage_path.read_text())
    features = data.get("features") or []
    compact_features = [compact_feature(str(aoi["id"]), feature) for feature in features]
    payload = {
        "type": "FeatureCollection",
        "name": data.get("name") or aoi["id"],
        "features": compact_features,
    }
    damage_path.write_text(json.dumps(payload, separators=(",", ":")))
    after_bytes = damage_path.stat().st_size

    downloads = aoi.get("downloads") or {}
    update_metadata(public_path(downloads.get("metadata")), before_bytes, after_bytes, len(compact_features))

    external = aoi.setdefault("externalTriage", {})
    external.setdefault("official", False)
    external.setdefault("triageOnly", True)
    external["mapPayloadGeometry"] = "Point"
    external["mapPayloadBytes"] = after_bytes

    return {
        "id": aoi["id"],
        "features": len(compact_features),
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
    }


def main() -> int:
    catalog = json.loads(CATALOG.read_text())
    results = []
    for aoi in catalog.get("aois", []):
        if aoi.get("status") != "external-prediction":
            continue
        result = compact_layer(aoi)
        if result:
            results.append(result)

    catalog["updatedAt"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n")
    print("Compacted external prediction map layers:")
    for item in results:
        print(f"- {item['id']}: {item['features']} features, {item['before_bytes']} -> {item['after_bytes']} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
