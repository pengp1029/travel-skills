# Script Schema

This file documents the JSON structures used by `travel-vlog-video`.

## llm_itinerary_schema

Before generating planning artifacts from natural language, the LLM should extract and complete a normalized itinerary schema. This prevents route chains such as `A→B→C` from being treated as one route destination or one POI.

```json
{
  "version": 1,
  "title": "天津一日游 vlog",
  "city": "天津",
  "ratio": "9:16",
  "route_mode_default": "walking",
  "items": [
    {
      "type": "attraction",
      "name": "世纪钟",
      "city": "天津",
      "description": "到达后展示图片",
      "image_path": ""
    },
    {
      "type": "food",
      "name": "狗不理包子",
      "city": "天津",
      "description": "美食停靠点"
    }
  ],
  "routes": [
    {
      "type": "route",
      "city": "天津",
      "from": "天津站",
      "to": "世纪钟",
      "mode": "walking"
    },
    {
      "type": "route",
      "city": "天津",
      "from": "世纪钟",
      "to": "意大利风情区",
      "mode": "walking"
    }
  ],
  "intercityTransfers": [],
  "user_media": [],
  "generation_options": {
    "collect_poi_images": true,
    "generate_amap_routes": true,
    "compose_final_video": true,
    "include_source_cards": false
  }
}
```

Extraction and completion rules:

- Infer `city` from explicit city text or clear POI context when safe.
- Infer `title` as `{city or 旅行} vlog` when absent.
- Infer same-city `route.mode` as `walking` when absent.
- Classify food stops from words such as `吃`, `美食`, `小吃`, `餐厅`, `咖啡`, or known dish/store names.
- Preserve user-provided `image_path`, `local_image`, `photo_path`, `image_url`, `cover_image_url`, or `photo_url` fields.
- Do not invent local image paths or direct image URLs when the user did not provide them.
- Keep `generation_options.include_source_cards` false unless the user explicitly asks to include source/reference cards in the final MP4.

Route-chain normalization rules:

- `A→B→C→D`, `A -> B -> C`, or `A 到 B 到 C` must become adjacent route legs: `A -> B`, `B -> C`, `C -> D`.
- Route `from` and `to` must each be one stop name.
- Route `from` and `to` must not contain `→`, `->`, `=>`, or another chained destination.
- Same-city route legs must have non-empty `city`, `from`, `to`, and `mode`.
- Every route destination intended for arrival display should have a matching `attraction` or `food` item.
- Return points such as `天津站返程` can be represented as a route destination without creating a POI image item when they are not scenic arrivals.

Current script-compatible input shape:

`build_vlog_plan.py` reads `items` and `days[].items`. Until script-level schema support is expanded, merge route items into `items` before calling `--input-file`:

```json
{
  "title": "天津一日游 vlog",
  "city": "天津",
  "items": [
    {"type": "attraction", "name": "世纪钟", "city": "天津"},
    {"type": "route", "city": "天津", "from": "天津站", "to": "世纪钟", "mode": "walking"},
    {"type": "attraction", "name": "意大利风情区", "city": "天津"},
    {"type": "route", "city": "天津", "from": "世纪钟", "to": "意大利风情区", "mode": "walking"},
    {"type": "food", "name": "狗不理包子", "city": "天津"},
    {"type": "route", "city": "天津", "from": "意大利风情区", "to": "狗不理包子", "mode": "walking"}
  ],
  "intercityTransfers": []
}
```

Expected normalization example:

Input:

```text
天津一日游：天津站→世纪钟→意大利风情区→狗不理包子→五大道→古文化街→天津之眼→天津站返程
```

Normalized route legs:

```text
天津站 -> 世纪钟
世纪钟 -> 意大利风情区
意大利风情区 -> 狗不理包子
狗不理包子 -> 五大道
五大道 -> 古文化街
古文化街 -> 天津之眼
天津之眼 -> 天津站
```

Normalized POI image items:

```text
世纪钟
意大利风情区
狗不理包子
五大道
古文化街
天津之眼
```

The normalized output must not contain `to=世纪钟→意大利风情区→...` or `poi-世纪钟-意大利风情区-...`.

## video_script.json

