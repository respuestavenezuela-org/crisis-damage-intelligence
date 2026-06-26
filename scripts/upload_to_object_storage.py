#!/usr/bin/env python3
"""Upload static AOI outputs to S3-compatible object storage.

Requires env:
  S3_ENDPOINT_URL
  S3_BUCKET
  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY

Optional:
  S3_PREFIX
  AWS_DEFAULT_REGION
"""
import os
import subprocess
import sys
from pathlib import Path


def require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("Usage: scripts/upload_to_object_storage.py LOCAL_PATH REMOTE_PREFIX")
    local_path = Path(sys.argv[1])
    remote_prefix = sys.argv[2].strip("/")
    endpoint = require("S3_ENDPOINT_URL")
    bucket = require("S3_BUCKET")
    if not local_path.exists():
        raise SystemExit(f"Local path does not exist: {local_path}")

    target = f"s3://{bucket}/{remote_prefix}"
    cmd = [
        "aws",
        "s3",
        "sync" if local_path.is_dir() else "cp",
        str(local_path),
        target if local_path.is_dir() else f"{target}/{local_path.name}",
        "--endpoint-url",
        endpoint,
        "--only-show-errors",
    ]
    subprocess.run(cmd, check=True)
    print(f"Uploaded {local_path} -> {target}")


if __name__ == "__main__":
    main()
