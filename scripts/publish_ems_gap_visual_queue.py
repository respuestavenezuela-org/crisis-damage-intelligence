#!/usr/bin/env python3
"""Publish HOT/MapSwipe EMS-gap visual triage queue as a public static AOI."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.ops import unary_union


ROOT = Path(__file__).resolve().parents[1]
OPS_GEOJSON = ROOT / "ops" / "data_acquisition_plan" / "ems_gap_visual_queue.geojson"
OPS_CSV = ROOT / "ops" / "data_acquisition_plan" / "ems_gap_visual_queue.csv"
PUBLIC_ROOT = ROOT / "public" / "data" / "aoi" / "external-hot-mapswipe-ems-gap-visual"
CATALOG = ROOT / "public" / "data" / "catalog.json"


def load_geojson() -> dict[str, Any]:
    return json.loads(OPS_GEOJSON.read_text())


def feature_point(feature: dict[str, Any]) -> tuple[float, float]:
    geom = shape(feature["geometry"])
    point = geom.representative_point()
    return point.y, point.x


def normalize_feature(feature: dict[str, Any], index: int) -> dict[str, Any]:
    props = feature.get("properties", {})
    lat, lon = feature_point(feature)
    status = str(props.get("triage_status") or "")
    damage_class = "visual_confirmed_gap" if status == "visual_confirmed_gap" else "needs_human_review"
    damage_score = 95 if status == "visual_confirmed_gap" else 65
    source_id = str(props.get("candidate_id") or f"hot_gap_{index:05d}")
    return {
        "type": "Feature",
        "geometry": feature["geometry"],
        "properties": {
            "id": source_id,
            "source_feature_id": source_id,
            "aoi_id": "external-hot-mapswipe-ems-gap-visual",
            "aoi_label_en": "HOT/MapSwipe EMS-gap visual triage",
            "aoi_label_es": "Brechas visuales HOT/MapSwipe fuera de EMS",
            "damage_class": damage_class,
            "damage_gra": damage_class,
            "damage_score": damage_score,
            "damage_percent": damage_score,
            "centroid_lat": lat,
            "centroid_lon": lon,
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={lat},{lon}",
            "not_official_ems": True,
            "external_source": "HOT MapSwipe human validation",
            "external_verdict": props.get("verdict", ""),
            "external_answer": props.get("answer", ""),
            "external_yes_share": props.get("yes_share", ""),
            "external_sources": props.get("sources", ""),
            "official_gra_overlap_count": props.get("official_gra_overlap_count", 0),
            "triage_status": status,
            "source_url": props.get("source_url", ""),
            "imagery_tms": props.get("imagery_tms", ""),
        },
    }


def write_csv(features: list[dict[str, Any]]) -> None:
    fields = [
        "id",
        "damage_class",
        "damage_score",
        "centroid_lat",
        "centroid_lon",
        "google_maps_url",
        "not_official_ems",
        "external_verdict",
        "external_answer",
        "external_yes_share",
        "external_sources",
        "official_gra_overlap_count",
        "triage_status",
        "source_url",
    ]
    with (PUBLIC_ROOT / "damage.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for feature in features:
            p = feature["properties"]
            writer.writerow({field: p.get(field, "") for field in fields})


def write_kml(features: list[dict[str, Any]]) -> None:
    placemarks = []
    for feature in features:
        p = feature["properties"]
        placemarks.append(
            "    <Placemark>\n"
            f"      <name>{p['id']}</name>\n"
            f"      <description>{p['damage_class']} - triage only, not official EMS</description>\n"
            f"      <Point><coordinates>{p['centroid_lon']},{p['centroid_lat']},0</coordinates></Point>\n"
            "    </Placemark>"
        )
    (PUBLIC_ROOT / "damage.kml").write_text(
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<kml xmlns=\"http://www.opengis.net/kml/2.2\">\n"
        "  <Document>\n"
        "    <name>HOT/MapSwipe EMS-gap visual triage</name>\n"
        + "\n".join(placemarks)
        + "\n  </Document>\n"
        "</kml>\n"
    )


def catalog_record(features: list[dict[str, Any]]) -> dict[str, Any]:
    geoms = [shape(feature["geometry"]) for feature in features]
    bounds = unary_union(geoms).bounds
    lons = [float(feature["properties"]["centroid_lon"]) for feature in features]
    lats = [float(feature["properties"]["centroid_lat"]) for feature in features]
    statuses = Counter(feature["properties"]["triage_status"] for feature in features)
    return {
        "id": "external-hot-mapswipe-ems-gap-visual",
        "country": "Venezuela",
        "event": "EMSR884 Venezuela earthquake",
        "name": {
            "en": "HOT/MapSwipe EMS-gap Visual Triage",
            "es": "Brechas visuales HOT/MapSwipe fuera de EMS",
        },
        "status": "external-gap",
        "source": (
            "HOT/MapSwipe human validation from hotosm/venezuela_eq_2026 and HOT response sources. "
            "External visual gap candidates only; not official EMS damage labels and not official counts."
        ),
        "bounds": [[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        "center": [sum(lats) / len(lats), sum(lons) / len(lons)],
        "downloads": {
            "csv": "/data/aoi/external-hot-mapswipe-ems-gap-visual/damage.csv",
            "geojson": "/data/aoi/external-hot-mapswipe-ems-gap-visual/damage.geojson",
            "kml": "/data/aoi/external-hot-mapswipe-ems-gap-visual/damage.kml",
            "metadata": "/data/aoi/external-hot-mapswipe-ems-gap-visual/source_metadata.json",
            "hf_dataset": "https://huggingface.co/datasets/hotosm/venezuela_eq_2026",
            "hot_response": "https://www.hotosm.org/en/projects/2026-venezuela-earthquake-response/",
        },
        "layers": {
            "damage": "/data/aoi/external-hot-mapswipe-ems-gap-visual/damage.geojson",
        },
        "metrics": {
            "features": len(features),
            "destroyed": 0,
            "damagedConfirmed": 0,
            "possibleDamage": 0,
            "candidates": len(features),
            "visualConfirmedGap": statuses.get("visual_confirmed_gap", 0),
            "needsHumanReview": statuses.get("needs_human_review", 0),
            "vlmReviewed": 0,
        },
        "imagery": {
            "before": None,
            "after": None,
            "note": (
                "This layer is generated from HOT/MapSwipe external validation polygons. "
                "Use it to find EMS gaps and prioritize human/VLM review; do not count it as official EMS damage."
            ),
            "approximateReference": {
                "label": "Esri World Imagery aerial reference",
                "urlTemplate": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                "source": "Esri World Imagery / Maxar / Earthstar Geographics / GIS User Community basemap as displayed in the app aerial toggle",
                "intendedUse": "Human visual orientation only for triage candidates.",
                "limitations": "Not cached evidence, not official EMS imagery, and not a basis for official damage counts.",
            },
        },
    }


def update_catalog(record: dict[str, Any]) -> None:
    catalog = json.loads(CATALOG.read_text())
    catalog["updatedAt"] = "2026-07-01T17:55:00Z"
    catalog["aois"] = [aoi for aoi in catalog["aois"] if aoi.get("id") != record["id"]]
    catalog["aois"].append(record)
    CATALOG.write_text(json.dumps(catalog, indent=2) + "\n")


def main() -> int:
    data = load_geojson()
    features = [normalize_feature(feature, index) for index, feature in enumerate(data.get("features", []), start=1)]
    PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
    (PUBLIC_ROOT / "damage.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":")) + "\n")
    write_csv(features)
    write_kml(features)
    (PUBLIC_ROOT / "source_metadata.json").write_text(json.dumps({
        "source": "HOT/MapSwipe human validation via hotosm/venezuela_eq_2026",
        "source_urls": [
            "https://huggingface.co/datasets/hotosm/venezuela_eq_2026",
            "https://www.hotosm.org/en/projects/2026-venezuela-earthquake-response/",
        ],
        "official_status": "not_official_ems",
        "use": "triage_only_external_visual_gap_queue",
        "warning": "Do not merge into official EMS destroyed/damaged metrics.",
        "source_ops_files": [
            str(OPS_GEOJSON.relative_to(ROOT)),
            str(OPS_CSV.relative_to(ROOT)),
        ],
    }, indent=2) + "\n")
    record = catalog_record(features)
    update_catalog(record)
    print(json.dumps({"features": len(features), "catalog_id": record["id"], "metrics": record["metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
