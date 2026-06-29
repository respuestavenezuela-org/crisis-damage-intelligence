#!/usr/bin/env python3
"""Validate first-stage mobile performance budgets from the asset audit."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import audit_asset_budget


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = ROOT / "ops" / "performance_audit" / "mobile_budget.md"

CATALOG_MAX_BYTES = 200_000
INITIAL_AOI_LIST_MAX_BYTES = 250_000
DEFAULT_AOI_VECTOR_MAX_BYTES = 2_000_000
LOCAL_PUBLIC_DATA_TARGET_BYTES = 125_000_000
LOCAL_TILES_TARGET_BYTES = 75_000_000
LOCAL_CHIPS_TARGET_BYTES = 40_000_000
LOCAL_AOI_CRITICAL_FILE_BYTES = 50 * 1024 * 1024
REMOTE_PACKAGE_REMAINING_PUBLIC_DATA_TARGET_BYTES = 75_000_000


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def check_budget(report: dict, strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    catalog_bytes = int(report["catalog"]["bytes"])
    initial_bytes = int(report["initial_load_estimate"]["aoi_list_bytes_before_active_data"])
    default_bytes = int(report["initial_load_estimate"]["default_metadata_and_vector_bytes"])
    public_data_bytes = int(report["public_data"]["data"]["bytes"])
    tiles_bytes = int(report["public_data"]["tiles"]["bytes"])
    chips_bytes = int(report["public_data"]["chips"]["bytes"])
    package_pressure = report.get("production_package_pressure") or {}
    large_aoi_files = report.get("public_data", {}).get("large_local_aoi_files") or []

    if catalog_bytes > CATALOG_MAX_BYTES:
        errors.append(f"catalog.json is {catalog_bytes} bytes; budget is {CATALOG_MAX_BYTES}")
    if initial_bytes > INITIAL_AOI_LIST_MAX_BYTES:
        errors.append(f"AOI list initial bytes are {initial_bytes}; budget is {INITIAL_AOI_LIST_MAX_BYTES}")
    if default_bytes > DEFAULT_AOI_VECTOR_MAX_BYTES:
        errors.append(f"default AOI catalog+damage+VLM bytes are {default_bytes}; budget is {DEFAULT_AOI_VECTOR_MAX_BYTES}")
    if report["frontend_loading_scan"]["loads_all_aois_on_initial_render"]:
        errors.append("OperationsConsole appears to eager-load all AOI damage/VLM data")
    for item in large_aoi_files:
        if int(item.get("bytes") or 0) >= LOCAL_AOI_CRITICAL_FILE_BYTES:
            errors.append(
                f"{item['path']} is {item['human']}; local AOI files must stay below "
                f"{audit_asset_budget.bytes_human(LOCAL_AOI_CRITICAL_FILE_BYTES)} unless moved to remote storage"
            )

    if public_data_bytes > LOCAL_PUBLIC_DATA_TARGET_BYTES:
        warnings.append(
            f"public/data is above target ({report['public_data']['data']['human']} > "
            f"{audit_asset_budget.bytes_human(LOCAL_PUBLIC_DATA_TARGET_BYTES)}); use remote-asset package for production"
        )
    if tiles_bytes > LOCAL_TILES_TARGET_BYTES:
        warnings.append(
            f"public/data/tiles is above target ({report['public_data']['tiles']['human']} > "
            f"{audit_asset_budget.bytes_human(LOCAL_TILES_TARGET_BYTES)}); do not deploy raw local package to Vercel"
        )
    if chips_bytes > LOCAL_CHIPS_TARGET_BYTES:
        warnings.append(
            f"public/data/chips is above target ({report['public_data']['chips']['human']} > "
            f"{audit_asset_budget.bytes_human(LOCAL_CHIPS_TARGET_BYTES)}); verify R2/CDN mirror before pruning"
        )
    if package_pressure.get("remote_asset_package_required"):
        warnings.append(
            "raw local public/data package is not production-safe; build and deploy the remote-asset package after remote URL validation"
        )
    remaining_public_data = int(package_pressure.get("non_remote_public_data_bytes") or 0)
    if remaining_public_data > REMOTE_PACKAGE_REMAINING_PUBLIC_DATA_TARGET_BYTES:
        warnings.append(
            f"public/data remains {package_pressure.get('non_remote_public_data_human', remaining_public_data)} after excluding local tiles/chips; "
            f"target is {audit_asset_budget.bytes_human(REMOTE_PACKAGE_REMAINING_PUBLIC_DATA_TARGET_BYTES)}"
        )
    external_large = [item for item in large_aoi_files if item.get("status") == "external-prediction"]
    if external_large:
        total = sum(int(item.get("bytes") or 0) for item in external_large)
        examples = ", ".join(f"{item['path']} ({item['human']})" for item in external_large[:3])
        warnings.append(
            f"external-prediction local AOI payloads above {audit_asset_budget.bytes_human(audit_asset_budget.LOCAL_HEAVY_THRESHOLD)} "
            f"total {audit_asset_budget.bytes_human(total)}; keep out of official metrics and consider vector tiles/remote storage: {examples}"
        )
    report_large = [item for item in large_aoi_files if item.get("role") == "report"]
    if report_large:
        total = sum(int(item.get("bytes") or 0) for item in report_large)
        examples = ", ".join(f"{item['path']} ({item['human']})" for item in report_large[:3])
        warnings.append(
            f"local report PDFs above {audit_asset_budget.bytes_human(audit_asset_budget.LOCAL_HEAVY_THRESHOLD)} "
            f"total {audit_asset_budget.bytes_human(total)}; remote package or CDN hosting is required before raw production deploy: {examples}"
        )
    if not report["bundle"]["build_present"]:
        warnings.append(".next is missing; run npm run build before interpreting bundle JS/CSS budgets")

    if strict and warnings:
        errors.extend(f"strict warning: {warning}" for warning in warnings)
    return errors, warnings


def write_report(path: Path, report: dict, errors: list[str], warnings: list[str]) -> None:
    lines = [
        "# Mobile Performance Budget",
        "",
        f"- Generated UTC: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Result: `{'fail' if errors else 'pass'}`",
        f"- Catalog: `{report['catalog']['human']}` / `{audit_asset_budget.bytes_human(CATALOG_MAX_BYTES)}`",
        f"- Initial AOI list bytes: `{report['initial_load_estimate']['aoi_list_human']}` / `{audit_asset_budget.bytes_human(INITIAL_AOI_LIST_MAX_BYTES)}`",
        f"- Default AOI metadata+damage+VLM bytes: `{report['initial_load_estimate']['default_metadata_and_vector_human']}` / `{audit_asset_budget.bytes_human(DEFAULT_AOI_VECTOR_MAX_BYTES)}`",
        f"- Local public data: `{report['public_data']['data']['human']}` target `{audit_asset_budget.bytes_human(LOCAL_PUBLIC_DATA_TARGET_BYTES)}`",
        f"- Local tiles: `{report['public_data']['tiles']['human']}` target `{audit_asset_budget.bytes_human(LOCAL_TILES_TARGET_BYTES)}`",
        f"- Local chips: `{report['public_data']['chips']['human']}` target `{audit_asset_budget.bytes_human(LOCAL_CHIPS_TARGET_BYTES)}`",
        f"- Raw local production package safe: `{report.get('production_package_pressure', {}).get('raw_local_package_safe')}`",
        f"- Remote asset package required: `{report.get('production_package_pressure', {}).get('remote_asset_package_required')}`",
        f"- Public data after excluding local tiles/chips: `{report.get('production_package_pressure', {}).get('non_remote_public_data_human', 'unknown')}` / `{audit_asset_budget.bytes_human(REMOTE_PACKAGE_REMAINING_PUBLIC_DATA_TARGET_BYTES)}`",
        f"- Large local AOI files: `{report.get('production_package_pressure', {}).get('large_local_aoi_file_count', 0)}` / `{report.get('production_package_pressure', {}).get('large_local_aoi_human', '0 B')}`",
        f"- Eager all-AOI data detected: `{report['frontend_loading_scan']['loads_all_aois_on_initial_render']}`",
        "",
    ]
    if errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    if warnings:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    large_aoi_files = report.get("public_data", {}).get("large_local_aoi_files") or []
    if large_aoi_files:
        lines.extend([
            "## Large Local AOI Files",
            "",
            "| File | Status | Role | Size | Source |",
            "| --- | --- | --- | ---: | --- |",
        ])
        for item in large_aoi_files[:12]:
            lines.append(
                f"| `{item['path']}` | `{item.get('status', '-')}` | `{item.get('role', '-')}` | "
                f"{item['human']} | {item.get('source_summary') or '-'} |"
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--strict", action="store_true", help="Treat target-stage warnings as failures.")
    args = parser.parse_args()

    report = audit_asset_budget.build_report()
    errors, warnings = check_budget(report, strict=args.strict)
    write_report(args.report, report, errors, warnings)
    payload = {
        "result": "fail" if errors else "pass",
        "report": rel(args.report),
        "errors": len(errors),
        "warnings": len(warnings),
        "catalog_bytes": report["catalog"]["bytes"],
        "initial_aoi_list_bytes": report["initial_load_estimate"]["aoi_list_bytes_before_active_data"],
        "default_aoi_vector_bytes": report["initial_load_estimate"]["default_metadata_and_vector_bytes"],
        "remote_asset_package_required": report.get("production_package_pressure", {}).get("remote_asset_package_required"),
        "large_local_aoi_files": report.get("production_package_pressure", {}).get("large_local_aoi_file_count", 0),
    }
    print(json.dumps(payload, indent=2))
    if errors:
        for error in errors:
            print(f"- {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
