import base64
import io
import json
import os
import re
from functools import lru_cache
from typing import Any

import torch
from fastapi import FastAPI, HTTPException
from PIL import Image
from pydantic import BaseModel, Field
from transformers import AutoModelForImageTextToText, AutoProcessor

try:
    from transformers import Qwen3VLForConditionalGeneration
except ImportError:  # pragma: no cover - depends on the Space transformers build.
    Qwen3VLForConditionalGeneration = None

try:
    from qwen_vl_utils import process_vision_info
except ImportError:  # pragma: no cover - optional fallback helper.
    process_vision_info = None


MODEL_ID = os.environ.get("HF_VLM_MODEL", "Qwen/Qwen3-VL-8B-Instruct")
MAX_NEW_TOKENS = int(os.environ.get("MAX_NEW_TOKENS", "768"))
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"

app = FastAPI(title="Respuesta Venezuela VLM Damage Triage")


class PredictRequest(BaseModel):
    system: str = ""
    prompt: str
    images: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    response_format: str = "json"


def decode_image(data_url: str) -> Image.Image:
    if "," in data_url and data_url.startswith("data:image"):
        data_url = data_url.split(",", 1)[1]
    try:
        raw = base64.b64decode(data_url)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}") from exc


def extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise HTTPException(status_code=502, detail=f"Model did not return JSON: {text[:500]}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid model JSON: {exc}") from exc


@lru_cache(maxsize=1)
def load_model():
    processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)
    model_cls = (
        Qwen3VLForConditionalGeneration
        if Qwen3VLForConditionalGeneration and "qwen3-vl" in MODEL_ID.lower()
        else AutoModelForImageTextToText
    )
    model_kwargs = {
        "torch_dtype": torch.bfloat16 if torch.cuda.is_available() else torch.float32,
        "device_map": "auto",
        "trust_remote_code": True,
    }
    attn_implementation = os.environ.get("ATTN_IMPLEMENTATION", "sdpa").strip()
    if attn_implementation:
        model_kwargs["attn_implementation"] = attn_implementation
    try:
        model = model_cls.from_pretrained(MODEL_ID, **model_kwargs)
    except TypeError:
        model_kwargs.pop("attn_implementation", None)
        model = model_cls.from_pretrained(MODEL_ID, **model_kwargs)
    model.eval()
    return processor, model


def dry_result(req: PredictRequest) -> dict[str, Any]:
    review_type = "dated_pre_event_comparison" if len(req.images) != 1 or "before" in req.prompt.lower() else "post_event_only"
    result = {
        "damage_class": "uncertain_comparison_problem" if review_type == "dated_pre_event_comparison" else "uncertain_imagery_problem",
        "damage_percent": None,
        "confidence": 0.0,
        "image_quality": "dry_run",
        "action_priority": "review",
        "uncertainty_reason": "DRY_RUN=1; no VLM inference was executed.",
        "review_type": review_type,
        "vlm_model": MODEL_ID,
    }
    if review_type == "dated_pre_event_comparison":
        result.update(
            {
                "change_evidence": "DRY_RUN=1; before/after comparison was not executed.",
                "before_observation": "DRY_RUN=1; before image not inspected.",
                "after_observation": "DRY_RUN=1; after image not inspected.",
                "image_alignment": "dry_run",
            }
        )
    else:
        result["evidence"] = "DRY_RUN=1; post-event image was not inspected."
    return result


def model_device(model) -> torch.device:
    try:
        return model.device
    except AttributeError:
        return next(model.parameters()).device


def build_messages(req: PredictRequest, images: list[Image.Image]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    if req.system:
        messages.append({"role": "system", "content": [{"type": "text", "text": req.system}]})
    content: list[dict[str, Any]] = [{"type": "image", "image": image} for image in images]
    content.append({"type": "text", "text": req.prompt})
    messages.append({"role": "user", "content": content})
    return messages


def prepare_inputs(processor, model, messages: list[dict[str, Any]], images: list[Image.Image]):
    try:
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
    except Exception:
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        processor_kwargs: dict[str, Any] = {"text": [text], "images": images, "return_tensors": "pt"}
        if process_vision_info:
            try:
                image_inputs, video_inputs = process_vision_info(messages)
                processor_kwargs["images"] = image_inputs or images
                if video_inputs:
                    processor_kwargs["videos"] = video_inputs
            except Exception:
                pass
        inputs = processor(**processor_kwargs)
    inputs.pop("token_type_ids", None)
    return inputs.to(model_device(model))


@app.get("/")
def health() -> dict[str, Any]:
    return {"ok": True, "model": MODEL_ID, "dry_run": DRY_RUN}


@app.post("/predict")
def predict(req: PredictRequest) -> dict[str, Any]:
    if not req.images:
        raise HTTPException(status_code=400, detail="At least one image is required")
    if DRY_RUN:
        return {"result": dry_result(req)}

    images = [decode_image(image) for image in req.images]
    processor, model = load_model()

    messages = build_messages(req, images)
    inputs = prepare_inputs(processor, model, messages, images)
    with torch.inference_mode():
        output_ids = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    generated_ids = output_ids[:, inputs.input_ids.shape[-1]:]
    answer = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    result = extract_json(answer)
    result.setdefault("vlm_model", MODEL_ID)
    return {"result": result}
