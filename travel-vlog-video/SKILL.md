---
name: travel-vlog-video
description: >
  旅游视频 vlog 生成专用 skill。用户想把旅行 plan、行程单、城市路线、多城市旅行、景点/美食安排生成游玩 vlog、路线短视频、旅行混剪 MP4、带高德路线动画、POI 景点图片素材、小红书/大众点评/图片入口参考素材或可选豆包/Seedance AI 视频素材时必须使用。本 skill 默认按路线到达顺序编排：先播放路线视频，到达某个景点后再播放该景点图片；豆包视频生成为可选增强，再编排跨城转场和 FFmpeg 最终合成。
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - ffmpeg
        - ffprobe
        - node
        - npm
      env:
        - AMAP_KEY
    os:
      - darwin
      - linux
---

# travel-vlog-video

## Environment

At the start of every skill run, load environment variables from `/Users/user/.openclaw/.env` if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

Use this skill to turn a travel plan into a reproducible travel vlog video workflow: script the timeline, resolve scenic/food POI image assets, generate city route animations with `amap-route-video`, order the final sequence as route video followed by the arrived destination POI image, optionally generate Doubao/Seedance clips when explicitly requested and credentials are available, and compose the final MP4 with `ffmpeg-media-compose`.

## What This Skill Does

- Parses an itinerary or travel plan into a short-video timeline.
- Creates `video_script.json` with ordered segments, captions, durations, visual intent, and asset policies.
- Creates `poi_image_requests.json` for attraction, food, city vibe, and B-roll image assets.
- Enriches POI image requests with `poi-image-collector` via `scripts/enrich_poi_images_with_collector.py`, adding Baidu image/web, Xiaohongshu, Dianping, Wikimedia, and official/encyclopedia source entries when user images are not provided.
- Resolves POI images into `poi_image_assets.json` with `scripts/resolve_poi_images.py`.
- Finalizes FFmpeg manifests with `scripts/finalize_ffmpeg_manifest.py`, preserving route-arrival order while skipping POI source cards and orphan arrival images by default so only real local/direct POI images reached by available routes enter the final video.
- Provides `scripts/run_vlog_workflow.py` as the preferred end-to-end runner with retry classification for AMap, image acquisition, manifest finalization, and FFmpeg composition.
- Creates `doubao_requests.json` as an optional enhancement manifest for AI-generated attraction, food, city vibe, and B-roll clips.
- Creates `amap_route_plan.json` for in-city point-to-point route animations.
- Creates `intercity_transitions.json` for train, flight, and driving transitions between cities.
- Creates an `ffmpeg_manifest.draft.json` for final composition ordered as `route video -> arrived destination POI image`.
- Provides `scripts/generate_doubao_video.py` to submit, poll, and download Doubao/Seedance videos when the user wants AI video generation.
- Delegates final media concatenation to `ffmpeg-media-compose`.

## Read References As Needed

- `references/workflow.md`: end-to-end operating procedure.
- `references/doubao-seedance-api.md`: Doubao/Seedance API notes, parameters, and failure handling.
- `references/input-output.md`: accepted input formats and expected outputs.
- `references/script-schema.md`: JSON schema conventions for script and manifests.

## Runtime Requirements

For offline planning and POI image cards:

- `python3`
- `ffmpeg` for converting generated fallback cards to PNG

For route videos:

- `AMAP_KEY` or `AMAP_WEB_SERVICE_KEY`
- the existing `amap-route-video` skill dependencies

For optional Doubao/Seedance generation:

- `ARK_API_KEY` or `DOUBAO_API_KEY`
- Python package: `volcengine-python-sdk[ark]`

For final composition:

- `ffmpeg`
- `ffprobe`
- the existing `ffmpeg-media-compose` skill

## Default Settings

- Output style: mobile travel vlog.
- Ratio: `9:16`.
- Final canvas: `1080x1920`.
- FPS: `30`.
- Default sequence policy: title, route video, arrived destination POI image when a real image exists, repeated by route order. Final filtering must preserve this stable order and must not batch routes before images.
- Default POI visual strategy: user image first, then `poi-image-collector` direct candidates. If no real image is available, generate a source card for report/review only and skip that POI image in the final MP4.
- Default route clip duration: `8` seconds.
- Default image duration: `3` seconds.
- Optional Doubao model: `doubao-seedance-2-0-260128`.
- Optional Doubao clip duration: `5` seconds.

