from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from amap_client import build_amap_navigation_url, geocode, plan_route, search_poi
from weather_client import build_weather_summary
from web_search import search_web

DEFAULT_PROFILE: dict[str, Any] = {
    "intent": "都要",
    "crowd_preference": "适中",
    "duration": "一天",
    "travel_type": "朋友",
    "budget": None,
    "first_time": None,
    "known_info": [],
}

ALLOWED_INTENTS = {"想玩", "想吃", "都要"}
ALLOWED_CROWD_PREFERENCES = {"热闹", "适中", "人少"}
ALLOWED_DURATIONS = {"半天", "一天", "晚上"}
ALLOWED_TRAVEL_TYPES = {"情侣", "朋友", "家庭", "独行"}
ALLOWED_ROUTE_MODES = {"walking", "driving", "transit"}

SUPPORTED_CITIES = {
    "上海", "杭州", "成都", "重庆", "广州", "深圳", "长沙", "郴州", "清远",
    "衡阳", "北京", "南京", "苏州", "武汉", "西安",
}

INTENT_PATTERNS = [
    ("都要", ["逛吃", "玩吃", "边玩边吃", "又想玩又想吃", "都要", "一起安排", "顺便吃饭"]),
    ("想吃", ["吃什么", "美食", "餐厅", "馆子", "饭店", "夜宵", "小吃", "想吃"]),
    ("想玩", ["玩什么", "去哪玩", "景点", "打卡", "逛逛", "游玩", "想玩"]),
]
CROWD_PATTERNS = [
    ("人少", ["人少", "避开人流", "别太挤", "不喜欢拥挤", "不想排队", "清净", "安静", "小众"]),
    ("热闹", ["热闹", "人多一点", "烟火气", "繁华", "热闹点", "越热闹越好"]),
    ("适中", ["适中", "别太冷清", "平衡一点"]),
]
DURATION_PATTERNS = [("晚上", ["晚上", "夜里", "夜游", "晚饭后", "今晚"]), ("半天", ["半天", "半日", "下午", "上午"]), ("一天", ["一天", "一日", "全天"])]
TRAVEL_TYPE_PATTERNS = [("情侣", ["情侣", "约会", "和对象", "和男朋友", "和女朋友", "两个人"]), ("家庭", ["家庭", "带娃", "亲子", "爸妈", "老人", "全家"]), ("独行", ["一个人", "独自", "独行", "solo"]), ("朋友", ["朋友", "同学", "闺蜜", "兄弟", "同事"])]
FIRST_TIME_TRUE_PATTERNS = ["第一次来", "初次来", "第一次去", "头一回来", "第一次到"]
FIRST_TIME_FALSE_PATTERNS = ["不是第一次", "来过很多次", "之前来过", "去过好几次", "熟一点"]
KNOWN_INFO_HINTS = {
    "夜景": ["夜景", "灯光", "江边", "江景", "citywalk夜景"],
    "拍照": ["拍照", "出片", "打卡", "好看", "氛围感"],
    "小吃": ["小吃", "路边摊", "夜宵", "街边吃的"],
    "本地菜": ["本地菜", "当地特色", "特色馆子", "地道"],
    "预算敏感": ["别太贵", "省钱", "预算有限", "穷游", "性价比"],
    "不想排队": ["不想排队", "别排太久", "少排队", "排队短一点"],
}
BUDGET_RANGE_PATTERNS = [re.compile(r"预算\s*(\d{2,5})\s*[到\-~至]\s*(\d{2,5})\s*元?"), re.compile(r"(\d{2,5})\s*[到\-~至]\s*(\d{2,5})\s*元\s*(预算|以内)?")]
BUDGET_SINGLE_PATTERNS = [re.compile(r"预算\s*(\d{2,5})\s*元"), re.compile(r"人均\s*(\d{2,5})\s*元"), re.compile(r"(\d{2,5})\s*元以内")]
WEATHER_HINTS = ["天气", "气温", "下雨", "适合出游", "适合旅游", "穿什么"]
ROUTE_HINTS = ["怎么走", "路线", "导航", "步行", "公交", "驾车"]
WEB_SEARCH_HINTS = ["最新", "实时", "最近", "官网", "开放时间", "营业时间", "票价", "门票", "政策"]


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.strip())


