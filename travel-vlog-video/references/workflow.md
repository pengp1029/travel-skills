# Workflow

This workflow turns a travel plan into a reproducible travel vlog video pipeline. The default path resolves POI image assets, renders route animations, then composes the main video in route-arrival order: each route clip is followed by the image for the destination reached by that route. Doubao/Seedance video generation is optional enhancement, not a prerequisite.

## 1. Understand The Plan

Accept either natural language or JSON. Before running generation scripts, extract and complete a normalized itinerary schema. The schema must include:

- title
- city or cities
- day order
- ordered attraction and food POI items
- adjacent route segments
- intercity transfers
- user-provided image/video assets
- optional image source fields such as `image_path`, `local_image`, `image_url`, `cover_image_url`, `photo_url`, `xhs_intro_url`, `dianping_url`, and `image_search_url`
- generation options such as `collect_poi_images`, `generate_amap_routes`, `compose_final_video`, and `include_source_cards`

Complete inferable fields before asking the user:

- Infer `city` from an explicit city name or clear POI context.
- Infer `title` as `{city or 旅行} vlog` when absent.
- Infer same-city route `mode` as `walking` when absent.
- Classify food stops from words such as `吃`, `美食`, `小吃`, `餐厅`, `咖啡`, or dish names.
- Preserve user-provided local/direct image fields; do not invent missing image paths.

Split route chains into adjacent legs before any script call:

```text
天津站→世纪钟→意大利风情区→狗不理包子
```

must become:

```text
天津站 -> 世纪钟
世纪钟 -> 意大利风情区
意大利风情区 -> 狗不理包子
```

Do not pass `to=世纪钟→意大利风情区→狗不理包子` or create one POI named `世纪钟→意大利风情区→狗不理包子`.

Validate the normalized schema:

- Same-city routes must have non-empty `city`, `from`, `to`, and `mode`.
- Route `from` and `to` values must be single stop names and must not contain `→`, `->`, `=>`, or chained destinations.
- Every route destination that should be shown on arrival should have a matching attraction or food POI item.
- Return/terminal stops can be omitted from POI image display when they are not meant as scenic arrivals.
- `include_source_cards` stays false by default; source cards are report/review material only.

Ask only when a blocker exists: missing city for route generation, no stop order, or unclear cross-city transport.

## 2. Run The Retryable End-To-End Workflow

Use the end-to-end runner when the user asks to generate a final MP4. It keeps the skill workflow auditable and prevents manual fake-card fallbacks:

```bash
python3 scripts/run_vlog_workflow.py \
  --plan "杭州一日游：杭州东站到西湖步行，西湖到雷峰塔步行" \
  --out-dir out/my-trip \
  --amap-key "$AMAP_KEY" \
  --route-retries 3 \
  --image-retries 2 \
  --compose-retries 2
```

Retryable failures include network timeouts, TLS handshake timeouts, AMap QPS/temporary engine errors, HTTP 5xx, Remotion transient failures, and FFmpeg transient failures. Non-retryable failures include missing key, `INVALID_USER_KEY`, `USERKEY_PLAT_NOMATCH`, daily quota exhaustion, and invalid route input.

The runner writes `workflow_report.json` and `route_generation_report.json`. Report final success only if the final MP4 exists.

## 3. Build Offline Planning Artifacts

Use the completed normalized schema as the input source. Prefer JSON input when practical:

```bash
python3 scripts/build_vlog_plan.py --input-file plan.normalized.json --out-dir out/my-trip
```

The current script-compatible JSON shape can include route items directly in `items`:

```json
{
  "title": "天津一日游 vlog",
  "city": "天津",
  "items": [
    {"type": "attraction", "name": "世纪钟", "city": "天津"},
    {"type": "route", "city": "天津", "from": "天津站", "to": "世纪钟", "mode": "walking"},
    {"type": "attraction", "name": "意大利风情区", "city": "天津"},
    {"type": "route", "city": "天津", "from": "世纪钟", "to": "意大利风情区", "mode": "walking"}
  ],
  "intercityTransfers": []
}
```

If using natural-language `--plan`, first rewrite route chains into clean adjacent route statements:

```bash
python3 scripts/build_vlog_plan.py --plan "天津一日游：天津站到世纪钟步行，世纪钟到意大利风情区步行" --out-dir out/my-trip
```

Do not send raw multi-stop chains to `--plan` when they can be represented as normalized JSON.

Expected files:

- `video_script.json`
- `poi_image_requests.json`
- `doubao_requests.json`
- `amap_route_plan.json`
- `intercity_transitions.json`
- `ffmpeg_manifest.draft.json`
- `report.json`

This step is offline and should not require API keys. `doubao_requests.json` is still produced so the user can opt into AI video generation later.

## 4. Collect And Resolve POI Image Assets

First enrich POI image requests with `poi-image-collector` so every POI has Baidu image/web, Xiaohongshu, Dianping, Wikimedia, and official/encyclopedia source entries when the user did not provide direct assets. By default, this also runs public image acquisition through Wikimedia Commons and fills verified direct candidates when available:

```bash
python3 scripts/enrich_poi_images_with_collector.py \
  --manifest out/my-trip/poi_image_requests.json \
  --out-manifest out/my-trip/poi_image_requests.enriched.json \
  --out-collection out/my-trip/poi_image_collection.json \
  --max-images-per-poi 2
```

Use `--no-acquire-public-images` to keep source scaffolding only.

