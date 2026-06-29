#!/usr/bin/env python3
"""Build deterministic multi-source POI image request scaffolding.

This script does not crawl websites or download images. It creates source query URLs
and downstream-compatible request JSON for manual or agent-assisted collection.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List

DEFAULT_DURATION = 5


def slugify(text: str) -> str:
    value = re.sub(r"\s+", "-", text.strip().lower())
    value = re.sub(r"[^\w\-\u4e00-\u9fff]+", "", value)
    return value.strip("-") or "poi"


def parse_pois(raw: str) -> List[Dict[str, str]]:
    pois: List[Dict[str, str]] = []
    for item in re.split(r"[,，;；\n]+", raw):
        name = item.strip()
        if not name:
            continue
        poi_type = "unknown"
        if ":" in name:
            poi_type, name = [part.strip() for part in name.split(":", 1)]
        elif "：" in name:
            poi_type, name = [part.strip() for part in name.split("：", 1)]
        if name:
            pois.append({"name": name, "type": poi_type or "unknown"})
    return pois


def quote_query(*parts: str) -> str:
    query = " ".join(part for part in parts if part)
    return urllib.parse.quote(query)


def build_source_urls(city: str, name: str) -> Dict[str, str]:
    return {
        "browser_search": f"https://www.bing.com/images/search?q={quote_query(city, name, '图片')}",
        "baidu_image": f"https://image.baidu.com/search/index?tn=baiduimage&word={quote_query(city, name, '图片')}",
        "baidu_web": f"https://www.baidu.com/s?wd={quote_query(city, name, '图片')}",
        "xhs": f"https://www.xiaohongshu.com/search_result?keyword={quote_query(city, name, '攻略')}",
        "dianping": f"https://www.dianping.com/search/keyword/1/0_{quote_query(city, name)}",
        "wikimedia": f"https://commons.wikimedia.org/w/index.php?search={quote_query(city, name)}&title=Special:MediaSearch&type=image",
        "official_or_encyclopedia": f"https://www.bing.com/search?q={quote_query(city, name, '官方 图片 百科')}",
    }


def build_query_terms(city: str, name: str) -> List[str]:
    return [
        " ".join(part for part in [city, name, "图片"] if part),
        " ".join(part for part in [city, name, "百度图片"] if part),
        " ".join(part for part in [city, name, "小红书"] if part),
        " ".join(part for part in [city, name, "大众点评"] if part),
        " ".join(part for part in [city, name, "Wikimedia Commons"] if part),
        " ".join(part for part in [city, name, "官方 图片"] if part),
    ]


def build_poi(city: str, poi: Dict[str, str]) -> Dict[str, Any]:
    name = poi["name"]
    poi_type = poi.get("type") or "unknown"
    return {
        "name": name,
        "type": poi_type,
        "query_terms": build_query_terms(city, name),
        "direct_image_candidates": [],
        "reference_image_candidates": [],
        "xhs_notes": [],
        "baidu_search_entries": [],
        "source_urls": build_source_urls(city, name),
        "best_preview_image": None,
        "license_hint": "unknown",
        "authorized_for_publish": False,
        "usable_for_preview": True,
        "source_note": "当前仅生成多渠道图片搜索入口；百度/小红书等第三方图片发布前需确认授权。",
        "degraded": True,
        "degraded_reason": "no_direct_image_candidate_collected_yet",
    }


def build_vlog_request(city: str, poi: Dict[str, Any]) -> Dict[str, Any]:
    poi_id = f"poi-{slugify(poi['name'])}"
    source_urls = poi["source_urls"]
    return {
        "id": poi_id,
        "segment_id": poi_id,
        "name": poi["name"],
        "city": city,
        "type": poi.get("type", "unknown"),
        "duration": DEFAULT_DURATION,
        "output": f"{poi_id}.png",
        "direct_image_candidates": [candidate["url"] for candidate in poi["direct_image_candidates"] if candidate.get("url")],
        "source_urls": {
            "baidu_image": source_urls["baidu_image"],
            "baidu_web": source_urls["baidu_web"],
            "xhs": source_urls["xhs"],
            "dianping": source_urls["dianping"],
            "image_search": source_urls["browser_search"],
            "wikimedia": source_urls["wikimedia"],
            "official_or_encyclopedia": source_urls["official_or_encyclopedia"],
        },
        "source_note": poi["source_note"],
    }


def build_collection(
    city: str,
    pois: List[Dict[str, str]],
    usage: str,
    max_images_per_poi: int,
    xhs_skill_dir: str | None,
) -> Dict[str, Any]:
    built_pois = [build_poi(city, poi) for poi in pois]
    return {
        "version": 1,
        "city": city,
        "usage": usage,
        "max_images_per_poi": max_images_per_poi,
        "xhs_enabled": bool(xhs_skill_dir),
        "xhs_skill_dir": xhs_skill_dir,
        "pois": built_pois,
        "travel_vlog_video_compatible": {
            "requests": [build_vlog_request(city, poi) for poi in built_pois]
        },
        "warnings": [
            "This file contains search/source scaffolding only; it does not verify licenses or download images.",
            "Baidu and Xiaohongshu entries are references by default and are not automatically direct image candidates.",
            "authorized_for_publish defaults to false until each source license is checked.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build multi-source POI image collection requests.")
    parser.add_argument("--city", required=True, help="City name, for example: 杭州")
    parser.add_argument("--pois", required=True, help="Comma-separated POI names. Optional format: type:name")
    parser.add_argument("--usage", default="travel_vlog_preview", help="Intended usage label")
    parser.add_argument("--max-images-per-poi", type=int, default=3, help="Target number of images per POI")
    parser.add_argument("--xhs-skill-dir", default=None, help="Optional xiaohongshu-skills directory")
    parser.add_argument("--out", required=True, help="Output JSON path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pois = parse_pois(args.pois)
    if not pois:
        raise SystemExit("No valid POIs provided")

    collection = build_collection(args.city, pois, args.usage, args.max_images_per_poi, args.xhs_skill_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))


if __name__ == "__main__":
    main()
