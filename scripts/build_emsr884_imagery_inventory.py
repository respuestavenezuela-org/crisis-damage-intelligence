#!/usr/bin/env python3
"""Build a public, source-backed EMSR884 imagery acquisition inventory.

The Copernicus dashboard API is the source for AOI, product, sensor and
acquisition metadata. Viewer COGs are validated with HEAD requests, but are not
downloaded. Repeated product records for the same AOI/sensor/time remain in the
ledger and share a ``distinctAcquisitionId`` so readers can distinguish product
records from physical acquisition events.
"""

from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
API_URL = "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884"
PUBLIC_JSON = ROOT / "public" / "data" / "imagery" / "emsr884-acquisitions.json"
OPS_CSV = ROOT / "ops" / "data_acquisition_plan" / "emsr884_imagery_inventory.csv"
USER_AGENT = "respuesta-venezuela-imagery-inventory/1.0"
COPERNICUS_LICENSE = "Copernicus EMS public product terms"


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def bounds_from_wkt(wkt: str) -> list[list[float]]:
    coordinates = [
        (float(lon), float(lat))
        for lon, lat in re.findall(r"(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)", wkt)
    ]
    if not coordinates:
        raise ValueError(f"AOI extent does not contain coordinates: {wkt[:80]}")
    lons = [lon for lon, _ in coordinates]
    lats = [lat for _, lat in coordinates]
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def center(bounds: list[list[float]]) -> list[float]:
    return [
        (bounds[0][0] + bounds[1][0]) / 2,
        (bounds[0][1] + bounds[1][1]) / 2,
    ]


def product_folder(product: dict[str, Any]) -> str:
    if product.get("monitoring"):
        return f"{product['type']}_MONIT{int(product.get('monitoringNumber') or 0):02d}"
    return f"{product['type']}_PRODUCT"


def cog_url(aoi_number: int, product: dict[str, Any], image: dict[str, Any]) -> str:
    filename = str(image.get("fileName") or "")
    if filename.lower().endswith(".tif"):
        filename = f"{filename[:-4]}_cog.tif"
    return (
        "https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/"
        f"EMSR884/AOI{aoi_number:02d}/{product_folder(product)}/{filename}"
    )