def extract_city(text: str) -> str | None:
    for city in SUPPORTED_CITIES:
        if city in text:
            return city
    match = re.search(r"去([\u4e00-\u9fa5]{2,6})(玩|旅游|逛|吃)", text)
    return match.group(1) if match else None


def extract_by_patterns(text: str, mapping: list[tuple[str, list[str]]]) -> str | None:
    for target, patterns in mapping:
        if any(keyword in text for keyword in patterns):
            return target
    return None


def extract_first_time(text: str) -> bool | None:
    if any(keyword in text for keyword in FIRST_TIME_FALSE_PATTERNS):
        return False
    if any(keyword in text for keyword in FIRST_TIME_TRUE_PATTERNS):
        return True
    return None


def extract_budget(text: str) -> str | None:
    for pattern in BUDGET_RANGE_PATTERNS:
        match = pattern.search(text)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
    for pattern in BUDGET_SINGLE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    if any(x in text for x in ["别太贵", "省钱", "穷游"]):
        return "预算敏感"
    return None


def extract_known_info(text: str) -> list[str]:
    return [label for label, keywords in KNOWN_INFO_HINTS.items() if any(keyword in text for keyword in keywords)]


def infer_route_mode(text: str) -> str:
    if "公交" in text or "地铁" in text:
        return "transit"
    if "驾车" in text or "开车" in text:
        return "driving"
    return "walking"


def infer_request_type(text: str) -> str:
    if any(keyword in text for keyword in WEATHER_HINTS):
        return "weather"
    if ("从" in text and "到" in text) or any(keyword in text for keyword in ROUTE_HINTS):
        return "route"
    if any(keyword in text for keyword in WEB_SEARCH_HINTS):
        return "web_search"
    return "recommendation"


def extract_route_points(text: str) -> dict[str, str | None]:
    match = re.search(r"从(.+?)到(.+?)(怎么走|路线|导航|最方便|最划算|步行|公交|驾车|$)", text)
    if not match:
        return {"origin": None, "destination": None}
    return {"origin": match.group(1).strip("，。！？； "), "destination": match.group(2).strip("，。！？； ")}


def parse_query(query: str) -> dict[str, Any]:
    text = normalize_text(query)
    route_points = extract_route_points(text)
    known_info = extract_known_info(text)
    city = extract_city(text)
    return {
        "city": city,
        "intent": extract_by_patterns(text, INTENT_PATTERNS) or "都要",
        "crowd_preference": extract_by_patterns(text, CROWD_PATTERNS),
        "duration": extract_by_patterns(text, DURATION_PATTERNS),
        "travel_type": extract_by_patterns(text, TRAVEL_TYPE_PATTERNS),
        "budget": extract_budget(text),
        "first_time": extract_first_time(text),
        "known_info": known_info,
        "request_type": infer_request_type(text),
        "route_mode": infer_route_mode(text),
        "origin": route_points["origin"],
        "destination": route_points["destination"],
        "search_query": " ".join(part for part in ([city] if city else []) + known_info[:2] + [query] if part),
        "raw_query": query,
    }


def build_profile(user_input: dict[str, Any]) -> dict[str, Any]:
    query = user_input.get("query") or user_input.get("text") or ""
    parsed = parse_query(query) if query else {}
    profile = dict(DEFAULT_PROFILE)
    profile.update({k: v for k, v in parsed.items() if v not in (None, "", [])})
    profile.update({k: v for k, v in user_input.items() if v not in (None, "", [])})
    known = []
    for value in [user_input.get("known_info"), parsed.get("known_info")]:
        if not value:
            continue
        known.extend([value] if isinstance(value, str) else value)
    profile["known_info"] = list(dict.fromkeys(known))
    return profile


