---
name: poi-image-collector
description: >
  多渠道 POI 图片素材收集 skill。用户想为指定景点、餐厅、商圈、地图点位或旅行 vlog 收集图片素材、百度图片/网页搜索入口、公开图库入口、大众点评/小红书图片参考入口时使用。本 skill 区分可直接下载的图片候选和仅供参考的来源页面，输出可供 travel-vlog-video、trip-map-builder 等下游消费的结构化结果。
---

# POI Image Collector

## Environment

At the start of every skill run, load environment variables from `/Users/user/.openclaw/.env` if the file exists, before running any bundled script, CLI, browser automation, or network request. Do not print secret values.

Use this skill when the user needs to collect image materials for specified POIs, including attractions, restaurants, shops, districts, hotels, or map points.

This skill focuses on multi-source image discovery and structured output. It does not compose videos, generate route animations, bypass website restrictions, or assert that third-party images are publishable without license verification.

## When to use

Use this skill for requests such as:

- “帮我收集这些景点的图片素材”
- “给西湖、灵隐寺、河坊街找图”
- “从百度图片、大众点评、小红书找景点图片”
- “给 vlog 补齐每个 POI 的图片”
- “多渠道收集指定景点图片”
- “为地图点位找 imageUrl / photoUrl / sourceUrl”

## Inputs

Accept either natural language or structured JSON.

```json
{
  "city": "杭州",
  "usage": "travel_vlog_preview",
  "pois": [
    {"name": "西湖", "type": "attraction"},
    {"name": "楼外楼", "type": "food"},
    {"name": "河坊街", "type": "district"}
  ],
  "preferred_sources": ["baidu_image", "baidu_web", "xhs", "dianping", "wikimedia", "official"],
  "max_images_per_poi": 3
}
```

## Workflow

1. Normalize the POI list.
   - Identify city, POI name, POI type, intended usage, and image count.
   - If the city is missing and cannot be inferred, ask the user to provide it.
   - Keep ambiguous POIs marked as ambiguous instead of guessing.

2. Build source queries.
   - Baidu image search: `{city} {poi_name} 图片`
   - Baidu web search: `{city} {poi_name} 图片`
   - Browser image search: `{city} {poi_name} 图片`
   - Xiaohongshu search: `{city} {poi_name} 攻略` or `{city} {poi_name} 拍照`
   - Dianping search: `{city} {poi_name}`
   - Wikimedia Commons search: `{city} {poi_name}`
   - Official / encyclopedia search: `{city} {poi_name} 官方 图片` or `{city} {poi_name} 百科`

3. Collect source information.
   - Baidu entries are default no-login source entries; do not treat Baidu thumbnails as direct image candidates by default.
   - Direct image candidates may be stored in `direct_image_candidates` only when the URL appears to be a real image resource or an already provided local image path.
   - Search pages, note pages, shop pages, official pages, encyclopedia pages, and gallery pages should be stored in `source_urls`.
   - For Dianping and Xiaohongshu, prefer recording visible reference pages or search entry URLs unless direct image URLs are clearly available.
   - If `skills/xiaohongshu-skills` is available and the user wants real XHS results, use its read-only CLI through `scripts/collect_xhs_images.py`.

4. Acquire public direct image candidates when needed.
   - Use `scripts/acquire_public_images.py` after baseline source scaffolding when downstream tools need real preview images.
   - The current acquisition flow uses Wikimedia Commons API image metadata and verifies direct image URLs before adding them to `direct_image_candidates`.
   - Keep Baidu, Xiaohongshu, and Dianping as reference/source channels unless true source pages and direct image URLs are verified.
   - Record source page, content type, license hint, verification time, and acquisition method for each acquired candidate.

5. Classify usage safety.
   - `usable_for_preview`: true when the image can be used for local preview or as a reference candidate.
   - `authorized_for_publish`: false unless the license is explicitly verified and compatible with the user’s intended usage.
   - `license_hint`: record visible license information when available; otherwise use `unknown`.

6. Produce outputs.
   - Standard collection JSON.
   - `travel_vlog_video_compatible.requests` for `travel-vlog-video`.
   - Human-readable report listing each POI, available candidates, source entries, degradation reasons, and license notes.

## Source channels

### Baidu image / web search