```json
{
  "title": "杭州一日游 vlog",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "ratio": "9:16",
  "segments": [
    {
      "id": "title-001",
      "kind": "title",
      "duration_sec": 3,
      "caption": "杭州一日轻松逛吃路线",
      "visual": "标题卡 + 城市氛围",
      "asset_policy": "template_or_image"
    },
    {
      "id": "poi-west-lake",
      "kind": "poi-image",
      "duration_sec": 5,
      "caption": "西湖",
      "visual": "杭州西湖 图片素材卡 / 景点氛围图",
      "asset_policy": "prefer_user_image_then_direct_image_then_source_card"
    }
  ]
}
```

Segment fields:

- `id`: stable unique segment ID.
- `kind`: `title`, `poi-image`, `doubao-video`, `amap-route-video`, `intercity-transition`, `user-media`, `image`, or `outro`.
- `duration_sec`: intended segment length.
- `caption`: subtitle or on-screen text.
- `visual`: plain-language visual direction.
- `asset_policy`: how to source the visual asset.

## poi_image_requests.json

```json
{
  "version": 1,
  "default_strategy": "prefer_user_image_then_direct_image_then_source_card",
  "requests": [
    {
      "id": "poi-west-lake",
      "segment_id": "poi-west-lake",
      "name": "西湖",
      "city": "杭州",
      "type": "attraction",
      "duration": 5,
      "output": "poi-west-lake.png",
      "direct_image_candidates": ["/Users/me/photos/west-lake.jpg"],
      "source_urls": {
        "baidu_image": "https://image.baidu.com/search/index?...",
        "baidu_web": "https://www.baidu.com/s?...",
        "xhs": "https://www.xiaohongshu.com/search_result?keyword=...",
        "dianping": "https://www.dianping.com/search/keyword/...",
        "image_search": "https://www.bing.com/images/search?q=...",
        "wikimedia": "https://commons.wikimedia.org/w/index.php?search=...",
        "official_or_encyclopedia": "https://www.bing.com/search?q=..."
      },
      "reference_image_candidates": [],
      "xhs_notes": [],
      "baidu_search_entries": [],
      "source_note": "第三方图片/平台入口仅作素材参考；下载和发布前需确认授权。"
    }
  ]
}
```

Field rules:

- `direct_image_candidates`: local image paths or direct HTTP(S) image URLs only. Public acquisition metadata stays in `poi_image_collection.json`; the compatible resolver manifest receives only URL strings.
- `source_urls`: reference/search pages, not guaranteed direct images.
- `output`: local output filename for the resolved image asset.
- `source_note`: attribution, authorization, or usage caution.
- `collector.public_image_acquisition`: optional metadata describing acquisition source, candidate count, and verification time.

## poi_image_assets.json

```json
{
  "assets": [
    {
      "segment_id": "poi-west-lake",
      "path": "/abs/out/my-trip/assets/poi-west-lake.png",
      "type": "image",
      "source_type": "source_card",
      "source": null,
      "source_urls": {
        "xhs": "...",
        "dianping": "...",
        "image_search": "..."
      },
      "authorized_for_publish": false,
      "note": "未获取可直接下载图片，已生成非黑色参考卡片。"
    }
  ],
  "degraded": true,
  "warnings": []
}
```

Supported `source_type` values:

- `local_image`
- `direct_image`
- `source_card`

## doubao_requests.json

```json
{
  "model": "doubao-seedance-2-0-260128",
  "ratio": "9:16",
  "resolution": "720p",
  "duration": 5,
  "watermark": false,
  "optional": true,
  "usage": "optional_enhancement_after_poi_image_assets",
  "requests": [
    {
      "id": "poi-west-lake",
      "segment_id": "poi-west-lake",
      "prompt": "西湖清晨湖面，游客慢慢散步，轻快旅行 vlog 风格，手持镜头",
      "output": "poi-west-lake.mp4",
      "return_last_frame": true,
      "optional": true
    }
  ]
}
```

Optional request fields:

- `image_url`: public image URL, base64 data URL, or approved asset ID.
- `image_role`: usually `first_frame`.
- `seed`: integer seed.
- `model`, `ratio`, `resolution`, `duration`, `watermark`: per-request overrides.

## amap_route_plan.json

```json
{
  "title": "杭州一日游路线",
  "routes": [
    {
      "id": "route-west-lake-hefang",
      "city": "杭州",
      "title": "西湖到河坊街",
      "segments": [
        {"from": "西湖", "to": "河坊街", "mode": "walking"}
      ],
      "expected_output": "route-west-lake-hefang.mp4"
    }
  ]
}
```

Supported route modes mirror `amap-route-video`:

- `walking`
- `bicycling`
- `driving`
- `transit`

## intercity_transitions.json

