#!/usr/bin/env python3
"""Publish Microsoft/HDX predicted damage layers as external triage-only data.

The generated AOIs are intentionally separate from official Copernicus EMS AOIs:
they are model predictions for field triage and must not contribute to official
damage counts.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "ops" / "external_source_review" / "analysis" / "msft_hdx" / "summary.json"
MANIFEST_PATH = ROOT / "ops" / "external_source_review" / "downloads" / "msft_hdx" / "download_manifest.json"
CATALOG_PATH = ROOT / "public" / "data" / "catalog.json"
PUBLIC_AOI_DIR = ROOT / "public" / "data" / "aoi"

THRESHOLD = 0.50
PROVIDER = "Microsoft AI for Good Lab via HDX"
WARNING = (
    "External model prediction for triage only. Not official Copernicus EMS damage. "
    "Do not use for official counts without field or official validation."
)

LAYERS = {
    "caraballeda_east": {
        "public_id": "external-msft-caraballeda-east-predicted-damage",
        "source_id": "hdx-msft-caraballeda-predicted-damage",
        "short_prefix": "msft_caraballeda",
        "name_en": "Caraballeda East - Microsoft AI4G Triage Candidates",
        "name_es": "Caraballeda Este - Candidatos triage Microsoft AI4G",
        "dataset_title": "Venezuela Earthquakes: Building Damage Assessment in Caraballeda",
        "hdx_url": "https://data.humdata.org/dataset/venezuela-earthquakes-building-damage-assessment-in-caraballeda",
    },
    "catia_la_mar_east": {
        "public_id": "external-msft-catia-la-mar-east-predicted-damage",
        "source_id": "hdx-msft-catia-la-mar-east-predicted-damage",
        "short_prefix": "msft_catia_east",
        "name_en": "Catia La Mar East - Microsoft AI4G Triage Candidates",
        "name_es": "Catia La Mar Este - Candidatos triage Microsoft AI4G",
        "dataset_title": "Venezuela Earthquakes: Building Damage Assessment in East Catia La Mar",
        "hdx_url": "https://data.humdata.org/dataset/venezuela-earthquakes-building-damage-assessment-in-catia-la-mar-east",
    },
    "la_guaira_east": {
        "public_id": "external-msft-la-guaira-east-predicted-damage",
        "source_id": "hdx-msft-la-guaira-predicted-damage",
        "short_prefix": "msft_la_guaira",
        "name_en": "La Guaira East - Microsoft AI4G Triage Candidates",
        "name_es": "La Guaira Este - Candidatos triage Microsoft AI4G",
        "dataset_title": "Venezuela Earthquakes: Building Damage Assessment in La Guaira East",
        "hdx_url": "https://data.humdata.org/dataset/venezuela-earthquakes-building-damage-assessment-in-la-guaira",
    },
}

CSV_FIELDS = [
    "id",
    "source_id",
    "damage_gra",
    "damage_class",
    "damage_percent",
    "max_damage_pct",
    "damage_pct_0m",
    "damage_pct_10m",
    "damage_pct_20m",
    "unknown_pct",
    "damaged",
    "source_confidence",
    "source_provider",
    "centroid_lat",
    "centroid_lon",
    "google_maps_url",
]
MAP_GEOJSON_FIELDS = [
    "id",
    "source_id",
    "damage_gra",
    "damage_class",
    "damage_percent",
    "not_official_ems",
    "centroid_lat",
    "centroid_lon",
]
KML_FEATURE_LIMIT = 3_000


def run(args: list[str]) -> str:
    return subprocess.check_output(args, text=True)


def as_float(value: object) -> float:
    if value in (None, ""):
        return 0.0
    return float(value)


def centroid(coords: object) -> tuple[float, float]:
    points: list[tuple[float, float]] = []

    def walk(node: object) -> None:
        if (
            isinstance(node, list)
            and len(node) >= 2
            and isinstance(node[0], (int, float))
            and isinstance(node[1], (int, float))
        ):
            points.append((float(node[0]), float(node[1])))
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(coords)
    if not points:
        return 0.0, 0.0
    lon = sum(point[0] for point in points) / len(points)
    lat = sum(point[1] for point in points) / len(points)
    return lat, lon


def bounds(features: list[dict]) -> tuple[list[list[float]], list[float]]:
    lats: list[float] = []
    lons: list[float] = []
    for feature in features:
        props = feature["properties"]
        lats.append(props["centroid_lat"])
        lons.append(props["centroid_lon"])
    return [[min(lats), min(lons)], [max(lats), max(lons)]], [
        sum(lats) / len(lats),
        sum(lons) / len(lons),
    ]


def compact_float(value: object, digits: int = 6) -> float:
    return round(as_float(value), digits)


def compact_coordinates(value: object, digits: int = 6) -> object:
    if (
        isinstance(value, list)
        and len(value) >= 2
        and isinstance(value[0], (int, float))
        and isinstance(value[1], (int, float))
    ):
        return [round(float(value[0]), digits), round(float(value[1]), digits)]
    if isinstance(value, list):
        return [compact_coordinates(item, digits) for item in value]
    return value


def map_payload_feature(feature: dict) -> dict:
    props = feature["properties"]
    compact_props = {field: props[field] for field in MAP_GEOJSON_FIELDS if field in props}
    compact_props["aoi_id"] = props.get("aoi")
    compact_props["triage_only"] = True
    return {
        "type": "Feature",
        "properties": compact_props,
        "geometry": {
            **(feature.get("geometry") or {}),
            "coordinates": compact_coordinates((feature.get("geometry") or {}).get("coordinates", [])),
        },
    }


def gpkg_resource_url(manifest: list[dict], source_id: str) -> str:
    for item in manifest:
        if item.get("source_id") == source_id and item.get("format") == "GPKG":
            return item["url"]
    return ""


def export_raw_geojson(source_path: Path, layer_name: str, output_path: Path) -> None:
    if output_path.exists():
        output_path.unlink()
    subprocess.run(
        [
            "ogr2ogr",
            "-f",
            "GeoJSON",
            "-t_srs",
            "EPSG:4326",
            str(output_path),
            str(source_path),
            layer_name,
        ],
        check=True,
    )


def normalize_features(raw_geojson: Path, config: dict) -> list[dict]:
    data = json.loads(raw_geojson.read_text())
    features = []
    for feature in data.get("features", []):
        source_props = feature.get("properties") or {}
        damage_scores = [
            as_float(source_props.get("damage_pct_0m")),
            as_float(source_props.get("damage_pct_10m")),
            as_float(source_props.get("damage_pct_20m")),
        ]
        max_damage = max(damage_scores)
        damaged_flag = int(as_float(source_props.get("damaged")))
        if damaged_flag != 1 and max_damage < THRESHOLD:
            continue

        lat, lon = centroid(feature.get("geometry", {}).get("coordinates", []))
        index = len(features) + 1
        props = {
            "id": f"{config['short_prefix']}_{index:05d}",
            "source_id": source_props.get("id"),
            "aoi": config["public_id"],
            "damage_gra": "Damaged",
            "damage_class": "external-predicted-damaged",
            "damage_percent": round(max_damage * 100, 1),
            "max_damage_pct": compact_float(max_damage),
            "damage_pct_0m": compact_float(source_props.get("damage_pct_0m")),
            "damage_pct_10m": compact_float(source_props.get("damage_pct_10m")),
            "damage_pct_20m": compact_float(source_props.get("damage_pct_20m")),
            "unknown_pct": compact_float(source_props.get("unknown_pct")),
            "damaged": damaged_flag,
            "triage_only": True,
            "not_official_ems": True,
            "source_confidence": "external-model-prediction",
            "source_provider": PROVIDER,
            "source_dataset": config["dataset_title"],
            "centroid_lat": round(lat, 7),
            "centroid_lon": round(lon, 7),
            "google_maps_url": f"https://www.google.com/maps/search/?api=1&query={lat:.7f},{lon:.7f}",
        }
        features.append({"type": "Feature", "properties": props, "geometry": feature.get("geometry")})
    return features


def write_csv(features: list[dict], path: Path) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for feature in features:
            writer.writerow({field: feature["properties"].get(field, "") for field in CSV_FIELDS})


def write_kml(features: list[dict], path: Path, title: str) -> None:
    placemarks = []
    for feature in features:
        props = feature["properties"]
        description = "<![CDATA[" + (
            f"<b>Status:</b> external triage prediction, not official EMS damage<br/>"
            f"<b>Source ID:</b> {escape(str(props['source_id']))}<br/>"
            f"<b>Max damage score:</b> {escape(str(props['max_damage_pct']))}<br/>"
            f"<b>Damaged flag:</b> {escape(str(props['damaged']))}<br/>"
            f"<b>Google Maps:</b> <a href='{escape(props['google_maps_url'])}'>open</a><br/>"
        ) + "]]>"
        placemarks.append(
            f"""
    <Placemark>
      <name>{escape(props['id'])}</name>
      <description>{description}</description>
      <Style><IconStyle><color>ff1a12c4</color><scale>0.85</scale><Icon><href>http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png</href></Icon></IconStyle></Style>
      <Point><coordinates>{props['centroid_lon']},{props['centroid_lat']},0</coordinates></Point>
    </Placemark>"""
        )
    path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>{escape(title)}</name>\n'
        + "\n".join(placemarks)
        + "\n</Document></kml>\n"
    )


def write_layer(layer_id: str, summary: dict, manifest: list[dict]) -> dict:
    config = LAYERS[layer_id]
    output_dir = PUBLIC_AOI_DIR / config["public_id"]
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory() as tmp:
        raw_geojson = Path(tmp) / "raw.geojson"
        export_raw_geojson(ROOT / summary["file"], summary["layer"], raw_geojson)
        features = normalize_features(raw_geojson, config)

    if not features:
        raise RuntimeError(f"{layer_id}: no features passed external triage filter")

    feature_collection = {
        "type": "FeatureCollection",
        "name": config["public_id"],
        "features": [map_payload_feature(feature) for feature in features],
    }
    (output_dir / "damage.geojson").write_text(json.dumps(feature_collection, separators=(",", ":")))
    write_csv(features, output_dir / "damage.csv")
    kml_written = len(features) <= KML_FEATURE_LIMIT
    if kml_written:
        write_kml(features, output_dir / "damage.kml", config["name_en"])

    layer_bounds, layer_center = bounds(features)
    source_gpkg_url = gpkg_resource_url(manifest, config["source_id"])

    metadata = {
        "source": "HDX dataset from Microsoft AI for Good Lab; external model-predicted building damage footprints, not official Copernicus EMS damage labels.",
        "dataset_title": config["dataset_title"],
        "hdx_dataset_url": config["hdx_url"],
        "source_resource_url": source_gpkg_url,
        "source_layer": summary["layer"],
        "source_crs": "converted to EPSG:4326",
        "filter": "Published only if damaged == 1 or max(damage_pct_0m, damage_pct_10m, damage_pct_20m) >= 0.50.",
        "total_source_features": summary["feature_count"],
        "exported_triage_features": len(features),
        "official_damage_counts_included": False,
        "map_payload": "damage.geojson is a compact browser map payload with trimmed properties and 6 decimal coordinate precision; use CSV or the HDX source GPKG for full attribute review.",
        "kml_public_download": (
            "Included in the static package."
            if kml_written
            else f"Omitted from the static public package because {len(features)} features exceeded the {KML_FEATURE_LIMIT} feature KML budget; use source_resource_url for full GIS export."
        ),
        "bounds": layer_bounds,
        "center": layer_center,
        "warning": WARNING,
    }
    (output_dir / "source_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")

    downloads = {
        "csv": f"/data/aoi/{config['public_id']}/damage.csv",
        "geojson": f"/data/aoi/{config['public_id']}/damage.geojson",
        "metadata": f"/data/aoi/{config['public_id']}/source_metadata.json",
        "hdx": config["hdx_url"],
        "source_gpkg": source_gpkg_url,
    }
    if kml_written:
        downloads["kml"] = f"/data/aoi/{config['public_id']}/damage.kml"

    return {
        "id": config["public_id"],
        "country": "Venezuela",
        "event": "Venezuela earthquake June 2026",
        "name": {"en": config["name_en"], "es": config["name_es"]},
        "status": "external-prediction",
        "source": f"HDX dataset from Microsoft AI for Good Lab: {config['dataset_title']}. External predicted building-footprint triage candidates, not official Copernicus EMS damage labels.",
        "bounds": layer_bounds,
        "center": layer_center,
        "downloads": downloads,
        "layers": {"damage": f"/data/aoi/{config['public_id']}/damage.geojson"},
        "metrics": {
            "features": len(features),
            "destroyed": 0,
            "damagedConfirmed": 0,
            "possibleDamage": 0,
            "candidates": len(features),
            "vlmReviewed": 0,
        },
        "externalTriage": {
            "provider": PROVIDER,
            "official": False,
            "triageOnly": True,
            "filter": "damaged == 1 or max damage probability >= 0.50",
            "warning": WARNING,
        },
        "imagery": {
            "before": None,
            "after": None,
            "note": "No imagery is bundled with this external prediction layer. Use only as optional triage context. Official EMS AOI records remain the source for official counts.",
            "approximateReference": {
                "label": "Esri World Imagery aerial reference",
                "urlTemplate": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                "source": "Esri World Imagery / Maxar / Earthstar Geographics / GIS User Community basemap as displayed in the app aerial toggle",
                "intendedUse": "Human visual orientation and low-confidence review context.",
                "limitations": "Not official EMS before imagery, not guaranteed to be pre-event at each tile, and must not be used for official damage counts.",
            },
        },
    }


def update_catalog(entries: list[dict]) -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    managed_ids = {entry["id"] for entry in entries}
    catalog["aois"] = [aoi for aoi in catalog.get("aois", []) if aoi.get("id") not in managed_ids]
    catalog["aois"].extend(entries)
    catalog["updatedAt"] = "2026-06-28T14:40:00Z"
    CATALOG_PATH.write_text(json.dumps(catalog, indent=2) + "\n")


def validate_outputs(entries: list[dict]) -> None:
    for entry in entries:
        geojson_path = ROOT / "public" / entry["downloads"]["geojson"].lstrip("/")
        data = json.loads(geojson_path.read_text())
        for feature in data["features"]:
            props = feature["properties"]
            if props.get("not_official_ems") is not True or props.get("triage_only") is not True:
                raise RuntimeError(f"{entry['id']}: feature missing external guardrails")
        metrics = entry["metrics"]
        if any(metrics[key] != 0 for key in ("destroyed", "damagedConfirmed", "possibleDamage")):
            raise RuntimeError(f"{entry['id']}: official metric fields must remain zero")


def main() -> int:
    summaries = {item["id"]: item for item in json.loads(SUMMARY_PATH.read_text())}
    manifest = json.loads(MANIFEST_PATH.read_text())
    entries = [write_layer(layer_id, summaries[layer_id], manifest) for layer_id in LAYERS]
    validate_outputs(entries)
    update_catalog(entries)
    print("Published external Microsoft/HDX triage layers:")
    for entry in entries:
        print(f"- {entry['id']}: {entry['metrics']['candidates']} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
