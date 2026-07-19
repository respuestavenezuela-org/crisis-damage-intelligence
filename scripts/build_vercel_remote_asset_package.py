#!/usr/bin/env python3
"""Build a Vercel deploy package that keeps heavy imagery outside Vercel.

The source app can run locally with bundled ``public/data/tiles`` and
``public/data/chips``. Vercel should not receive those directories because they
currently contain tens of thousands of files. This script copies the app into a
separate deploy directory, omits heavy local assets, and rewrites references to
``/data/tiles`` and ``/data/chips`` so they point at a public object-storage
base URL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT.parent / "crisis_damage_intelligence_vercel_remote_assets"
DEFAULT_REMOTE_BASE = "https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev"
DEFAULT_REMOTE_VALIDATION_REPORT = ROOT / "deploy" / "remote_asset_validation.json"
MAX_DEPLOY_PACKAGE_FILES = 15_000
MAX_DEPLOY_PACKAGE_BYTES = 250_000_000
MAX_REMOTE_ATTESTATION_AGE = timedelta(hours=24)

EXCLUDE_DIRS = {
    ".codex",
    ".cursor",
    ".git",
    ".next",
    ".omo",
    ".playwright-cli",
    ".vercel",
    ".wrangler",
    "build",
    "coverage",
    "node_modules",
    "ops",
    "out",
    "output",
    "qa",
    "outputs",
    "playwright-report",
    "test-results",
    "tmp",
}

EXCLUDE_FILE_NAMES = {
    ".DS_Store",
    ".env",
}

EXCLUDE_FILE_PREFIXES = (
    ".env.",
)

HEAVY_PUBLIC_DIRS = {
    Path("public/data/tiles"),
    Path("public/data/chips"),
}

TEXT_REFERENCE_SUFFIXES = {".json", ".geojson", ".jsonl", ".csv", ".html", ".md", ".txt", ".kml"}
LOCAL_HEAVY_ASSET_REF_RE = re.compile(r"(?<![A-Za-z0-9:/._-])/(?:data)/(?:tiles|chips)/[^\s\"'<>),]+")
LOCAL_HEAVY_ASSET_PREFIX_RE = re.compile(r"(?<![A-Za-z0-9:/._-])/(data)/(tiles|chips)/")
LOCAL_REF_PREVIEW_LIMIT = 50


def normalize_base(value: str) -> str:
    return value.rstrip("/")


def bytes_human(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def rel(path: Path, root: Path = ROOT) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def display_path(path: Path, root: Path = ROOT.parent) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def is_heavy_public_path(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    return any(rel == heavy or heavy in rel.parents for heavy in HEAVY_PUBLIC_DIRS)


def ignore(src: str, names: list[str]) -> set[str]:
    src_path = Path(src)
    ignored: set[str] = set()
    for name in names:
        path = src_path / name
        rel = path.relative_to(ROOT)
        if path.is_dir() and name in EXCLUDE_DIRS:
            ignored.add(name)
        elif path.is_file() and (name in EXCLUDE_FILE_NAMES or name.startswith(EXCLUDE_FILE_PREFIXES)):
            ignored.add(name)
        elif any(rel == heavy for heavy in HEAVY_PUBLIC_DIRS):
            ignored.add(name)
    return ignored


def rewrite_value(value: Any, remote_base: str) -> Any:
    if isinstance(value, str):
        if value.startswith("/data/tiles/") or value.startswith("/data/chips/"):
            return f"{remote_base}{value}"
        return value
    if isinstance(value, list):
        return [rewrite_value(item, remote_base) for item in value]
    if isinstance(value, dict):
        return {key: rewrite_value(item, remote_base) for key, item in value.items()}
    return value


def rewrite_json(path: Path, remote_base: str) -> None:
    data = json.loads(path.read_text())
    path.write_text(json.dumps(rewrite_value(data, remote_base), indent=2, ensure_ascii=False) + "\n")


def rewrite_jsonl(path: Path, remote_base: str) -> None:
    lines = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        lines.append(json.dumps(rewrite_value(json.loads(line), remote_base), ensure_ascii=False))
    path.write_text("\n".join(lines) + ("\n" if lines else ""))


def rewrite_text_references(path: Path, remote_base: str) -> None:
    text = path.read_text()
    text = LOCAL_HEAVY_ASSET_PREFIX_RE.sub(
        lambda match: f"{remote_base}/{match.group(1)}/{match.group(2)}/",
        text,
    )
    path.write_text(text)


def rewrite_asset_references(out_dir: Path, remote_base: str) -> list[str]:
    changed: list[str] = []
    data_dir = out_dir / "public" / "data"
    for path in data_dir.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(out_dir).as_posix()
        suffix = path.suffix.lower()
        before = path.read_bytes()
        if suffix in {".json", ".geojson"}:
            rewrite_json(path, remote_base)
        elif suffix == ".jsonl":
            rewrite_jsonl(path, remote_base)
        elif suffix in {".csv", ".html", ".md", ".txt", ".kml"}:
            rewrite_text_references(path, remote_base)
        else:
            continue
        if path.read_bytes() != before:
            changed.append(rel)
    return changed


def count_files(path: Path) -> int:
    return sum(1 for item in path.rglob("*") if item.is_file())


def dir_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def package_stats(path: Path, ignore_excluded_dirs: bool = False) -> tuple[int, int]:
    files = 0
    total_bytes = 0
    for current, dirs, names in os.walk(path):
        if ignore_excluded_dirs:
            dirs[:] = [name for name in dirs if name not in EXCLUDE_DIRS]
        current_path = Path(current)
        for name in names:
            item = current_path / name
            if item.is_file():
                files += 1
                total_bytes += item.stat().st_size
    return files, total_bytes


def heavy_public_dir_findings(package_dir: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for heavy_dir in sorted(HEAVY_PUBLIC_DIRS, key=lambda item: item.as_posix()):
        path = package_dir / heavy_dir
        if not path.exists():
            continue
        files = count_files(path) if path.is_dir() else 1
        size = dir_size(path) if path.is_dir() else path.stat().st_size
        findings.append({
            "path": heavy_dir.as_posix(),
            "exists": True,
            "files": files,
            "bytes": size,
            "human": bytes_human(size),
        })
    return findings


def local_heavy_asset_references(package_dir: Path) -> list[dict[str, Any]]:
    public_data = package_dir / "public" / "data"
    if not public_data.exists():
        return []

    references: list[dict[str, Any]] = []
    for path in sorted(item for item in public_data.rglob("*") if item.is_file() and item.suffix.lower() in TEXT_REFERENCE_SUFFIXES):
        try:
            lines = path.read_text(errors="ignore").splitlines()
        except OSError:
            continue
        for line_no, line in enumerate(lines, start=1):
            for match in LOCAL_HEAVY_ASSET_REF_RE.finditer(line):
                references.append({
                    "file": rel(path, package_dir),
                    "line": line_no,
                    "reference": match.group(0),
                })
    return references


def heavy_reference_fingerprint(source_root: Path = ROOT) -> dict[str, Any]:
    references = local_heavy_asset_references(source_root)
    normalized = "\n".join(
        f"{item['file']}:{item['line']}:{item['reference']}"
        for item in references
    )
    return {
        "algorithm": "sha256",
        "sha256": hashlib.sha256(normalized.encode()).hexdigest(),
        "reference_count": len(references),
    }


def manifest_source_fingerprint(package_dir: Path) -> dict[str, Any] | None:
    manifest_path = package_dir / "REMOTE_ASSET_PACKAGE_MANIFEST.json"
    if not manifest_path.exists():
        return None
    try:
        manifest = json.loads(manifest_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    fingerprint = (
        manifest.get("validation", {})
        .get("remote_validation", {})
        .get("source_reference_fingerprint")
    )
    if (
        isinstance(fingerprint, dict)
        and fingerprint.get("algorithm") == "sha256"
        and isinstance(fingerprint.get("sha256"), str)
        and isinstance(fingerprint.get("reference_count"), int)
        and fingerprint["reference_count"] > 0
    ):
        return fingerprint
    return None


def deploy_package_validation(
    package_dir: Path,
    ignore_excluded_dirs: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    summary: dict[str, Any] = {
        "package_dir": display_path(package_dir),
        "heavy_public_dirs": [],
        "local_heavy_asset_references": [],
    }
    if not package_dir.exists():
        errors.append(f"Deploy package does not exist: {display_path(package_dir)}")
        return summary, errors
    if not package_dir.is_dir():
        errors.append(f"Deploy package is not a directory: {display_path(package_dir)}")
        return summary, errors

    package_files, package_bytes = package_stats(package_dir, ignore_excluded_dirs)
    heavy_dirs = heavy_public_dir_findings(package_dir)
    local_refs = local_heavy_asset_references(package_dir)
    summary["file_count"] = package_files
    summary["bytes"] = package_bytes
    summary["human"] = bytes_human(package_bytes)
    summary["max_file_count"] = MAX_DEPLOY_PACKAGE_FILES
    summary["max_bytes"] = MAX_DEPLOY_PACKAGE_BYTES
    summary["ignored_runtime_dirs"] = sorted(EXCLUDE_DIRS) if ignore_excluded_dirs else []
    summary["heavy_public_dirs"] = heavy_dirs
    summary["local_heavy_asset_references"] = local_refs[:LOCAL_REF_PREVIEW_LIMIT]
    summary["local_heavy_asset_reference_preview_limit"] = LOCAL_REF_PREVIEW_LIMIT
    summary["heavy_public_dir_count"] = len(heavy_dirs)
    summary["local_heavy_asset_reference_count"] = len(local_refs)

    if heavy_dirs:
        details = ", ".join(f"{item['path']} ({item['files']} files, {item['human']})" for item in heavy_dirs)
        errors.append(f"Deploy package still contains local heavy public asset directories: {details}")
    if local_refs:
        preview = ", ".join(f"{item['file']}:{item['line']}" for item in local_refs[:10])
        errors.append(
            "Deploy package public data still contains local /data/tiles or /data/chips references"
            f" ({len(local_refs)} refs; first hits: {preview})"
        )
    if package_files > MAX_DEPLOY_PACKAGE_FILES:
        errors.append(
            f"Deploy package has {package_files} files, above the {MAX_DEPLOY_PACKAGE_FILES} file guard."
        )
    if package_bytes > MAX_DEPLOY_PACKAGE_BYTES:
        errors.append(
            f"Deploy package is {bytes_human(package_bytes)}, above the {bytes_human(MAX_DEPLOY_PACKAGE_BYTES)} guard."
        )
    return summary, errors


def remote_validation_gate(
    report_path: Path,
    remote_base: str,
    source_fingerprint: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    summary: dict[str, Any] = {
        "report": rel(report_path),
        "required": True,
        "remote_base": remote_base,
    }
    if not report_path.exists():
        errors.append(
            f"Remote validation report is missing: {rel(report_path)}. "
            "Run `python3 scripts/validate_remote_asset_urls.py` before building a pruned deploy package."
        )
        return summary, errors

    try:
        report = json.loads(report_path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Remote validation report cannot be read as JSON: {rel(report_path)}: {exc}")
        return summary, errors

    remote_assets = report.get("remote_assets") or {}
    deploy_gate = report.get("deploy_gate") or {}
    source_fingerprint = source_fingerprint or heavy_reference_fingerprint()
    report_fingerprint = report.get("source_reference_fingerprint")
    generated_utc = report.get("generated_utc")
    generated_at: datetime | None = None
    if isinstance(generated_utc, str):
        try:
            generated_at = datetime.fromisoformat(generated_utc.replace("Z", "+00:00"))
            if generated_at.tzinfo is None:
                generated_at = generated_at.replace(tzinfo=timezone.utc)
            generated_at = generated_at.astimezone(timezone.utc)
        except ValueError:
            generated_at = None
    now = datetime.now(timezone.utc)
    attestation_expires_utc = (
        (generated_at + MAX_REMOTE_ATTESTATION_AGE).isoformat()
        if generated_at is not None
        else None
    )
    failures = remote_assets.get("failures") or []
    quality_errors = remote_assets.get("quality_errors") or []
    sampled_cogs = remote_assets.get("sampled_cogs") or []
    sampled_tile_count = int(deploy_gate.get("sampled_tile_count") or 0)
    sampled_chip_count = int(deploy_gate.get("sampled_chip_count") or 0)
    cog_failures = [item for item in failures if item.get("kind") == "cog"]
    cog_quality_errors = [item for item in quality_errors if item.get("kind") == "cog"]

    summary.update({
        "generated_utc": generated_utc,
        "attestation_expires_utc": attestation_expires_utc,
        "max_attestation_age_seconds": int(MAX_REMOTE_ATTESTATION_AGE.total_seconds()),
        "report_result": report.get("result"),
        "report_remote_base": report.get("remote_base"),
        "remote_checked": remote_assets.get("checked", 0),
        "remote_failed": remote_assets.get("failed", 0),
        "quality_error_count": remote_assets.get("quality_error_count", 0),
        "sampled_cog_count": len(sampled_cogs),
        "sampled_tile_count": sampled_tile_count,
        "sampled_chip_count": sampled_chip_count,
        "cog_failure_count": len(cog_failures),
        "cog_quality_error_count": len(cog_quality_errors),
        "deploy_gate_ready": deploy_gate.get("pruned_remote_asset_package_ready"),
        "deploy_gate_blockers": deploy_gate.get("blockers") or [],
        "source_reference_fingerprint": source_fingerprint,
        "report_source_reference_fingerprint": report_fingerprint,
    })

    if report.get("remote_base") != remote_base:
        errors.append(
            f"Remote validation report used remote_base={report.get('remote_base')!r}, "
            f"but this package is being rewritten to {remote_base!r}"
        )
    if report.get("result") != "pass":
        errors.append("Remote validation report result is not pass; refusing to build a pruned deploy package.")
    if generated_at is None:
        errors.append(
            "Remote validation report has an invalid or missing generated_utc timestamp. "
            "Rerun `python3 scripts/validate_remote_asset_urls.py` before building or deploying."
        )
    elif now - generated_at > MAX_REMOTE_ATTESTATION_AGE:
        errors.append(
            f"Remote validation report is older than {int(MAX_REMOTE_ATTESTATION_AGE.total_seconds() // 3600)} hours. "
            "Rerun `python3 scripts/validate_remote_asset_urls.py` before building or deploying."
        )
    elif generated_at - now > timedelta(minutes=5):
        errors.append(
            "Remote validation report timestamp is in the future. "
            "Check the build clock and rerun `python3 scripts/validate_remote_asset_urls.py`."
        )
    if report_fingerprint != source_fingerprint:
        errors.append(
            "Remote validation report does not match the current tile/chip reference manifest. "
            "Rerun `python3 scripts/validate_remote_asset_urls.py` before building or deploying."
        )
    if deploy_gate and not deploy_gate.get("pruned_remote_asset_package_ready"):
        blockers = "; ".join(deploy_gate.get("blockers") or ["unspecified deploy gate blocker"])
        errors.append(f"Remote validation deploy gate is not ready: {blockers}")
    if not sampled_tile_count:
        errors.append("Remote validation report sampled zero tile URLs; remote tile availability was not verified.")
    if not sampled_chip_count:
        errors.append("Remote validation report sampled zero chip URLs; remote evidence-chip availability was not verified.")
    if not sampled_cogs:
        errors.append("Remote validation report sampled zero COG URLs; COG Range/content-type fallback was not verified.")
    if cog_failures or cog_quality_errors:
        errors.append(
            "Sampled COG fallback failed Range/content-type validation; refusing to build a pruned deploy package."
        )

    return summary, errors


def run_guards(
    package_dir: Path,
    remote_base: str,
    report_path: Path,
    skip_remote_validation_report: bool,
    source_fingerprint: dict[str, Any] | None = None,
    ignore_excluded_dirs: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    package_summary, package_errors = deploy_package_validation(package_dir, ignore_excluded_dirs)
    remote_summary: dict[str, Any] = {"required": False, "skipped": True}
    remote_errors: list[str] = []
    if not skip_remote_validation_report:
        remote_summary, remote_errors = remote_validation_gate(report_path, remote_base, source_fingerprint)
    summary = {
        "package": package_summary,
        "remote_validation": remote_summary,
    }
    return summary, package_errors + remote_errors


def print_guard_result(result: str, summary: dict[str, Any], errors: list[str]) -> None:
    print(json.dumps({
        "result": result,
        "validation": summary,
        "errors": errors,
    }, indent=2))


def build_manifest(
    package_dir: Path,
    remote_base: str,
    changed: list[str],
    validation: dict[str, Any],
    *,
    source_root: str,
) -> dict[str, Any]:
    package_summary = validation.get("package", {})
    return {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": source_root,
        "package_dir": display_path(package_dir),
        "remote_asset_base": remote_base,
        "excluded_dirs": sorted(EXCLUDE_DIRS),
        "excluded_file_names": sorted(EXCLUDE_FILE_NAMES),
        "excluded_file_prefixes": sorted(EXCLUDE_FILE_PREFIXES),
        "excluded_public_asset_dirs": sorted(path.as_posix() for path in HEAVY_PUBLIC_DIRS),
        "rewritten_files": changed,
        "validation": validation,
        "file_count": package_summary.get("file_count", count_files(package_dir)),
        "bytes": package_summary.get("bytes", dir_size(package_dir)),
        "warning": "This package expects /data/tiles and /data/chips to be available at remote_asset_base before production deploy.",
    }


def finalize_manifest(
    package_dir: Path,
    manifest: dict[str, Any],
    remote_base: str,
    report_path: Path,
    *,
    skip_remote_validation_report: bool = False,
    source_fingerprint: dict[str, Any] | None = None,
    ignore_excluded_dirs: bool = False,
) -> dict[str, Any]:
    manifest_path = package_dir / "REMOTE_ASSET_PACKAGE_MANIFEST.json"
    for _ in range(6):
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        validation, errors = run_guards(
            package_dir,
            remote_base,
            report_path,
            skip_remote_validation_report,
            source_fingerprint,
            ignore_excluded_dirs,
        )
        if errors:
            print_guard_result("fail", validation, errors)
            raise SystemExit(1)
        package_summary = validation["package"]
        next_file_count = package_summary["file_count"]
        next_bytes = package_summary["bytes"]
        if (
            manifest.get("validation") == validation
            and manifest.get("file_count") == next_file_count
            and manifest.get("bytes") == next_bytes
        ):
            return manifest
        manifest["validation"] = validation
        manifest["file_count"] = next_file_count
        manifest["bytes"] = next_bytes
    raise SystemExit("Package manifest totals did not converge after six validation passes.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-base", default=DEFAULT_REMOTE_BASE, help="Public base URL that serves /data/tiles and /data/chips")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output package directory")
    parser.add_argument("--force", action="store_true", help="Delete output directory if it already exists")
    parser.add_argument("--check-only", action="store_true", help="Validate an existing deploy package without copying or rewriting files")
    parser.add_argument("--package", type=Path, help="Existing deploy package directory to validate with --check-only; defaults to --out")
    parser.add_argument(
        "--prepare-package",
        type=Path,
        help=(
            "Rewrite an already-pruned package in place. The repository root is accepted only in Vercel, "
            "where --prune-heavy may remove tracked heavy assets from the ephemeral build checkout."
        ),
    )
    parser.add_argument(
        "--prune-heavy",
        action="store_true",
        help=(
            "With --prepare-package, remove local tile/chip directories from the ephemeral Vercel checkout "
            "after the remote validation and source-fingerprint gates pass"
        ),
    )
    parser.add_argument("--remote-validation-report", type=Path, default=DEFAULT_REMOTE_VALIDATION_REPORT, help="Remote asset validation JSON report required for pruned deploy packages")
    parser.add_argument(
        "--skip-remote-validation-report",
        action="store_true",
        help="Only run deterministic local package guards; accepted for Vercel preview preparation, never production",
    )
    args = parser.parse_args()

    remote_base = normalize_base(args.remote_base)
    out_dir = args.out.resolve()
    report_path = args.remote_validation_report.resolve()

    if args.prepare_package:
        preview_skip = (
            args.skip_remote_validation_report
            and os.environ.get("VERCEL") == "1"
            and os.environ.get("VERCEL_ENV") == "preview"
        )
        if args.skip_remote_validation_report and not preview_skip:
            raise SystemExit(
                "--skip-remote-validation-report can be used with --prepare-package only for a Vercel preview; "
                "production pruning requires a fresh remote attestation."
            )
        package_dir = args.prepare_package.resolve()
        if package_dir == ROOT and os.environ.get("VERCEL") != "1":
            raise SystemExit(
                "Refusing to rewrite the development checkout in place. "
                "Use the default copy mode, or run this command inside Vercel where VERCEL=1."
            )
        source_fingerprint = heavy_reference_fingerprint(package_dir)
        if source_fingerprint["reference_count"] == 0:
            source_fingerprint = manifest_source_fingerprint(package_dir) or source_fingerprint
        heavy_dirs = heavy_public_dir_findings(package_dir)
        remote_summary: dict[str, Any] = {
            "required": False,
            "skipped": True,
            "reason": "Vercel preview uses deterministic package guards; production performs live remote validation.",
        }
        remote_errors: list[str] = []
        if not preview_skip:
            remote_summary, remote_errors = remote_validation_gate(report_path, remote_base, source_fingerprint)
        preflight_errors = list(remote_errors)
        if heavy_dirs and not args.prune_heavy:
            details = ", ".join(f"{item['path']} ({item['files']} files, {item['human']})" for item in heavy_dirs)
            preflight_errors.append(
                "In-place production preparation requires a pruned source tree, but heavy asset directories remain: "
                f"{details}"
            )
        if preflight_errors:
            print_guard_result(
                "fail",
                {
                    "package": {
                        "package_dir": display_path(package_dir),
                        "heavy_public_dirs": heavy_dirs,
                    },
                    "remote_validation": remote_summary,
                },
                preflight_errors,
            )
            raise SystemExit(1)

        if args.prune_heavy:
            for heavy_dir in HEAVY_PUBLIC_DIRS:
                path = package_dir / heavy_dir
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()

        changed = rewrite_asset_references(package_dir, remote_base)
        validation, errors = run_guards(
            package_dir,
            remote_base,
            report_path,
            preview_skip,
            source_fingerprint,
            True,
        )
        if errors:
            print_guard_result("fail", validation, errors)
            raise SystemExit(1)
        manifest = build_manifest(
            package_dir,
            remote_base,
            changed,
            validation,
            source_root="pruned Vercel source checkout",
        )
        manifest["pruned_heavy_dirs"] = [
            item["path"]
            for item in heavy_dirs
        ]
        manifest = finalize_manifest(
            package_dir,
            manifest,
            remote_base,
            report_path,
            skip_remote_validation_report=preview_skip,
            source_fingerprint=source_fingerprint,
            ignore_excluded_dirs=True,
        )
        print(json.dumps(manifest, indent=2))
        return

    if args.check_only:
        package_dir = (args.package or args.out).resolve()
        source_fingerprint = manifest_source_fingerprint(package_dir)
        validation, errors = run_guards(
            package_dir,
            remote_base,
            report_path,
            args.skip_remote_validation_report,
            source_fingerprint,
        )
        if errors:
            print_guard_result("fail", validation, errors)
            raise SystemExit(1)
        print_guard_result("pass", validation, [])
        return

    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"Output already exists: {out_dir}. Use --force to replace it.")
        shutil.rmtree(out_dir)

    shutil.copytree(ROOT, out_dir, ignore=ignore)
    changed = rewrite_asset_references(out_dir, remote_base)
    validation, errors = run_guards(out_dir, remote_base, report_path, args.skip_remote_validation_report)
    if errors:
        print_guard_result("fail", validation, errors)
        raise SystemExit(1)

    manifest = build_manifest(
        out_dir,
        remote_base,
        changed,
        validation,
        source_root="repository root",
    )
    manifest = finalize_manifest(
        out_dir,
        manifest,
        remote_base,
        report_path,
        skip_remote_validation_report=args.skip_remote_validation_report,
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