## Operating Workflow

1. **Clarify only blockers**
   - If the user provides no city or no stop order, ask for those details.
   - If the user provides a usable plan, do not ask for exact timestamps; infer a clean vlog order.
   - Do not require Doubao credentials for the default workflow.
   - Ask only for real blockers: missing city for AMap route generation, missing stop order, or unclear cross-city transport.

2. **Extract and complete the itinerary schema first**
   - Before running any planning or generation script, normalize the user request into an itinerary schema with `title`, `city`, ordered POI `items`, adjacent `route` legs, optional `intercityTransfers`, user media fields, and generation options.
   - Complete inferable fields without asking: infer city from explicit city names or well-known POI context, infer title as `{city or 旅行} vlog`, infer same-city route mode as `walking` when unspecified, classify food stops from words such as `吃`, `美食`, `小吃`, `餐厅`, `咖啡`, or dish names, and preserve user-provided `image_path`, `local_image`, `image_url`, `cover_image_url`, or `photo_url`.
   - Split route chains into adjacent legs. `A→B→C→D`, `A -> B -> C`, or `A 到 B 到 C` must become `A -> B`, `B -> C`, and `C -> D`; never keep the full tail as a single destination.
   - Validate every in-city route before generation: `city`, `from`, `to`, and `mode` must be present; `from` and `to` must each be a single stop name and must not contain `→`, `->`, `=>`, or another route chain.
   - Ensure every route destination that should be shown on arrival has a matching attraction or food POI item for image collection. Return/terminal stops can be marked as return points and omitted from POI image display.
   - Keep `include_source_cards` false by default. If a POI has no real local/direct image, its source card is report/review material only and must not enter the final MP4 unless explicitly requested.

3. **Build the vlog plan**
   - Prefer `scripts/run_vlog_workflow.py` for full generation so planning, images, route clips, manifest filtering, retries, and composition stay in one auditable workflow.
   - Use `scripts/build_vlog_plan.py` directly only for offline plan normalization or debugging.
   - Prefer passing the completed normalized JSON plan through `--input-file` when practical; if using `--plan`, first rewrite the plan into clean adjacent route statements rather than a raw multi-stop chain.
   - Save outputs under an explicit working directory such as `out/<trip-name>/` or a user-provided directory.
   - Produce `video_script.json`, `poi_image_requests.json`, `doubao_requests.json`, `amap_route_plan.json`, `intercity_transitions.json`, and `ffmpeg_manifest.draft.json`.

4. **Collect and resolve scenic and food image assets**
   - Prefer user-provided local images and direct image URLs from the plan.
   - Run `scripts/enrich_poi_images_with_collector.py` to enrich `poi_image_requests.json` with `poi-image-collector` output when POIs do not already have usable direct images.
   - Use `scripts/resolve_poi_images.py` against the enriched manifest when available.
   - Treat 百度、小红书、大众点评 and image-search URLs as source/reference entries unless they are direct image URLs.
   - If no direct image is usable, generate a non-black POI source card for report/review only; do not include it in the final MP4 unless explicitly requested.

5. **Generate in-city route clips**
   - Use the `amap-route-video` skill for city route segments.
   - Convert route segments to the AMap plan shape: `title`, `city`, `segments[].from`, `segments[].to`, `segments[].mode`.
   - Call AMap APIs serially only: geocoding and route planning requests must run one segment at a time, not in parallel.
   - Limit concurrency when AMap QPS limits appear.
   - Do not use in-city walking/driving route rendering for cross-city train or flight transitions.

6. **Optionally generate Doubao/Seedance clips**
   - Use `scripts/generate_doubao_video.py` only when the user wants AI-generated scenic/food videos and the account has model access.
   - Prefer POI image assets for `image_url` first-frame generation when available.
   - For multi-segment continuity, enable `return_last_frame` and feed the last frame into the next request only when the user wants a continuous story.

7. **Handle cross-city transitions**
   - For high-speed rail/train: create an intercity transition plan with train or car-like marker language.
   - For flight: create an intercity transition plan with airplane marker and arc route language.
   - If no renderer exists for intercity maps, create a placeholder requirement or static title card; do not fake a generated video.