```json
{
  "transitions": [
    {
      "id": "intercity-shanghai-hangzhou",
      "kind": "intercity-transition",
      "from_city": "上海",
      "to_city": "杭州",
      "transport": "train",
      "duration_sec": 5,
      "visual": "地图上从上海到杭州的点到点移动线，列车 marker 沿线移动",
      "fallback": "静态地图标题卡",
      "status": "needs_renderer_or_placeholder"
    }
  ]
}
```

Transport values:

- `train`
- `high_speed_rail`
- `flight`
- `drive`
- `bus`
- `unknown`

## ffmpeg_manifest.draft.json

```json
{
  "output": "travel-vlog.mp4",
  "width": 1080,
  "height": 1920,
  "fps": 30,
  "image_duration": 3,
  "items": [
    {"path": "PLACEHOLDER/title-001.png", "type": "image", "duration": 3},
    {"path": "PLACEHOLDER/route-west-lake-hefang.mp4", "type": "video", "start": 0, "duration": 8},
    {"path": "PLACEHOLDER/poi-hefang-street.png", "type": "image", "duration": 5}
  ]
}
```

Before invoking `ffmpeg-media-compose`, replace placeholders with real existing paths or remove missing items and report degradation. The main sequence should follow route-arrival order: route clip first, then the destination POI image when a real image exists. POI placeholders should resolve through `poi_image_assets.json`; source cards are skipped from final composition by default. Final filtering must preserve the input item order and must not regroup route clips and POI images by media type.

## workflow_report.json

```json
{
  "ok": true,
  "out_dir": "/abs/out/my-trip",
  "amap_key": "bde01a…c450",
  "final_mp4": "/abs/out/my-trip/final/my-trip-vlog.mp4",
  "retry_policy": {
    "retryable": ["timeout", "handshake", "qps", "ENGINE_RESPONSE_DATA_ERROR", "remotion"],
    "non_retryable": ["INVALID_USER_KEY", "USERKEY_PLAT_NOMATCH", "USER_DAILY_QUERY_OVER_LIMIT"]
  },
  "steps": {
    "build_plan": {"ok": true},
    "images": {"ok": true, "attempts": []},
    "routes": {"routes_total": 2, "routes_ok": 2, "routes_failed": 0},
    "compose": {"ok": true, "attempts": []}
  }
}
```

## route_generation_report.json

```json
{
  "routes_total": 2,
  "routes_ok": 1,
  "routes_failed": 1,
  "routes": [
    {
      "id": "route-西湖-雷峰塔",
      "ok": false,
      "retryable": true,
      "failure_class": "timeout",
      "attempts": []
    }
  ]
}
```

## final_ffmpeg_manifest.report.json

```json
{
  "items_before": 8,
  "items_after": 7,
  "include_source_cards": false,
  "drop_orphan_arrival_images": true,
  "kept_poi_images": [
    {
      "index": 3,
      "segment_id": "poi-雷峰塔",
      "source_type": "direct_image",
      "path": "/abs/out/assets/poi-雷峰塔.png"
    }
  ],
  "skipped_poi_images": [
    {
      "index": 2,
      "segment_id": "poi-西湖手摇船",
      "source_type": "source_card",
      "path": "/abs/out/assets/poi-西湖手摇船.png",
      "reason": "no_acquired_real_image",
      "source_urls": {}
    }
  ],
  "missing_items": [],
  "degraded": true
}
```

`skipped_poi_images` records POI image cards that were useful for review but excluded from final MP4 because they were not real local/direct images. It can also include `reason: "orphan_arrival_image_after_missing_route"` when a destination image immediately follows a route clip that could not be generated; this prevents orphan POI images from being appended after route failures.

## report.json

```json
{
  "degraded": false,
  "outputs": {
    "video_script": "/abs/path/video_script.json",
    "poi_image_requests": "/abs/path/poi_image_requests.json",
    "doubao_requests": "/abs/path/doubao_requests.json",
    "amap_route_plan": "/abs/path/amap_route_plan.json",
    "intercity_transitions": "/abs/path/intercity_transitions.json",
    "ffmpeg_manifest_draft": "/abs/path/ffmpeg_manifest.draft.json"
  },
  "counts": {
    "segments": 4,
    "poi_image_requests": 2,
    "doubao_requests": 2,
    "amap_routes": 1,
    "intercity_transitions": 0
  },
  "warnings": []
}
```

Use `degraded: true` when credentials, route generation, video generation, image resolution, or composition cannot complete.