def validate_profile(profile: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    request_type = profile.get("request_type", "recommendation")
    if request_type in {"weather", "recommendation"} and not profile.get("city"):
        errors.append("缺少 city，当前请求至少需要城市信息。")
    if request_type == "route":
        if not profile.get("origin"):
            errors.append("路线查询缺少 origin。")
        if not profile.get("destination"):
            errors.append("路线查询缺少 destination。")
    return errors


def build_response_outline(profile: dict[str, Any]) -> dict[str, Any]:
    request_type = profile.get("request_type", "recommendation")
    intent = profile.get("intent", "都要")
    if request_type == "weather":
        sections = ["天气概览", "未来预报", "出行建议"]
    elif request_type == "route":
        sections = ["路线概览", "起终点", "时长和距离", "补充建议"]
    elif request_type == "web_search":
        sections = ["搜索结论", "结果列表", "使用建议"]
    elif intent == "想玩":
        sections = ["总判断", "景点卡片", "时间安排", "注意事项"]
    elif intent == "想吃":
        sections = ["总判断", "餐厅卡片", "推荐菜", "踩坑提醒"]
    else:
        sections = ["总判断", "主路线", "景点卡片", "避坑提醒"]
    return {"city": profile.get("city"), "request_type": request_type, "intent": intent, "duration": profile.get("duration", "一天"), "crowd_preference": profile.get("crowd_preference", "适中"), "sections": sections}


def build_xhs_search_url(city: str, poi_name: str) -> str:
    keyword = " ".join(part for part in [city, poi_name, "攻略"] if part)
    return f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(keyword)}"


def build_image_search_url(city: str, poi_name: str) -> str:
    keyword = " ".join(part for part in [city, poi_name, "景点 图片"] if part)
    return f"https://www.bing.com/images/search?q={urllib.parse.quote(keyword)}"


def build_dianping_search_url(city: str, poi_name: str) -> str:
    keyword = " ".join(part for part in [city, poi_name] if part)
    return f"https://www.dianping.com/search/keyword/1/0_{urllib.parse.quote(keyword)}"


def build_poi_search_keyword(profile: dict[str, Any]) -> str:
    city = profile.get("city", "")
    intent = profile.get("intent", "都要")
    known_info = profile.get("known_info") or []
    if intent == "想吃":
        return " ".join([city, "美食"] + known_info[:1])
    return " ".join([city, "景点"] + known_info[:1])


def enrich_poi_item(poi: Any, city: str) -> dict[str, Any]:
    item = poi.to_dict() if hasattr(poi, "to_dict") else dict(poi)
    name = item.get("name", "")
    image_search_url = build_image_search_url(city, name)
    xhs_intro_url = build_xhs_search_url(city, name)
    dianping_url = item.get("dianping_url") or item.get("dianping_detail_url") or build_dianping_search_url(city, name)
    amap_navigation_url = build_amap_navigation_url(name, item.get("location"), city)
    detail_url = item.get("detail_url") or item.get("url") or dianping_url or amap_navigation_url
    source_note = item.get("source_note") or "大众点评/小红书/图片入口用于参考；开放时间、票务和实时排队以官方或平台实时页为准。"
    enriched = {
        **item,
        "detail_url": detail_url,
        "dianping_url": dianping_url,
        "xhs_url": item.get("xhs_url") or xhs_intro_url,
        "xhs_intro_url": xhs_intro_url,
        "image_url": item.get("image_url") or image_search_url,
        "image_search_url": image_search_url,
        "cover_image_url": item.get("cover_image_url") or image_search_url,
        "amap_navigation_url": amap_navigation_url,
        "source_note": source_note,
    }
    enriched["card"] = build_poi_card(enriched)
    enriched["feishu_card"] = build_feishu_recommendation_card(enriched)
    return enriched


def build_feishu_button(label: str, url: str | None, button_type: str = "default") -> dict[str, Any] | None:
    if not url:
        return None
    return {
        "tag": "button",
        "text": {"tag": "plain_text", "content": label},
        "type": button_type,
        "behaviors": [{"type": "open_url", "default_url": url}],
    }