8. **Compose final MP4**
   - Convert the completed assets into an `ffmpeg-media-compose` manifest.
   - Keep the main sequence in route-arrival order: route clip first, then the image for the route destination when a real POI image exists.
   - Replace POI placeholders with `poi_image_assets.json` paths.
   - Run `scripts/finalize_ffmpeg_manifest.py` before composition to remove POI source cards and missing media from the final manifest while preserving stable input order.
   - If a route video is missing, skip the immediately following arrived POI image by default so the image does not appear as an orphan segment later.
   - Do not batch all POI images before all route clips.
   - Remove or mark missing assets before composition; the manifest must not reference nonexistent files.
   - Invoke `ffmpeg-media-compose` for final normalization and concatenation.

9. **Report results**
   - Include final MP4 path only if the file exists.
   - Include generated script paths and manifests.
   - Include segment counts and total duration when known.
   - Include image source cards, missing assets, optional Doubao task status, failed AMap route tasks, and downgraded intercity transitions.

## Safety And Accuracy Rules

- Never invent local output paths for videos or images that were not generated.
- Never pass a raw multi-stop route chain as a single route destination; normalize and validate itinerary schema first.
- Never allow route `from` or `to` values to contain `→`, `->`, `=>`, or multiple chained destinations.
- Never assume API keys are configured; check or use dry-run mode.
- Do not hardcode private credentials.
- Do not upload user media to external APIs unless the user requested generation and the API requires it.
- Treat 小红书、大众点评 and image-search pages as references unless a direct image URL or user-approved local asset exists.
- Do not bypass login, CAPTCHA, slider verification, robots restrictions, or platform risk controls to fetch third-party images.
- For third-party web images/videos, flag copyright and authorization considerations; set publish authorization as unknown/false unless the user confirms rights.
- For real-person portraits, brands, landmarks with restrictions, or copyrighted characters, remind the user to confirm rights and model/platform policy compliance.

## Common Commands

Run the full retryable workflow:

```bash
python3 scripts/run_vlog_workflow.py \
  --plan "杭州一日游：西湖到河坊街步行，河坊街到南宋御街步行" \
  --out-dir out/hangzhou-vlog \
  --amap-key "$AMAP_KEY" \
  --route-retries 3 \
  --image-retries 2 \
  --compose-retries 2
```

Create an offline plan:

```bash
python3 scripts/build_vlog_plan.py \
  --plan "杭州一日游：西湖到河坊街步行，河坊街到南宋御街步行" \
  --out-dir out/hangzhou-vlog
```

Enrich and resolve POI image assets:

```bash
python3 scripts/enrich_poi_images_with_collector.py \
  --manifest out/hangzhou-vlog/poi_image_requests.json \
  --out-manifest out/hangzhou-vlog/poi_image_requests.enriched.json \
  --out-collection out/hangzhou-vlog/poi_image_collection.json

python3 scripts/resolve_poi_images.py \
  --manifest out/hangzhou-vlog/poi_image_requests.enriched.json \
  --out-dir out/hangzhou-vlog/assets
```

Dry-run an optional Doubao request:

```bash
python3 scripts/generate_doubao_video.py \
  --prompt "西湖清晨湖面，游客慢慢散步，轻快旅行 vlog 风格，手持镜头" \
  --output out/poi-west-lake.mp4 \
  --ratio 9:16 \
  --resolution 720p \
  --duration 5 \
  --dry-run
```

Generate from an optional Doubao manifest:

```bash
python3 scripts/generate_doubao_video.py \
  --manifest out/hangzhou-vlog/doubao_requests.json \
  --out-dir out/hangzhou-vlog/doubao
```

## Output Contract

When responding to a user, use this concise structure:

1. **脚本与素材计划**: paths to `video_script.json`, `poi_image_requests.json`, `doubao_requests.json`, route plan, and intercity transitions.
2. **生成结果**: generated POI image assets/cards, route clips, optional Doubao clips, final MP4 path if available.
3. **缺失/降级**: missing API keys, missing media, source-card fallbacks, failed tasks, placeholder transitions, authorization notes.
4. **下一步**: exact command or input needed to continue.
