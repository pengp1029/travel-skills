#!/usr/bin/env python3
"""Build offline travel vlog planning artifacts from a travel plan."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_WIDTH = 1080
DEFAULT_HEIGHT = 1920
DEFAULT_FPS = 30
DEFAULT_RATIO = "9:16"

ROUTE_MODES = {
    "步行": "walking",
    "走路": "walking",
    "walking": "walking",
    "walk": "walking",
    "骑行": "bicycling",
    "bike": "bicycling",
    "bicycling": "bicycling",
    "驾车": "driving",
    "开车": "driving",
    "drive": "driving",
    "driving": "driving",
    "地铁": "transit",
    "公交": "transit",
    "公共交通": "transit",
    "transit": "transit",
    "subway": "transit",
    "bus": "transit",
}

TRANSPORTS = {
    "高铁": "train",
    "火车": "train",
    "动车": "train",
    "train": "train",
    "飞机": "flight",
    "航班": "flight",
    "flight": "flight",
    "自驾": "drive",
    "开车": "drive",
    "drive": "drive",
    "大巴": "bus",
    "巴士": "bus",
    "bus": "bus",
}


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", text)
    text = text.strip("-")
    return text or "segment"


def infer_city(text: str) -> str:
    for city in ["杭州", "上海", "北京", "苏州", "南京", "成都", "重庆", "广州", "深圳", "西安", "厦门"]:
        if city in text:
            return city
    return ""


def infer_route_mode(text: str) -> str:
    for key, mode in ROUTE_MODES.items():
        if key.lower() in text.lower():
            return mode
    return "walking"


def infer_transport(text: str) -> str:
    for key, value in TRANSPORTS.items():
        if key.lower() in text.lower():
            return value
    return "unknown"


def split_parts(text: str) -> List[str]:
    parts = re.split(r"[，,；;。\n]+", text)
    return [part.strip() for part in parts if part.strip()]


def clean_stop_name(name: str) -> str:
    name = name.strip(" 从")
    if "：" in name:
        name = name.rsplit("：", 1)[-1]
    if ":" in name:
        name = name.rsplit(":", 1)[-1]
    return name.strip()


def parse_route_part(part: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"(.+?)(?:->|→|到|至)(.+)", part)
    if not match:
        return None
    from_name = clean_stop_name(match.group(1))
    tail = match.group(2).strip()
    mode = infer_route_mode(part)
    for key in sorted(ROUTE_MODES.keys(), key=len, reverse=True):
        tail = tail.replace(key, "")
    to_name = clean_stop_name(tail.strip(" 一段路线") or match.group(2).strip())
    if not from_name or not to_name:
        return None
    return {"type": "route", "from": from_name, "to": to_name, "mode": mode}


def parse_intercity_part(part: str) -> Optional[Dict[str, Any]]:
    transport = infer_transport(part)
    if transport == "unknown":
        return None
    match = re.search(r"(.+?)(?:到|至|->|→)(.+)", part)
    if not match:
        return None
    from_city = match.group(1).strip(" 从乘坐搭坐坐")
    tail = match.group(2).strip()
    for key in sorted(TRANSPORTS.keys(), key=len, reverse=True):
        tail = tail.replace(key, "")
    to_city = tail.strip(" 前往出发抵达")
    if len(from_city) > 8 or len(to_city) > 8:
        return None
    return {"from_city": from_city, "to_city": to_city, "transport": transport}


def parse_natural_plan(text: str) -> Dict[str, Any]:
    city = infer_city(text)
    items: List[Dict[str, Any]] = []
    transfers: List[Dict[str, Any]] = []
    seen_pois = set()

    for part in split_parts(text):
        intercity = parse_intercity_part(part)
        if intercity:
            transfers.append(intercity)
            continue
        route = parse_route_part(part)
        if route:
            route["city"] = city
            items.append(route)
            for name in [route["from"], route["to"]]:
                if name not in seen_pois and not any(token in name for token in ["上午", "下午", "晚上", "中午"]):
                    seen_pois.add(name)
            continue
        if any(word in part for word in ["吃", "美食", "小吃", "餐厅", "咖啡"]):
            name = re.sub(r".*?(去|吃|到)", "", part).strip() or part
            items.append({"type": "food", "name": name, "description": part})
        elif any(word in part for word in ["游", "逛", "玩", "拍照", "景点", "散步"]):
            name = re.sub(r".*?(去|到|逛|游)", "", part).strip() or part
            items.append({"type": "attraction", "name": name, "description": part})

    for poi in seen_pois:
        if not any(item.get("name") == poi for item in items):
            items.insert(0, {"type": "attraction", "name": poi, "description": f"{poi} 游玩片段"})

    return {
        "title": f"{city or '旅行'} vlog",
        "city": city,
        "items": items,
        "intercityTransfers": transfers,
    }


def load_plan(args: argparse.Namespace) -> Dict[str, Any]:
    if args.input_file:
        data = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        raise ValueError("input JSON must be an object")
    if args.plan:
        return parse_natural_plan(args.plan)
    raise ValueError("provide --plan or --input-file")


def flatten_items(plan: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    if isinstance(plan.get("items"), list):
        for item in plan["items"]:
            yield dict(item)
    for day in plan.get("days", []) or []:
        city = day.get("city") or plan.get("city") or ""
        for item in day.get("items", []) or []:
            new_item = dict(item)
            new_item.setdefault("city", city)
            yield new_item


def prompt_for_item(item: Dict[str, Any], city: str) -> str:
    name = item.get("name") or item.get("title") or "旅行片段"
    desc = item.get("description") or ""
    if item.get("type") == "food":
        return f"{city}{name}，{desc}，食物特写，热气和真实街头氛围，轻快旅行 vlog 风格，手机竖屏，手持镜头"
    return f"{city}{name}，{desc}，游客自然游玩，景点氛围真实，轻快旅行 vlog 风格，手机竖屏，手持镜头缓慢推进"


def build_xhs_search_url(city: str, poi_name: str) -> str:
    keyword = " ".join(part for part in [city, poi_name, "攻略"] if part)
    return f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(keyword)}"


def build_image_search_url(city: str, poi_name: str) -> str:
    keyword = " ".join(part for part in [city, poi_name, "景点 图片"] if part)
    return f"https://www.bing.com/images/search?q={urllib.parse.quote(keyword)}"


def build_dianping_search_url(city: str, poi_name: str) -> str:
    keyword = " ".join(part for part in [city, poi_name] if part)
    return f"https://www.dianping.com/search/keyword/1/0_{urllib.parse.quote(keyword)}"


def collect_direct_image_candidates(item: Dict[str, Any]) -> List[str]:
    candidates: List[str] = []
    for key in ["image_path", "local_image", "photo_path", "image_url", "cover_image_url", "photo_url"]:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
    for key in ["image_urls", "images", "photos"]:
        values = item.get(key)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, str) and value.strip():
                    candidates.append(value.strip())
                elif isinstance(value, dict):
                    url = value.get("url") or value.get("image_url") or value.get("photo_url")
                    if isinstance(url, str) and url.strip():
                        candidates.append(url.strip())
    return list(dict.fromkeys(candidates))


def build_source_urls(item: Dict[str, Any], city: str, name: str) -> Dict[str, str]:
    return {
        "xhs": item.get("xhs_url") or item.get("xhs_intro_url") or item.get("xhs_reference_url") or build_xhs_search_url(city, name),
        "dianping": item.get("dianping_url") or item.get("dianping_detail_url") or build_dianping_search_url(city, name),
        "image_search": item.get("image_search_url") or build_image_search_url(city, name),
    }


def normalize_poi_name(name: Any) -> str:
    text = re.sub(r"第[一二三四五六七八九十]+天", "", str(name or ""))
    return re.sub(r"\s+", "", text).strip()


def find_poi_request_for_destination(destination: Any, poi_image_requests: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    normalized_destination = normalize_poi_name(destination)
    if not normalized_destination:
        return None
    by_name = {normalize_poi_name(request.get("name")): request for request in poi_image_requests}
    if normalized_destination in by_name:
        return by_name[normalized_destination]
    for normalized_name, request in by_name.items():
        if normalized_name and (normalized_destination in normalized_name or normalized_name in normalized_destination):
            return request
    return None


def build_ffmpeg_items_by_route_arrival(
    route_plans: List[Dict[str, Any]],
    poi_image_requests: List[Dict[str, Any]],
    transitions: List[Dict[str, Any]],
) -> tuple[List[Dict[str, Any]], List[str], List[str]]:
    items: List[Dict[str, Any]] = [{"path": "PLACEHOLDER/title-001.png", "type": "image", "duration": 3}]
    for transition in transitions:
        items.append({"path": f"PLACEHOLDER/{transition['id']}.png", "type": "image", "duration": transition["duration_sec"]})

    used_poi_ids: set[str] = set()
    missing_destination_pois: List[str] = []
    if route_plans:
        for route in route_plans:
            items.append({"path": f"PLACEHOLDER/{route['id']}.mp4", "type": "video", "start": 0, "duration": 8})
            segment = (route.get("segments") or [{}])[0]
            destination = segment.get("to")
            poi_request = find_poi_request_for_destination(destination, poi_image_requests)
            if poi_request:
                used_poi_ids.add(str(poi_request["id"]))
                items.append({"path": f"PLACEHOLDER/{poi_request['id']}.png", "type": "image", "duration": poi_request["duration"]})
            elif destination:
                missing_destination_pois.append(str(destination))
        extra_poi_ids = [str(request["id"]) for request in poi_image_requests if str(request["id"]) not in used_poi_ids]
        return items, extra_poi_ids, missing_destination_pois

    for request in poi_image_requests:
        used_poi_ids.add(str(request["id"]))
        items.append({"path": f"PLACEHOLDER/{request['id']}.png", "type": "image", "duration": request["duration"]})
    return items, [], missing_destination_pois


def build_artifacts(plan: Dict[str, Any], out_dir: Path) -> Dict[str, Any]:
    title = plan.get("title") or "旅行 vlog"
    city = plan.get("city") or ""
    segments: List[Dict[str, Any]] = [{
        "id": "title-001",
        "kind": "title",
        "duration_sec": 3,
        "caption": title,
        "visual": "标题卡 + 城市氛围",
        "asset_policy": "template_or_image",
    }]
    poi_image_requests: List[Dict[str, Any]] = []
    doubao_requests: List[Dict[str, Any]] = []
    route_plans: List[Dict[str, Any]] = []

    for item in flatten_items(plan):
        item_type = item.get("type", "attraction")
        item_city = item.get("city") or city
        if item_type == "route" or (item.get("from") and item.get("to")):
            from_name = item.get("from")
            to_name = item.get("to")
            mode = item.get("mode") or infer_route_mode(json.dumps(item, ensure_ascii=False))
            route_id = f"route-{slugify(str(from_name))}-{slugify(str(to_name))}"
            segments.append({
                "id": route_id,
                "kind": "amap-route-video",
                "duration_sec": int(item.get("duration_sec", 8)),
                "caption": f"{from_name} → {to_name}",
                "visual": f"高德路线动画：{from_name} 到 {to_name}",
                "asset_policy": "amap-route-video",
                "route": {"city": item_city, "from": from_name, "to": to_name, "mode": mode},
            })
            route_plans.append({
                "id": route_id,
                "city": item_city,
                "title": f"{from_name}到{to_name}",
                "segments": [{"from": from_name, "to": to_name, "mode": mode}],
                "expected_output": f"{route_id}.mp4",
            })
            continue

        name = item.get("name") or item.get("title") or "旅行片段"
        segment_id = f"poi-{slugify(str(name))}"
        duration = int(item.get("duration_sec", 5))
        prompt = item.get("prompt") or prompt_for_item(item, item_city)
        direct_image_candidates = collect_direct_image_candidates(item)
        source_urls = build_source_urls(item, item_city, str(name))
        segments.append({
            "id": segment_id,
            "kind": "poi-image",
            "duration_sec": duration,
            "caption": str(name),
            "visual": f"{item_city}{name} 图片素材卡 / 景点氛围图",
            "asset_policy": "prefer_user_image_then_direct_image_then_source_card",
        })
        poi_image_requests.append({
            "id": segment_id,
            "segment_id": segment_id,
            "name": str(name),
            "city": item_city,
            "type": item_type,
            "duration": duration,
            "output": f"{segment_id}.png",
            "direct_image_candidates": direct_image_candidates,
            "source_urls": source_urls,
            "source_note": item.get("source_note") or "第三方图片/平台入口仅作素材参考；下载和发布前需确认授权。",
        })
        request: Dict[str, Any] = {
            "id": segment_id,
            "segment_id": segment_id,
            "prompt": prompt,
            "output": f"{segment_id}.mp4",
            "duration": duration,
            "return_last_frame": True,
            "optional": True,
            "usage": "optional_enhancement_after_poi_image_assets",
        }
        if direct_image_candidates:
            request["image_url"] = direct_image_candidates[0]
            request["image_role"] = "first_frame"
        doubao_requests.append(request)

    transitions = []
    for transfer in plan.get("intercityTransfers", []) or plan.get("intercity_transfers", []) or []:
        from_city = transfer.get("from_city") or transfer.get("fromCity") or transfer.get("from")
        to_city = transfer.get("to_city") or transfer.get("toCity") or transfer.get("to")
        transport = transfer.get("transport") or transfer.get("mode") or "unknown"
        transition_id = f"intercity-{slugify(str(from_city))}-{slugify(str(to_city))}"
        visual_marker = "飞机 marker 和弧线航线" if transport == "flight" else "列车/小车 marker 沿线移动"
        transition = {
            "id": transition_id,
            "kind": "intercity-transition",
            "from_city": from_city,
            "to_city": to_city,
            "transport": transport,
            "duration_sec": int(transfer.get("duration_sec", 5)),
            "visual": f"地图上从{from_city}到{to_city}的点到点移动线，{visual_marker}",
            "fallback": "静态地图标题卡",
            "status": "needs_renderer_or_placeholder",
        }
        transitions.append(transition)
        segments.insert(1, {
            "id": transition_id,
            "kind": "intercity-transition",
            "duration_sec": transition["duration_sec"],
            "caption": f"{from_city} → {to_city}",
            "visual": transition["visual"],
            "asset_policy": "renderer_or_placeholder",
        })

    ffmpeg_items, extra_poi_ids, missing_destination_pois = build_ffmpeg_items_by_route_arrival(route_plans, poi_image_requests, transitions)

    video_script = {
        "title": title,
        "width": DEFAULT_WIDTH,
        "height": DEFAULT_HEIGHT,
        "fps": DEFAULT_FPS,
        "ratio": DEFAULT_RATIO,
        "segments": segments,
    }
    poi_image_manifest = {
        "version": 1,
        "default_strategy": "prefer_user_image_then_direct_image_then_source_card",
        "requests": poi_image_requests,
    }
    doubao_manifest = {
        "model": "doubao-seedance-2-0-260128",
        "ratio": DEFAULT_RATIO,
        "resolution": "720p",
        "duration": 5,
        "watermark": False,
        "optional": True,
        "usage": "optional_enhancement_after_poi_image_assets",
        "requests": doubao_requests,
    }
    amap_plan = {"title": f"{title} 路线", "routes": route_plans}
    intercity = {"transitions": transitions}
    ffmpeg_manifest = {
        "output": "travel-vlog.mp4",
        "width": DEFAULT_WIDTH,
        "height": DEFAULT_HEIGHT,
        "fps": DEFAULT_FPS,
        "image_duration": 3,
        "items": ffmpeg_items,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "video_script": out_dir / "video_script.json",
        "poi_image_requests": out_dir / "poi_image_requests.json",
        "doubao_requests": out_dir / "doubao_requests.json",
        "amap_route_plan": out_dir / "amap_route_plan.json",
        "intercity_transitions": out_dir / "intercity_transitions.json",
        "ffmpeg_manifest_draft": out_dir / "ffmpeg_manifest.draft.json",
    }
    payloads = {
        "video_script": video_script,
        "poi_image_requests": poi_image_manifest,
        "doubao_requests": doubao_manifest,
        "amap_route_plan": amap_plan,
        "intercity_transitions": intercity,
        "ffmpeg_manifest_draft": ffmpeg_manifest,
    }
    for key, path in files.items():
        path.write_text(json.dumps(payloads[key], ensure_ascii=False, indent=2), encoding="utf-8")

    warnings = []
    if not city:
        warnings.append("未识别到默认城市；路线生成前可能需要补充 city。")
    if transitions:
        warnings.append("跨城转场已生成脚本；初版需要渲染器或静态占位素材。")
    if extra_poi_ids:
        warnings.append(f"以下 POI 未作为路线目的地插入主序列：{', '.join(extra_poi_ids)}。")
    if missing_destination_pois:
        warnings.append(f"以下路线目的地缺少 POI 图片请求：{', '.join(missing_destination_pois)}。")

    report = {
        "degraded": bool(warnings),
        "outputs": {key: str(path.resolve()) for key, path in files.items()},
        "counts": {
            "segments": len(segments),
            "poi_image_requests": len(poi_image_requests),
            "doubao_requests": len(doubao_requests),
            "amap_routes": len(route_plans),
            "intercity_transitions": len(transitions),
        },
        "sequence_policy": "route_then_arrived_destination_poi_image",
        "extra_poi_ids": extra_poi_ids,
        "missing_destination_pois": missing_destination_pois,
        "warnings": warnings,
    }
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["outputs"]["report"] = str(report_path.resolve())
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Build travel vlog planning artifacts")
    parser.add_argument("--plan", help="Natural language travel plan")
    parser.add_argument("--input-file", help="JSON travel plan file")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    args = parser.parse_args()

    try:
        plan = load_plan(args)
        report = build_artifacts(plan, Path(args.out_dir))
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"degraded": True, "error_code": "fatal", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
