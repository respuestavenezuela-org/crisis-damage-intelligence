#!/usr/bin/env python3
"""Build AOI12 GRA v1 to v2 geometry remap without changing public data."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import shape
from shapely.ops import transform
from shapely.wkt import dumps as wkt_dumps


ROOT = Path(__file__).resolve().parents[1]
OLD_GEOJSON = ROOT / "public" / "data" / "aoi" / "emsr884-aoi12-caraballeda" / "damage.geojson"
VLM_SUMMARY = ROOT / "public" / "data" / "aoi" / "emsr884-aoi12-caraballeda" / "vlm_before_after_summary.csv"
NEW_ZIP = ROOT / "ops" / "data_acquisition_plan" / "official_products" / "EMSR884_AOI12_GRA_PRODUCT_v2.zip"
NEW_MEMBER = "EMSR884_AOI12_GRA_PRODUCT_builtUpA_v2.json"
OUT_DIR = ROOT / "ops" / "data_acquisition_plan"
REMAP_CSV = OUT_DIR / "aoi12_v1_v2_remap.csv"
VLM_QUEUE_CSV = OUT_DIR / "aoi12_vlm_v1_v2_reuse_queue.csv"
SUMMARY_JSON = OUT_DIR / "aoi12_v1_v2_remap_summary.json"
V2_GEOJSON = OUT_DIR / "aoi12_gra_v2_builtup.geojson"


TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:32619", always_xy=True)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def load_v2() -> dict[str, Any]:
    with zipfile.ZipFile(NEW_ZIP) as zf:
        return json.load(zf.open(NEW_MEMBER))


def damage_percent(damage_gra: str) -> int:
    return {"Destroyed": 100, "Damaged": 70, "Possibly damaged": 35}.get(damage_gra, 0)


def clean_geom(feature: dict[str, Any]) -> Any:
    geom = shape(feature["geometry"])
    if not geom.is_valid:
        geom = make_valid(geom)
    return geom


def projected(geom: Any) -> Any:
    return transform(TRANSFORMER.transform, geom)


def geom_hash(geom: Any) -> str:
    normalized = geom.normalize()
    text = wkt_dumps(normalized, rounding_precision=8, trim=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def centroid_latlon(geom: Any) -> tuple[float, float]:
    c = geom.centroid
    return c.y, c.x


def source_id(prefix: str, index: int) -> str:
    return f"{prefix}_{index:05d}"


def indexed_features(data: dict[str, Any], prefix: str, old: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, feature in enumerate(data["features"], start=1):
        props = dict(feature.get("properties") or {})
        geom = clean_geom(feature)
        geom_m = projected(geom)
        lat, lon = centroid_latlon(geom)
        damage = props.get("damage_gra", "")
        fid = props.get("id") if old else source_id(prefix, index)
        rows.append(
            {
                "index": index,
                "id": fid,
                "damage_gra": damage,
                "damage_percent": props.get("damage_percent") or damage_percent(damage),
                "geometry": geom,
                "geometry_m": geom_m,
                "geometry_hash": geom_hash(geom),
                "area_m2": geom_m.area,
                "centroid_lat": lat,
                "centroid_lon": lon,
                "properties": props,
            }
        )
    return rows


def iou(a: Any, b: Any) -> tuple[float, float]:
    if a.is_empty or b.is_empty:
        return 0.0, 0.0
    inter = a.intersection(b).area
    union = a.union(b).area
    return (inter / union if union else 0.0), inter


def best_matches(old_rows: list[dict[str, Any]], new_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    matches: dict[str, dict[str, Any]] = {}
    for old in old_rows:
        best: dict[str, Any] | None = None
        for new in new_rows:
            score, overlap = iou(old["geometry_m"], new["geometry_m"])
            if score <= 0 and old["geometry_hash"] != new["geometry_hash"]:
                continue
            distance = old["geometry_m"].centroid.distance(new["geometry_m"].centroid)
            candidate = {
                "old": old,
                "new": new,
                "iou": score,
                "overlap_m2": overlap,
                "centroid_distance_m": distance,
            }
            if best is None or (candidate["iou"], -candidate["centroid_distance_m"]) > (best["iou"], -best["centroid_distance_m"]):
                best = candidate
        if best:
            matches[old["id"]] = best
    return matches


def action_for(match: dict[str, Any] | None, duplicate_new: bool) -> tuple[str, bool, str]:
    if match is None:
        return "retire_or_manual_locate", False, "No v2 overlap found for old feature."
    old = match["old"]
    new = match["new"]
    same_hash = old["geometry_hash"] == new["geometry_hash"]
    same_damage = old["damage_gra"] == new["damage_gra"]
    if duplicate_new:
        return "split_merge_review", False, "Multiple v1 features map to the same v2 feature."
    if same_hash:
        if same_damage:
            return "reuse", True, "Exact geometry and same official damage class."
        return "reuse_geometry_update_official_attrs", True, "Exact geometry but official damage class changed in v2."
    if match["iou"] >= 0.97 and match["centroid_distance_m"] <= 1:
        if same_damage:
            return "reuse_geometry_minor_change", True, "Geometry drift is below reuse threshold."
        return "reuse_geometry_update_official_attrs", True, "Geometry drift is minor but official damage class changed in v2."
    if match["iou"] >= 0.75:
        return "human_review", False, "Geometry overlap is substantial but not stable enough for automatic reuse."
    return "regenerate_review", False, "Geometry changed enough to require regenerated chips/VLM."


def read_vlm_rows() -> dict[str, dict[str, str]]:
    if not VLM_SUMMARY.exists():
        return {}
    with VLM_SUMMARY.open(newline="") as handle:
        return {row["id"]: row for row in csv.DictReader(handle)}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    old_data = load_json(OLD_GEOJSON)
    new_data = load_v2()
    old_rows = indexed_features(old_data, "aoi12_v1", old=True)
    new_rows = indexed_features(new_data, "aoi12_v2", old=False)
    vlm_rows = read_vlm_rows()

    matches = best_matches(old_rows, new_rows)
    new_match_counts = Counter(match["new"]["id"] for match in matches.values())
    matched_new_ids: set[str] = set()

    remap_rows: list[dict[str, Any]] = []
    for old in old_rows:
        match = matches.get(old["id"])
        duplicate_new = bool(match and new_match_counts[match["new"]["id"]] > 1)
        action, reuse, notes = action_for(match, duplicate_new)
        new = match["new"] if match else {}
        if new:
            matched_new_ids.add(new["id"])
        area_ratio = ""
        if new and new.get("area_m2"):
            area_ratio = old["area_m2"] / new["area_m2"]
        remap_rows.append(
            {
                "old_id": old["id"],
                "new_id": new.get("id", ""),
                "old_index": old["index"],
                "new_index": new.get("index", ""),
                "old_damage_gra": old["damage_gra"],
                "new_damage_gra": new.get("damage_gra", ""),
                "old_damage_percent": old["damage_percent"],
                "new_damage_percent": new.get("damage_percent", ""),
                "old_geometry_hash": old["geometry_hash"],
                "new_geometry_hash": new.get("geometry_hash", ""),
                "iou": round(match["iou"], 6) if match else "",
                "overlap_m2": round(match["overlap_m2"], 3) if match else "",
                "centroid_distance_m": round(match["centroid_distance_m"], 3) if match else "",
                "old_area_m2": round(old["area_m2"], 3),
                "new_area_m2": round(new.get("area_m2", 0), 3) if new else "",
                "area_ratio": round(area_ratio, 6) if area_ratio != "" else "",
                "old_centroid_lat": old["centroid_lat"],
                "old_centroid_lon": old["centroid_lon"],
                "new_centroid_lat": new.get("centroid_lat", ""),
                "new_centroid_lon": new.get("centroid_lon", ""),
                "has_before_after_vlm": old["id"] in vlm_rows,
                "vlm_reuse_eligible": reuse,
                "remap_action": action,
                "notes": notes,
            }
        )

    for new in new_rows:
        if new["id"] in matched_new_ids:
            continue
        remap_rows.append(
            {
                "old_id": "",
                "new_id": new["id"],
                "old_index": "",
                "new_index": new["index"],
                "old_damage_gra": "",
                "new_damage_gra": new["damage_gra"],
                "old_damage_percent": "",
                "new_damage_percent": new["damage_percent"],
                "old_geometry_hash": "",
                "new_geometry_hash": new["geometry_hash"],
                "iou": "",
                "overlap_m2": "",
                "centroid_distance_m": "",
                "old_area_m2": "",
                "new_area_m2": round(new["area_m2"], 3),
                "area_ratio": "",
                "old_centroid_lat": "",
                "old_centroid_lon": "",
                "new_centroid_lat": new["centroid_lat"],
                "new_centroid_lon": new["centroid_lon"],
                "has_before_after_vlm": False,
                "vlm_reuse_eligible": False,
                "remap_action": "new_regenerate",
                "notes": "New v2 feature has no matched v1 feature.",
            }
        )

    fieldnames = [
        "old_id",
        "new_id",
        "old_index",
        "new_index",
        "old_damage_gra",
        "new_damage_gra",
        "old_damage_percent",
        "new_damage_percent",
        "old_geometry_hash",
        "new_geometry_hash",
        "iou",
        "overlap_m2",
        "centroid_distance_m",
        "old_area_m2",
        "new_area_m2",
        "area_ratio",
        "old_centroid_lat",
        "old_centroid_lon",
        "new_centroid_lat",
        "new_centroid_lon",
        "has_before_after_vlm",
        "vlm_reuse_eligible",
        "remap_action",
        "notes",
    ]
    write_csv(REMAP_CSV, remap_rows, fieldnames)

    vlm_queue: list[dict[str, Any]] = []
    remap_by_old = {row["old_id"]: row for row in remap_rows if row.get("old_id")}
    for old_id, vlm in vlm_rows.items():
        row = remap_by_old.get(old_id, {})
        reuse = row.get("vlm_reuse_eligible") is True
        if reuse:
            vlm_action = "reuse_existing_vlm_with_v2_binding"
        elif not row.get("new_id"):
            vlm_action = "retire_existing_vlm_no_v2_binding"
        elif row.get("remap_action") in ("human_review", "split_merge_review"):
            vlm_action = "human_review_before_reuse"
        else:
            vlm_action = "regenerate_before_after_chip_and_vlm"
        vlm_queue.append(
            {
                "old_id": old_id,
                "new_id": row.get("new_id", ""),
                "old_damage_gra": row.get("old_damage_gra", vlm.get("official_ems_damage_gra", "")),
                "new_damage_gra": row.get("new_damage_gra", ""),
                "vlm_damage_class": vlm.get("vlm_damage_class", ""),
                "vlm_confidence": vlm.get("confidence", ""),
                "remap_action": row.get("remap_action", ""),
                "vlm_action": vlm_action,
                "compare_chip": vlm.get("compare_chip", ""),
                "iou": row.get("iou", ""),
                "centroid_distance_m": row.get("centroid_distance_m", ""),
                "google_maps_url": vlm.get("google_maps_url", ""),
            }
        )
    write_csv(
        VLM_QUEUE_CSV,
        vlm_queue,
        [
            "old_id",
            "new_id",
            "old_damage_gra",
            "new_damage_gra",
            "vlm_damage_class",
            "vlm_confidence",
            "remap_action",
            "vlm_action",
            "compare_chip",
            "iou",
            "centroid_distance_m",
            "google_maps_url",
        ],
    )

    v2_out = dict(new_data)
    for index, feature in enumerate(v2_out["features"], start=1):
        props = dict(feature.get("properties") or {})
        props["id"] = source_id("aoi12_v2", index)
        props["aoi"] = "EMSR884_AOI12_GRA_v2"
        props["damage_class"] = props.get("damage_gra", "").lower().replace(" ", "-")
        props["damage_percent"] = damage_percent(props.get("damage_gra", ""))
        feature["properties"] = props
    V2_GEOJSON.write_text(json.dumps(v2_out, ensure_ascii=True, separators=(",", ":")) + "\n")

    action_counts = Counter(row["remap_action"] for row in remap_rows)
    vlm_action_counts = Counter(row["vlm_action"] for row in vlm_queue)
    damage_transitions = Counter(
        f"{row['old_damage_gra']} -> {row['new_damage_gra']}"
        for row in remap_rows
        if row.get("old_id") and row.get("new_id") and row.get("old_damage_gra") != row.get("new_damage_gra")
    )
    summary = {
        "old_public_v1_features": len(old_rows),
        "new_official_v2_features": len(new_rows),
        "remap_rows": len(remap_rows),
        "matched_old_features": sum(1 for row in remap_rows if row.get("old_id") and row.get("new_id")),
        "new_v2_unmatched_features": action_counts.get("new_regenerate", 0),
        "old_v1_unmatched_features": action_counts.get("retire_or_manual_locate", 0),
        "before_after_vlm_rows": len(vlm_rows),
        "action_counts": dict(action_counts),
        "vlm_action_counts": dict(vlm_action_counts),
        "damage_transition_counts": dict(damage_transitions),
        "remap_csv": str(REMAP_CSV.relative_to(ROOT)),
        "vlm_queue_csv": str(VLM_QUEUE_CSV.relative_to(ROOT)),
        "v2_geojson": str(V2_GEOJSON.relative_to(ROOT)),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
