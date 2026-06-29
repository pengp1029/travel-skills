# Integration Guide

`poi-image-collector` is designed as an image-material collection layer for the travel skill ecosystem.

## Upstream integrations

### travel-skill

Use `travel-skill` when the user starts with a broad travel request and needs POI recommendations first. It may provide:

- POI names and types.
- `cover_image_url` or `image_url`.
- `image_search_url`.
- `dianping_url`.
- `xhs_url` or `xhs_intro_url`.

`poi-image-collector` can enrich those fields with Baidu, Xiaohongshu, Dianping, Wikimedia, official, and encyclopedia source channels.

### trip-map-builder

Use `trip-map-builder` when the user starts from a route, hotel, map, or wish list. It may provide map points with:

- `imageUrl`.
- `imageKey`.
- `dianpingUrl`.
- `xhsUrl`.
- `sourceNote`.

`poi-image-collector` can fill missing image fields or add source entries for map cards.

### dianping-info-query

Use `dianping-info-query` when a restaurant, shop, or local-life POI needs Dianping-specific information. It may provide:

- `photo_url`.
- `image_url`.
- `xhs_reference_url`.
- `source_urls.dianping`.
- Shop metadata used to disambiguate POIs.

Respect all Dianping login, captcha, and anti-abuse boundaries.

### xiaohongshu-skills

Use `xiaohongshu-skills` only for read-only search and browsing:

```bash
cd /Users/user/.openclaw/skills/xiaohongshu-skills
uv run python scripts/cli.py search-feeds --keyword "杭州 西湖 拍照" --note-type 图文
```

For normalized POI image references, prefer the wrapper:

```bash
python3 /Users/user/.openclaw/skills/poi-image-collector/scripts/collect_xhs_images.py \
  --city 杭州 \
  --poi 西湖 \
  --out /tmp/xhs-west-lake.json
```

Only use these XHS commands from image collection workflows:

- `check-login`.
- `search-feeds`.
- `get-feed-detail`.
- `list-feeds`.
- `user-profile`.

Do not call publish, comment, like, favorite, or other write commands.

## Baidu integration

`build_image_requests.py` always emits Baidu source entries:

- `source_urls.baidu_image`.
- `source_urls.baidu_web`.

Use these as no-login discovery links for Chinese POIs. Baidu entries help users or downstream agents find official pages, Baike pages, media galleries, public images, Xiaohongshu pages, and Dianping pages. They are not direct image candidates by default.

## Downstream integrations

### Public image acquisition

After `build_image_requests.py` creates a baseline collection, run `acquire_public_images.py` when downstream tools need real preview images instead of source cards:

```bash
python3 /Users/user/.openclaw/skills/poi-image-collector/scripts/acquire_public_images.py \
  --collection /tmp/poi_image_collection.json \
  --out /tmp/poi_image_collection.json \
  --max-images-per-poi 2
```

The acquisition step currently uses Wikimedia Commons, verifies direct image URLs, and keeps Baidu/XHS/Dianping as references unless verified direct source URLs are available.

## Downstream integrations

### travel-vlog-video

Pass `travel_vlog_video_compatible.requests` to `travel-vlog-video` as POI image requests.

Compatible fields include:

- `id`.
- `segment_id`.
- `name`.
- `city`.
- `type`.
- `duration`.
- `output`.
- `direct_image_candidates`.
- `source_urls` including `baidu_image`, `baidu_web`, and `xhs`.
- `source_note`.

`travel-vlog-video` can then resolve direct images or generate non-black source cards for missing images.

### ffmpeg-media-compose

`ffmpeg-media-compose` does not collect images. Use it only after image assets have been resolved to local files.

### trip-map-builder

Use selected image candidates or source entries to populate map card fields:

```json
{
  "name": "西湖",
  "imageUrl": "https://example.com/west-lake.jpg",
  "dianpingUrl": "https://www.dianping.com/...",
  "xhsUrl": "https://www.xiaohongshu.com/...",
  "sourceNote": "第三方图片仅作预览，发布前需确认授权。"
}
```

## Typical workflows

### Collect images for a travel vlog

1. User provides POI list or travel plan.
2. `poi-image-collector` builds Baidu, XHS, Dianping, Wikimedia, and official source entries.
3. `acquire_public_images.py` attempts to add verified public direct image candidates.
4. If XHS is available and useful, `collect_xhs_images.py` normalizes XHS note references.
5. `travel-vlog-video` consumes compatible requests.
6. `ffmpeg-media-compose` composes final media after local image resolution.

### Enrich a trip map

1. `trip-map-builder` creates map points.
2. `poi-image-collector` fills missing image/source fields.
3. `trip-map-builder` renders map cards with source notes.

### Restaurant image sourcing

1. User specifies restaurants or food POIs.
2. `dianping-info-query` retrieves Dianping metadata and visible image entries.
3. `poi-image-collector` normalizes them with Baidu, browser, Xiaohongshu, and public search entries.