Use Baidu image and web search as the default no-login entry for Chinese POI image discovery. Record them as `source_urls.baidu_image` and `source_urls.baidu_web`. Do not bulk download Baidu thumbnails, bypass verification, or assume any Baidu result is publishable.

### Browser search / image search

Use browser or search tools to locate public pages and image search entry points. Do not invent URLs. If only a search results page is available, record it as a source entry instead of a direct image.

### Dianping

Use Dianping for restaurants, districts, shops, and local lifestyle POIs. Record detail pages, search pages, visible `photo_url` or `image_url` when available. Stop if login, captcha, slider verification, or anti-abuse controls appear.

### Xiaohongshu

Use Xiaohongshu for recent atmosphere, photo angles, travel notes, and lifestyle references. Prefer search or note entries. If `xiaohongshu-skills` is installed, use only read-only commands such as `search-feeds` and `get-feed-detail`. Do not publish, comment, like, favorite, bypass login, or bypass platform restrictions.

### Public galleries / official / encyclopedia pages

Prefer verifiable public pages such as Wikimedia Commons, attraction official websites, city tourism portals, or encyclopedia pages. Record attribution and license hints when visible. Even for public galleries, do not mark content as publishable unless the license is explicitly confirmed.

For automated public acquisition, use `scripts/acquire_public_images.py`. It currently queries Wikimedia Commons, verifies returned direct image URLs, and records metadata before adding candidates to `direct_image_candidates`.

## Output schema

See `references/output-schema.md` for the full schema.

Core fields per POI:

```json
{
  "name": "西湖",
  "type": "attraction",
  "query_terms": ["杭州 西湖 图片", "杭州 西湖 百度图片", "杭州 西湖 小红书"],
  "direct_image_candidates": [],
  "reference_image_candidates": [],
  "xhs_notes": [],
  "baidu_search_entries": [],
  "source_urls": {
    "browser_search": "...",
    "baidu_image": "...",
    "baidu_web": "...",
    "xhs": "...",
    "dianping": "...",
    "wikimedia": "...",
    "official_or_encyclopedia": "..."
  },
  "best_preview_image": null,
  "license_hint": "unknown",
  "authorized_for_publish": false,
  "source_note": "发布前需确认授权。",
  "degraded": false
}
```

## Safety rules

- Do not bypass login, captcha, slider verification, paywalls, rate limits, robots restrictions, or platform anti-abuse controls.
- Do not scrape images in bulk.
- Do not fabricate image URLs, source URLs, licenses, or attribution.
- Do not mark third-party images as publishable unless the license is explicitly verified.
- Do not treat Baidu, Xiaohongshu, or Dianping images as publishable by default.
- If direct images are unavailable, return source entries and set `degraded=true` where appropriate.
- If a source requires manual login or user review, record that in `source_note`.

## Integration

- Use `travel-skill` or `trip-map-builder` as upstream POI providers when the user starts from a travel plan or map.
- Use `dianping-info-query` for Dianping-specific extraction when detailed shop information is needed.
- Use `xiaohongshu-skills` only for read-only XHS search/detail when available.
- Pass `travel_vlog_video_compatible.requests` to `travel-vlog-video` for video image asset resolution.
- Pass selected `imageUrl` and `source_urls` to `trip-map-builder` for map cards.

## Helper scripts

Build baseline query JSON:

```bash
python3 skills/poi-image-collector/scripts/build_image_requests.py \
  --city 杭州 \
  --pois 西湖,苏堤,雷峰塔 \
  --xhs-skill-dir /Users/user/.openclaw/skills/xiaohongshu-skills \
  --out /tmp/hangzhou-poi-images.json
```

Acquire verified public direct image candidates:

```bash
python3 skills/poi-image-collector/scripts/acquire_public_images.py \
  --collection /tmp/hangzhou-poi-images.json \
  --out /tmp/hangzhou-poi-images.acquired.json \
  --max-images-per-poi 2
```

Collect Xiaohongshu note references:

```bash
python3 skills/poi-image-collector/scripts/collect_xhs_images.py \
  --city 杭州 \
  --poi 西湖 \
  --out /tmp/hangzhou-west-lake-xhs.json
```

The scripts build source scaffolding, verified public preview candidates, and normalized references. They do not publish content, bypass platform controls, or mark images as publishable without license verification.
