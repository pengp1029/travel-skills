# Source Policy

This policy defines how `poi-image-collector` should classify and report image sources.

## Source priority

1. User-provided local images or direct image URLs.
2. Baidu image and web search entries for no-login discovery.
3. Official attraction, restaurant, hotel, or tourism pages.
4. Public galleries with visible license information, such as Wikimedia Commons.
5. Encyclopedia or city tourism pages.
6. Browser image search result entries.
7. Dianping pages for restaurants, shops, districts, and local lifestyle POIs.
8. Xiaohongshu read-only search or note pages for atmosphere and visual references.

Priority does not mean automatic publishability. License and permission still need to be verified.

## Direct candidates vs reference candidates vs source entries

Use `direct_image_candidates` only for:

- User-provided local image paths.
- User-provided image URLs.
- URLs that are clearly direct image resources by extension or response metadata.
- Public gallery image URLs where the actual image file is visible and source page can be recorded.

Use `reference_image_candidates` for:

- Xiaohongshu note covers or detail images.
- Baidu thumbnails or result preview images.
- Dianping visible images without clear reuse permission.
- Any platform image that is useful for local preview but not verified for publishing.

Use `source_urls` for:

- Baidu image search pages.
- Baidu web search pages.
- Search result pages.
- HTML detail pages.
- Xiaohongshu notes or search pages.
- Dianping shops, photo pages, or search pages.
- Official pages that show images but do not expose direct image files.
- Encyclopedia pages or article pages.

## Public acquisition policy

- Run public acquisition only after source scaffolding is built.
- Prefer structured public galleries such as Wikimedia Commons before platform thumbnails or arbitrary search results.
- Add a URL to `direct_image_candidates` only after response metadata confirms it is an image and the source page can be recorded.
- Record `source_page_url`, `content_type`, `license_hint`, `verified_at`, and `acquisition_method` for acquired candidates.
- Keep `authorized_for_publish=false` unless the license and target usage are explicitly verified.
- If acquisition fails, keep source URLs and set a clear `degraded_reason`; do not fabricate image availability.

## Baidu policy

- Generate `source_urls.baidu_image` and `source_urls.baidu_web` by default for Chinese POIs.
- Treat Baidu results as discovery entries, not as verified image sources.
- Do not bulk download Baidu thumbnails.
- Do not bypass Baidu verification, captcha, rate limits, or anti-abuse controls.
- Only move a Baidu-discovered image into `direct_image_candidates` after the true source page and direct image URL are verified.

## Xiaohongshu policy

- Use `xiaohongshu-skills` only in read-only mode: `search-feeds`, `get-feed-detail`, `list-feeds`, `user-profile`.
- Do not publish, comment, reply, like, favorite, or clear login state from image collection workflows.
- Stop on login failure, captcha, scan verification, risk control, extension unavailability, or rate limiting.
- Store XHS note covers in `reference_image_candidates`, not `direct_image_candidates`, unless the user explicitly provides an approved local asset.
- Do not treat Xiaohongshu content as official facts for opening hours, ticket prices, addresses, or reservations.

## License fields

- `license_hint`: visible license text or `unknown`.
- `authorized_for_publish`: default `false`.
- `usable_for_preview`: may be `true` for local preview or review workflows.

Only set `authorized_for_publish=true` when all of the following are true:

1. The license is visible and unambiguous.
2. The license permits the intended user scenario.
3. Required attribution or share-alike conditions are captured in `source_note`.
4. The result is not from a source that prohibits reuse.

## Degradation rules

Set `degraded=true` when:

- No direct image candidate is available.
- The only available result is a search entry.
- The site requires login, captcha, slider verification, scan verification, or manual user action.
- The POI is ambiguous and the source cannot be confidently matched.

Use `degraded_reason` to explain the cause.

## Safety constraints

- Do not bypass login, captcha, slider verification, scan verification, paywalls, rate limits, or anti-abuse controls.
- Do not scrape or download images in bulk.
- Do not fabricate URLs, sources, licenses, attributions, or content availability.
- Do not treat Baidu, Xiaohongshu, or Dianping images as publishable by default.
- Do not represent search snippets as verified source facts.
- If platform content is only visible after login or manual verification, record the entry and ask for user-provided material when necessary.

## Recommended source notes

For unknown licensing:

```text
第三方图片仅作本地预览或素材候选；发布前需确认授权。
```

For Baidu entries:

```text
百度搜索入口仅用于发现来源页面；结果图片不默认可下载或发布。
```

For Xiaohongshu entries:

```text
小红书结果仅作近期体验、氛围和图片参考；发布前需确认授权。
```

For login-limited pages:

```text
来源需要登录或人工验证，未抓取图片；仅保留参考入口。
```
