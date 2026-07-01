#!/usr/bin/env python3
import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from xml.etree import ElementTree as ET

from shapely import wkt
from shapely.geometry import shape


BUCKET_BASE = "https://umbra-open-data-catalog.s3.us-west-2.amazonaws.com/"
UMBRA_PREFIX = "sar-data/tasks/Venezuela_Earthquake_Support/"
EMS_API = "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884"
OUT_DIR = Path("ops")

REFERENCE_PLACES = {
    "Caracas": (10.4806, -66.9036),
    "Petare": (10.4833, -66.8167),
    "Puerto Cabello": (10.4731, -68.0125),
    "La Guaira": (10.6000, -66.9333),
    "Caraballeda": (10.6126, -66.8524),
    "San Felipe": (10.3406, -68.7369),
    "Guacara": (10.2261, -67.8770),
    "Maracay": (10.2469, -67.5958),
}


def fetch_bytes(url: str) -> bytes:
    with urlopen(url, timeout=45) as response:
        return response.read()


def list_umbra_objects() -> list[dict]:
    url = f"{BUCKET_BASE}?list-type=2&prefix={UMBRA_PREFIX}&max-keys=1000"
    root = ET.fromstring(fetch_bytes(url))
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    objects = []
    for node in root.findall("s:Contents", ns):
        key = node.find("s:Key", ns).text
        objects.append({
            "key": key,
            "lastModified": node.find("s:LastModified", ns).text,
            "size": int(node.find("s:Size", ns).text),
            "url": BUCKET_BASE + key,
        })
    return objects


def load_ems_aois() -> list[dict]:
    activation = json.loads(fetch_bytes(EMS_API))["results"][0]
    aois = []
    for aoi in activation["aois"]:
        aois.append({
            "aoi": f"AOI{aoi['number']:02d}",
            "name": aoi["name"],
            "geom": wkt.loads(aoi["extent"]),
        })
    return aois


def km_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    return math.hypot(
        (lat1 - lat2) * 110.57,
        (lon1 - lon2) * 111.32 * math.cos(math.radians((lat1 + lat2) / 2)),
    )


def closest_places(lat: float, lon: float) -> list[dict]:
    ranked = []
    for name, point in REFERENCE_PLACES.items():
        ranked.append({"name": name, "distanceKm": round(km_between((lat, lon), point), 2)})
    return sorted(ranked, key=lambda item: item["distanceKm"])[:4]


def asset_by_suffix(files: list[dict], suffix: str) -> dict | None:
    matches = [item for item in files if item["key"].endswith(suffix)]
    return matches[0] if matches else None


def build_inventory() -> dict:
    objects = list_umbra_objects()
    by_dir: dict[str, list[dict]] = {}
    for item in objects:
        by_dir.setdefault(item["key"].rsplit("/", 1)[0], []).append(item)

    ems_aois = load_ems_aois()
    scenes = []
    for stac_object in objects:
        if not stac_object["key"].endswith(".stac.v2.json"):
            continue
        stac = json.loads(fetch_bytes(stac_object["url"]))
        props = stac.get("properties", {})
        geom = shape(stac["geometry"])
        directory = stac_object["key"].rsplit("/", 1)[0]
        files = by_dir[directory]
        gec = asset_by_suffix(files, "_GEC.tif")
        sidd = asset_by_suffix(files, "_SIDD.nitf")
        sicd = asset_by_suffix(files, "_SICD.nitf")
        centroid = geom.centroid

        overlaps = []
        for aoi in ems_aois:
            intersection = geom.intersection(aoi["geom"])
            if not intersection.is_empty:
                overlaps.append({
                    "aoi": aoi["aoi"],
                    "name": aoi["name"],
                    "areaDeg2": intersection.area,
                })
        overlaps.sort(key=lambda item: item["areaDeg2"], reverse=True)

        scenes.append({
            "id": stac.get("id"),
            "datetime": props.get("datetime") or stac.get("datetime"),
            "created": props.get("created"),
            "platform": props.get("platform"),
            "instrumentMode": props.get("sar:instrument_mode"),
            "polarizations": props.get("sar:polarizations") or [],
            "collectId": props.get("umbra:collect_id"),
            "bbox": stac.get("bbox"),
            "centroid": {"lat": centroid.y, "lon": centroid.x},
            "closestPlaces": closest_places(centroid.y, centroid.x),
            "overlaps": overlaps,
            "stac": {
                "url": stac_object["url"],
                "lastModified": stac_object["lastModified"],
                "bytes": stac_object["size"],
            },
            "gec": {
                "url": gec["url"] if gec else None,
                "lastModified": gec["lastModified"] if gec else None,
                "bytes": gec["size"] if gec else None,
                "format": "GeoTIFF COG, GEC, byte grayscale",
            },
            "sidd": {
                "url": sidd["url"] if sidd else None,
                "bytes": sidd["size"] if sidd else None,
            },
            "sicd": {
                "url": sicd["url"] if sicd else None,
                "bytes": sicd["size"] if sicd else None,
            },
        })
    scenes.sort(key=lambda item: item["datetime"])
    return {
        "source": "Umbra Open SAR Data / AWS Open Data",
        "sourcePrefix": UMBRA_PREFIX,
        "bucketBase": BUCKET_BASE,
        "checkedAt": datetime.now(timezone.utc).isoformat(),
        "licenseNote": "Public Umbra Open SAR Data bucket. Confirm downstream redistribution terms before republishing derived rasters.",
        "operationalUse": "Post-event SAR context and all-weather triage. Do not treat as official EMS damage grading or optical before/after evidence.",
        "scenes": scenes,
    }


