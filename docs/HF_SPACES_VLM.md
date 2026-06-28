# Hugging Face Spaces VLM Shift

Status: wired as primary VLM provider on 2026-06-28.

## Hugging Face Account

- Account display name: `Luis Rosal`
- Hugging Face username: `takove`
- Profile URL: `https://huggingface.co/takove`

Hugging Face settings did not expose a separate numeric account ID in the web UI. For credits, repository ownership, and Space assignment, the username `takove` is the account identifier to use.

## Provider Policy

The VLM runners now default to Hugging Face Spaces:

```bash
export VLM_PROVIDER=hf_space
export HF_SPACE_API_URL="https://<space-host>/..."
export HF_VLM_MODEL="Qwen/Qwen3-VL-8B-Instruct"
# optional for private Spaces:
export HF_TOKEN="..."
```

MiniMax is no longer the default provider. It is retained only as an explicit legacy fallback:

```bash
export VLM_PROVIDER=minimax
export MINIMAX_API_KEY="..."
```

## Expected HF Space Contract

The Space endpoint should accept a JSON `POST` body:

```json
{
  "system": "string",
  "prompt": "string",
  "images": ["data:image/png;base64,..."],
  "metadata": {"aoi_id": "...", "id": "..."},
  "response_format": "json"
}
```

The endpoint should return either a JSON object directly or one of these wrapper shapes:

```json
{"result": {"damage_class": "..."}}
{"prediction": {"damage_class": "..."}}
{"output": {"damage_class": "..."}}
```

Required VLM output keys remain unchanged:

- before/after: `damage_class`, `damage_percent`, `confidence`, `change_evidence`, `before_observation`, `after_observation`, `image_alignment`, `image_quality`, `action_priority`, `uncertainty_reason`
- post-event-only: `damage_class`, `damage_percent`, `confidence`, `evidence`, `image_quality`, `action_priority`, `uncertainty_reason`

The adapter records `vlm_provider: hf_space` in new outputs.

## Entry Points

Preferred scripts:

```bash
python3 scripts/run_hf_space_ems_before_after_review.py emsr884-aoi12-caraballeda --limit 10
python3 scripts/run_hf_space_ems_post_event_review.py emsr884-aoi08-san-felipe --limit 10
```

Legacy filenames still work, but they now call the shared provider adapter and default to HF Spaces unless `VLM_PROVIDER=minimax` is explicitly set.