def build_feishu_action_buttons(item: dict[str, Any]) -> list[dict[str, Any]]:
    buttons = [
        build_feishu_button("看详情", item.get("detail_url"), "primary"),
        build_feishu_button("大众点评", item.get("dianping_url")),
        build_feishu_button("小红书", item.get("xhs_url") or item.get("xhs_intro_url")),
        build_feishu_button("图片示例", item.get("image_url") or item.get("image_search_url")),
        build_feishu_button("高德导航", item.get("amap_navigation_url")),
    ]
    return [button for button in buttons if button]


def build_feishu_recommendation_card(item: dict[str, Any]) -> dict[str, Any]:
    title = item.get("name") or item.get("title") or "推荐卡片"
    subtitle = item.get("subtitle") or "｜".join(part for part in [item.get("district"), item.get("poi_type"), item.get("address")] if part) or "推荐信息"
    summary = item.get("summary") or item.get("recommend_reason") or item.get("reason") or "建议结合详情页、图片示例和实时平台信息确认。"
    risk_note = item.get("risk_note") or item.get("risk_notes") or item.get("notice") or "图片和平台入口仅作参考，开放时间、票务和排队以官方或平台实时页为准。"
    source_note = item.get("source_note") or "详情、图片、大众点评和小红书入口用于参考。"
    elements: list[dict[str, Any]] = [
        {"tag": "div", "text": {"tag": "plain_text", "content": str(subtitle)}},
        {"tag": "div", "text": {"tag": "plain_text", "content": f"推荐理由：{summary}"}},
        {"tag": "div", "text": {"tag": "plain_text", "content": f"提醒：{risk_note}"}},
        {"tag": "hr"},
    ]
    actions = build_feishu_action_buttons(item)
    if actions:
        elements.append({"tag": "action", "actions": actions})
    elements.append({"tag": "div", "text": {"tag": "plain_text", "content": str(source_note)}})
    return {
        "schema": "2.0",
        "config": {"width_mode": "fill"},
        "header": {
            "title": {"tag": "plain_text", "content": str(title)},
            "template": "blue",
        },
        "body": {"elements": elements},
    }


def build_feishu_channel_payload(card: dict[str, Any]) -> dict[str, Any]:
    return {"channelData": {"feishu": {"card": card}}}


def build_feishu_fallback_text(item: dict[str, Any]) -> str:
    lines = [
        f"推荐：{item.get('name') or item.get('title') or '未命名推荐'}",
        f"区域/类型：{item.get('subtitle') or item.get('district') or item.get('poi_type') or '待确认'}",
        f"推荐理由：{item.get('summary') or item.get('recommend_reason') or item.get('reason') or '建议结合详情页确认。'}",
        f"提醒：{item.get('source_note') or '平台入口用于参考，实时信息以官方或平台页面为准。'}",
    ]
    links = [
        ("看详情", item.get("detail_url")),
        ("大众点评", item.get("dianping_url")),
        ("小红书", item.get("xhs_url") or item.get("xhs_intro_url")),
        ("图片示例", item.get("image_url") or item.get("image_search_url")),
        ("高德导航", item.get("amap_navigation_url")),
    ]
    lines.extend(f"{label}：{url}" for label, url in links if url)
    return "\n".join(lines)


