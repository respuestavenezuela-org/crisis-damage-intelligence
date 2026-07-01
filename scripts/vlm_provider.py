#!/usr/bin/env python3
"""VLM provider adapter for emergency damage triage scripts.

Primary provider is a Hugging Face Space HTTP endpoint. MiniMax is retained as
an explicit legacy fallback only when VLM_PROVIDER=minimax is set.
"""

import base64
import json
import os
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REQUIRED_KEYS = {
    "dated_pre_event_comparison": (
        "damage_class",
        "damage_percent",
        "confidence",
        "change_evidence",
        "before_observation",
        "after_observation",
        "image_alignment",
        "image_quality",
        "action_priority",
        "uncertainty_reason",
    ),
    "post_event_only": (
        "damage_class",
        "damage_percent",
        "confidence",
        "evidence",
        "image_quality",
        "action_priority",
        "uncertainty_reason",
    ),
}


def encode_image(path: str | Path) -> str:
    path = Path(path)
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _extract_json_text(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError(f"No JSON object in VLM response: {text[:400]}")
    return json.loads(match.group(0))


def hf_space_api_url() -> str:
    url = os.environ.get("HF_SPACE_API_URL", "").strip()
    if url:
        return url
    space_id = os.environ.get("HF_SPACE_ID", "").strip()
    if "/" in space_id:
        owner, name = space_id.split("/", 1)
        return f"https://{owner}-{name}.hf.space/predict"
    raise SystemExit("HF_SPACE_API_URL missing. Set it to the Hugging Face Space /predict endpoint.")


def hf_token() -> str:
    return (os.environ.get("HF_TOKEN") or os.environ.get("HF-TOKEN") or "").strip()


def validate_result(result: dict, review_type: str) -> None:
    required = REQUIRED_KEYS.get(review_type)
    if not required:
        return
    missing = [key for key in required if key not in result]
    if missing:
        raise ValueError(f"VLM response missing required {review_type} keys: {', '.join(missing)}")


def call_hf_space(system: str, prompt: str, image_paths: list[str | Path], metadata: dict, review_type: str) -> dict:
    url = hf_space_api_url()
    token = hf_token()
    model = os.environ.get("HF_VLM_MODEL", "Qwen/Qwen3-VL-8B-Instruct")
    payload = {
        "system": system,
        "prompt": prompt,
        "images": [encode_image(path) for path in image_paths],
        "metadata": metadata,
        "response_format": "json",
    }
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    raw = ""
    attempts = max(1, int(os.environ.get("HF_SPACE_RETRIES", "4")))
    retry_seconds = max(1.0, float(os.environ.get("HF_SPACE_RETRY_SECONDS", "8")))
    timeout = int(os.environ.get("HF_SPACE_TIMEOUT_SECONDS", "180"))
    for attempt in range(1, attempts + 1):
        req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            break
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == attempts:
                raise RuntimeError(f"HF Space HTTP {exc.code}: {detail}") from exc
            time.sleep(retry_seconds * attempt)
        except URLError as exc:
            if attempt == attempts:
                raise RuntimeError(f"HF Space request failed: {exc}") from exc
            time.sleep(retry_seconds * attempt)
    data = json.loads(raw)
    if isinstance(data, dict) and data.get("error") and not any(key in data for key in ("result", "prediction", "output")):
        raise RuntimeError(f"HF Space returned error: {data.get('error')}")
    result = data.get("result") or data.get("prediction") or data.get("output") or data
    if isinstance(result, str):
        result = _extract_json_text(result)
    if not isinstance(result, dict):
        raise ValueError(f"Unexpected HF Space response shape: {raw[:400]}")
    validate_result(result, review_type)
    result["vlm_model"] = model
    result["vlm_provider"] = "hf_space"
    result["review_type"] = review_type
    return result


def call_minimax_legacy(system: str, prompt: str, image_paths: list[str | Path], review_type: str) -> dict:
    key = os.environ.get("MINIMAX_API_KEY")
    if not key:
        raise SystemExit("MINIMAX_API_KEY missing and VLM_PROVIDER=minimax was requested")
    model = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
                + [{"type": "image_url", "image_url": {"url": encode_image(path)}} for path in image_paths],
            },
        ],
        "temperature": 0,
    }
    req = Request(
        "https://api.minimax.io/v1/text/chatcompletion_v2",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MiniMax HTTP {exc.code}: {detail}") from exc
    data = json.loads(raw)
    text = data["choices"][0]["message"]["content"]
    result = _extract_json_text(text)
    validate_result(result, review_type)
    result["vlm_model"] = model
    result["vlm_provider"] = "minimax_legacy"
    result["review_type"] = review_type
    return result


def call_vlm(system: str, prompt: str, image_paths: list[str | Path], metadata: dict, review_type: str) -> dict:
    provider = os.environ.get("VLM_PROVIDER", "hf_space").strip().lower()
    if provider in ("hf", "hf_space", "huggingface", "huggingface_space"):
        return call_hf_space(system, prompt, image_paths, metadata, review_type)
    if provider == "minimax":
        return call_minimax_legacy(system, prompt, image_paths, review_type)
    raise SystemExit(f"Unsupported VLM_PROVIDER={provider!r}; use hf_space or minimax")
