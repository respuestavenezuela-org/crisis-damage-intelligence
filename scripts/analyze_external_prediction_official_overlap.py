#!/usr/bin/env python3
"""Compare external prediction footprints against official EMS GRA polygons."""

from __future__ import annotations

import csv
import json
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from pyproj import Transformer
from shapely import make_valid
from shapely.geometry import shape
from shapely.ops import transform
from shapely.strtree import STRtree


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = ROOT / "ops" / "data_acquisition_plan" / "official_products"
EXTERNAL_INVENTORY = ROOT / "ops" / "data_acquisition_plan" / "external_prediction_gpkg_inventory.csv"
OUT = ROOT / "ops" / "data_acquisition_plan" / "external_prediction_official_overlap_summary.csv"
DETAIL = ROOT / "ops" / "data_acquisition_plan" / "external_prediction_official_overlap_detail.csv"
SUMMARY = ROOT / "ops" / "data_acquisition_plan" / "external_prediction_official_overlap_summary.json"
TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:32619", always_xy=True)


def clean_geom(feature: dict[str, Any]) -> Any:
    geom = shape(feature["geometry"])
    if not geom.is_valid:
        geom = make_valid(geom)
    return geom


def to_meters(geom: Any) -> Any:
    return transform(TRANSFORMER.transform, geom)


def official_gra_polygons() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for zip_path in sorted(PRODUCT_DIR.glob("EMSR884_AOI*_GRA_PRODUCT_v*.zip")):
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.namelist():
                name = Path(member).name
                if "_builtUpA_" not in name or not name.endswith(".json"):
                    continue
                data = json.load(zf.open(member))
                for index, feature in enumerate(data.get("features", []), start=1):
                    geom = clean_geom(feature)
                    if geom.geom_type not in ("Polygon", "MultiPolygon"):
                        continue
                    props = feature.get("properties") or {}
                    rows.append(
                        {
                            "official_product_zip": zip_path.name,
                            "official_member": member,
                            "official_feature_index": index,
                            "damage_gra": props.get("damage_gra", ""),
                            "geometry_m": to_meters(geom),
                        }
                    )
    return rows


def read_external_layers() -> list[dict[str, str]]:
    with EXTERNAL_INVENTORY.open(newline="") as handle:
        return list(csv.DictReader(handle))


def layer_to_geojson(path: Path, layer: str, dst: Path) -> None:
    subprocess.check_call(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            "-t_srs",
            "EPSG:4326",
            str(dst),
            str(path),
            layer,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def is_high_priority(props: dict[str, Any]) -> bool:
    if props.get("damaged") == 1 or props.get("damaged") == "1":
        return True
    for field in ("damage_pct_0m", "damage_pct_10m", "damage_pct_20m"):
        try:
            if float(props.get(field, 0) or 0) >= 0.5:
                return True
        except (TypeError, ValueError):
            continue
    return False


def max_damage_pct(props: dict[str, Any]) -> float:
    values = []
    for field in ("damage_pct_0m", "damage_pct_10m", "damage_pct_20m"):
        try:
            values.append(float(props.get(field, 0) or 0))
        except (TypeError, ValueError):
            values.append(0.0)
    return max(values) if values else 0.0


def main() -> int:
    official = official_gra_polygons()
    official_geoms = [row["geometry_m"] for row in official]
    tree = STRtree(official_geoms)
    summary_rows: list[dict[str, Any]] = []
    detail_rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        for layer_row in read_external_layers():
            source = layer_row["source_name"]
            layer = layer_row["layer_name"]
            local_path = ROOT / layer_row["local_path"]
            geojson = tmp / f"{local_path.stem}_{layer}.geojson"
            layer_to_geojson(local_path, layer, geojson)
            data = json.loads(geojson.read_text())

            total = 0
            high = 0
            overlaps = 0
            high_overlaps = 0
            outside = 0
            high_outside = 0
            for index, feature in enumerate(data.get("features", []), start=1):
                total += 1
                props = feature.get("properties") or {}
                geom_m = to_meters(clean_geom(feature))
                high_priority = is_high_priority(props)
                if high_priority:
                    high += 1
                candidates = tree.query(geom_m)
                overlap_count = 0
                overlap_area = 0.0
                for candidate_index in candidates:
                    official_geom = official_geoms[int(candidate_index)]
                    if not geom_m.intersects(official_geom):
                        continue
                    area = geom_m.intersection(official_geom).area
                    if area > 0:
                        overlap_count += 1
                        overlap_area += area
                has_overlap = overlap_count > 0
                if has_overlap:
                    overlaps += 1
                    if high_priority:
                        high_overlaps += 1
                else:
                    outside += 1
                    if high_priority:
                        high_outside += 1
                if high_priority and (not has_overlap or overlap_count > 1):
                    centroid = feature["geometry"]
                    point = clean_geom(feature).centroid
                    detail_rows.append(
                        {
                            "source_name": source,
                            "layer_name": layer,
                            "feature_index": index,
                            "damaged": props.get("damaged", ""),
                            "max_damage_pct": round(max_damage_pct(props), 6),
                            "overlaps_official_gra": has_overlap,
                            "official_overlap_count": overlap_count,
                            "official_overlap_area_m2": round(overlap_area, 3),
                            "centroid_lat": point.y,
                            "centroid_lon": point.x,
                        }
                    )

            summary_rows.append(
                {
                    "source_name": source,
                    "layer_name": layer,
                    "total_features": total,
                    "high_priority_features": high,
                    "overlaps_official_gra_features": overlaps,
                    "outside_official_gra_features": outside,
                    "high_priority_overlaps_official_gra": high_overlaps,
                    "high_priority_outside_official_gra": high_outside,
                    "official_gra_polygon_count_compared": len(official),
                    "status": "external_prediction_triage_only",
                }
            )

    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_name",
                "layer_name",
                "total_features",
                "high_priority_features",
                "overlaps_official_gra_features",
                "outside_official_gra_features",
                "high_priority_overlaps_official_gra",
                "high_priority_outside_official_gra",
                "official_gra_polygon_count_compared",
                "status",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    with DETAIL.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_name",
                "layer_name",
                "feature_index",
                "damaged",
                "max_damage_pct",
                "overlaps_official_gra",
                "official_overlap_count",
                "official_overlap_area_m2",
                "centroid_lat",
                "centroid_lon",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(detail_rows)

    summary = {
        "official_gra_polygon_count_compared": len(official),
        "external_layers": len(summary_rows),
        "external_features": sum(int(row["total_features"]) for row in summary_rows),
        "high_priority_features": sum(int(row["high_priority_features"]) for row in summary_rows),
        "high_priority_outside_official_gra": sum(int(row["high_priority_outside_official_gra"]) for row in summary_rows),
        "summary_csv": str(OUT.relative_to(ROOT)),
        "detail_csv": str(DETAIL.relative_to(ROOT)),
        "warning": "External predictions are triage only and are not official EMS damage counts.",
    }
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
