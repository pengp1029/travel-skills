# Doubao Seedance API Reference

This reference summarizes the Doubao/Seedance video generation workflow for travel vlog production. Use it when generating attraction, food, city vibe, and B-roll clips.

## API Shape

Doubao video generation is exposed through Volcengine Ark content generation tasks. The workflow is asynchronous:

```text
create task -> poll task -> download content.video_url -> save local MP4
```

Typical Python SDK usage:

```python
from volcenginesdkarkruntime import Ark

client = Ark(api_key=os.environ.get("ARK_API_KEY"))
create_result = client.content_generation.tasks.create(
    model="doubao-seedance-2-0-260128",
    content=[{"type": "text", "text": "travel vlog prompt"}],
    resolution="720p",
    ratio="9:16",
    duration=5,
    watermark=False,
    return_last_frame=True,
)
get_result = client.content_generation.tasks.get(task_id=create_result.id)
```

## Authentication

Prefer environment variables instead of inline keys:

- `ARK_API_KEY`: preferred Volcengine Ark API key.
- `DOUBAO_API_KEY`: fallback alias accepted by this skill's script.
- `ARK_BASE_URL`: optional custom or regional base URL.

If neither `ARK_API_KEY` nor `DOUBAO_API_KEY` exists, use `--dry-run` or stop with a structured error.

## Models

Common model IDs found in current documentation:

- `doubao-seedance-2-0-260128`: default for this skill.
- `doubao-seedance-1-5-pro-251215`.
- `doubao-seedance-1-0-pro-250528`.
- `doubao-seedance-1-0-pro-fast-251015`.

Model availability can vary by account and region. If a task fails with model access errors, report the model ID and ask the user to confirm enabled models in Ark.

## Content Inputs

### Text To Video

```json
{
  "type": "text",
  "text": "西湖清晨湖面，游客慢慢散步，轻快旅行 vlog 风格，手持镜头"
}
```

Use for scenic atmosphere, food close-ups, city vibe, and abstract transitions.

### Image To Video

```json
{
  "type": "image_url",
  "image_url": {"url": "https://example.com/west-lake.jpg"},
  "role": "first_frame"
}
```

Use when the user supplies a scenic image, restaurant photo, cover image, or AI-generated still. Supported roles commonly include:

- `first_frame`
- `last_frame`
- `reference_image`

For local images, upload or expose them according to the user's available asset pipeline before submitting. Do not invent public URLs for local files.

### Reference Video And Audio

Seedance 2.0 documentation mentions reference video and audio support in some routes. Use only when the user provides accessible media URLs or approved asset IDs. Do not upload private videos or audio unless the user explicitly approves external API use.

## Common Parameters

- `model`: required model ID.
- `content`: required list of text/image/video/audio/draft inputs.
- `resolution`: `480p`, `720p`, or `1080p` depending on model support.
- `ratio`: `9:16`, `16:9`, `1:1`, `4:3`, `3:4`, `21:9`, or `adaptive` where supported.
- `duration`: clip duration in seconds; travel vlog defaults to `5`.
- `watermark`: boolean.
- `seed`: optional deterministic seed.
- `return_last_frame`: boolean; useful for chaining continuous clips.
- `callback_url`: optional status callback URL. This skill defaults to polling.
- `service_tier`: optional service tier where supported.

## Task Status

Expected statuses:

- `queued`: task accepted and waiting.
- `running`: task is generating.
- `succeeded`: task completed and `content.video_url` should be available.
- `failed`: task failed; report error details.
- `expired`: task timed out or result expired.
- `cancelled`: task was cancelled.

## Download Rule

When a task succeeds, immediately download `content.video_url` to a local MP4. Generated URLs may expire, so reports should prioritize the local output path and keep the task ID for traceability.

## Travel Prompt Pattern

A good travel vlog prompt includes:

- place or food name
- time of day or atmosphere
- camera movement
- visual style
- duration-compatible action
- aspect ratio intent

Example:

```text
西湖清晨湖面，游客沿湖边慢慢散步，微风吹动树叶，轻快旅行 vlog 风格，手持镜头轻微推进，画面真实自然，适合手机竖屏短视频
```

Food example:

```text
杭州街边小吃摊，热气腾腾的葱包桧和小笼包特写，手拿食物靠近镜头，暖色灯光，旅行 vlog 风格，真实食欲感
```

## Error Handling

- Missing API key: exit with `degraded: true`, `error_code: missing_api_key`.
- Missing SDK: exit with `degraded: true`, `error_code: missing_sdk`, and install hint.
- Task failure: include `task_id`, `status`, and provider error fields where available.
- Timeout: include `task_id` so the user can query later.
- Missing `video_url`: treat as failure even when status is `succeeded`.
- Download failure: include URL host, HTTP status if known, and target output path.

## Compliance Notes

- Confirm authorization for real-person portraits, brand marks, copyrighted characters, and third-party media.
- Prefer user-provided media or AI-generated assets.
- Do not claim commercial usage rights for generated media; report that rights and platform policies should be checked by the user.
