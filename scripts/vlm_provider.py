#!/usr/bin/env python3
"""VLM provider adapter for emergency damage triage scripts.

Primary provider is a Hugging Face Space HTTP endpoint. MiniMax is retained as
an explicit legacy fallback only when VLM_PROVIDER=minimax is set.
"""

import base64
import json
import os
import re
import socket
import threading
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
    "temporal_response_comparison": (
        "response_class",
        "confidence",
        "image_quality",
        "alignment_quality",
        "observed_assets",
        "temporal_change",
        "first_visible_date",
        "last_absent_date",
        "evidence",
        "human_review_priority",
        "uncertainty_reason",
    ),
}

_MINIMAX_CALL_LOCK = threading.Lock()
_MINIMAX_CALL_COUNT = 0


def _reserve_minimax_call() -> int:
    """Atomically enforce a per-process request ceiling, including retries."""

    global _MINIMAX_CALL_COUNT
    maximum = max(0, int(os.environ.get("MINIMAX_MAX_CALLS", "0")))
    with _MINIMAX_CALL_LOCK:
        if maximum and _MINIMAX_CALL_COUNT >= maximum:
            raise RuntimeError(f"MiniMax request ceiling reached ({maximum} calls)")
        _MINIMAX_CALL_COUNT += 1
        return _MINIMAX_CALL_COUNT


def _release_minimax_call() -> None:
    """Release a reservation when MiniMax explicitly reports a no-usage quota response."""

    global _MINIMAX_CALL_COUNT
    with _MINIMAX_CALL_LOCK:
        _MINIMAX_CALL_COUNT = max(0, _MINIMAX_CALL_COUNT - 1)


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


