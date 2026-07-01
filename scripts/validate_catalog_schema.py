#!/usr/bin/env python3
"""Validate catalog shape and crisis-response publication guardrails."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CATALOG = PUBLIC / "data" / "catalog.json"
DEFAULT_REPORT = ROOT / "ops" / "performance_audit" / "catalog_validation.md"

ALLOWED_STATUSES = {
    "test-fixture",
    "official-vector",
    "official-monitor-points",
    "external-prediction",
    "imagery-only",
    "waiting",
    "in-production",
    "no-official-product",
    "external-gap",
}
LOCAL_PATH_RE = re.compile(r"^/data/[A-Za-z0-9._~:/{}-]+$")
SECRET_RE = re.compile(r"(service[_-]?role|secret|password|api[_-]?key|access[_-]?token|bearer\s+[A-Za-z0-9._-]+)", re.I)
TOKEN_VALUE_RE = re.compile(r"(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,})")
PRIVATE_HOST_RE = re.compile(r"(^localhost$|^127\.|^10\.|^172\.(1[6-9]|2\d|3[0-1])\.|^192\.168\.|\.local$)", re.I)
LOCAL_ABSOLUTE_RE = re.compile(r"(?<![A-Za-z0-9.:_-])/(?:Users|home|Volumes|private|tmp|var/folders)/|(?<![A-Za-z0-9])[A-Za-z]:[\\/]")
FILE_URL_RE = re.compile(r"file://[^\s\"'<>)}\]]+", re.I)
HTTP_URL_RE = re.compile(r"https?://[^\s\"'<>)}\]]+", re.I)
CRITICAL_LOCAL_FILE_LIMIT = 50 * 1024 * 1024
WARN_LOCAL_FILE_LIMIT = 5 * 1024 * 1024
PUBLIC_TEXT_SUFFIXES = {".json", ".geojson", ".jsonl", ".csv", ".kml", ".md", ".html", ".txt"}
OFFICIAL_DAMAGE_STATUSES = {"official-vector", "official-monitor-points"}
OFFICIAL_COUNT_METRICS = (
    "destroyed",
    "destroyedConfirmed",
    "officialDestroyed",
    "damaged",
    "damagedConfirmed",
    "damaged_confirmed",
    "confirmedDamaged",
    "officialDamaged",
    "officialDamagedConfirmed",
    "officialConfirmed",
    "possibleDamage",
)
DIRECT_RASTER_MOBILE_MAX_BYTES = 250_000_000
RASTER_SUFFIXES = (".tif", ".tiff", ".ntf", ".nitf")
STRICT_LICENSE_HOSTS = (
    "data.source.coop",
    "oin-hotosm-temp.s3.us-east-1.amazonaws.com",
    "oin-hotosm-temp.s3.amazonaws.com",
)


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text())


def public_path(value: str | None) -> Path | None:
    if not value or urlparse(value).scheme:
        return None
    if not value.startswith("/"):
        return None
    return PUBLIC / value.lstrip("/")


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


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def metric_number(value: Any) -> float | None:
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def validate_lat_lon(errors: list[str], label: str, point: Any) -> tuple[float, float] | None:
    if not isinstance(point, list) or len(point) != 2 or not all(is_number(item) for item in point):
        errors.append(f"{label}: expected [lat, lon]")
        return None
    lat = float(point[0])
    lon = float(point[1])
    if not -90 <= lat <= 90:
        errors.append(f"{label}: latitude {lat} outside [-90, 90]")
    if not -180 <= lon <= 180:
        errors.append(f"{label}: longitude {lon} outside [-180, 180]")
    return lat, lon


def validate_url_value(errors: list[str], warnings: list[str], label: str, value: str) -> None:
    parsed = urlparse(value)
    if SECRET_RE.search(value):
        errors.append(f"{label}: looks like it contains a secret or token")
    if value.startswith(("file://", "/Users/", "/home/", "C:\\", "../", "./")):
        errors.append(f"{label}: local filesystem path is not allowed in the public catalog")
    if parsed.scheme in {"http", "https"}:
        if PRIVATE_HOST_RE.search(parsed.hostname or ""):
            errors.append(f"{label}: private or localhost URL is not allowed")
        if "google." in parsed.netloc and "/maps" not in parsed.path:
            warnings.append(f"{label}: Google URL must stay a user-click external reference, not evidence")
        return
    if parsed.scheme:
        errors.append(f"{label}: unsupported URL scheme {parsed.scheme!r}")
        return
    if value.startswith("/"):
        if not LOCAL_PATH_RE.match(value):
            errors.append(f"{label}: invalid public path syntax {value!r}")
        return
    if "{" in value and "}" in value:
        errors.append(f"{label}: tile templates must use absolute /data or https URLs")


def local_file_check(errors: list[str], warnings: list[str], label: str, value: str) -> None:
    path = public_path(value)
    if path is None:
        return
    if any(token in value for token in ("{z}", "{x}", "{y}")):
        # Tile templates are directory contracts; existence is covered by asset-budget audit.
        return
    if not path.exists():
        errors.append(f"{label}: missing local public file {rel(path)}")
        return
    size = path.stat().st_size
    if size > CRITICAL_LOCAL_FILE_LIMIT:
        errors.append(f"{label}: local public file exceeds 50 MB: {rel(path)}")
    elif size > WARN_LOCAL_FILE_LIMIT:
        warnings.append(f"{label}: local public file exceeds 5 MB and should be justified or moved to CDN: {rel(path)}")


def count_geojson_features(path: Path) -> int | None:
    try:
        return len((read_json(path).get("features") or []))
    except Exception:
        return None


def validate_vlm_guardrails(errors: list[str], warnings: list[str], aoi: dict[str, Any]) -> None:
    aoi_id = str(aoi.get("id"))
    downloads = aoi.get("downloads") or {}
    metrics = aoi.get("metrics") or {}
    imagery = aoi.get("imagery") or {}
    layers = aoi.get("layers") or {}
    has_before_after_download = any(str(key).startswith("vlm_before_after") for key in downloads)
    before_after_reviewed = int(metrics.get("vlmBeforeAfterReviewed") or 0)
    post_event_reviewed = int(metrics.get("vlmPostEventReviewed") or 0)

    if has_before_after_download:
        if before_after_reviewed <= 0:
            errors.append(f"{aoi_id}: before/after VLM downloads require vlmBeforeAfterReviewed > 0")
        if not imagery.get("before") or not imagery.get("after"):
            errors.append(f"{aoi_id}: before/after VLM requires imagery.before and imagery.after metadata")
    if post_event_reviewed and before_after_reviewed == 0 and metrics.get("vlmReviewed"):
        errors.append(f"{aoi_id}: post-event-only VLM must not use legacy vlmReviewed as an aggregate")
    if layers.get("vlm") and not (downloads.get("vlm_jsonl") or downloads.get("vlm_before_after_jsonl")):
        warnings.append(f"{aoi_id}: layers.vlm exists without a matching VLM download key")


def looks_like_raster_url(value: str | None) -> bool:
    if not value:
        return False
    path = urlparse(value).path.lower()
    return path.endswith(RASTER_SUFFIXES)


def validate_official_metric_guardrails(errors: list[str], warnings: list[str], aoi: dict[str, Any]) -> None:
    aoi_id = str(aoi.get("id"))
    status = str(aoi.get("status") or "")
    metrics = aoi.get("metrics") or {}
    if status in OFFICIAL_DAMAGE_STATUSES:
        return

    status_label = "external prediction" if status == "external-prediction" else f"non-official status {status!r}"
    for key in OFFICIAL_COUNT_METRICS:
        value = metric_number(metrics.get(key))
        if value is None:
            errors.append(f"{aoi_id}: {status_label} official count metric {key} must be numeric zero when present")
        elif value != 0:
            errors.append(f"{aoi_id}: {status_label} must not publish official count metric {key}")

    source_text = " ".join(str(x) for _, x in walk_strings({
        "source": aoi.get("source"),
        "name": aoi.get("name", {}),
        "imagery": aoi.get("imagery", {}),
    })).lower()
    if status in {"external-prediction", "imagery-only", "external-gap"} and "official" in source_text and "not official" not in source_text and "no official" not in source_text:
        warnings.append(f"{aoi_id}: non-official record mentions official sources; verify labels keep triage/context separate")


def imagery_entry_for_layer(aoi: dict[str, Any], layer_key: str) -> dict[str, Any]:
    imagery = aoi.get("imagery") or {}
    if layer_key == "beforeImage":
        return imagery.get("before") if isinstance(imagery.get("before"), dict) else {}
    if layer_key == "afterImage":
        return imagery.get("after") if isinstance(imagery.get("after"), dict) else {}
    return {}


def paired_tiles_key(layer_key: str) -> str:
    return "beforeTiles" if layer_key == "beforeImage" else "afterTiles"


def validate_imagery_guardrails(errors: list[str], warnings: list[str], aoi: dict[str, Any]) -> None:
    aoi_id = str(aoi.get("id"))
    layers = aoi.get("layers") or {}
    imagery = aoi.get("imagery") or {}

    for layer_key in ("beforeImage", "afterImage"):
        value = layers.get(layer_key)
        if not isinstance(value, str) or not looks_like_raster_url(value):
            continue

        entry = imagery_entry_for_layer(aoi, layer_key)
        bytes_value = entry.get("bytes")
        has_tiles = bool(layers.get(paired_tiles_key(layer_key)))
        if not has_tiles and not isinstance(bytes_value, int):
            errors.append(
                f"{aoi_id}.{layer_key}: direct raster layer requires imagery byte metadata or a paired tile layer"
            )
        if isinstance(bytes_value, int):
            if bytes_value > DIRECT_RASTER_MOBILE_MAX_BYTES and not has_tiles:
                errors.append(
                    f"{aoi_id}.{layer_key}: direct raster is {bytes_value} bytes without tiles; "
                    "publish tiles/chips or keep it as a download-only evidence link"
                )

        parsed = urlparse(value)
        host = parsed.netloc.lower()
        if any(host == strict_host for strict_host in STRICT_LICENSE_HOSTS):
            license_text = str(entry.get("license") or "")
            source_text = " ".join(str(x) for x in (
                entry.get("source"),
                entry.get("limitations"),
                (imagery.get("note") if isinstance(imagery, dict) else None),
            ))
            if not license_text:
                errors.append(f"{aoi_id}.{layer_key}: external imagery from {host} requires explicit license metadata")
            if "data.source.coop" in host and "CC-BY-NC" not in license_text.upper().replace(" ", "-"):
                errors.append(f"{aoi_id}.{layer_key}: Planet Source Cooperative imagery must be labeled CC-BY-NC")
            if "oin-hotosm-temp" in host and not ("OpenAerialMap" in source_text or "Open Imagery Network" in source_text):
                errors.append(f"{aoi_id}.{layer_key}: OIN/OpenAerialMap imagery requires explicit attribution/source metadata")

    for part in ("before", "after"):
        entry = imagery.get(part) if isinstance(imagery, dict) else None
        if not isinstance(entry, dict):
            continue
        url = entry.get("url")
        if not isinstance(url, str) or not urlparse(url).scheme:
            continue
        if looks_like_raster_url(url) and not entry.get("license"):
            warnings.append(f"{aoi_id}.imagery.{part}: remote raster metadata should include license/terms")


def validate_public_data_text(errors: list[str], public_root: Path = PUBLIC / "data") -> None:
    if not public_root.exists():
        errors.append(f"{rel(public_root)}: public data directory is missing")
        return

    for path in sorted(item for item in public_root.rglob("*") if item.is_file() and item.suffix.lower() in PUBLIC_TEXT_SUFFIXES):
        try:
            text = path.read_text(errors="ignore")
        except OSError as exc:
            errors.append(f"{rel(path)}: unable to read public text file: {exc}")
            continue
        for match in LOCAL_ABSOLUTE_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{rel(path)}:{line}: public data contains a local absolute path")
            break
        for match in FILE_URL_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{rel(path)}:{line}: public data contains a file:// URL")
            break
        for match in SECRET_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{rel(path)}:{line}: public data contains a secret-looking string")
            break
        for match in TOKEN_VALUE_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{rel(path)}:{line}: public data contains a token-shaped value")
            break
        for match in HTTP_URL_RE.finditer(text):
            parsed = urlparse(match.group(0).rstrip(".,;"))
            if PRIVATE_HOST_RE.search(parsed.hostname or ""):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{rel(path)}:{line}: public data contains a private or localhost URL")
                break


def validate_aoi(errors: list[str], warnings: list[str], aoi: dict[str, Any]) -> None:
    aoi_id = str(aoi.get("id") or "")
    prefix = aoi_id or "<missing-id>"
    if not re.match(r"^[a-z0-9][a-z0-9._-]+$", aoi_id):
        errors.append(f"{prefix}: id must be lowercase URL-safe text")
    if aoi.get("status") not in ALLOWED_STATUSES:
        errors.append(f"{prefix}: unsupported status {aoi.get('status')!r}")
    for lang in ("en", "es"):
        if not isinstance((aoi.get("name") or {}).get(lang), str) or not (aoi.get("name") or {}).get(lang):
            errors.append(f"{prefix}: name.{lang} is required")
    for key in ("country", "event", "source"):
        if not isinstance(aoi.get(key), str) or not aoi.get(key):
            errors.append(f"{prefix}: {key} is required")

    bounds = aoi.get("bounds")
    if not isinstance(bounds, list) or len(bounds) != 2:
        errors.append(f"{prefix}: bounds must be [[lat, lon], [lat, lon]]")
        bounds_points = []
    else:
        bounds_points = [
            validate_lat_lon(errors, f"{prefix}.bounds[0]", bounds[0]),
            validate_lat_lon(errors, f"{prefix}.bounds[1]", bounds[1]),
        ]
    center = validate_lat_lon(errors, f"{prefix}.center", aoi.get("center"))
    if center and all(bounds_points):
        min_lat, min_lon = bounds_points[0]  # type: ignore[index]
        max_lat, max_lon = bounds_points[1]  # type: ignore[index]
        lat, lon = center
        if min_lat > max_lat or min_lon > max_lon:
            errors.append(f"{prefix}: bounds must be southwest/northeast [lat, lon] pairs")
        elif not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
            warnings.append(f"{prefix}: center is outside bounds")

    downloads = aoi.get("downloads")
    layers = aoi.get("layers")
    metrics = aoi.get("metrics")
    if not isinstance(downloads, dict):
        errors.append(f"{prefix}: downloads must be an object")
        downloads = {}
    if not isinstance(layers, dict):
        errors.append(f"{prefix}: layers must be an object")
        layers = {}
    if not isinstance(metrics, dict):
        errors.append(f"{prefix}: metrics must be an object")
        metrics = {}

    if aoi.get("status") not in {"no-official-product", "external-gap", "waiting", "in-production"} and not layers.get("damage"):
        errors.append(f"{prefix}: layers.damage is required for public AOI records")

    for path, value in walk_strings({"downloads": downloads, "layers": layers, "imagery": aoi.get("imagery", {})}):
        validate_url_value(errors, warnings, f"{prefix}.{path}", value)
        local_file_check(errors, warnings, f"{prefix}.{path}", value)

    if aoi.get("status") == "external-prediction":
        source_text = " ".join(str(x) for _, x in walk_strings({"source": aoi.get("source"), "name": aoi.get("name", {})}))
        if all(token not in source_text.lower() for token in ("triage", "predict")):
            warnings.append(f"{prefix}: external prediction should say triage/prediction/predicted in source/name")

    damage_path = public_path(layers.get("damage"))
    if damage_path and damage_path.exists():
        count = count_geojson_features(damage_path)
        if count is not None and metrics.get("features") is not None and int(metrics.get("features") or 0) != count:
            errors.append(f"{prefix}: metrics.features={metrics.get('features')} does not match GeoJSON feature count {count}")

    validate_official_metric_guardrails(errors, warnings, aoi)
    validate_imagery_guardrails(errors, warnings, aoi)
    validate_vlm_guardrails(errors, warnings, aoi)


def validate_catalog(catalog_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    catalog = read_json(catalog_path)
    updated_at = catalog.get("updatedAt")
    try:
        if isinstance(updated_at, str):
            datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        else:
            raise ValueError
    except ValueError:
        errors.append("updatedAt must be an ISO timestamp")
    if not isinstance(catalog.get("platform"), str) or not catalog.get("platform"):
        errors.append("platform is required")
    aois = catalog.get("aois")
    if not isinstance(aois, list) or not aois:
        errors.append("aois must be a non-empty list")
        aois = []

    seen: set[str] = set()
    for aoi in aois:
        aoi_id = str(aoi.get("id") or "")
        if aoi_id in seen:
            errors.append(f"{aoi_id}: duplicate AOI id")
        seen.add(aoi_id)
        validate_aoi(errors, warnings, aoi)

    for index, item in enumerate(catalog.get("watchlist") or []):
        item_id = item.get("id") or f"watchlist[{index}]"
        if item.get("status") not in ALLOWED_STATUSES:
            errors.append(f"{item_id}: unsupported watchlist status {item.get('status')!r}")
        for lang in ("en", "es"):
            if not (item.get("name") or {}).get(lang):
                errors.append(f"{item_id}: watchlist name.{lang} is required")

    validate_public_data_text(errors)

    return errors, warnings


def write_report(report_path: Path, errors: list[str], warnings: list[str]) -> None:
    lines = [
        "# Catalog Validation",
        "",
        f"- Generated UTC: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Result: `{'fail' if errors else 'pass'}`",
        f"- Errors: `{len(errors)}`",
        f"- Warnings: `{len(warnings)}`",
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
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    errors, warnings = validate_catalog(args.catalog)
    write_report(args.report, errors, warnings)
    if errors:
        print(f"Catalog validation failed with {len(errors)} errors; report={rel(args.report)}")
        for error in errors:
            print(f"- {error}")
        return 1
    print(json.dumps({
        "result": "pass",
        "report": rel(args.report),
        "warnings": len(warnings),
    }, indent=2))
    if warnings:
        print("Warnings:")
        for warning in warnings[:20]:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
