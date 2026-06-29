#!/usr/bin/env python3
"""Measure static data, bundle, and local asset pressure for the crisis map."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CATALOG = PUBLIC / "data" / "catalog.json"
DEFAULT_REPORT_JSON = ROOT / "ops" / "performance_audit" / "latest.json"
DEFAULT_REPORT_MD = ROOT / "ops" / "performance_audit" / "latest.md"
DEFAULT_AOI_ID = "emsr884-aoi12-caraballeda"
LOCAL_HEAVY_THRESHOLD = 5 * 1024 * 1024
LOCAL_AOI_CRITICAL_THRESHOLD = 50 * 1024 * 1024
LOCAL_PUBLIC_DATA_TARGET_BYTES = 125_000_000
LOCAL_TILES_TARGET_BYTES = 75_000_000
LOCAL_CHIPS_TARGET_BYTES = 40_000_000
TEXT_DATA_SUFFIXES = {".json", ".geojson", ".jsonl", ".csv", ".kml"}


def bytes_human(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def file_bytes(path: Path) -> int:
    return path.stat().st_size if path.exists() and path.is_file() else 0


def dir_stats(path: Path) -> dict[str, Any]:
    total = 0
    files = 0
    if path.exists():
        for root, _, names in os.walk(path):
            for name in names:
                item = Path(root) / name
                if item.is_file():
                    files += 1
                    total += item.stat().st_size
    return {"path": rel(path), "exists": path.exists(), "files": files, "bytes": total, "human": bytes_human(total)}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def public_path(value: str | None) -> Path | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme:
        return None
    if not value.startswith("/"):
        return None
    return PUBLIC / value.lstrip("/")


def source_summary(value: Any, limit: int = 110) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def walk_strings(value: Any, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((path, value))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(walk_strings(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else str(key)
            found.extend(walk_strings(item, child))
    return found


def count_geojson_features(path: Path) -> int | None:
    if not path.exists() or path.stat().st_size > 25 * 1024 * 1024:
        return None
    try:
        return len((read_json(path).get("features") or []))
    except Exception:
        return None


def count_jsonl_lines(path: Path) -> int | None:
    if not path.exists():
        return None
    try:
        return sum(1 for line in path.read_text().splitlines() if line.strip())
    except UnicodeDecodeError:
        return None


def top_files(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    files: list[Path] = []
    if path.exists():
        for root, _, names in os.walk(path):
            for name in names:
                item = Path(root) / name
                if item.is_file():
                    files.append(item)
    files.sort(key=lambda item: item.stat().st_size, reverse=True)
    return [{"path": rel(item), "bytes": item.stat().st_size, "human": bytes_human(item.stat().st_size)} for item in files[:limit]]


def catalog_local_ref_index(catalog: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    refs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for aoi in catalog.get("aois", []):
        aoi_id = str(aoi.get("id") or "")
        for catalog_path, value in walk_strings({"downloads": aoi.get("downloads", {}), "layers": aoi.get("layers", {}), "imagery": aoi.get("imagery", {})}):
            if any(token in value for token in ("{z}", "{x}", "{y}")):
                continue
            path = public_path(value)
            if path is None:
                continue
            refs[rel(path)].append({
                "aoi_id": aoi_id,
                "status": aoi.get("status"),
                "catalog_path": catalog_path,
            })
    return refs


def aoi_id_for_public_aoi_file(path: Path) -> str | None:
    try:
        parts = path.relative_to(PUBLIC / "data" / "aoi").parts
    except ValueError:
        return None
    return parts[0] if parts else None


def local_aoi_file_role(path: Path, refs: list[dict[str, Any]]) -> str:
    parts = set(path.parts)
    suffix = path.suffix.lower()
    if "reports" in parts or suffix == ".pdf":
        return "report"
    if any(str(ref.get("catalog_path", "")).startswith("layers.") for ref in refs):
        return "active-layer"
    if refs:
        return "catalog-download"
    return "local-aoi-file"


def large_local_aoi_files(catalog: dict[str, Any], threshold: int = LOCAL_HEAVY_THRESHOLD) -> list[dict[str, Any]]:
    aoi_by_id = {str(aoi.get("id") or ""): aoi for aoi in catalog.get("aois", [])}
    ref_index = catalog_local_ref_index(catalog)
    files: list[dict[str, Any]] = []
    aoi_root = PUBLIC / "data" / "aoi"
    if not aoi_root.exists():
        return files

    for path in sorted(item for item in aoi_root.rglob("*") if item.is_file()):
        size = path.stat().st_size
        if size < threshold:
            continue
        aoi_id = aoi_id_for_public_aoi_file(path)
        aoi = aoi_by_id.get(aoi_id or "", {})
        refs = ref_index.get(rel(path), [])
        files.append({
            "path": rel(path),
            "bytes": size,
            "human": bytes_human(size),
            "aoi_id": aoi_id,
            "status": aoi.get("status") or "uncataloged",
            "source": aoi.get("source"),
            "source_summary": source_summary(aoi.get("source")),
            "suffix": path.suffix.lower() or "<none>",
            "role": local_aoi_file_role(path, refs),
            "catalog_refs": sorted({str(ref.get("catalog_path")) for ref in refs if ref.get("catalog_path")}),
            "catalog_ref_count": len(refs),
            "is_external_prediction": aoi.get("status") == "external-prediction",
            "exceeds_critical_threshold": size >= LOCAL_AOI_CRITICAL_THRESHOLD,
        })
    files.sort(key=lambda item: item["bytes"], reverse=True)
    return files


def group_large_files_by_status(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for item in files:
        status = str(item.get("status") or "uncataloged")
        if status not in grouped:
            grouped[status] = {"status": status, "files": 0, "bytes": 0, "sources": set()}
        grouped[status]["files"] += 1
        grouped[status]["bytes"] += int(item.get("bytes") or 0)
        if item.get("source_summary"):
            grouped[status]["sources"].add(item["source_summary"])

    rows: list[dict[str, Any]] = []
    for item in grouped.values():
        rows.append({
            "status": item["status"],
            "files": item["files"],
            "bytes": item["bytes"],
            "human": bytes_human(item["bytes"]),
            "sources": sorted(item["sources"]),
        })
    rows.sort(key=lambda item: item["bytes"], reverse=True)
    return rows


def production_package_pressure(public_data: dict[str, Any], large_aoi: list[dict[str, Any]]) -> dict[str, Any]:
    data_bytes = int(public_data["data"]["bytes"])
    tiles_bytes = int(public_data["tiles"]["bytes"])
    chips_bytes = int(public_data["chips"]["bytes"])
    remote_excluded_bytes = tiles_bytes + chips_bytes
    non_remote_bytes = max(0, data_bytes - remote_excluded_bytes)
    unsafe_reasons: list[str] = []

    if data_bytes > LOCAL_PUBLIC_DATA_TARGET_BYTES:
        unsafe_reasons.append(
            f"public/data is {bytes_human(data_bytes)}, above the raw package target {bytes_human(LOCAL_PUBLIC_DATA_TARGET_BYTES)}"
        )
    if tiles_bytes > LOCAL_TILES_TARGET_BYTES:
        unsafe_reasons.append(
            f"public/data/tiles is {bytes_human(tiles_bytes)}, above the local tile target {bytes_human(LOCAL_TILES_TARGET_BYTES)}"
        )
    if chips_bytes > LOCAL_CHIPS_TARGET_BYTES:
        unsafe_reasons.append(
            f"public/data/chips is {bytes_human(chips_bytes)}, above the local chip target {bytes_human(LOCAL_CHIPS_TARGET_BYTES)}"
        )

    dangerous_files = [item for item in large_aoi if item["exceeds_critical_threshold"]]
    for item in dangerous_files:
        unsafe_reasons.append(f"{item['path']} is {item['human']}, above the single-file critical threshold")

    external_prediction_bytes = sum(int(item["bytes"]) for item in large_aoi if item["status"] == "external-prediction")
    report_bytes = sum(int(item["bytes"]) for item in large_aoi if item["role"] == "report")
    return {
        "raw_local_package_safe": not unsafe_reasons,
        "remote_asset_package_required": bool(unsafe_reasons),
        "unsafe_reasons": unsafe_reasons,
        "remote_excluded_bytes": remote_excluded_bytes,
        "remote_excluded_human": bytes_human(remote_excluded_bytes),
        "non_remote_public_data_bytes": non_remote_bytes,
        "non_remote_public_data_human": bytes_human(non_remote_bytes),
        "large_local_aoi_file_count": len(large_aoi),
        "large_local_aoi_bytes": sum(int(item["bytes"]) for item in large_aoi),
        "large_local_aoi_human": bytes_human(sum(int(item["bytes"]) for item in large_aoi)),
        "external_prediction_large_file_bytes": external_prediction_bytes,
        "external_prediction_large_file_human": bytes_human(external_prediction_bytes),
        "local_report_large_file_bytes": report_bytes,
        "local_report_large_file_human": bytes_human(report_bytes),
        "critical_large_file_count": len(dangerous_files),
    }


def bundle_stats() -> dict[str, Any]:
    next_dir = ROOT / ".next"
    static_dir = next_dir / "static"
    js_files = list(static_dir.rglob("*.js")) if static_dir.exists() else []
    css_files = list(static_dir.rglob("*.css")) if static_dir.exists() else []
    js_bytes = sum(path.stat().st_size for path in js_files)
    css_bytes = sum(path.stat().st_size for path in css_files)
    return {
        "build_present": next_dir.exists(),
        "js_files": len(js_files),
        "js_bytes": js_bytes,
        "js_human": bytes_human(js_bytes),
        "css_files": len(css_files),
        "css_bytes": css_bytes,
        "css_human": bytes_human(css_bytes),
        "next_dir": dir_stats(next_dir),
    }


def aoi_file_inventory(aoi: dict[str, Any]) -> dict[str, Any]:
    aoi_id = str(aoi.get("id"))
    aoi_dir = PUBLIC / "data" / "aoi" / aoi_id
    chips_dir = PUBLIC / "data" / "chips" / aoi_id
    tiles_dir = PUBLIC / "data" / "tiles" / aoi_id
    data_files: list[dict[str, Any]] = []
    suffix_bytes: dict[str, int] = defaultdict(int)
    suffix_files: dict[str, int] = defaultdict(int)

    if aoi_dir.exists():
        for path in sorted(item for item in aoi_dir.rglob("*") if item.is_file()):
            suffix = path.suffix.lower() or "<none>"
            size = path.stat().st_size
            suffix_bytes[suffix] += size
            suffix_files[suffix] += 1
            if suffix in TEXT_DATA_SUFFIXES or size >= LOCAL_HEAVY_THRESHOLD:
                data_files.append({"path": rel(path), "bytes": size, "human": bytes_human(size)})

    local_refs: list[dict[str, Any]] = []
    remote_refs: list[dict[str, Any]] = []
    for catalog_path, value in walk_strings({"downloads": aoi.get("downloads", {}), "layers": aoi.get("layers", {}), "imagery": aoi.get("imagery", {})}):
        parsed = urlparse(value)
        if parsed.scheme in {"http", "https"}:
            remote_refs.append({"catalog_path": catalog_path, "url": value, "host": parsed.netloc})
        elif value.startswith("/"):
            path = PUBLIC / value.lstrip("/")
            local_refs.append({
                "catalog_path": catalog_path,
                "path": value,
                "exists": path.exists() or any(token in value for token in ("{z}", "{x}", "{y}")),
                "bytes": file_bytes(path),
                "human": bytes_human(file_bytes(path)),
            })

    damage_path = public_path((aoi.get("layers") or {}).get("damage"))
    vlm_path = public_path((aoi.get("layers") or {}).get("vlm"))
    return {
        "id": aoi_id,
        "status": aoi.get("status"),
        "metrics_features": (aoi.get("metrics") or {}).get("features"),
        "aoi_dir": dir_stats(aoi_dir),
        "chips": dir_stats(chips_dir),
        "tiles": dir_stats(tiles_dir),
        "by_suffix": {
            suffix: {"files": suffix_files[suffix], "bytes": suffix_bytes[suffix], "human": bytes_human(suffix_bytes[suffix])}
            for suffix in sorted(suffix_bytes)
        },
        "data_files": data_files,
        "damage_geojson_features": count_geojson_features(damage_path) if damage_path else None,
        "vlm_jsonl_records": count_jsonl_lines(vlm_path) if vlm_path else None,
        "local_catalog_refs": local_refs,
        "remote_catalog_refs": remote_refs,
    }


def initial_load_estimate(catalog: dict[str, Any], aois: list[dict[str, Any]]) -> dict[str, Any]:
    default = next((aoi for aoi in catalog.get("aois", []) if aoi.get("id") == DEFAULT_AOI_ID), None)
    catalog_bytes = file_bytes(CATALOG)
    default_damage = public_path((default or {}).get("layers", {}).get("damage"))
    default_vlm = public_path((default or {}).get("layers", {}).get("vlm"))
    damage_bytes = file_bytes(default_damage) if default_damage else 0
    vlm_bytes = file_bytes(default_vlm) if default_vlm else 0
    non_default_damage = 0
    non_default_vlm = 0
    for aoi in catalog.get("aois", []):
        if aoi.get("id") == DEFAULT_AOI_ID:
            continue
        damage_path = public_path((aoi.get("layers") or {}).get("damage"))
        vlm_path = public_path((aoi.get("layers") or {}).get("vlm"))
        non_default_damage += file_bytes(damage_path) if damage_path else 0
        non_default_vlm += file_bytes(vlm_path) if vlm_path else 0
    return {
        "default_aoi_id": DEFAULT_AOI_ID,
        "aoi_list_bytes_before_active_data": catalog_bytes,
        "aoi_list_human": bytes_human(catalog_bytes),
        "default_damage_bytes": damage_bytes,
        "default_vlm_bytes": vlm_bytes,
        "default_metadata_and_vector_bytes": catalog_bytes + damage_bytes + vlm_bytes,
        "default_metadata_and_vector_human": bytes_human(catalog_bytes + damage_bytes + vlm_bytes),
        "non_default_damage_bytes_if_eager": non_default_damage,
        "non_default_vlm_bytes_if_eager": non_default_vlm,
        "non_default_data_human_if_eager": bytes_human(non_default_damage + non_default_vlm),
        "note": "Tile bytes are intentionally excluded because first visible tile count depends on viewport, zoom, CDN cache, and network.",
        "aoi_inventory_count": len(aois),
    }


def code_loading_scan() -> dict[str, Any]:
    source = ROOT / "src" / "components" / "OperationsConsole.tsx"
    text = source.read_text() if source.exists() else ""
    eager_patterns = [
        r"Promise\.all\s*\(\s*catalog\.aois",
        r"catalog\.aois\.map\s*\([^)]*fetch",
        r"for\s*\([^)]*of\s+catalog\.aois\)[\s\S]{0,240}fetch",
    ]
    findings = [pattern for pattern in eager_patterns if re.search(pattern, text)]
    return {
        "source": rel(source),
        "fetches_catalog": 'fetch("/data/catalog.json")' in text or "fetch('/data/catalog.json')" in text,
        "fetches_active_damage_layer": "fetch(aoi.layers.damage)" in text,
        "fetches_active_vlm_layer": "fetch(aoi.layers.vlm)" in text,
        "possible_eager_all_aoi_patterns": findings,
        "loads_all_aois_on_initial_render": bool(findings),
    }


def build_report() -> dict[str, Any]:
    catalog = read_json(CATALOG)
    aois = [aoi_file_inventory(aoi) for aoi in catalog.get("aois", [])]
    heavy_local = [item for item in top_files(PUBLIC / "data", limit=40) if item["bytes"] >= LOCAL_HEAVY_THRESHOLD]
    large_aoi = large_local_aoi_files(catalog)
    public_data = {
        "data": dir_stats(PUBLIC / "data"),
        "aoi": dir_stats(PUBLIC / "data" / "aoi"),
        "tiles": dir_stats(PUBLIC / "data" / "tiles"),
        "chips": dir_stats(PUBLIC / "data" / "chips"),
        "heavy_local_files": heavy_local,
        "large_local_aoi_files": large_aoi,
        "large_local_aoi_by_status": group_large_files_by_status(large_aoi),
    }
    return {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "catalog": {
            "path": rel(CATALOG),
            "bytes": file_bytes(CATALOG),
            "human": bytes_human(file_bytes(CATALOG)),
            "updated_at": catalog.get("updatedAt"),
            "aoi_count": len(catalog.get("aois", [])),
            "watchlist_count": len(catalog.get("watchlist", [])),
        },
        "bundle": bundle_stats(),
        "public_data": public_data,
        "production_package_pressure": production_package_pressure(public_data, large_aoi),
        "initial_load_estimate": initial_load_estimate(catalog, aois),
        "frontend_loading_scan": code_loading_scan(),
        "aois": aois,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Performance Audit Baseline",
        "",
        f"- Generated UTC: `{report['generated_utc']}`",
        f"- Catalog: `{report['catalog']['human']}` across `{report['catalog']['aoi_count']}` AOIs",
        f"- JS bundle in `.next/static`: `{report['bundle']['js_human']}` across `{report['bundle']['js_files']}` files",
        f"- CSS bundle in `.next/static`: `{report['bundle']['css_human']}` across `{report['bundle']['css_files']}` files",
        f"- `public/data`: `{report['public_data']['data']['human']}` across `{report['public_data']['data']['files']}` files",
        f"- `public/data/tiles`: `{report['public_data']['tiles']['human']}` across `{report['public_data']['tiles']['files']}` files",
        f"- `public/data/chips`: `{report['public_data']['chips']['human']}` across `{report['public_data']['chips']['files']}` files",
        f"- Raw local production package safe: `{report['production_package_pressure']['raw_local_package_safe']}`",
        f"- Remote asset package required: `{report['production_package_pressure']['remote_asset_package_required']}`",
        "",
        "## Initial Load Estimate",
        "",
        f"- AOI list before active AOI data: `{report['initial_load_estimate']['aoi_list_human']}`",
        f"- Default AOI vector/VLM plus catalog: `{report['initial_load_estimate']['default_metadata_and_vector_human']}`",
        f"- Non-default damage/VLM bytes that would load if eager: `{report['initial_load_estimate']['non_default_data_human_if_eager']}`",
        f"- Frontend eager-load pattern detected: `{report['frontend_loading_scan']['loads_all_aois_on_initial_render']}`",
        "",
        "## Production Package Pressure",
        "",
        f"- Local tiles/chips removable by remote-asset package: `{report['production_package_pressure']['remote_excluded_human']}`",
        f"- Public data remaining after remote tiles/chips are excluded: `{report['production_package_pressure']['non_remote_public_data_human']}`",
        f"- Local AOI files >= {bytes_human(LOCAL_HEAVY_THRESHOLD)}: `{report['production_package_pressure']['large_local_aoi_file_count']}` files / `{report['production_package_pressure']['large_local_aoi_human']}`",
        f"- External-prediction large local files: `{report['production_package_pressure']['external_prediction_large_file_human']}`",
        f"- Local report large files: `{report['production_package_pressure']['local_report_large_file_human']}`",
        "",
    ]
    if report["production_package_pressure"]["unsafe_reasons"]:
        lines.extend(["### Raw Local Package Unsafe Reasons", ""])
        lines.extend(f"- {reason}" for reason in report["production_package_pressure"]["unsafe_reasons"])
        lines.append("")

    if report["public_data"]["large_local_aoi_by_status"]:
        lines.extend([
            "### Large Local AOI Files By Status",
            "",
            "| Status | Files | Bytes | Sources |",
            "| --- | ---: | ---: | --- |",
        ])
        for item in report["public_data"]["large_local_aoi_by_status"]:
            sources = "; ".join(item["sources"][:2])
            lines.append(f"| `{item['status']}` | {item['files']} | {item['human']} | {sources or '-'} |")
        lines.append("")

    if report["public_data"]["large_local_aoi_files"]:
        lines.extend([
            "### Large Local AOI Files",
            "",
            "| File | AOI | Status | Role | Size | Catalog refs | Source |",
            "| --- | --- | --- | --- | ---: | --- | --- |",
        ])
        for item in report["public_data"]["large_local_aoi_files"][:20]:
            refs = ", ".join(item["catalog_refs"]) if item["catalog_refs"] else "-"
            lines.append(
                f"| `{item['path']}` | `{item['aoi_id'] or '-'}` | `{item['status']}` | "
                f"`{item['role']}` | {item['human']} | {refs} | {item['source_summary'] or '-'} |"
            )
        lines.append("")

    lines.extend([
        "## AOI Data Pressure",
        "",
        "| AOI | Status | AOI files | Tiles | Chips | GeoJSON features | VLM rows |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ])
    for aoi in report["aois"]:
        lines.append(
            f"| `{aoi['id']}` | `{aoi['status']}` | {aoi['aoi_dir']['human']} | "
            f"{aoi['tiles']['human']} | {aoi['chips']['human']} | "
            f"{aoi['damage_geojson_features'] if aoi['damage_geojson_features'] is not None else '-'} | "
            f"{aoi['vlm_jsonl_records'] if aoi['vlm_jsonl_records'] is not None else '-'} |"
        )
    if report["public_data"]["heavy_local_files"]:
        lines.extend(["", "## Largest Local Public Data Files", ""])
        for item in report["public_data"]["heavy_local_files"][:20]:
            lines.append(f"- `{item['path']}`: {item['human']}")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    args = parser.parse_args()

    report = build_report()
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2) + "\n")
    write_markdown(report, args.report_md)
    print(json.dumps({
        "result": "ok",
        "report_json": rel(args.report_json),
        "report_md": rel(args.report_md),
        "catalog_bytes": report["catalog"]["bytes"],
        "public_data_bytes": report["public_data"]["data"]["bytes"],
        "initial_default_bytes": report["initial_load_estimate"]["default_metadata_and_vector_bytes"],
        "eager_all_aoi_detected": report["frontend_loading_scan"]["loads_all_aois_on_initial_render"],
    }, indent=2))


if __name__ == "__main__":
    main()
