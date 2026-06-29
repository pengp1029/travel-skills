# Input And Output

## Accepted Inputs

### Natural Language Plan

```text
杭州一日游：上午西湖散步，中午去河坊街吃小吃，下午到南宋御街拍照。西湖到河坊街步行，河坊街到南宋御街步行。
```

### JSON Plan

```json
{
  "title": "杭州一日游 vlog",
  "city": "杭州",
  "items": [
    {"time": "09:00", "type": "attraction", "name": "西湖", "description": "湖边散步拍照"},
    {"time": "11:00", "type": "route", "from": "西湖", "to": "河坊街", "mode": "walking"},
    {"time": "12:00", "type": "food", "name": "河坊街小吃", "description": "街边小吃和热闹市井氛围"}
  ]
}
```

### JSON Plan With Image Sources

```json
{
  "title": "带素材的西湖 vlog",
  "city": "杭州",
  "items": [
    {
      "type": "attraction",
      "name": "西湖",
      "image_url": "/Users/me/photos/west-lake.jpg",
      "cover_image_url": "https://example.com/west-lake.jpg",
      "xhs_intro_url": "https://www.xiaohongshu.com/search_result?keyword=杭州%20西湖%20攻略",
      "dianping_url": "https://www.dianping.com/search/keyword/1/0_%E6%9D%AD%E5%B7%9E%20%E8%A5%BF%E6%B9%96",
      "image_search_url": "https://www.bing.com/images/search?q=杭州%20西湖%20景点%20图片"
    }
  ]
}
```

`image_url`, `cover_image_url`, and `photo_url` are treated as direct image candidates only when they are local files or direct image URLs. 小红书、大众点评 and image-search URLs are treated as reference/source entries unless they point directly to an image file.

### Multi-City Plan

```json
{
  "title": "上海到杭州周末 vlog",
  "intercityTransfers": [
    {"from_city": "上海", "to_city": "杭州", "transport": "train", "time": "08:00"}
  ],
  "days": [
    {
      "day": 1,
      "city": "杭州",
      "items": [
        {"type": "attraction", "name": "西湖"},
        {"type": "route", "from": "西湖", "to": "河坊街", "mode": "walking"}
      ]
    }
  ]
}
```

### User Media Hints

```json
{
  "title": "带素材的西湖 vlog",
  "city": "杭州",
  "items": [
    {
      "type": "attraction",
      "name": "西湖",
      "image_path": "/Users/me/photos/west-lake.jpg",
      "media": [{"path": "/Users/me/photos/west-lake.jpg", "type": "image"}]
    }
  ]
}
```

Local media paths can be used by FFmpeg. For optional Doubao image-to-video, provide a public URL or approved asset ID unless the user has a separate upload pipeline.

## Generated Outputs

`build_vlog_plan.py` writes these files:

```text
out-dir/
  video_script.json
  poi_image_requests.json
  doubao_requests.json
  amap_route_plan.json
  intercity_transitions.json
  ffmpeg_manifest.draft.json
  report.json
```

`enrich_poi_images_with_collector.py` writes these files:

```text
out-dir/
  poi_image_requests.enriched.json
  poi_image_collection.json
```

The enriched manifest preserves user-provided images first, then adds `poi-image-collector` source entries such as Baidu image/web, Xiaohongshu, Dianping, Wikimedia, and official/encyclopedia links. By default it also runs public image acquisition and can add verified Wikimedia direct image URLs to `direct_image_candidates`.

`resolve_poi_images.py` writes these files:

```text
out-dir/
  assets/
    poi-*.png
    poi-*.txt
  poi_image_assets.json
  poi_image_resolution_report.json
```

`run_vlog_workflow.py` writes retryable workflow reports:

```text
out-dir/
  workflow_report.json
  route_generation_report.json
```

`workflow_report.json` records each step, attempts, retry classification, final MP4 path, and whether the workflow succeeded. `route_generation_report.json` records each AMap route, attempts, route spec path, generated route video path, and non-retryable failures.

`finalize_ffmpeg_manifest.py` writes these files before final composition:

```text
out-dir/
  final_ffmpeg_manifest.filtered.json
  final_ffmpeg_manifest.report.json
```

The filtered manifest skips POI source cards by default; source cards remain available for report/review but do not enter the final MP4 unless `--include-source-cards` is passed.

## Single-City Example Output

Input:

```bash
python3 scripts/build_vlog_plan.py \
  --plan "杭州一日游：西湖到河坊街步行，河坊街到南宋御街步行" \
  --out-dir out/hangzhou
```

Expected outputs:

- `video_script.json`: title card, POI image segment, AMap route, POI image segment, AMap route, POI image segment.
- `poi_image_requests.json`: scenic and food image/source-card requests.
- `doubao_requests.json`: optional scenic and food text-to-video requests.
- `amap_route_plan.json`: two walking segments.
- `ffmpeg_manifest.draft.json`: POI image placeholders and route video placeholders that should be replaced with actual generated asset paths.

## POI Image Resolution Example

If an attraction has an image URL or local image path:

```json
{
  "type": "attraction",
  "name": "西湖",
  "image_url": "/Users/me/photos/west-lake.jpg",
  "photo_url": "https://example.com/west-lake.jpg"
}
```

The POI image request should contain:

```json
{
  "id": "poi-west-lake",
  "segment_id": "poi-west-lake",
  "name": "西湖",
  "city": "杭州",
  "type": "attraction",
  "duration": 5,
  "output": "poi-west-lake.png",
  "direct_image_candidates": [
    "/Users/me/photos/west-lake.jpg",
    "https://example.com/west-lake.jpg"
  ],
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
  "baidu_search_entries": []
}
```

If no direct image is usable, `resolve_poi_images.py` should generate a non-black source card and mark `authorized_for_publish` as `false`. The source card is for report/review only and is skipped from the final MP4 by `finalize_ffmpeg_manifest.py` unless explicitly included. If public acquisition succeeds, `poi_image_collection.json` also records `public_image_acquisition`, candidate metadata, and per-POI `best_preview_image`; the compatible manifest stores the acquired URLs as direct candidates for the resolver.

## Optional Image-To-Video Example

Doubao generation is optional. If an attraction has an image URL:

```json
{
  "type": "attraction",
  "name": "西湖",
  "image_url": "https://example.com/west-lake.jpg"
}
```

The optional Doubao request may contain:

```json
{
  "id": "poi-west-lake",
  "prompt": "从这张西湖照片开始，镜头缓慢推进，湖面有微风，旅行 vlog 风格",
  "image_url": "https://example.com/west-lake.jpg",
  "image_role": "first_frame",
  "optional": true
}
```

## Cross-City Example Output

A transfer from Shanghai to Hangzhou by train should produce an `intercity_transitions.json` item:

```json
{
  "id": "intercity-shanghai-hangzhou",
  "kind": "intercity-transition",
  "from_city": "上海",
  "to_city": "杭州",
  "transport": "train",
  "duration_sec": 5,
  "visual": "地图上从上海到杭州的点到点移动线，列车 marker 沿线移动",
  "fallback": "静态地图标题卡"
}
```

Do not send this to `amap-route-video` as a walking or driving route unless the user explicitly wants driving route rendering.

## Final Report

The final response should include:

- generated script and manifest paths
- generated POI image asset/card paths
- generated route clip paths
- optional generated Doubao clip paths if requested
- final composed MP4 path if available
- missing assets, source-card fallbacks, or degraded segments
- third-party image authorization notes
- exact command needed for the next step
