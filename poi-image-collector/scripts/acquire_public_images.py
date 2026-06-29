#!/usr/bin/env python3
"""Acquire verified public direct image candidates for POI image collections.

The script enriches collection JSON produced by build_image_requests.py. It only
uses structured public sources and keeps platform/search pages as references.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
DEFAULT_TIMEOUT_SEC = 12
DEFAULT_MAX_CHECK_BYTES = 12 * 1024 * 1024
USER_AGENT = "OpenClaw poi-image-collector/1.0"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def is_http_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def looks_like_supported_image(value: str) -> bool:
    suffix = Path(urllib.parse.urlparse(value).path).suffix.lower()
    return suffix in IMAGE_EXTENSIONS


def load_collection(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("pois"), list):
        raise ValueError("collection must contain a pois array")
    return data


def fetch_json(url: str, timeout: int) -> Dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "").lower()
        if "json" not in content_type and "javascript" not in content_type:
            raise ValueError(f"unexpected_json_content_type:{content_type or 'unknown'}")
        return json.loads(response.read().decode("utf-8"))


def commons_file_page(title: str) -> str:
    return "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(title.replace(" ", "_"), safe="/:_")


def extract_license_hint(metadata: Dict[str, Any]) -> str:
    for key in ["LicenseShortName", "UsageTerms", "License", "LicenseUrl"]:
        value = metadata.get(key)
        if isinstance(value, dict) and value.get("value"):
            return str(value["value"])
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "Wikimedia Commons metadata; verify license and attribution before publishing"


def search_wikimedia_images(query: str, limit: int, timeout: int) -> List[Dict[str, Any]]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(max(limit, 1)),
        "prop": "imageinfo",
        "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": "1080",
        "format": "json",
        "formatversion": "2",
    }
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    data = fetch_json(url, timeout)
    pages = data.get("query", {}).get("pages", [])
    if not isinstance(pages, list):
        return []

    results: List[Dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        title = str(page.get("title") or "").strip()
        imageinfo = page.get("imageinfo")
        if not title or not isinstance(imageinfo, list) or not imageinfo:
            continue
        info = imageinfo[0] if isinstance(imageinfo[0], dict) else {}
        mime = str(info.get("mime") or "").lower()
        if not mime.startswith("image/"):
            continue
        image_url = str(info.get("thumburl") or info.get("url") or "").strip()
        if not image_url:
            continue
        lower_blob = f"{title} {image_url}".lower()
        if any(marker in lower_blob for marker in [".djvu", ".pdf", "scan", "book", "page"]):
            continue
        results.append({
            "url": image_url,
            "source": "wikimedia_commons",
            "source_page_url": commons_file_page(title),
            "content_type": mime,
            "width": info.get("thumbwidth") or info.get("width"),
            "height": info.get("thumbheight") or info.get("height"),
            "size": info.get("size"),
            "license_hint": extract_license_hint(info.get("extmetadata") if isinstance(info.get("extmetadata"), dict) else {}),
            "authorized_for_publish": False,
            "usable_for_preview": True,
            "acquisition_method": "wikimedia_api_imageinfo",
        })
    return results


def verify_direct_image_url(url: str, timeout: int, max_bytes: int) -> Tuple[bool, Dict[str, Any]]:
    if not is_http_url(url):
        return False, {"reason": "not_http_url"}
    if not looks_like_supported_image(url):
        return False, {"reason": "unsupported_image_extension"}

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("content-type", "").lower()
            if "image" not in content_type:
                return False, {"reason": f"invalid_content_type:{content_type or 'unknown'}"}
            content_length = response.headers.get("content-length")
            if content_length and content_length.isdigit() and int(content_length) > max_bytes:
                return False, {"reason": "image_too_large", "content_type": content_type, "content_length": int(content_length)}
            data = response.read(min(max_bytes + 1, 65536))
            if not data:
                return False, {"reason": "empty_response", "content_type": content_type}
            if len(data) > max_bytes:
                return False, {"reason": "image_too_large", "content_type": content_type}
            return True, {"content_type": content_type, "checked_bytes": len(data)}
    except urllib.error.URLError as exc:
        return False, {"reason": f"download_failed:{exc.reason}"}
    except Exception as exc:
        return False, {"reason": f"download_failed:{exc}"}


def existing_candidate_urls(poi: Dict[str, Any]) -> set[str]:
    urls: set[str] = set()
    candidates = poi.get("direct_image_candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            if isinstance(candidate, str):
                urls.add(candidate)
            elif isinstance(candidate, dict) and isinstance(candidate.get("url"), str):
                urls.add(candidate["url"])
    return urls


def build_queries(city: str, poi: Dict[str, Any]) -> List[str]:
    name = str(poi.get("name") or "").strip()
    terms = []
    if city and name:
        terms.append(f"{city} {name}")
    if name:
        terms.append(name)
    for query in poi.get("query_terms") or []:
        if isinstance(query, str) and "Wikimedia" in query:
            terms.append(query.replace("Wikimedia Commons", "" ).strip())
    result: List[str] = []
    seen = set()
    for term in terms:
        if term and term not in seen:
            seen.add(term)
            result.append(term)
    return result


def acquire_for_poi(city: str, poi: Dict[str, Any], max_images: int, timeout: int, max_check_bytes: int) -> Dict[str, Any]:
    direct_candidates = poi.get("direct_image_candidates")
    if not isinstance(direct_candidates, list):
        direct_candidates = []
    poi["direct_image_candidates"] = direct_candidates

    warnings = poi.get("warnings") if isinstance(poi.get("warnings"), list) else []
    errors = poi.get("acquisition_errors") if isinstance(poi.get("acquisition_errors"), list) else []
    seen_urls = existing_candidate_urls(poi)
    added = 0

    for query in build_queries(city, poi):
        if added >= max_images:
            break
        try:
            results = search_wikimedia_images(query, max(max_images * 3, 5), timeout)
        except Exception as exc:
            errors.append({"source": "wikimedia_commons", "query": query, "reason": str(exc)})
            continue

        for candidate in results:
            if added >= max_images:
                break
            url = candidate.get("url")
            if not isinstance(url, str) or url in seen_urls:
                continue
            ok, verification = verify_direct_image_url(url, timeout, max_check_bytes)
            if not ok:
                errors.append({"source": "wikimedia_commons", "query": query, "url": url, **verification})
                continue
            candidate = dict(candidate)
            candidate["content_type"] = verification.get("content_type") or candidate.get("content_type")
            candidate["verified_at"] = utc_now()
            candidate["authorized_for_publish"] = False
            candidate["usable_for_preview"] = True
            candidate["note"] = "Wikimedia Commons 图片可作本地预览候选；发布前需核对许可证、署名和使用场景。"
            direct_candidates.append(candidate)
            seen_urls.add(url)
            added += 1
        time.sleep(0.2)

    if direct_candidates:
        first = direct_candidates[0]
        poi["best_preview_image"] = first.get("url") if isinstance(first, dict) else first
        poi["degraded"] = False
        poi["degraded_reason"] = None
        poi["source_note"] = "已获取公开来源直连图片候选；发布前仍需确认授权与署名要求。"
    else:
        poi["degraded"] = True
        poi["degraded_reason"] = "no_verified_direct_image_candidate"
        warnings.append("No verified direct image candidate acquired from public sources.")

    if warnings:
        poi["warnings"] = warnings
    if errors:
        poi["acquisition_errors"] = errors
    return poi


def update_compatible_requests(collection: Dict[str, Any]) -> None:
    pois = collection.get("pois") if isinstance(collection.get("pois"), list) else []
    compatible = collection.get("travel_vlog_video_compatible")
    if not isinstance(compatible, dict):
        return
    requests = compatible.get("requests")
    if not isinstance(requests, list):
        return
    by_name = {str(poi.get("name") or "").strip(): poi for poi in pois if isinstance(poi, dict)}
    for request in requests:
        if not isinstance(request, dict):
            continue
        poi = by_name.get(str(request.get("name") or "").strip())
        if not poi:
            continue
        urls: List[str] = []
        for candidate in poi.get("direct_image_candidates") or []:
            if isinstance(candidate, str) and candidate.strip():
                urls.append(candidate.strip())
            elif isinstance(candidate, dict) and isinstance(candidate.get("url"), str) and candidate["url"].strip():
                urls.append(candidate["url"].strip())
        seen = set()
        request["direct_image_candidates"] = [url for url in urls if not (url in seen or seen.add(url))]
        request["source_note"] = poi.get("source_note") or request.get("source_note")


def acquire_collection(collection: Dict[str, Any], max_images_per_poi: int, timeout: int, max_check_bytes: int) -> Dict[str, Any]:
    city = str(collection.get("city") or "").strip()
    pois = collection.get("pois") if isinstance(collection.get("pois"), list) else []
    total_added = 0
    for poi in pois:
        if not isinstance(poi, dict):
            continue
        before = len(poi.get("direct_image_candidates") or [])
        acquire_for_poi(city, poi, max_images_per_poi, timeout, max_check_bytes)
        after = len(poi.get("direct_image_candidates") or [])
        total_added += max(after - before, 0)
    update_compatible_requests(collection)
    collection["public_image_acquisition"] = {
        "enabled": True,
        "sources": ["wikimedia_commons"],
        "max_images_per_poi": max_images_per_poi,
        "acquired_direct_candidates": total_added,
        "verified_at": utc_now(),
    }
    warnings = collection.get("warnings") if isinstance(collection.get("warnings"), list) else []
    warnings.append("Public image acquisition currently uses Wikimedia Commons only; Baidu/XHS/Dianping remain reference sources unless direct source verification is added.")
    collection["warnings"] = warnings
    return collection


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Acquire verified public direct image candidates for a POI collection.")
    parser.add_argument("--collection", required=True, help="Input collection JSON from build_image_requests.py")
    parser.add_argument("--out", required=True, help="Output enriched collection JSON")
    parser.add_argument("--max-images-per-poi", type=int, default=2, help="Maximum verified direct images per POI")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC, help="Network timeout in seconds")
    parser.add_argument("--max-check-bytes", type=int, default=DEFAULT_MAX_CHECK_BYTES, help="Maximum accepted image size in bytes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collection_path = Path(args.collection)
    out_path = Path(args.out)
    collection = load_collection(collection_path)
    enriched = acquire_collection(collection, max(args.max_images_per_poi, 0), args.timeout, args.max_check_bytes)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(out_path.resolve()),
        "pois": len(enriched.get("pois", [])),
        "acquired_direct_candidates": enriched.get("public_image_acquisition", {}).get("acquired_direct_candidates", 0),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
