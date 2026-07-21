#!/usr/bin/env python3
"""Add every EMSR884 AOI and its dated imagery records to the public catalog.

This is intentionally conservative: large COGs without a first-party tile
pyramid remain download/evidence links instead of being loaded by the map.
Imagery-only AOIs publish empty damage layers and zero official damage counts.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "public" / "data" / "catalog.json"
INVENTORY_PATH = ROOT / "public" / "data" / "imagery" / "emsr884-acquisitions.json"
AOI_DIR = ROOT / "public" / "data" / "aoi"
INVENTORY_PUBLIC_PATH = "/data/imagery/emsr884-acquisitions.json"
DIRECT_RASTER_MOBILE_MAX_BYTES = 250_000_000
AOI_SLUGS = {
    0: "central-coastal-venezuela",
    1: "petare",
    2: "caracas",
    3: "antimano",
    4: "maracay",
    5: "santa-cruz",
    6: "moron",
    7: "puerto-cabello",
    8: "san-felipe",
    9: "valencia",
    10: "guacara",
    11: "villa-de-cura",
    12: "caraballeda",
}


def aoi_id(number: int) -> str:
    return f"emsr884-aoi{number:02d}-{AOI_SLUGS[number]}"


def ensure_empty_damage_package(number: int, name: str) -> None:
    directory = AOI_DIR / aoi_id(number)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "damage.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": []}, indent=2) + "\n"
    )
    (directory / "damage.csv").write_text(
        "id,damage_gra,damage_percent,centroid_lat,centroid_lon,google_maps_url\n"
    )
    (directory / "damage.kml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2"><Document></Document></kml>\n'
    )
    (directory / "source_metadata.json").write_text(
        json.dumps(
            {
                "source": "Copernicus EMSR884 imagery metadata; no official GRA damage vector product",
                "aoi": aoi_id(number),
                "aoiCode": f"AOI{number:02d}",
                "aoiName": name,
                "imageryInventory": INVENTORY_PUBLIC_PATH,
                "officialDamageCounts": False,
            },
            indent=2,
        )
        + "\n"
    )


def public_acquisition(record: dict[str, Any]) -> dict[str, Any]:
    result = {
        "recordId": record["recordId"],
        "distinctAcquisitionId": record["distinctAcquisitionId"],
        "product": record["product"],
        "productStatusCode": record["productStatusCode"],
        "sensorType": record["sensorType"],
        "sensor": record["sensor"],
        "resolutionClass": record["resolutionClass"],
        "acquisitionUtc": record["acquisitionUtc"],
        "url": record.get("cogUrl") or record.get("productDownloadUrl"),
        "bytes": record["access"]["bytes"],
        "httpStatus": record["access"]["httpStatus"],
        "publiclyReadable": record["access"]["publiclyReadable"],
        "acceptRanges": record["access"]["acceptRanges"],
        "productDownloadUrl": record["productDownloadUrl"],
        "source": record["source"],
        "license": record["license"],
        "role": record["role"],
        "analysisStatus": "not-reviewed-for-response-logistics",
    }
    if record["aoiNumber"] == 12 and record["acquisitionUtc"] == "2026-06-26T15:10:00":
        if record["product"] == "GRA_PRODUCT":
            result["analysisStatus"] = "reviewed-response-sites"
        else:
            result["analysisStatus"] = "duplicate-product-record"
            result["duplicateOf"] = "EMSR884-AOI12-GRA_PRODUCT"
    if record["aoiNumber"] == 12 and record["acquisitionUtc"] == "2026-07-05T15:05:00":
        result["analysisStatus"] = "temporal-follow-up-pending-human-review"
    return result


def new_local_optical_aoi(inventory_aoi: dict[str, Any]) -> dict[str, Any]:
    number = int(inventory_aoi["aoiNumber"])
    name = str(inventory_aoi["name"])
    acquisitions = [public_acquisition(record) for record in inventory_aoi["acquisitions"]]
    earliest = min(acquisitions, key=lambda record: record["acquisitionUtc"])
    identifier = aoi_id(number)
    ensure_empty_damage_package(number, name)
    damage_base = f"/data/aoi/{identifier}"
    layers: dict[str, str] = {"damage": f"{damage_base}/damage.geojson"}
    if earliest["publiclyReadable"] and earliest["bytes"] <= DIRECT_RASTER_MOBILE_MAX_BYTES:
        layers["afterImage"] = earliest["url"]
    return {
        "id": identifier,
        "country": "Venezuela",
        "event": "EMSR884 Venezuela earthquake",
        "name": {
            "en": f"AOI{number:02d} {name} - Imagery available, no official damage vector",
            "es": f"AOI{number:02d} {name} - Imagen disponible, sin vector oficial de daños",
        },
        "status": "imagery-only",
        "source": (
            f"Copernicus EMSR884 public dashboard imagery metadata for AOI{number:02d}. "
            "No official GRA damage vector product was produced; imagery is context only and "
            "must not be converted into official damage counts."
        ),
        "bounds": inventory_aoi["bounds"],
        "center": inventory_aoi["center"],
        "downloads": {
            "csv": f"{damage_base}/damage.csv",
            "geojson": f"{damage_base}/damage.geojson",
            "kml": f"{damage_base}/damage.kml",
            "metadata": f"{damage_base}/source_metadata.json",
            "cog": earliest["url"],
            "imagery_inventory": INVENTORY_PUBLIC_PATH,
            **(
                {"baseline_product": inventory_aoi["baselineProductUrl"]}
                if inventory_aoi.get("baselineProductUrl")
                else {}
            ),
        },
        "layers": layers,
        "metrics": {
            "features": 0,
            "destroyed": 0,
            "damagedConfirmed": 0,
            "possibleDamage": 0,
            "vlmReviewed": 0,
        },
        "imagery": {
            "before": None,
            "after": {
                "url": earliest["url"],
                "sensor": earliest["sensor"],
                "acquisitionUtc": earliest["acquisitionUtc"],
                "bytes": earliest["bytes"],
                "source": "Copernicus EMSR884 post-event VHR optical COG",
                "license": earliest["license"],
                "coverage": f"Official EMSR884 AOI{number:02d} imagery footprint.",
                "limitations": (
                    "Imagery-only context. No official damage vector was produced. "
                    + (
                        "The source COG is linked for evidence access but is not loaded directly "
                        "on mobile because it exceeds the direct-raster budget."
                        if earliest["bytes"] > DIRECT_RASTER_MOBILE_MAX_BYTES
                        else "The source COG is within the direct-raster budget but may still be slow on constrained links."
                    )
                ),
            },
            "acquisitions": acquisitions,
            "note": (
                "All dated Copernicus image records for this AOI are listed under acquisitions. "
                "No pre-event comparison is claimed, and absence of a visible feature is not evidence of absence."
            ),
        },
    }


def new_regional_sar_aoi(inventory_aoi: dict[str, Any]) -> dict[str, Any]:
    number = int(inventory_aoi["aoiNumber"])
    acquisitions = [public_acquisition(record) for record in inventory_aoi["acquisitions"]]
    product_url = next(
        (
            acquisition["productDownloadUrl"]
            for acquisition in acquisitions
            if acquisition.get("productDownloadUrl")
        ),
        None,
    )
    identifier = aoi_id(number)
    ensure_empty_damage_package(number, str(inventory_aoi["name"]))
    damage_base = f"/data/aoi/{identifier}"
    downloads = {
        "csv": f"{damage_base}/damage.csv",
        "geojson": f"{damage_base}/damage.geojson",
        "kml": f"{damage_base}/damage.kml",
        "metadata": f"{damage_base}/source_metadata.json",
        "imagery_inventory": INVENTORY_PUBLIC_PATH,
    }
    if product_url:
        downloads["product_zip"] = product_url
    return {
        "id": identifier,
        "country": "Venezuela",
        "event": "EMSR884 Venezuela earthquake",
        "name": {
            "en": "AOI00 Central Coastal Venezuela - Regional Sentinel-1 context",
            "es": "AOI00 Venezuela centro-costera - Contexto regional Sentinel-1",
        },
        "status": "imagery-only",
        "source": (
            "Copernicus EMSR884 AOI00 GRM regional Sentinel-1 product. This SAR overview is "
            "context only and is not a building-, vehicle- or shelter-level optical record. "
            "No official damage counts are published from this catalog record."
        ),
        "bounds": inventory_aoi["bounds"],
        "center": inventory_aoi["center"],
        "downloads": downloads,
        "layers": {"damage": f"{damage_base}/damage.geojson"},
        "metrics": {
            "features": 0,
            "destroyed": 0,
            "damagedConfirmed": 0,
            "possibleDamage": 0,
            "vlmReviewed": 0,
        },
        "imagery": {
            "before": None,
            "after": None,
            "acquisitions": acquisitions,
            "note": (
                "The two AOI00 Sentinel-1 image records are official regional SAR context. "
                "Their derived viewer COG endpoints returned HTTP 403 at the inventory check, "
                "so the public catalog links the official product ZIP instead of claiming direct raster access."
            ),
        },
    }


def main() -> None:
    catalog = json.loads(CATALOG_PATH.read_text())
    inventory = json.loads(INVENTORY_PATH.read_text())
    inventory_by_number = {
        int(aoi["aoiNumber"]): aoi
        for aoi in inventory["aois"]
    }
    existing_by_id = {aoi["id"]: aoi for aoi in catalog["aois"]}

    for number in range(1, 13):
        identifier = aoi_id(number)
        existing = existing_by_id.get(identifier)
        if existing is not None:
            imagery = existing.setdefault("imagery", {})
            imagery["acquisitions"] = [
                public_acquisition(record)
                for record in inventory_by_number[number]["acquisitions"]
            ]
            existing.setdefault("downloads", {})["imagery_inventory"] = INVENTORY_PUBLIC_PATH
            continue
        existing_by_id[identifier] = new_local_optical_aoi(inventory_by_number[number])

    regional_id = aoi_id(0)
    if regional_id not in existing_by_id:
        existing_by_id[regional_id] = new_regional_sar_aoi(inventory_by_number[0])
    else:
        regional = existing_by_id[regional_id]
        regional["source"] = (
            "Copernicus EMSR884 AOI00 GRM regional Sentinel-1 product. This SAR overview is "
            "context only and is not a building-, vehicle- or shelter-level optical record. "
            "No official damage counts are published from this catalog record."
        )
        regional.setdefault("imagery", {})["acquisitions"] = [
            public_acquisition(record)
            for record in inventory_by_number[0]["acquisitions"]
        ]

    official_records = [
        aoi for aoi in existing_by_id.values()
        if aoi["id"].startswith("emsr884-")
    ]
    external_records = [
        aoi for aoi in catalog["aois"]
        if not aoi["id"].startswith("emsr884-")
    ]

    def official_sort_key(record: dict[str, Any]) -> tuple[int, int]:
        number = int(record["id"].split("-aoi", 1)[1][:2])
        monitor = 1 if "monitor" in record["id"] else 0
        return number, monitor

    catalog["aois"] = sorted(official_records, key=official_sort_key) + external_records
    catalog["updatedAt"] = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    catalog["imageryInventory"] = INVENTORY_PUBLIC_PATH
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "catalogAois": len(catalog["aois"]),
                "officialEmsRecords": len(official_records),
                "numberedEmsAois": len(
                    {
                        int(aoi["id"].split("-aoi", 1)[1][:2])
                        for aoi in official_records
                    }
                ),
                "newImageryOnlyAois": [
                    aoi_id(number)
                    for number in (0, 1, 4, 7, 9, 11)
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
