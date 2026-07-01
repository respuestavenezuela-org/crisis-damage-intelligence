#!/usr/bin/env python3
"""Ingest P0 EMSR884 source data into ops without changing public layers."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import urllib.request
from urllib.error import HTTPError, URLError
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "ops" / "data_acquisition_plan"
PRODUCT_DIR = OUT / "official_products"
API_URL = "https://rapidmapping.emergency.copernicus.eu/backend/dashboard-api/public-activations/?code=EMSR884"


def utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def fetch_json(url: str) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "respuesta-venezuela-data-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def clean_filename(name: str) -> str:
    name = name.rsplit("/", 1)[-1]
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)


def activation(data: dict[str, Any]) -> dict[str, Any]:
    results = data.get("results") or []
    if not results:
        raise SystemExit("No EMSR884 activation returned by Copernicus API")
    return results[0]


def product_key(aoi: dict[str, Any], product: dict[str, Any]) -> str:
    mon = f"_MONIT{int(product.get('monitoringNumber') or 0):02d}" if product.get("monitoring") else ""
    version = (product.get("version") or {}).get("number")
    return f"AOI{int(aoi.get('number')):02d}_{product.get('type')}{mon}_v{version}"


def extract_manifests(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    act = activation(data)
    products: list[dict[str, Any]] = []
    images: list[dict[str, Any]] = []
    layers: list[dict[str, Any]] = []
    for aoi in act.get("aois") or []:
        for product in aoi.get("products") or []:
            version = product.get("version") or {}
            key = product_key(aoi, product)
            row = {
                "checked_at": act.get("_checked_at", ""),
                "activation_code": act.get("code"),
                "activation_name": act.get("name"),
                "activation_closed": act.get("closed"),
                "aoi_number": aoi.get("number"),
                "aoi_name": aoi.get("name"),
                "product_key": key,
                "product_id": product.get("id"),
                "product_type": product.get("type"),
                "monitoring": product.get("monitoring"),
                "monitoring_number": product.get("monitoringNumber"),
                "feasible": product.get("feasible"),
                "version_number": version.get("number"),
                "status_code": version.get("statusCode"),
                "delivery_time": version.get("deliveryTime"),
                "version_reason": " ".join((version.get("reason") or "").split()),
                "expected_delivery": product.get("expectedDelivery"),
                "download_path": product.get("downloadPath") or "",
                "download_filename": clean_filename(product.get("downloadPath") or ""),
                "maps_count": product.get("mapsCount"),
                "image_count": len(product.get("images") or []),
                "layer_count": len(product.get("layers") or []),
            }
            products.append(row)
            for image in product.get("images") or []:
                images.append(
                    {
                        **{key2: row[key2] for key2 in ("checked_at", "activation_code", "aoi_number", "aoi_name", "product_key", "product_type", "version_number", "status_code")},
                        "image_uuid": image.get("uuid"),
                        "image_new": image.get("new"),
                        "sensor_type": image.get("sensorType"),
                        "sensor_name": image.get("sensorName"),
                        "resolution_class": image.get("resolutionClass"),
                        "acquisition_time": image.get("acquisitionTime"),
                        "file_name": image.get("fileName"),
                    }
                )
            for layer in product.get("layers") or []:
                layers.append(
                    {
                        **{key2: row[key2] for key2 in ("checked_at", "activation_code", "aoi_number", "aoi_name", "product_key", "product_type", "version_number", "status_code")},
                        "layer_name": layer.get("name"),
                        "layer_format": layer.get("format"),
                        "sld_url": layer.get("sld"),
                        "json_url": layer.get("json"),
                    }
                )
    return products, images, layers


def download(url: str, dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 0:
        return
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": "respuesta-venezuela-data-ingest/1.0"})
    with urllib.request.urlopen(req, timeout=300) as resp, tmp.open("wb") as out:
        shutil.copyfileobj(resp, out)
    tmp.replace(dst)


def table_exists(gpkg: Path, table: str) -> bool:
    con = sqlite3.connect(gpkg)
    try:
        row = con.execute("select 1 from sqlite_master where type in ('table','view') and name = ?", (table,)).fetchone()
    finally:
        con.close()
    return row is not None


def table_row_count(gpkg: Path, table: str) -> int | None:
    if not table_exists(gpkg, table):
        return None
    con = sqlite3.connect(gpkg)
    try:
        return int(con.execute(f'select count(*) from "{table}"').fetchone()[0])
    finally:
        con.close()


def gpkg_layers(gpkg: Path) -> list[str]:
    con = sqlite3.connect(gpkg)
    try:
        rows = con.execute("select table_name from gpkg_contents order by table_name").fetchall()
    finally:
        con.close()
    return [row[0] for row in rows]


def table_columns(gpkg: Path, table: str) -> set[str]:
    if not table_exists(gpkg, table):
        return set()
    con = sqlite3.connect(gpkg)
    try:
        rows = con.execute(f'pragma table_info("{table}")').fetchall()
    finally:
        con.close()
    return {row[1] for row in rows}


def damage_counts(gpkg: Path, table: str) -> dict[str, int]:
    cols = table_columns(gpkg, table)
    if "damage_gra" not in cols:
        return {}
    con = sqlite3.connect(gpkg)
    try:
        rows = con.execute(f'select damage_gra, count(*) from "{table}" group by damage_gra order by damage_gra').fetchall()
    finally:
        con.close()
    return {str(key): int(value) for key, value in rows}


def product_folder(product_row: dict[str, Any]) -> str:
    product_type = product_row.get("product_type")
    if product_row.get("monitoring") in (True, "True", "true", "1", 1):
        return f"{product_type}_MONIT{int(product_row.get('monitoring_number') or 0):02d}"
    return f"{product_type}_PRODUCT"


def cog_url(image_row: dict[str, Any], product_rows_by_key: dict[str, dict[str, Any]]) -> str:
    product = product_rows_by_key[image_row["product_key"]]
    file_name = image_row.get("file_name") or ""
    if file_name.lower().endswith(".tif"):
        file_name = file_name[:-4] + "_cog.tif"
    return f"https://rapidmapping-viewer.s3.eu-west-1.amazonaws.com/EMSR884/AOI{int(image_row['aoi_number']):02d}/{product_folder(product)}/{file_name}"


def validate_url(url: str) -> dict[str, Any]:
    headers = {"User-Agent": "respuesta-venezuela-data-ingest/1.0"}
    result: dict[str, Any] = {
        "cog_url": url,
        "http_status": "",
        "content_type": "",
        "content_length": "",
        "accept_ranges": "",
        "range_status": "",
        "range_ok": False,
        "error": "",
    }
    try:
        req = urllib.request.Request(url, method="HEAD", headers=headers)
        with urllib.request.urlopen(req, timeout=30) as resp:
            result["http_status"] = resp.status
            result["content_type"] = resp.headers.get("Content-Type", "")
            result["content_length"] = resp.headers.get("Content-Length", "")
            result["accept_ranges"] = resp.headers.get("Accept-Ranges", "")
    except (HTTPError, URLError, TimeoutError) as exc:
        result["error"] = str(exc)
    try:
        req = urllib.request.Request(url, headers={**headers, "Range": "bytes=0-0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result["range_status"] = resp.status
            result["range_ok"] = resp.status in (200, 206)
            if not result["content_type"]:
                result["content_type"] = resp.headers.get("Content-Type", "")
            if not result["accept_ranges"]:
                result["accept_ranges"] = resp.headers.get("Accept-Ranges", "")
            if not result["content_length"]:
                result["content_length"] = resp.headers.get("Content-Length", "")
    except (HTTPError, URLError, TimeoutError) as exc:
        if not result["error"]:
            result["error"] = str(exc)
    return result


def ogr_layer_summary(gpkg: Path, layer: str) -> dict[str, str]:
    try:
        out = subprocess.check_output(["ogrinfo", "-ro", "-so", str(gpkg), layer], text=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        return {"ogr_error": exc.output.strip()[:500]}
    summary: dict[str, str] = {}
    for line in out.splitlines():
        if line.startswith("Geometry:"):
            summary["geometry"] = line.split(":", 1)[1].strip()
        elif line.startswith("Feature Count:"):
            summary["feature_count"] = line.split(":", 1)[1].strip()
        elif line.startswith("Extent:"):
            summary["extent"] = line.split(":", 1)[1].strip()
        elif line.startswith("Layer SRS WKT:"):
            summary["srs"] = "present"
    return summary


def inspect_zip(zip_path: Path, product_row: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    zip_rows: list[dict[str, Any]] = []
    layer_rows: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        zip_rows.append(
            {
                "product_key": product_row["product_key"],
                "download_filename": product_row["download_filename"],
                "local_path": str(zip_path.relative_to(ROOT)),
                "bytes": zip_path.stat().st_size,
                "sha256": sha256(zip_path),
                "member_count": len(names),
                "gpkg_count": sum(1 for name in names if name.lower().endswith(".gpkg")),
                "pdf_count": sum(1 for name in names if name.lower().endswith(".pdf")),
                "xlsx_count": sum(1 for name in names if name.lower().endswith(".xlsx")),
            }
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for member in names:
                if not member.lower().endswith(".gpkg"):
                    continue
                zf.extract(member, tmp)
                gpkg = tmp / member
                for layer in gpkg_layers(gpkg):
                    ogr = ogr_layer_summary(gpkg, layer)
                    counts = damage_counts(gpkg, layer)
                    layer_rows.append(
                        {
                            "product_key": product_row["product_key"],
                            "download_filename": product_row["download_filename"],
                            "gpkg_member": member,
                            "layer_name": layer,
                            "geometry": ogr.get("geometry", ""),
                            "feature_count": ogr.get("feature_count", ""),
                            "sqlite_row_count": table_row_count(gpkg, layer),
                            "extent": ogr.get("extent", ""),
                            "damage_counts_json": json.dumps(counts, sort_keys=True, separators=(",", ":")),
                            "ogr_error": ogr.get("ogr_error", ""),
                        }
                    )
    return zip_rows, layer_rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    PRODUCT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()

    data = fetch_json(API_URL)
    act = activation(data)
    act["_checked_at"] = stamp
    data["_checked_at"] = stamp

    raw_path = OUT / f"emsr884_live_products_{stamp}.json"
    latest_raw = OUT / "emsr884_live_products_latest.json"
    raw_text = json.dumps(data, ensure_ascii=True, indent=2) + "\n"
    raw_path.write_text(raw_text)
    latest_raw.write_text(raw_text)

    products, images, layers = extract_manifests(data)
    products_by_key = {row["product_key"]: row for row in products}
    write_csv(
        OUT / "emsr884_product_manifest.csv",
        products,
        [
            "checked_at",
            "activation_code",
            "activation_name",
            "activation_closed",
            "aoi_number",
            "aoi_name",
            "product_key",
            "product_id",
            "product_type",
            "monitoring",
            "monitoring_number",
            "feasible",
            "version_number",
            "status_code",
            "delivery_time",
            "version_reason",
            "expected_delivery",
            "download_path",
            "download_filename",
            "maps_count",
            "image_count",
            "layer_count",
        ],
    )
    write_csv(
        OUT / "emsr884_product_images.csv",
        images,
        [
            "checked_at",
            "activation_code",
            "aoi_number",
            "aoi_name",
            "product_key",
            "product_type",
            "version_number",
            "status_code",
            "image_uuid",
            "image_new",
            "sensor_type",
            "sensor_name",
            "resolution_class",
            "acquisition_time",
            "file_name",
        ],
    )
    imagery_rows: list[dict[str, Any]] = []
    for image in images:
        url = cog_url(image, products_by_key)
        validation = validate_url(url)
        imagery_rows.append(
            {
                **image,
                **validation,
                "official_status": "official_ems" if image.get("status_code") == "F" else "official_ems_imagery_for_not_produced_aoi",
                "should_use_for_building_vlm": "conditional" if image.get("sensor_type") == "optical" else "no",
                "use_case": "post_event_optical_chip_source" if image.get("sensor_type") == "optical" else "sar_context_only",
            }
        )
    write_csv(
        OUT / "official_imagery_manifest.csv",
        imagery_rows,
        [
            "checked_at",
            "activation_code",
            "aoi_number",
            "aoi_name",
            "product_key",
            "product_type",
            "version_number",
            "status_code",
            "image_uuid",
            "image_new",
            "sensor_type",
            "sensor_name",
            "resolution_class",
            "acquisition_time",
            "file_name",
            "cog_url",
            "http_status",
            "content_type",
            "content_length",
            "accept_ranges",
            "range_status",
            "range_ok",
            "official_status",
            "should_use_for_building_vlm",
            "use_case",
            "error",
        ],
    )
    write_csv(
        OUT / "emsr884_product_layers.csv",
        layers,
        [
            "checked_at",
            "activation_code",
            "aoi_number",
            "aoi_name",
            "product_key",
            "product_type",
            "version_number",
            "status_code",
            "layer_name",
            "layer_format",
            "sld_url",
            "json_url",
        ],
    )

    downloaded: list[dict[str, Any]] = []
    layer_inventory: list[dict[str, Any]] = []
    for product in products:
        url = product.get("download_path") or ""
        if not url:
            continue
        filename = product["download_filename"] or clean_filename(url)
        dst = PRODUCT_DIR / filename
        print(f"download/check {product['product_key']} {filename}", flush=True)
        download(url, dst)
        zip_rows, layer_rows = inspect_zip(dst, product)
        downloaded.extend(zip_rows)
        layer_inventory.extend(layer_rows)

    write_csv(
        OUT / "official_product_zip_manifest.csv",
        downloaded,
        ["product_key", "download_filename", "local_path", "bytes", "sha256", "member_count", "gpkg_count", "pdf_count", "xlsx_count"],
    )
    write_csv(
        OUT / "official_product_layer_inventory.csv",
        layer_inventory,
        ["product_key", "download_filename", "gpkg_member", "layer_name", "geometry", "feature_count", "sqlite_row_count", "extent", "damage_counts_json", "ogr_error"],
    )

    summary = {
        "checked_at": stamp,
        "activation_code": act.get("code"),
        "activation_closed": act.get("closed"),
        "aoi_count": len(act.get("aois") or []),
        "product_count": len(products),
        "downloadable_product_count": len(downloaded),
        "image_count": len(images),
        "layer_count": len(layers),
        "raw_snapshot": str(raw_path.relative_to(ROOT)),
        "product_manifest": "ops/data_acquisition_plan/emsr884_product_manifest.csv",
        "image_manifest": "ops/data_acquisition_plan/emsr884_product_images.csv",
        "official_imagery_manifest": "ops/data_acquisition_plan/official_imagery_manifest.csv",
        "layer_manifest": "ops/data_acquisition_plan/emsr884_product_layers.csv",
        "zip_manifest": "ops/data_acquisition_plan/official_product_zip_manifest.csv",
        "zip_layer_inventory": "ops/data_acquisition_plan/official_product_layer_inventory.csv",
    }
    (OUT / "emsr884_ingest_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