def call_hf_router(system: str, prompt: str, image_paths: list[str | Path], metadata: dict, review_type: str) -> dict:
    """Call Hugging Face's OpenAI-compatible inference router.

    The router uses the user's Hugging Face credits and avoids coupling batch
    work to the lifecycle of the project's optional private Space.
    """

    token = hf_token()
    if not token:
        cached = Path.home() / ".cache" / "huggingface" / "token"
        if cached.is_file():
            token = cached.read_text().strip()
    if not token:
        raise SystemExit("HF_TOKEN missing and no cached Hugging Face token was found.")

    url = os.environ.get("HF_ROUTER_API_URL", "https://router.huggingface.co/v1/chat/completions").strip()
    model = os.environ.get("HF_VLM_MODEL", "Qwen/Qwen3-VL-30B-A3B-Instruct")
    content = [
        {"type": "image_url", "image_url": {"url": encode_image(path)}}
        for path in image_paths
    ]
    content.append({"type": "text", "text": prompt})
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        "temperature": 0,
        "max_tokens": int(os.environ.get("HF_ROUTER_MAX_TOKENS", "900")),
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    raw = ""
    attempts = max(1, int(os.environ.get("HF_ROUTER_RETRIES", "4")))
    retry_seconds = max(1.0, float(os.environ.get("HF_ROUTER_RETRY_SECONDS", "6")))
    timeout = int(os.environ.get("HF_ROUTER_TIMEOUT_SECONDS", "180"))
    for attempt in range(1, attempts + 1):
        req = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            break
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            if exc.code not in (408, 429, 500, 502, 503, 504) or attempt == attempts:
                raise RuntimeError(f"HF Router HTTP {exc.code}: {detail}") from exc
            time.sleep(retry_seconds * attempt)
        except (URLError, TimeoutError, ConnectionError) as exc:
            if attempt == attempts:
                raise RuntimeError(f"HF Router request failed: {exc}") from exc
            time.sleep(retry_seconds * attempt)

    data = json.loads(raw)
    choices = data.get("choices") or []
    if not choices:
        raise ValueError(f"Unexpected HF Router response shape: {raw[:600]}")
    result = choices[0].get("message", {}).get("content")
    if isinstance(result, str):
        result = _extract_json_text(result)
    if not isinstance(result, dict):
        raise ValueError(f"Unexpected HF Router model output: {raw[:600]}")
    validate_result(result, review_type)
    result["vlm_model"] = data.get("model") or model
    result["vlm_provider"] = "hf_router"
    result["review_type"] = review_type
    result["source_metadata"] = metadata
    if isinstance(data.get("usage"), dict):
        result["provider_usage"] = data["usage"]
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
    raw = ""
    attempts = max(1, int(os.environ.get("MINIMAX_RETRIES", "75")))
    retry_seconds = max(1.0, float(os.environ.get("MINIMAX_RETRY_SECONDS", "8")))
    quota_retry_seconds = max(1.0, float(os.environ.get("MINIMAX_QUOTA_RETRY_SECONDS", "300")))
    timeout = int(os.environ.get("MINIMAX_TIMEOUT_SECONDS", "180"))
    for attempt in range(1, attempts + 1):
        _reserve_minimax_call()
        req = Request(
            "https://api.minimax.io/v1/text/chatcompletion_v2",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            base_response = data.get("base_resp") or {}
            status_code = int(base_response.get("status_code") or 0)
            if status_code in (2056, 2062):
                _release_minimax_call()
                if attempt == attempts:
                    raise RuntimeError(
                        "MiniMax Token Plan rate limit remained active after "
                        f"{attempts} attempts: {base_response.get('status_msg')}"
                    )
                print(
                    f"MiniMax Token Plan quota reached; waiting {quota_retry_seconds:.0f}s "
                    f"before retry {attempt + 1}/{attempts}",
                    flush=True,
                )
                time.sleep(quota_retry_seconds)
                continue
            if status_code:
                raise RuntimeError(
                    f"MiniMax API status {status_code}: {base_response.get('status_msg')}"
                )
            choices = data.get("choices") or []
            if not choices:
                raise ValueError(f"MiniMax returned no completion choices: {base_response}")
            text = choices[0]["message"]["content"]
            result = _extract_json_text(text)
            validate_result(result, review_type)
            result["vlm_model"] = model
            result["vlm_provider"] = "minimax_legacy"
            result["review_type"] = review_type
            if isinstance(data.get("usage"), dict):
                result["provider_usage"] = data["usage"]
            return result
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code in (408, 429, 500, 502, 503, 504)
            if not retryable or attempt == attempts:
                raise RuntimeError(f"MiniMax HTTP {exc.code}: {detail}") from exc
            if exc.code == 429:
                retry_after = exc.headers.get("Retry-After")
                try:
                    wait_seconds = max(quota_retry_seconds, float(retry_after or 0))
                except ValueError:
                    wait_seconds = quota_retry_seconds
            else:
                wait_seconds = retry_seconds * min(attempt, 8)
            print(
                f"MiniMax HTTP {exc.code}; waiting {wait_seconds:.0f}s "
                f"before retry {attempt + 1}/{attempts}",
                flush=True,
            )
            time.sleep(wait_seconds)
        except (URLError, TimeoutError, socket.timeout) as exc:
            if attempt == attempts:
                raise RuntimeError(f"MiniMax request failed: {exc}") from exc
            time.sleep(retry_seconds * min(attempt, 8))
    raise RuntimeError("MiniMax request attempts exhausted without a usable result")


def call_vlm(system: str, prompt: str, image_paths: list[str | Path], metadata: dict, review_type: str) -> dict:
    provider = os.environ.get("VLM_PROVIDER", "hf_space").strip().lower()
    if provider in ("hf_router", "huggingface_router", "router"):
        return call_hf_router(system, prompt, image_paths, metadata, review_type)
    if provider in ("hf", "hf_space", "huggingface", "huggingface_space"):
        return call_hf_space(system, prompt, image_paths, metadata, review_type)
    if provider == "minimax":
        return call_minimax_legacy(system, prompt, image_paths, review_type)
    raise SystemExit(f"Unsupported VLM_PROVIDER={provider!r}; use hf_router, hf_space, or minimax")
