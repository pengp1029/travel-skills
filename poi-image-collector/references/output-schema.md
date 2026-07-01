# Output Schema

`poi-image-collector` produces two related outputs:

1. A source-rich collection result for human review and downstream tools.
2. A `travel-vlog-video` compatible request list.

## Collection JSON

```json
{
  "version": 1,
  "city": "杭州",
  "usage": "travel_vlog_preview",
  "max_images_per_poi": 3,
  "xhs_enabled": true,
  "xhs_skill_dir": "$HOME/.openclaw/skills/xiaohongshu-skills",
  "pois": [
    {
      "name": "西湖",
      "type": "attraction",
      "query_terms": [
        "杭州 西湖 图片",
        "杭州 西湖 百度图片",
        "杭州 西湖 小红书",
        "杭州 西湖 大众点评",
        "杭州 西湖 Wikimedia Commons",
        "杭州 西湖 官方 图片"
      ],
      "direct_image_candidates": [],
      "reference_image_candidates": [
        {
          "url": "https://example.com/xhs-cover.jpg",
          "source": "xhs_cover",
          "note_url": "https://www.xiaohongshu.com/explore/...",
          "authorized_for_publish": false,
          "usable_for_preview": true,
          "note": "小红书封面仅作本地预览或参考候选；发布前需确认授权。"
        }
      ],
      "xhs_notes": [
        {
          "feed_id": "...",
          "xsec_token": "...",
          "title": "西湖拍照机位",
          "author": "...",
          "cover_url": "https://example.com/xhs-cover.jpg",
          "note_url": "https://www.xiaohongshu.com/explore/...",
          "source_note": "小红书结果仅作近期体验、氛围和图片参考；发布前需确认授权。"
        }
      ],
      "baidu_search_entries": [],
      "source_urls": {
        "browser_search": "https://www.bing.com/images/search?q=...",
        "baidu_image": "https://image.baidu.com/search/index?tn=baiduimage&word=...",
        "baidu_web": "https://www.baidu.com/s?wd=...",
        "xhs": "https://www.xiaohongshu.com/search_result?keyword=...",
        "dianping": "https://www.dianping.com/search/keyword/...",
        "wikimedia": "https://commons.wikimedia.org/w/index.php?search=...",
        "official_or_encyclopedia": "https://www.bing.com/search?q=..."
      },
      "best_preview_image": null,
      "license_hint": "unknown",
      "authorized_for_publish": false,
      "usable_for_preview": true,
      "source_note": "第三方图片仅作预览候选；发布前需确认授权。",
      "degraded": true,
      "degraded_reason": "no_direct_image_candidate_collected_yet"
    }
  ],
  "travel_vlog_video_compatible": {
    "requests": []
  },
  "public_image_acquisition": {
    "enabled": true,
    "sources": ["wikimedia_commons"],
    "max_images_per_poi": 2,
    "acquired_direct_candidates": 3,
    "verified_at": "2026-06-29T12:00:00Z"
  },
  "warnings": []
}
```

## POI fields

- `name`: Required POI name.
- `type`: POI type such as `attraction`, `food`, `district`, `hotel`, `shop`, or `unknown`.
- `query_terms`: Search phrases used or recommended for collection.
- `direct_image_candidates`: Direct image URLs or local paths that may be usable by downstream resolvers. Entries may be strings or metadata objects; acquired public candidates should use metadata objects.
- `reference_image_candidates`: Reference images such as XHS covers or platform-visible thumbnails. These are not publishable by default.
- `xhs_notes`: Normalized Xiaohongshu note results from read-only search.
- `baidu_search_entries`: Optional normalized Baidu result entries if a later process extracts result metadata.
- `source_urls`: Source pages or search entry points grouped by channel.
- `best_preview_image`: Preferred preview image when a direct candidate is available.
- `license_hint`: Visible license note if found; otherwise `unknown`.
- `authorized_for_publish`: `true` only when the license is explicitly verified for the target usage.
- `usable_for_preview`: Whether the candidate can be used for local preview or review.
- `source_note`: Human-readable note about provenance and limitations.
- `degraded`: `true` when no direct image candidate is available.
- `degraded_reason`: Explanation for degraded output.

## Source URL fields

- `baidu_image`: Baidu image search entry. Default no-login source entry; not a direct image candidate.
- `baidu_web`: Baidu web search entry. Useful for finding official pages, Baike pages, media galleries, and platform pages.
- `xhs`: Xiaohongshu search entry or note entry.
- `dianping`: Dianping detail/search entry.
- `wikimedia`: Wikimedia Commons media search entry.
- `browser_search`: General image search entry.
- `official_or_encyclopedia`: Search entry for official or encyclopedia pages.

## Candidate fields

```json
{
  "url": "https://upload.wikimedia.org/example.jpg",
  "source": "wikimedia_commons",
  "source_page_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
  "content_type": "image/jpeg",
  "width": 1080,
  "height": 720,
  "license_hint": "Wikimedia Commons metadata; verify license and attribution before publishing",
  "authorized_for_publish": false,
  "usable_for_preview": true,
  "verified_at": "2026-06-29T12:00:00Z",
  "acquisition_method": "wikimedia_api_imageinfo",
  "note": "Wikimedia Commons 图片可作本地预览候选；发布前需核对许可证、署名和使用场景。"
}
```

Use `direct_image_candidates` only for directly usable image URLs or local files. Acquired public candidates should include `source_page_url`, `content_type`, `license_hint`, `verified_at`, and `acquisition_method`. Use `reference_image_candidates` for XHS covers, Baidu thumbnails, platform visible images, or other references that require manual review.

## travel-vlog-video compatible output

```json
{
  "travel_vlog_video_compatible": {
    "requests": [
      {
        "id": "poi-west-lake",
        "segment_id": "poi-west-lake",
        "name": "西湖",
        "city": "杭州",
        "type": "attraction",
        "duration": 5,
        "output": "poi-west-lake.png",
        "direct_image_candidates": [],
        "source_urls": {
          "baidu_image": "https://image.baidu.com/search/index?...",
          "baidu_web": "https://www.baidu.com/s?...",
          "xhs": "https://www.xiaohongshu.com/search_result?keyword=...",
          "dianping": "https://www.dianping.com/search/keyword/...",
          "image_search": "https://www.bing.com/images/search?q=...",
          "wikimedia": "https://commons.wikimedia.org/w/index.php?search=...",
          "official_or_encyclopedia": "https://www.bing.com/search?q=..."
        },
        "source_note": "第三方图片/平台入口仅作素材参考；下载和发布前需确认授权。"
      }
    ]
  }
}
```
