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
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT.parent / "crisis_damage_intelligence_vercel_remote_assets"
DEFAULT_REMOTE_BASE = "https://pub-35cd6458677c4b4c844a23fb91b0370e.r2.dev"

EXCLUDE_DIRS = {
    ".git",
    ".next",
    ".vercel",
    ".wrangler",
    "node_modules",
    "ops",
    "qa",
    "outputs",
}

HEAVY_PUBLIC_DIRS = {
    Path("public/data/tiles"),
    Path("public/data/chips"),
}


def normalize_base(value: str) -> str:
    return value.rstrip("/")


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
    text = text.replace("/data/tiles/", f"{remote_base}/data/tiles/")
    text = text.replace("/data/chips/", f"{remote_base}/data/chips/")
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
        elif suffix in {".csv", ".html", ".md", ".txt"}:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-base", default=DEFAULT_REMOTE_BASE, help="Public base URL that serves /data/tiles and /data/chips")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Output package directory")
    parser.add_argument("--force", action="store_true", help="Delete output directory if it already exists")
    args = parser.parse_args()

    remote_base = normalize_base(args.remote_base)
    out_dir = args.out.resolve()
    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"Output already exists: {out_dir}. Use --force to replace it.")
        shutil.rmtree(out_dir)

    shutil.copytree(ROOT, out_dir, ignore=ignore)
    changed = rewrite_asset_references(out_dir, remote_base)

    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(ROOT),
        "package_dir": str(out_dir),
        "remote_asset_base": remote_base,
        "excluded_dirs": sorted(EXCLUDE_DIRS),
        "excluded_public_asset_dirs": sorted(path.as_posix() for path in HEAVY_PUBLIC_DIRS),
        "rewritten_files": changed,
        "file_count": count_files(out_dir),
        "bytes": dir_size(out_dir),
        "warning": "This package expects /data/tiles and /data/chips to be available at remote_asset_base before production deploy.",
    }
    manifest_path = out_dir / "REMOTE_ASSET_PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
