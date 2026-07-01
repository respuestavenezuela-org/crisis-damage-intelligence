#!/usr/bin/env python3
"""Download and profile external prediction GPKGs as triage sources only."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sqlite3
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE_INVENTORY = ROOT / "ops" / "data_acquisition_plan" / "source_inventory.csv"
OUT_DIR = ROOT / "ops" / "data_acquisition_plan"
DOWNLOAD_DIR = OUT_DIR / "external_prediction_sources"
INVENTORY_CSV = OUT_DIR / "external_prediction_gpkg_inventory.csv"
FIELDS_CSV = OUT_DIR / "external_prediction_field_profiles.csv"
SUMMARY_JSON = OUT_DIR / "external_prediction_ingest_summary.json"
USER_AGENT = "respuesta-venezuela-external-prediction-ingest/1.0"


def clean_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name.rsplit("/", 1)[-1])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dst: Path) -> None:
    if dst.exists() and dst.stat().st_size > 0:
        return
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=300) as resp, tmp.open("wb") as out:
        shutil.copyfileobj(resp, out)
    tmp.replace(dst)


def quote_ident(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def source_rows() -> list[dict[str, str]]:
    with SOURCE_INVENTORY.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if row.get("data_type") == "external_prediction" and row.get("url", "").lower().endswith(".gpkg")]


def gpkg_layers(path: Path) -> list[dict[str, Any]]:
    con = sqlite3.connect(path)
    try:
        rows = con.execute(
            """
            select c.table_name, c.data_type, c.min_x, c.min_y, c.max_x, c.max_y,
                   g.column_name, g.geometry_type_name, g.srs_id
            from gpkg_contents c
            left join gpkg_geometry_columns g on c.table_name = g.table_name
            order by c.table_name
            """
        ).fetchall()
    finally:
        con.close()
    return [
        {
            "layer_name": row[0],
            "data_type": row[1],
            "min_x": row[2],
            "min_y": row[3],
            "max_x": row[4],
            "max_y": row[5],
            "geometry_column": row[6],
            "geometry_type": row[7],
            "srs_id": row[8],
        }
        for row in rows
    ]


def table_columns(con: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    rows = con.execute(f"pragma table_info({quote_ident(table)})").fetchall()
    return [{"name": row[1], "type": row[2]} for row in rows]


def row_count(con: sqlite3.Connection, table: str) -> int:
    return int(con.execute(f"select count(*) from {quote_ident(table)}").fetchone()[0])


def candidate_prediction_fields(columns: list[dict[str, Any]]) -> list[str]:
    tokens = ("damage", "damaged", "pct", "score", "conf", "prob", "model", "class")
    fields: list[str] = []
    for col in columns:
        name = col["name"]
        lower = name.lower()
        if any(token in lower for token in tokens):
            fields.append(name)
    return fields


def field_profile(con: sqlite3.Connection, table: str, field: str) -> dict[str, Any]:
    qtable = quote_ident(table)
    qfield = quote_ident(field)
    non_null = con.execute(f"select count(*) from {qtable} where {qfield} is not null").fetchone()[0]
    distinct = con.execute(f"select count(distinct {qfield}) from {qtable} where {qfield} is not null").fetchone()[0]
    minmax = con.execute(f"select min({qfield}), max({qfield}) from {qtable} where {qfield} is not null").fetchone()
    top = con.execute(f"select {qfield}, count(*) as n from {qtable} where {qfield} is not null group by {qfield} order by n desc limit 8").fetchall()
    return {
        "field_name": field,
        "non_null": int(non_null),
        "distinct_count": int(distinct),
        "min": minmax[0],
        "max": minmax[1],
        "top_values_json": json.dumps([{str(value): int(count)} for value, count in top], separators=(",", ":")),
    }


def damaged_count(con: sqlite3.Connection, table: str, fields: list[str]) -> str:
    if "damaged" in fields:
        try:
            return str(con.execute(f"select count(*) from {quote_ident(table)} where {quote_ident('damaged')} = 1").fetchone()[0])
        except sqlite3.Error:
            return ""
    return ""


def high_pct_count(con: sqlite3.Connection, table: str, fields: list[str]) -> str:
    pct_fields = [field for field in fields if "pct" in field.lower()]
    if not pct_fields:
        return ""
    clauses = [f"{quote_ident(field)} >= 0.5" for field in pct_fields]
    try:
        return str(con.execute(f"select count(*) from {quote_ident(table)} where {' or '.join(clauses)}").fetchone()[0])
    except sqlite3.Error:
        return ""


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def main() -> int:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    inventory_rows: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    downloaded = []

    for source in source_rows():
        url = source["url"]
        dst = DOWNLOAD_DIR / clean_filename(url)
        download(url, dst)
        downloaded.append(dst)
        con = sqlite3.connect(dst)
        try:
            for layer in gpkg_layers(dst):
                table = layer["layer_name"]
                columns = table_columns(con, table)
                fields = candidate_prediction_fields(columns)
                count = row_count(con, table)
                inventory_rows.append(
                    {
                        "source_name": source.get("source_name", ""),
                        "url": url,
                        "local_path": str(dst.relative_to(ROOT)),
                        "bytes": dst.stat().st_size,
                        "sha256": sha256(dst),
                        "layer_name": table,
                        "row_count": count,
                        "geometry_column": layer.get("geometry_column", ""),
                        "geometry_type": layer.get("geometry_type", ""),
                        "srs_id": layer.get("srs_id", ""),
                        "bbox_json": json.dumps([layer.get("min_x"), layer.get("min_y"), layer.get("max_x"), layer.get("max_y")], separators=(",", ":")),
                        "columns_json": json.dumps(columns, separators=(",", ":")),
                        "prediction_fields_json": json.dumps(fields, separators=(",", ":")),
                        "damaged_eq_1_count": damaged_count(con, table, fields),
                        "damage_pct_ge_0_5_count": high_pct_count(con, table, fields),
                        "official_status": "external_prediction_triage_only",
                    }
                )
                for field in fields:
                    profile = field_profile(con, table, field)
                    field_rows.append(
                        {
                            "source_name": source.get("source_name", ""),
                            "layer_name": table,
                            **profile,
                        }
                    )
        finally:
            con.close()

    write_csv(
        INVENTORY_CSV,
        inventory_rows,
        [
            "source_name",
            "url",
            "local_path",
            "bytes",
            "sha256",
            "layer_name",
            "row_count",
            "geometry_column",
            "geometry_type",
            "srs_id",
            "bbox_json",
            "columns_json",
            "prediction_fields_json",
            "damaged_eq_1_count",
            "damage_pct_ge_0_5_count",
            "official_status",
        ],
    )
    write_csv(
        FIELDS_CSV,
        field_rows,
        ["source_name", "layer_name", "field_name", "non_null", "distinct_count", "min", "max", "top_values_json"],
    )
    summary = {
        "downloaded_gpkg_count": len(downloaded),
        "total_downloaded_bytes": sum(path.stat().st_size for path in downloaded),
        "layer_count": len(inventory_rows),
        "field_profile_count": len(field_rows),
        "inventory_csv": str(INVENTORY_CSV.relative_to(ROOT)),
        "field_profiles_csv": str(FIELDS_CSV.relative_to(ROOT)),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
