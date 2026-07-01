---
title: Respuesta Venezuela VLM Damage Triage
emoji: 🛰️
colorFrom: red
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# Respuesta Venezuela VLM Damage Triage

HTTP VLM inference Space for `respuestavenezuela.org` batch damage-triage jobs.

Default model target:

- `Qwen/Qwen3-VL-8B-Instruct`

Fallback model target:

- `OpenGVLab/InternVL3_5-8B`

The public app does not depend on this Space at runtime. This Space is used only by offline/batch VLM scripts that generate static JSONL evidence files.

## Endpoint

```http
POST /predict
Content-Type: application/json
Authorization: Bearer <HF_TOKEN> # optional/private Space
```

Input:

```json
{
  "system": "string",
  "prompt": "string",
  "images": ["data:image/png;base64,..."],
  "metadata": {"aoi_id": "...", "id": "..."},
  "response_format": "json"
}
```

Output:

```json
{
  "result": {
    "damage_class": "possible_major_damage",
    "damage_percent": 70,
    "confidence": 0.65,
    "image_quality": "usable",
    "action_priority": "urgent_review",
    "uncertainty_reason": "..."
  }
}
```

VLM output is triage evidence only. Official EMS labels remain the source of record.

## Publish

From the repo root:

```bash
export HF_TOKEN="<write token>"
python3 scripts/publish_hf_vlm_space.py --repo-id takove/respuesta-venezuela-vlm
```

That publish leaves `DRY_RUN=1`. Enable real inference only after credits/hardware are available:

```bash
python3 scripts/publish_hf_vlm_space.py \
  --repo-id takove/respuesta-venezuela-vlm \
  --hardware l4x1 \
  --sleep-time 3600 \
  --enable-inference \
  --restart
```
