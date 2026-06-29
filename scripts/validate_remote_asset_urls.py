#!/usr/bin/env python3
"""Validate remote chip/tile asset URLs before deploying a pruned package.

The public app can run from static AOI exports even when Supabase is down. A
remote-asset Vercel package additionally expects heavy ``/data/chips`` and
``/data/tiles`` paths to be available from object storage/CDN. This preflight
checks both assumptions without requiring secrets.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "public" / "data" / "catalog.json"
DEFAULT_REMOTE_BASE = "https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev"
DEFAULT_REPORT = ROOT / "ops" / "remote_asset_validation" / "latest.json"
TILE_TEMPLATE_RE = re.compile(r"/data/tiles/([^/]+)/([^/]+)/\{z\}/\{x\}/\{y\}\.webp")
COG_SUFFIXES = {".tif", ".tiff"}
EXPECTED_CONTENT_TYPES = {
    "tile": {"image/webp"},
    "chip": {"image/png"},
    "cog": {"image/tiff", "image/geotiff", "application/octet-stream", "binary/octet-stream"},
}
IMMUTABLE_MAX_AGE_SECONDS = 31_536_000
COG_RANGE_REQUIREMENT = "COG fallback URLs must honor Range: bytes=0-0 with HTTP 206 and a Content-Range header starting with 'bytes 0-0/'."
COG_CONTENT_TYPE_REQUIREMENT = "COG fallback URLs must return a GeoTIFF-compatible content type; binary/octet-stream is accepted for EMS/Vantor/Sentinel public S3 COGs when byte ranges work."


def normalize_base(value: str) -> str:
    return value.rstrip("/")


def bytes_human(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def dir_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path.relative_to(ROOT)), "exists": False, "files": 0, "bytes": 0, "human": "0 B"}
    files = [item for item in path.rglob("*") if item.is_file()]
    total = sum(item.stat().st_size for item in files)
    return {
        "path": str(path.relative_to(ROOT)),
        "exists": True,
        "files": len(files),
        "bytes": total,
        "human": bytes_human(total),
    }


def top_large_files(path: Path, limit: int = 10) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    files = sorted([item for item in path.rglob("*") if item.is_file()], key=lambda item: item.stat().st_size, reverse=True)
    return [
        {
            "path": str(item.relative_to(ROOT)),
            "bytes": item.stat().st_size,
            "human": bytes_human(item.stat().st_size),
        }
        for item in files[:limit]
    ]


def walk_strings(value: Any, path: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, str):
        found.append((path, value))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(walk_strings(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            child = f"{path}.{key}" if path else key
            found.extend(walk_strings(item, child))
    return found


def catalog_path_from_url(value: str) -> str | None:
    if value.startswith("/data/"):
        return value
    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        if parsed.path.startswith("/data/"):
            return parsed.path
    return None


def remote_url(remote_base: str, data_path: str) -> str:
    return f"{remote_base}{data_path}"


def local_public_path(data_path: str) -> Path:
    return ROOT / "public" / data_path.lstrip("/")


def evenly_sample(items: list[Path], limit: int) -> list[Path]:
    if limit <= 0 or len(items) <= limit:
        return items
    if limit == 1:
        return [items[0]]
    indexes = sorted({round(i * (len(items) - 1) / (limit - 1)) for i in range(limit)})
    return [items[index] for index in indexes]


def evenly_sample_records(items: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    if limit <= 0 or len(items) <= limit:
        return items
    if limit == 1:
        return [items[0]]
    indexes = sorted({round(i * (len(items) - 1) / (limit - 1)) for i in range(limit)})
    return [items[index] for index in indexes]


def sample_tile_files(template: str, limit: int) -> list[Path]:
    data_path = catalog_path_from_url(template)
    if not data_path:
        return []
    match = TILE_TEMPLATE_RE.search(data_path)
    if not match:
        return []
    aoi_id, kind = match.groups()
    tile_root = ROOT / "public" / "data" / "tiles" / aoi_id / kind
    if not tile_root.exists():
        return []

    candidates: list[Path] = []
    zoom_dirs = sorted([item for item in tile_root.iterdir() if item.is_dir()], key=lambda item: int(item.name))
    for zoom_dir in zoom_dirs:
        files = sorted(zoom_dir.rglob("*.webp"))
        if not files:
            continue
        picks = [files[0], files[len(files) // 2], files[-1]]
        candidates.extend(dict.fromkeys(picks))
    return evenly_sample(candidates, limit)


def sample_chip_files(limit: int) -> list[Path]:
    chips_root = ROOT / "public" / "data" / "chips"
    if not chips_root.exists():
        return []
    return evenly_sample(sorted(chips_root.rglob("*.png")), limit)


def public_data_path(path: Path) -> str:
    return "/" + path.relative_to(ROOT / "public").as_posix()


def check_url(url: str, timeout: float, pause: float) -> dict[str, Any]:
    request = Request(url, headers={"User-Agent": "cdi-remote-asset-validator/1.0", "Range": "bytes=0-0"})
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            content_type = response.headers.get("content-type")
            content_range = response.headers.get("content-range")
            cache_control = response.headers.get("cache-control")
            accept_ranges = response.headers.get("accept-ranges")
            content_length = response.headers.get("content-length")
            ok = 200 <= status < 400
    except HTTPError as exc:
        status = int(exc.code)
        content_type = exc.headers.get("content-type") if exc.headers else None
        content_range = exc.headers.get("content-range") if exc.headers else None
        cache_control = exc.headers.get("cache-control") if exc.headers else None
        accept_ranges = exc.headers.get("accept-ranges") if exc.headers else None
        content_length = exc.headers.get("content-length") if exc.headers else None
        ok = False
        error = str(exc)
    except (URLError, TimeoutError, OSError) as exc:
        status = None
        content_type = None
        content_range = None
        cache_control = None
        accept_ranges = None
        content_length = None
        ok = False
        error = str(exc)
    else:
        error = None
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    if pause:
        time.sleep(pause)
    return {
        "url": url,
        "ok": ok,
        "status": status,
        "content_type": content_type,
        "content_range": content_range,
        "accept_ranges": accept_ranges,
        "cache_control": cache_control,
        "content_length": content_length,
        "elapsed_ms": elapsed_ms,
        "error": error,
    }


def local_static_refs(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for path, value in walk_strings(catalog):
        data_path = catalog_path_from_url(value)
        if not data_path or not data_path.startswith("/data/aoi/"):
            continue
        if any(token in data_path for token in ("{z}", "{x}", "{y}")):
            continue
        local_path = local_public_path(data_path)
        refs.append({
            "catalog_path": path,
            "data_path": data_path,
            "exists": local_path.exists(),
            "bytes": local_path.stat().st_size if local_path.exists() else 0,
        })
    return refs


def tile_templates(catalog: dict[str, Any]) -> list[dict[str, str]]:
    seen: set[str] = set()
    templates: list[dict[str, str]] = []
    for path, value in walk_strings(catalog):
        data_path = catalog_path_from_url(value)
        if not data_path or "/data/tiles/" not in data_path:
            continue
        if data_path in seen:
            continue
        seen.add(data_path)
        templates.append({"catalog_path": path, "template": data_path})
    return templates


def remote_cog_urls(catalog: dict[str, Any], limit: int) -> list[dict[str, str]]:
    seen: set[str] = set()
    checks: list[dict[str, str]] = []
    for path, value in walk_strings(catalog):
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"}:
            continue
        if any(token in value for token in ("{z}", "{x}", "{y}")):
            continue
        suffix = Path(parsed.path).suffix.lower()
        if suffix not in COG_SUFFIXES and "cog" not in path.lower() and "cog" not in parsed.path.lower():
            continue
        if value in seen:
            continue
        seen.add(value)
        checks.append({
            "kind": "cog",
            "catalog_path": path,
            "data_path": parsed.path or value,
            "url": value,
        })
    return evenly_sample_records(checks, limit)


def normalized_content_type(value: str | None) -> str | None:
    if not value:
        return None
    return value.split(";", 1)[0].strip().lower()


def max_age_seconds(cache_control: str | None) -> int | None:
    if not cache_control:
        return None
    match = re.search(r"max-age=(\d+)", cache_control, flags=re.I)
    return int(match.group(1)) if match else None


def quality_messages(kind: str, status: int | None, content_type: str | None, content_range: str | None, cache_control: str | None) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if status is None or not 200 <= status < 400:
        return errors, warnings

    normalized_type = normalized_content_type(content_type)
    expected = EXPECTED_CONTENT_TYPES.get(kind)
    if expected and normalized_type not in expected:
        errors.append(f"unexpected content-type {content_type!r}; expected one of {sorted(expected)}")

    if kind == "cog":
        content_range_lower = (content_range or "").lower()
        if status != 206 or not content_range_lower.startswith("bytes 0-0/"):
            errors.append(COG_RANGE_REQUIREMENT)

    if kind in {"tile", "chip"}:
        age = max_age_seconds(cache_control)
        cache_lower = (cache_control or "").lower()
        if "public" not in cache_lower:
            warnings.append("Cache-Control should include public for CDN/browser reuse")
        if age is None or age < IMMUTABLE_MAX_AGE_SECONDS:
            warnings.append("Cache-Control max-age is below one year for a versioned asset")
        if "immutable" not in cache_lower:
            warnings.append("Cache-Control should include immutable for versioned tiles/chips")
    return errors, warnings


def deploy_gate(
    failures: list[dict[str, Any]],
    missing_static: list[dict[str, Any]],
    quality_errors: list[dict[str, Any]],
    sampled_cogs: list[dict[str, str]],
) -> dict[str, Any]:
    blockers: list[str] = []
    cog_failures = [item for item in failures if item.get("kind") == "cog"]
    cog_quality_errors = [item for item in quality_errors if item.get("kind") == "cog"]
    if missing_static:
        blockers.append(f"{len(missing_static)} local static /data/aoi references are missing")
    if failures:
        blockers.append(f"{len(failures)} sampled remote asset checks failed")
    if quality_errors:
        blockers.append(f"{len(quality_errors)} sampled remote asset checks have content/range quality errors")
    if not sampled_cogs:
        blockers.append("no COG URLs were sampled, so COG fallback Range/content-type support is unverified")
    if cog_failures or cog_quality_errors:
        blockers.append(
            f"sampled COG fallback is blocked by {len(cog_failures)} fetch failures "
            f"and {len(cog_quality_errors)} Range/content-type errors"
        )
    return {
        "pruned_remote_asset_package_ready": not blockers,
        "blockers": blockers,
        "cog_range_requirement": COG_RANGE_REQUIREMENT,
        "cog_content_type_requirement": COG_CONTENT_TYPE_REQUIREMENT,
        "expected_content_types": {key: sorted(value) for key, value in EXPECTED_CONTENT_TYPES.items()},
        "sampled_cog_count": len(sampled_cogs),
        "cog_failure_count": len(cog_failures),
        "cog_quality_error_count": len(cog_quality_errors),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Remote Asset Validation",
        "",
        f"- Generated UTC: `{report['generated_utc']}`",
        f"- Remote base: `{report['remote_base']}`",
        f"- Result: `{report['result']}`",
        "",
        "## Package Pressure",
        "",
    ]
    for item in report["package_pressure"].values():
        lines.append(f"- `{item['path']}`: {item['files']} files, {item['human']}")
    if report["top_large_files"]:
        lines.extend(["", "### Largest Bundled Files", ""])
        for item in report["top_large_files"]:
            lines.append(f"- `{item['path']}`: {item['human']}")
    lines.extend([
        "",
        "## Supabase-Free Static Data",
        "",
        f"- Local `/data/aoi` references checked: {report['static_data']['checked']}",
        f"- Missing local static references: {report['static_data']['missing']}",
        "",
        "## Pruned Deploy Gate",
        "",
        f"- Ready for pruned remote-asset package: `{report['deploy_gate']['pruned_remote_asset_package_ready']}`",
        f"- COG Range requirement: {report['deploy_gate']['cog_range_requirement']}",
        f"- COG content-type requirement: {report['deploy_gate']['cog_content_type_requirement']}",
        f"- Sampled COG URLs: `{report['deploy_gate']['sampled_cog_count']}`",
    ])
    if report["deploy_gate"]["blockers"]:
        lines.extend(["", "### Deploy Blockers", ""])
        lines.extend(f"- {blocker}" for blocker in report["deploy_gate"]["blockers"])
    lines.extend([
        "",
        "## Remote Asset Checks",
        "",
        f"- Checks run: {report['remote_assets']['checked']}",
        f"- OK: {report['remote_assets']['ok']}",
        f"- Failed: {report['remote_assets']['failed']}",
        f"- Quality errors: {report['remote_assets']['quality_error_count']}",
        f"- Quality warnings: {report['remote_assets']['quality_warning_count']}",
    ])
    if report["remote_assets"]["failures"]:
        lines.extend(["", "### Failures", ""])
        for failure in report["remote_assets"]["failures"][:50]:
            lines.append(f"- `{failure['kind']}` `{failure['data_path']}` -> HTTP `{failure.get('status')}`")
    if report["remote_assets"]["quality_errors"]:
        lines.extend(["", "### Quality Errors", ""])
        for item in report["remote_assets"]["quality_errors"][:50]:
            messages = "; ".join(item["messages"])
            lines.append(f"- `{item['kind']}` `{item['data_path']}`: {messages}")
    if report["remote_assets"]["quality_warnings"]:
        lines.extend(["", "### Quality Warnings", ""])
        for item in report["remote_assets"]["quality_warnings"][:50]:
            messages = "; ".join(item["messages"])
            lines.append(f"- `{item['kind']}` `{item['data_path']}`: {messages}")
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--remote-base", default=DEFAULT_REMOTE_BASE)
    parser.add_argument("--sample-per-template", type=int, default=12, help="Sampled tile files per catalog tile template; 0 means all selected zoom picks.")
    parser.add_argument("--sample-chips", type=int, default=32, help="Sampled evidence chips; 0 means all chips.")
    parser.add_argument("--sample-cogs", type=int, default=12, help="Sampled remote COG URLs from catalog; 0 means all COG URLs.")
    parser.add_argument("--timeout", type=float, default=8)
    parser.add_argument("--pause", type=float, default=0.05, help="Seconds to pause between public URL checks.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--allow-failures", action="store_true", help="Write the report and exit 0 even when remote URLs fail.")
    args = parser.parse_args()

    catalog = json.loads(args.catalog.read_text())
    remote_base = normalize_base(args.remote_base)
    static_refs = local_static_refs(catalog)
    templates = tile_templates(catalog)

    checks: list[dict[str, str]] = []
    for template in templates:
        for path in sample_tile_files(template["template"], args.sample_per_template):
            data_path = public_data_path(path)
            checks.append({
                "kind": "tile",
                "catalog_path": template["catalog_path"],
                "data_path": data_path,
                "url": remote_url(remote_base, data_path),
            })
    for path in sample_chip_files(args.sample_chips):
        data_path = public_data_path(path)
        checks.append({
            "kind": "chip",
            "catalog_path": "public/data/chips sample",
            "data_path": data_path,
            "url": remote_url(remote_base, data_path),
        })
    checks.extend(remote_cog_urls(catalog, args.sample_cogs))

    results: list[dict[str, Any]] = []
    for check in checks:
        result = check_url(check["url"], args.timeout, args.pause)
        quality_errors, quality_warnings = quality_messages(
            check["kind"],
            result["status"],
            result["content_type"],
            result["content_range"],
            result["cache_control"],
        )
        results.append({**check, **result, "quality_errors": quality_errors, "quality_warnings": quality_warnings})

    failures = [item for item in results if not item["ok"]]
    missing_static = [item for item in static_refs if not item["exists"]]
    quality_errors = [
        {"kind": item["kind"], "data_path": item["data_path"], "url": item["url"], "messages": item["quality_errors"]}
        for item in results
        if item["quality_errors"]
    ]
    quality_warnings = [
        {"kind": item["kind"], "data_path": item["data_path"], "url": item["url"], "messages": item["quality_warnings"]}
        for item in results
        if item["quality_warnings"]
    ]
    sampled_cogs = [item for item in checks if item["kind"] == "cog"]
    gate = deploy_gate(failures, missing_static, quality_errors, sampled_cogs)
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "catalog": rel(args.catalog),
        "remote_base": remote_base,
        "result": "pass" if gate["pruned_remote_asset_package_ready"] else "fail",
        "deploy_gate": gate,
        "package_pressure": {
            "public_data": dir_stats(ROOT / "public" / "data"),
            "chips": dir_stats(ROOT / "public" / "data" / "chips"),
            "tiles": dir_stats(ROOT / "public" / "data" / "tiles"),
        },
        "top_large_files": top_large_files(ROOT / "public" / "data"),
        "static_data": {
            "checked": len(static_refs),
            "missing": len(missing_static),
            "missing_refs": missing_static,
            "note": "These local static AOI exports keep public read-only viewing independent of Supabase.",
        },
        "remote_assets": {
            "tile_templates": templates,
            "sampled_cogs": sampled_cogs,
            "checked": len(results),
            "ok": len(results) - len(failures),
            "failed": len(failures),
            "quality_error_count": sum(len(item["quality_errors"]) for item in results),
            "quality_warning_count": sum(len(item["quality_warnings"]) for item in results),
            "checks": results,
            "failures": failures,
            "quality_errors": quality_errors,
            "quality_warnings": quality_warnings,
            "note": "Remote chip/tile URLs must pass before deploying the pruned remote-asset Vercel package.",
        },
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    markdown_path = args.report.with_suffix(".md")
    write_markdown(report, markdown_path)

    print(json.dumps({
        "result": report["result"],
        "report": rel(args.report),
        "markdown": rel(markdown_path),
        "static_missing": len(missing_static),
        "remote_checked": len(results),
        "remote_failed": len(failures),
        "remote_quality_errors": len(quality_errors),
        "remote_quality_warnings": len(quality_warnings),
        "pruned_deploy_ready": gate["pruned_remote_asset_package_ready"],
        "deploy_blockers": len(gate["blockers"]),
    }, indent=2))
    if report["result"] != "pass" and not args.allow_failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