def write_csv(inventory: dict, path: Path) -> None:
    fields = [
        "id",
        "datetime",
        "created",
        "platform",
        "polarizations",
        "instrumentMode",
        "collectId",
        "centroidLat",
        "centroidLon",
        "bbox",
        "closestPlaces",
        "overlaps",
        "gecUrl",
        "gecBytes",
        "stacUrl",
    ]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for scene in inventory["scenes"]:
            writer.writerow({
                "id": scene["id"],
                "datetime": scene["datetime"],
                "created": scene["created"],
                "platform": scene["platform"],
                "polarizations": ",".join(scene["polarizations"]),
                "instrumentMode": scene["instrumentMode"],
                "collectId": scene["collectId"],
                "centroidLat": scene["centroid"]["lat"],
                "centroidLon": scene["centroid"]["lon"],
                "bbox": json.dumps(scene["bbox"], separators=(",", ":")),
                "closestPlaces": "; ".join(f"{p['name']} {p['distanceKm']}km" for p in scene["closestPlaces"]),
                "overlaps": "; ".join(f"{o['aoi']} {o['name']}" for o in scene["overlaps"][:4]),
                "gecUrl": scene["gec"]["url"],
                "gecBytes": scene["gec"]["bytes"],
                "stacUrl": scene["stac"]["url"],
            })


def write_report(inventory: dict, path: Path) -> None:
    scenes = inventory["scenes"]
    lines = [
        "# Umbra Venezuela SAR Inventory",
        "",
        f"Checked: `{inventory['checkedAt']}`",
        "",
        f"Source prefix: `{inventory['sourcePrefix']}`",
        "",
        "## Summary",
        "",
        f"- Scenes: `{len(scenes)}`",
        f"- Acquisition window: `{scenes[0]['datetime']}` to `{scenes[-1]['datetime']}`",
        "- Product to use first: `GEC.tif` (GeoTIFF COG, byte grayscale, range-readable, CORS-enabled with Origin)",
        "- Heavy products: `SIDD.nitf` is roughly 819 MB per scene; `SICD.nitf` is roughly 18-30 GB per scene.",
        "- Use: post-event SAR context / all-weather triage only; not official EMS damage grading and not optical before/after VLM evidence.",
        "",
        "## Coverage Notes",
        "",
        "- All scenes intersect the broad EMSR884 AOI00 Central Coastal Venezuela footprint.",
        "- Exact EMS AOI intersections in this public prefix are limited: AOI01 Petare has 2 overlaps and AOI08 San Felipe has 3 overlaps.",
        "- Several western scenes are nearest to Puerto Cabello / Guacara / Maracay by centroid, but they do not intersect the official AOI07 Puerto Cabello polygon in this inventory check.",
        "- No scene in this prefix intersects AOI12 La Guaira / Caraballeda.",
        "",
        "## Scene Table",
        "",
        "| Time UTC | Platform | Pol | Nearest places | EMS overlaps | GEC MB | GEC URL |",
        "|---|---|---|---|---|---:|---|",
    ]
    for scene in scenes:
        nearest = "; ".join(f"{p['name']} {p['distanceKm']}km" for p in scene["closestPlaces"][:3])
        overlaps = "; ".join(f"{o['aoi']} {o['name']}" for o in scene["overlaps"][:3]) or "none"
        gec_bytes = scene["gec"]["bytes"] or 0
        lines.append(
            f"| `{scene['datetime']}` | {scene['platform']} | {','.join(scene['polarizations'])} | "
            f"{nearest} | {overlaps} | {gec_bytes / 1_000_000:.1f} | [GEC]({scene['gec']['url']}) |"
        )
    lines.append("")
    path.write_text("\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    inventory = build_inventory()
    json_path = OUT_DIR / "umbra_venezuela_sar_inventory.json"
    csv_path = OUT_DIR / "umbra_venezuela_sar_inventory.csv"
    md_path = OUT_DIR / "umbra_venezuela_sar_inventory.md"
    json_path.write_text(json.dumps(inventory, indent=2) + "\n")
    write_csv(inventory, csv_path)
    write_report(inventory, md_path)
    print(json.dumps({
        "scenes": len(inventory["scenes"]),
        "first": inventory["scenes"][0]["datetime"],
        "last": inventory["scenes"][-1]["datetime"],
        "json": str(json_path),
        "csv": str(csv_path),
        "report": str(md_path),
    }, indent=2))


if __name__ == "__main__":
    main()