Then use `resolve_poi_images.py` to turn enriched POI image requests into local assets:

```bash
python3 scripts/resolve_poi_images.py \
  --manifest out/my-trip/poi_image_requests.enriched.json \
  --out-dir out/my-trip/assets
```

Resolution order:

1. Existing local image paths supplied by the user.
2. User-provided direct HTTP(S) image URLs with image content type and supported extension.
3. Direct image candidates returned by `poi-image-collector`.
4. Non-black generated source cards containing POI/source metadata for report/review only.

Final composition skips source cards by default. A POI image enters the final MP4 only when `source_type` is `local_image` or `direct_image`.

Outputs:

- `poi_image_assets.json`
- `poi_image_resolution_report.json`
- local files under `assets/`

Treat 百度、小红书、大众点评 and image search URLs as references unless they are direct image URLs. Do not bypass login, CAPTCHA, slider verification, or platform controls to fetch images.

## 5. Generate AMap Route Clips

Use `amap-route-video` for every in-city route in `amap_route_plan.json`.

Plan shape to pass to AMap route generation:

```json
{
  "title": "西湖到河坊街",
  "city": "杭州",
  "segments": [
    {"from": "西湖", "to": "河坊街", "mode": "walking"}
  ]
}
```

Route clips should be copied or referenced from their real generated locations. Never claim a route video exists until the output file exists. If AMap returns QPS errors, retry sequentially with low concurrency.

## 6. Optionally Generate Doubao/Seedance Clips

Only run Doubao when the user explicitly wants AI-generated video clips and credentials/model access are available:

```bash
python3 scripts/generate_doubao_video.py \
  --manifest out/my-trip/doubao_requests.json \
  --out-dir out/my-trip/doubao
```

Use `--dry-run` to inspect requests without calling the API.

If generation fails for a segment, keep the segment in the report and do not add a nonexistent path to final composition. The default composition can still use POI image assets.

## 7. Handle Intercity Transitions

Read `intercity_transitions.json`.

- `train` / `high_speed_rail`: map line with train or car-like moving marker.
- `flight`: arc line with airplane marker.
- `drive`: road-trip marker.
- `unknown`: ask user or leave as placeholder.

Initial implementation can output placeholder requirements if no intercity renderer exists. This is preferable to misusing city route rendering.

## 8. Build Final FFmpeg Manifest

Start from `ffmpeg_manifest.draft.json` and replace placeholder paths with real assets:

- AMap route clips.
- POI images from `poi_image_assets.json`.
- Optional Doubao-generated clips if the user chose them and files exist.
- User media paths.
- Static title cards or placeholder images only if they exist locally.

The main sequence should follow the AMap route order: title, route clip, arrived destination POI image when a real POI image exists, next route clip, next available destination POI image. Do not batch all POI images before all routes. Final filtering must be stable: it should preserve the input manifest order and only remove invalid items, never regroup route clips and POI images by type.

Before composition, filter the final manifest so POI source cards are skipped by default:

```bash
python3 scripts/finalize_ffmpeg_manifest.py \
  --manifest out/my-trip/final_ffmpeg_manifest.json \
  --poi-assets out/my-trip/poi_image_assets.json \
  --out-manifest out/my-trip/final_ffmpeg_manifest.filtered.json \
  --out-report out/my-trip/final_ffmpeg_manifest.report.json
```

Use `--include-source-cards` only when the user explicitly wants source-card placeholders in the video. Remove missing items and record them as degraded segments. POI segments without real images should remain in reports, not the final MP4. When a route clip is missing, the immediately following arrived POI image is skipped by default as `orphan_arrival_image_after_missing_route`; use `--keep-orphan-arrival-images` only when explicitly requested.

## 9. Compose The Final Video

Use `ffmpeg-media-compose` with the filtered manifest:

```bash
python3 /Users/user/.openclaw/skills/ffmpeg-media-compose/scripts/compose_media.py \
  --manifest out/my-trip/final_ffmpeg_manifest.filtered.json \
  --out-dir out/my-trip/final
```

Report the final MP4 only after the output file exists.

## 10. Reporting Template

```text
脚本与素材计划
- video_script: ...
- poi_image_requests: ...
- doubao_requests: ...
- amap_route_plan: ...
- intercity_transitions: ...
- ffmpeg_manifest: ...

生成结果
- POI image assets: N real images / M skipped source cards
- AMap route clips: N succeeded / M failed
- Optional Doubao clips: N succeeded / M failed / skipped
- final video: ...

缺失/降级
- source-card fallbacks
- missing direct images
- failed route tasks
- third-party authorization notes

下一步
- exact command or required input
```

## Degradation Rules

- Missing direct POI image: generate a non-black source card for report/review, but skip it from the final MP4 by default.
- Missing `ARK_API_KEY`: skip optional Doubao generation; keep request manifest.
- Missing `AMAP_KEY`: create route plans, skip real route rendering.
- Missing FFmpeg: skip card conversion and composition, keep manifest/report.
- Missing media file: remove from final manifest and report.
- API timeout: report task ID and output path target.
- `succeeded` without `content.video_url`: treat as failure.

## Non-Goals

- Do not publish to social platforms.
- Do not buy media, booking, tickets, or paid assets.
- Do not claim copyright clearance.
- Do not create a fake route/video output for unrendered segments.
- Do not scrape images by bypassing login, CAPTCHA, sliders, risk controls, or platform restrictions.
