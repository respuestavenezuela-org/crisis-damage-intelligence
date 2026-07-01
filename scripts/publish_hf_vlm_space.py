#!/usr/bin/env python3
"""Create or update the Hugging Face Space used by offline VLM triage."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO_ID = "takove/respuesta-venezuela-vlm"
DEFAULT_SPACE_DIR = ROOT / "spaces" / "vlm-damage-triage"


def space_base_url(repo_id: str) -> str:
    owner, name = repo_id.split("/", 1)
    return f"https://{owner}-{name}.hf.space"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key == "HF-TOKEN":
            key = "HF_TOKEN"
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID, help="HF Space repo id, for example takove/respuesta-venezuela-vlm")
    parser.add_argument("--space-dir", type=Path, default=DEFAULT_SPACE_DIR, help="Local Space directory to upload")
    parser.add_argument("--model", default="Qwen/Qwen3-VL-8B-Instruct", help="HF_VLM_MODEL value for the Space")
    parser.add_argument("--max-new-tokens", default="768", help="MAX_NEW_TOKENS value for the Space")
    parser.add_argument("--hardware", default="", help="Optional Space hardware flavor, for example l4x1")
    parser.add_argument("--sleep-time", type=int, default=None, help="Optional Space sleep timeout in seconds")
    parser.add_argument("--private", action="store_true", help="Create the Space as private if it does not exist")
    parser.add_argument("--enable-inference", action="store_true", help="Set DRY_RUN=0. Default keeps DRY_RUN=1")
    parser.add_argument("--set-hf-token-secret", action="store_true", help="Also set HF_TOKEN as a Space secret from the local HF_TOKEN")
    parser.add_argument("--restart", action="store_true", help="Restart the Space after upload")
    return parser.parse_args()


def main() -> int:
    load_env(ROOT / ".env")
    args = parse_args()
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise SystemExit("Set HF_TOKEN to a Hugging Face write token before publishing the Space.")
    if "/" not in args.repo_id:
        raise SystemExit("--repo-id must be in owner/name form.")
    if not args.space_dir.exists():
        raise SystemExit(f"Space directory does not exist: {args.space_dir}")

    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise SystemExit("Install huggingface_hub before publishing: python3 -m pip install huggingface_hub") from exc

    api = HfApi(token=token)
    variables = [
        {"key": "HF_VLM_MODEL", "value": args.model},
        {"key": "MAX_NEW_TOKENS", "value": str(args.max_new_tokens)},
    ]
    if not args.enable_inference:
        variables.append({"key": "DRY_RUN", "value": "1"})

    create_kwargs = {
        "repo_id": args.repo_id,
        "repo_type": "space",
        "space_sdk": "docker",
        "exist_ok": True,
        "private": args.private,
        "space_variables": variables,
        "token": token,
    }
    if args.hardware:
        create_kwargs["space_hardware"] = args.hardware
    if args.sleep_time is not None:
        create_kwargs["space_sleep_time"] = args.sleep_time
    api.create_repo(**create_kwargs)

    for variable in variables:
        api.add_space_variable(args.repo_id, variable["key"], variable["value"], token=token)
    if args.enable_inference:
        try:
            api.delete_space_variable(args.repo_id, "DRY_RUN", token=token)
        except Exception:
            pass
    if args.set_hf_token_secret:
        api.add_space_secret(args.repo_id, "HF_TOKEN", token, token=token)
    if args.hardware:
        api.request_space_hardware(args.repo_id, hardware=args.hardware, sleep_time=args.sleep_time, token=token)

    commit = api.upload_folder(
        repo_id=args.repo_id,
        repo_type="space",
        folder_path=args.space_dir,
        commit_message="Update Respuesta Venezuela VLM Space",
        allow_patterns=["README.md", "Dockerfile", "requirements.txt", "app.py"],
        token=token,
    )
    if args.restart:
        api.restart_space(args.repo_id, token=token)

    base_url = space_base_url(args.repo_id)
    print(f"Uploaded {args.space_dir} to {args.repo_id}")
    print(f"Commit: {commit.oid}")
    print(f"Space URL: {base_url}")
    print(f"API endpoint: {base_url}/predict")
    print(f"Space DRY_RUN={'0' if args.enable_inference else '1'}")
    print("Local batch env:")
    print("  export VLM_PROVIDER=hf_space")
    print(f"  export HF_SPACE_ID={args.repo_id}")
    print(f"  export HF_VLM_MODEL={args.model}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