def build_poi_card(poi: dict[str, Any]) -> dict[str, Any]:
    subtitle = "｜".join(part for part in [poi.get("district"), poi.get("poi_type")] if part)
    return {
        "type": "poi_card",
        "title": poi.get("name", ""),
        "subtitle": subtitle,
        "cover_image_url": poi.get("cover_image_url"),
        "image_url": poi.get("image_url"),
        "image_alt": f"{poi.get('name', '')} 图片参考",
        "address": poi.get("address", ""),
        "detail_url": poi.get("detail_url"),
        "dianping_url": poi.get("dianping_url"),
        "xhs_url": poi.get("xhs_url") or poi.get("xhs_intro_url"),
        "amap_navigation_url": poi.get("amap_navigation_url"),
        "actions": [
            {"label": "看详情", "url": poi.get("detail_url")},
            {"label": "大众点评", "url": poi.get("dianping_url")},
            {"label": "小红书", "url": poi.get("xhs_url") or poi.get("xhs_intro_url")},
            {"label": "图片示例", "url": poi.get("image_url") or poi.get("image_search_url")},
            {"label": "高德导航", "url": poi.get("amap_navigation_url")},
        ],
        "source_note": poi.get("source_note"),
        "notice": "图片、大众点评和小红书入口用于参考；开放时间、票务和实时排队以官方或平台实时页为准。",
    }


def build_recommendation_data(profile: dict[str, Any]) -> dict[str, Any]:
    city = profile.get("city", "")
    data: dict[str, Any] = {
        "profile": profile,
        "outline": build_response_outline(profile),
        "poi_links_contract": {
            "detail": "detail_url 优先使用真实详情页；没有真实详情页时使用大众点评或高德搜索入口，不编造 URL。",
            "dianping": "dianping_url 使用大众点评详情页或搜索入口，用于餐厅、商户、商圈和本地生活参考。",
            "xhs": "xhs_url/xhs_intro_url 使用小红书搜索或代表笔记链接，用于软信号，不作为开放时间、票务、地址等硬事实。",
            "image": "cover_image_url/image_url/image_search_url 使用真实图片页或图片搜索参考入口，不声明版权或官方来源。",
            "amap": "amap_navigation_url 用于打开导航；无坐标时回退为高德搜索。",
            "card": "向用户推荐任何 POI 时，每个点位单独保留 card 字段，并携带详情、图片、大众点评、小红书和导航 actions。",
            "feishu_card": "飞书渠道优先使用非 Markdown interactive card；没有图片 key 时通过 图片示例 按钮打开 image_url。",
        },
        "pois": [],
        "poi_cards": [],
    }
    keyword = build_poi_search_keyword(profile)
    poi_result = search_poi(keyword, city)
    if not poi_result.ok:
        data["poi_search_error"] = poi_result.error
        return data
    pois = [enrich_poi_item(poi, city) for poi in (poi_result.data or [])[:5]]
    data["pois"] = pois
    data["poi_cards"] = [poi["card"] for poi in pois]
    return data


def route_request(user_input: dict[str, Any]) -> dict[str, Any]:
    profile = build_profile(user_input)
    errors = validate_profile(profile)
    if errors:
        return {"ok": False, "source": "travel-skill", "errors": errors, "profile": profile}
    request_type = profile.get("request_type", "recommendation")
    if request_type == "weather":
        return build_weather_summary(profile["city"]).to_dict()
    if request_type == "route":
        city = profile.get("city")
        origin_result = geocode(profile["origin"], city)
        if not origin_result.ok:
            return origin_result.to_dict()
        destination_result = geocode(profile["destination"], city)
        if not destination_result.ok:
            return destination_result.to_dict()
        route_result = plan_route(origin_result.data.get("location", ""), destination_result.data.get("location", ""), city or "", profile.get("route_mode", "walking"))
        return route_result.to_dict()
    if request_type == "web_search":
        return search_web(profile.get("search_query") or profile.get("raw_query") or "").to_dict()
    return {"ok": True, "source": "travel-skill", "data": build_recommendation_data(profile)}


def to_pretty_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    samples = [
        {"query": "帮我看看杭州这两天天气怎么样，适不适合旅游？"},
        {"query": "从橘子洲到岳麓山怎么走，公交最划算吗？", "city": "长沙"},
        {"query": "帮我查一下上海博物馆最新开放时间和预约政策"},
        {"query": "我和对象第一次去杭州玩半天，想拍照，不想排长队，顺便吃点本地菜，预算300到500元。"},
    ]
    for sample in samples:
        print(to_pretty_json(route_request(sample)))
        print("-" * 60)