def acquisition_id(aoi_number: int, image: dict[str, Any]) -> str:
    raw = "|".join(
        (
            f"AOI{aoi_number:02d}",
            str(image.get("sensorName") or ""),
            str(image.get("sensorType") or ""),
            str(image.get("acquisitionTime") or ""),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def validate_cog(url: str) -> dict[str, Any]:
    try:
        request = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": USER_AGENT},
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            return {
                "httpStatus": response.status,
                "publiclyReadable": response.status == 200,
                "bytes": int(response.headers.get("Content-Length") or 0),
                "contentType": response.headers.get("Content-Type") or "",
                "acceptRanges": response.headers.get("Accept-Ranges") or "",
            }
    except urllib.error.HTTPError as error:
        return {
            "httpStatus": error.code,
            "publiclyReadable": False,
            "bytes": 0,
            "contentType": error.headers.get("Content-Type") or "",
            "acceptRanges": error.headers.get("Accept-Ranges") or "",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {
            "httpStatus": None,
            "publiclyReadable": False,
            "bytes": 0,
            "contentType": "",
            "acceptRanges": "",
            "validationError": type(error).__name__,
        }


def main() -> None:
    checked_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    activation = fetch_json(API_URL)["results"][0]
    aois: list[dict[str, Any]] = []
    flat_records: list[dict[str, Any]] = []

    for aoi in sorted(activation.get("aois") or [], key=lambda item: int(item["number"])):
        aoi_number = int(aoi["number"])
        aoi_bounds = bounds_from_wkt(aoi["extent"])
        acquisitions: list[dict[str, Any]] = []
        for product in aoi.get("products") or []:
            version = product.get("version") or {}
            folder = product_folder(product)
            for image in product.get("images") or []:
                url = cog_url(aoi_number, product, image)
                record = {
                    "recordId": f"EMSR884-AOI{aoi_number:02d}-{folder}-{image.get('uuid')}",
                    "distinctAcquisitionId": acquisition_id(aoi_number, image),
                    "aoiNumber": aoi_number,
                    "aoiCode": f"AOI{aoi_number:02d}",
                    "aoiName": aoi.get("name"),
                    "coverageClass": "regional-sar" if image.get("sensorType") == "sar" else "local-vhr-optical",
                    "product": folder,
                    "productType": product.get("type"),
                    "monitoringNumber": product.get("monitoringNumber") if product.get("monitoring") else None,
                    "productStatusCode": version.get("statusCode"),
                    "productDeliveredAt": version.get("deliveryTime"),
                    "productDownloadUrl": product.get("downloadPath") or None,
                    "sensorType": image.get("sensorType"),
                    "sensor": image.get("sensorName"),
                    "resolutionClass": image.get("resolutionClass"),
                    "acquisitionUtc": image.get("acquisitionTime"),
                    "cogUrl": url,
                    "source": "Copernicus EMSR884 public dashboard API and Rapid Mapping Viewer",
                    "license": COPERNICUS_LICENSE,
                    "role": (
                        "Regional SAR context; not a direct replacement for optical building or vehicle inspection."
                        if image.get("sensorType") == "sar"
                        else "Post-event VHR optical context; official EMS vectors remain the damage source of record."
                    ),
                }
                acquisitions.append(record)
                flat_records.append(record)

        aois.append(
            {
                "aoiNumber": aoi_number,
                "aoiCode": f"AOI{aoi_number:02d}",
                "name": aoi.get("name"),
                "coverageClass": "regional-sar" if aoi_number == 0 else "local-vhr-optical",
                "bounds": aoi_bounds,
                "center": center(aoi_bounds),
                "baselineProductUrl": aoi.get("blpPath") or None,
                "acquisitions": acquisitions,
            }
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        validations = list(executor.map(lambda row: validate_cog(row["cogUrl"]), flat_records))
    for record, validation in zip(flat_records, validations, strict=True):
        record["access"] = validation

    distinct_ids = {record["distinctAcquisitionId"] for record in flat_records}
    optical = [record for record in flat_records if record["sensorType"] == "optical"]
    sar = [record for record in flat_records if record["sensorType"] == "sar"]
    readable_optical = [record for record in optical if record["access"]["publiclyReadable"]]
    payload = {
        "version": 1,
        "checkedAt": checked_at,
        "activation": {
            "code": activation.get("code"),
            "name": activation.get("name"),
            "closed": activation.get("closed"),
            "eventTimeAsPublished": activation.get("eventTime"),
            "activationTimeAsPublished": activation.get("activationTime"),
            "sourceUrl": API_URL,
            "reportUrl": activation.get("reportLink"),
            "allProductsUrl": activation.get("productsPath"),
        },
        "summary": {
            "officialAoiRecords": len(aois),
            "localOpticalAois": len({record["aoiNumber"] for record in optical}),
            "regionalSarAois": len({record["aoiNumber"] for record in sar}),
            "productImageRecords": len(flat_records),
            "distinctAcquisitionEvents": len(distinct_ids),
            "opticalProductImageRecords": len(optical),
            "distinctOpticalAcquisitionEvents": len(
                {record["distinctAcquisitionId"] for record in optical}
            ),
            "publiclyReadableOpticalCogRecords": len(readable_optical),
            "sarProductImageRecords": len(sar),
            "publiclyReadableSarCogRecords": len(
                [record for record in sar if record["access"]["publiclyReadable"]]
            ),
            "readableOpticalBytes": sum(record["access"]["bytes"] for record in readable_optical),
        },
        "countingRules": {
            "aoi": "A numbered Copernicus EMSR884 area of interest. AOI00 is regional SAR context; AOI01-AOI12 are local VHR optical areas.",
            "productImageRecord": "One image entry attached to one Copernicus product version. The same physical acquisition can appear in more than one product.",
            "distinctAcquisitionEvent": "Deduplicated by AOI, sensor name, sensor type and acquisition timestamp.",
            "availability": "A viewer COG is counted as publicly readable only when its URL returned HTTP 200 at checkedAt.",
            "absence": "Missing coverage or an unreadable viewer endpoint is not evidence that an event, object or response activity did not occur.",
        },
        "aois": aois,
    }

    public_payload = json.loads(json.dumps(payload))
    for public_aoi in public_payload["aois"]:
        for public_record in public_aoi["acquisitions"]:
            if not public_record["access"]["publiclyReadable"]:
                public_record["cogUrl"] = None
                public_record["access"]["note"] = (
                    "The derived viewer COG was not publicly readable at checkedAt. "
                    "Use the official product download URL where available."
                )

    PUBLIC_JSON.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_JSON.write_text(json.dumps(public_payload, ensure_ascii=False, indent=2) + "\n")

    OPS_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "aoiCode",
        "aoiName",
        "coverageClass",
        "product",
        "productStatusCode",
        "sensorType",
        "sensor",
        "resolutionClass",
        "acquisitionUtc",
        "distinctAcquisitionId",
        "cogUrl",
        "httpStatus",
        "publiclyReadable",
        "bytes",
        "acceptRanges",
        "productDownloadUrl",
    ]
    with OPS_CSV.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for record in flat_records:
            writer.writerow(
                {
                    **{key: record.get(key) for key in fieldnames},
                    **{key: value for key, value in record["access"].items() if key in fieldnames},
                }
            )

    print(json.dumps(payload["summary"], indent=2))
    print(f"public={PUBLIC_JSON.relative_to(ROOT)}")
    print(f"ops={OPS_CSV.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
