from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MEMORY_ROOT = SKILL_ROOT / ".travel_memory"
DEFAULT_USER_ID = "default"


def load_openclaw_env() -> None:
    for parent in Path(__file__).resolve().parents:
        if parent.name != ".openclaw":
            continue
        env_path = parent / ".env"
        if not env_path.exists():
            return
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value
        return


load_openclaw_env()

SENSITIVE_PATTERNS = [
    re.compile(r"1[3-9]\d{9}"),
    re.compile(r"\d{17}[\dXx]"),
    re.compile(r"(身份证|手机号|电话|支付|银行卡|密码|token|登录态|cookie|订票凭证|订单号)"),
]

CITY_NAMES = [
    "北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "长沙", "南京", "苏州",
    "武汉", "西安", "厦门", "青岛", "大理", "丽江", "昆明", "桂林", "三亚", "郴州",
    "清远", "衡阳", "天津", "宁波", "无锡", "扬州", "福州", "泉州", "香港", "澳门",
]

TRIP_TYPE_KEYWORDS = {
    "亲子": ["亲子", "带娃", "孩子", "小朋友", "家庭"],
    "情侣": ["情侣", "约会", "对象", "男朋友", "女朋友"],
    "老人": ["老人", "爸妈", "父母", "长辈"],
    "独行": ["独行", "一个人", "solo", "独自"],
    "朋友": ["朋友", "同学", "闺蜜", "兄弟", "同事"],
}

TAG_KEYWORDS = [
    "亲子", "情侣", "老人", "独行", "朋友", "美食", "本地菜", "小吃", "咖啡", "夜宵",
    "少排队", "人少", "热闹", "小众", "博物馆", "自然风景", "citywalk", "夜景",
    "拍照", "购物", "酒店周边", "轻松", "特种兵", "地铁", "自驾", "预算敏感",
]

ANCHOR_HINTS = ["西湖", "灵隐寺", "良渚", "外滩", "迪士尼", "宽窄巷子", "洪崖洞", "橘子洲", "岳麓山", "故宫", "长城", "夫子庙"]

PREFERENCE_RULES: dict[str, list[tuple[str, str | list[str], list[str], float]]] = {
    "crowd": [
        ("single", "人少", ["不喜欢排队", "少排队", "别太挤", "不想排队", "人少", "小众", "安静"], 0.8),
        ("single", "热闹", ["热闹", "烟火气", "繁华", "人多一点"], 0.7),
    ],
    "food": [
        ("multi", "本地菜", ["本地菜", "当地特色", "地道"], 0.7),
        ("multi", "小吃", ["小吃", "夜宵", "路边摊"], 0.7),
        ("multi", "咖啡", ["咖啡", "咖啡馆", "手冲"], 0.6),
        ("multi", "清淡", ["清淡", "不吃辣"], 0.7),
        ("multi", "辣", ["爱吃辣", "重口", "川菜", "湘菜"], 0.7),
        ("multi", "素食", ["素食", "吃素", "素菜"], 0.8),
        ("multi", "亲子友好", ["儿童餐", "亲子友好", "适合孩子"], 0.7),
    ],
    "pace": [
        ("single", "轻松", ["轻松", "别太赶", "不赶", "慢一点", "多休息"], 0.7),
        ("single", "紧凑", ["特种兵", "多打卡", "尽量多玩", "排满"], 0.7),
    ],
    "party": [
        ("single", "亲子", ["亲子", "带娃", "孩子", "小朋友"], 0.8),
        ("single", "情侣", ["情侣", "约会", "对象", "男朋友", "女朋友"], 0.8),
        ("single", "老人", ["老人", "爸妈", "父母", "长辈"], 0.8),
        ("single", "独行", ["独行", "一个人", "solo"], 0.8),
        ("single", "朋友", ["朋友", "闺蜜", "同学", "同事"], 0.7),
    ],
    "transport": [
        ("multi", "地铁优先", ["地铁优先", "坐地铁", "公交", "公共交通"], 0.7),
        ("multi", "打车", ["打车", "网约车", "出租车"], 0.7),
        ("multi", "少步行", ["少走路", "步行少", "走不动"], 0.8),
        ("multi", "自驾", ["开车", "自驾", "停车"], 0.7),
    ],
    "sightseeing": [
        ("multi", "博物馆", ["博物馆", "展览", "美术馆"], 0.7),
        ("multi", "自然风景", ["自然风景", "山水", "徒步", "公园"], 0.7),
        ("multi", "citywalk", ["citywalk", "城市漫步", "街区"], 0.7),
        ("multi", "夜景", ["夜景", "灯光", "江景"], 0.7),
        ("multi", "拍照", ["拍照", "出片", "打卡", "氛围感"], 0.7),
    ],
}

BUDGET_PATTERNS = [
    re.compile(r"人均\s*(\d{2,5})\s*(元|块)?\s*(以内|以下)?"),
    re.compile(r"预算\s*(\d{2,5})\s*[到\-~至]\s*(\d{2,5})\s*(元|块)?"),
    re.compile(r"(\d{2,5})\s*(元|块)?\s*以内"),
]

DAYS_PATTERNS = [
    (re.compile(r"(\d+)\s*(天|日)"), 1),
    (re.compile(r"([一二两三四五六七八九十])\s*(天|日)"), 1),
]
CHINESE_NUMBERS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_memory_root() -> Path:
    return Path(os.environ.get("TRAVEL_MEMORY_DIR") or DEFAULT_MEMORY_ROOT).expanduser().resolve()


def sanitize_user_id(user_id: Any) -> str:
    raw = str(user_id or DEFAULT_USER_ID).strip() or DEFAULT_USER_ID
    sanitized = re.sub(r"[^A-Za-z0-9_.@-]+", "_", raw).strip("._-/\\")
    return sanitized[:80] or DEFAULT_USER_ID


def resolve_user_id(args: argparse.Namespace, payload: dict[str, Any] | None = None) -> str:
    payload = payload or {}
    return sanitize_user_id(args.user_id or payload.get("user_id") or os.environ.get("OPENCLAW_USER_ID") or DEFAULT_USER_ID)


def user_dir(user_id: str) -> Path:
    root = get_memory_root() / "users"
    path = (root / sanitize_user_id(user_id)).resolve()
    if root.resolve() not in path.parents and path != root.resolve():
        raise ValueError("非法 user_id，无法创建用户记忆目录。")
    return path


def plans_path(user_id: str) -> Path:
    return user_dir(user_id) / "plans.json"


def preferences_path(user_id: str) -> Path:
    return user_dir(user_id) / "preferences.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return copy.deepcopy(default)
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON 文件损坏，已停止写入以保护原文件：{path}: {exc}") from exc


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temp_path.replace(path)


def read_payload(input_path: str | None) -> dict[str, Any]:
    raw = ""
    if input_path:
        raw = Path(input_path).read_text(encoding="utf-8")
    elif not sys.stdin.isatty():
        raw = sys.stdin.read()
    if not raw.strip():
        return {}
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("输入 JSON 必须是对象。")
    return data


def normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        items = value
    else:
        items = [value]
    return list(dict.fromkeys(str(item).strip() for item in items if str(item).strip()))


def normalize_days(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int) and value > 0:
        return value
    text = str(value)
    if text in {"半天", "半日"}:
        return 1
    if text in {"晚上", "夜游"}:
        return 1
    for pattern, group_index in DAYS_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        token = match.group(group_index)
        return int(token) if token.isdigit() else CHINESE_NUMBERS.get(token)
    return None


def detect_city(text: str) -> str | None:
    return next((city for city in CITY_NAMES if city in text), None)


def detect_trip_type(text: str) -> str | None:
    for trip_type, keywords in TRIP_TYPE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return trip_type
    return None


def detect_tags(text: str) -> list[str]:
    return [tag for tag in TAG_KEYWORDS if tag.lower() in text.lower()]


def detect_anchors(text: str) -> list[str]:
    anchors = [anchor for anchor in ANCHOR_HINTS if anchor in text]
    quoted = re.findall(r"[《『「\"]([^《》『』「」\"]{2,12})[》』」\"]", text)
    return list(dict.fromkeys(anchors + quoted))


def search_text(payload: dict[str, Any]) -> str:
    parts = []
    for key in ["title", "source_query", "query", "city", "duration", "trip_type"]:
        value = payload.get(key)
        if value:
            parts.append(str(value))
    parts.extend(normalize_list(payload.get("tags")))
    parts.extend(normalize_list(payload.get("anchors")))
    return " ".join(parts)


def build_plan_key(plan: dict[str, Any]) -> str:
    city = plan.get("city") or "未知城市"
    days = f"{plan['days']}天" if plan.get("days") else str(plan.get("duration") or "未知时长")
    trip_type = plan.get("trip_type") or "通用"
    anchors = "+".join(normalize_list(plan.get("anchors"))[:4]) or "+".join(normalize_list(plan.get("tags"))[:4]) or "未命名行程"
    return f"{plan.get('user_id', DEFAULT_USER_ID)}|{city}|{days}|{trip_type}|{anchors}"


def generate_plan_id(plan: dict[str, Any]) -> str:
    digest = hashlib.sha1(json.dumps(plan, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    return f"plan_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{digest}"


def extract_plan_fields(payload: dict[str, Any], user_id: str) -> dict[str, Any]:
    text = search_text(payload)
    days = normalize_days(payload.get("days") or payload.get("duration") or text)
    plan = {
        "plan_id": payload.get("plan_id"),
        "user_id": user_id,
        "city": payload.get("city") or detect_city(text),
        "days": days,
        "duration": payload.get("duration") or (f"{days}天" if days else None),
        "trip_type": payload.get("trip_type") or payload.get("travel_type") or detect_trip_type(text),
        "title": payload.get("title") or payload.get("name") or "未命名旅行计划",
        "status": payload.get("status") or "active",
        "tags": list(dict.fromkeys(normalize_list(payload.get("tags")) + detect_tags(text))),
        "anchors": list(dict.fromkeys(normalize_list(payload.get("anchors")) + detect_anchors(text))),
        "constraints": payload.get("constraints") if isinstance(payload.get("constraints"), dict) else {},
        "itinerary": payload.get("itinerary") or [],
        "evidence": payload.get("evidence") or [],
        "risks": payload.get("risks") or [],
        "source_query": payload.get("source_query") or payload.get("query"),
    }
    plan["plan_id"] = str(plan["plan_id"] or generate_plan_id(plan))
    plan["plan_key"] = build_plan_key(plan)
    return plan


def load_plans(user_id: str) -> dict[str, Any]:
    data = load_json(plans_path(user_id), {"plans": []})
    if not isinstance(data, dict) or not isinstance(data.get("plans"), list):
        raise ValueError("plans.json 格式错误，应包含 plans 数组。")
    return data


def save_plan(payload: dict[str, Any], user_id: str) -> dict[str, Any]:
    data = load_plans(user_id)
    plan = extract_plan_fields(payload, user_id)
    timestamp = now_iso()
    plan["created_at"] = payload.get("created_at") or timestamp
    plan["updated_at"] = timestamp
    plan["version"] = int(payload.get("version") or 1)
    plan["versions"] = payload.get("versions") if isinstance(payload.get("versions"), list) else []
    if not plan["versions"]:
        plan["versions"] = [{"version": 1, "changed_at": timestamp, "change_summary": "初始创建", "snapshot": copy.deepcopy(plan)}]
    warnings = []
    if not plan.get("city"):
        warnings.append("缺少 city，后续召回会更多依赖标题、标签和原始请求。")
    existing_index = next((index for index, item in enumerate(data["plans"]) if item.get("plan_id") == plan["plan_id"]), None)
    if existing_index is None:
        data["plans"].append(plan)
    else:
        data["plans"][existing_index] = plan
    save_json(plans_path(user_id), data)
    return {"ok": True, "user_id": user_id, "plan": plan, "warnings": warnings}


def score_plan(plan: dict[str, Any], query: str, filters: dict[str, Any]) -> tuple[float, list[str]]:
    text = query.strip()
    query_city = filters.get("city") or detect_city(text)
    query_days = normalize_days(filters.get("days") or filters.get("duration") or text)
    query_trip_type = filters.get("trip_type") or detect_trip_type(text)
    query_tags = set(normalize_list(filters.get("tags")) + detect_tags(text))
    query_anchors = set(normalize_list(filters.get("anchors")) + detect_anchors(text))
    haystack = " ".join(str(plan.get(key) or "") for key in ["title", "city", "duration", "trip_type", "plan_key", "source_query"])
    haystack += " " + " ".join(normalize_list(plan.get("tags")) + normalize_list(plan.get("anchors")))
    score = 0.0
    reasons: list[str] = []
    if query_city and plan.get("city") == query_city:
        score += 5
        reasons.append(f"城市匹配：{query_city}")
    if query_days and plan.get("days") == query_days:
        score += 3
        reasons.append(f"天数匹配：{query_days}天")
    if query_trip_type and plan.get("trip_type") == query_trip_type:
        score += 2
        reasons.append(f"行程类型匹配：{query_trip_type}")
    for tag in query_tags.intersection(set(normalize_list(plan.get("tags")))):
        score += 1
        reasons.append(f"标签匹配：{tag}")
    for anchor in query_anchors.intersection(set(normalize_list(plan.get("anchors")))):
        score += 1
        reasons.append(f"锚点匹配：{anchor}")
    for token in set(re.findall(r"[A-Za-z0-9\u4e00-\u9fa5]{2,}", text)):
        if token in haystack:
            score += 0.3
    if plan.get("status") == "active":
        score += 0.5
    if plan.get("updated_at"):
        score += 0.1
    return score, reasons


def recall_plans(user_id: str, query: str, filters: dict[str, Any], limit: int) -> dict[str, Any]:
    plans = load_plans(user_id)["plans"]
    matches = []
    for plan in plans:
        score, reasons = score_plan(plan, query, filters)
        if query.strip() or filters:
            if score <= 0.6:
                continue
        matches.append({"score": round(score, 2), "match_reasons": reasons or ["最近可用计划"], "plan": plan})
    matches.sort(key=lambda item: (item["score"], item["plan"].get("updated_at") or ""), reverse=True)
    return {"ok": True, "user_id": user_id, "query": query, "matches": matches[:limit]}


def modify_plan(user_id: str, plan_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    data = load_plans(user_id)
    index = next((idx for idx, item in enumerate(data["plans"]) if item.get("plan_id") == plan_id), None)
    if index is None:
        return {"ok": False, "user_id": user_id, "error": f"未找到当前用户下的 plan：{plan_id}"}
    current = data["plans"][index]
    before = copy.deepcopy(current)
    updates = patch.get("updates") if isinstance(patch.get("updates"), dict) else patch
    for key, value in updates.items():
        if key in {"plan_id", "user_id", "created_at", "versions", "version"}:
            continue
        if key == "constraints" and isinstance(value, dict):
            merged = dict(current.get("constraints") or {})
            merged.update(value)
            current["constraints"] = merged
        else:
            current[key] = value
    current["user_id"] = user_id
    current["days"] = normalize_days(current.get("days") or current.get("duration"))
    current["plan_key"] = build_plan_key(current)
    current["version"] = int(current.get("version") or 1) + 1
    current["updated_at"] = now_iso()
    versions = current.get("versions") if isinstance(current.get("versions"), list) else []
    versions.append({
        "version": current["version"],
        "changed_at": current["updated_at"],
        "change_summary": patch.get("change_summary") or "更新旅行计划",
        "snapshot": before,
    })
    current["versions"] = versions
    data["plans"][index] = current
    save_json(plans_path(user_id), data)
    return {"ok": True, "user_id": user_id, "plan": current}


def contains_sensitive_text(text: str) -> bool:
    return any(pattern.search(text) for pattern in SENSITIVE_PATTERNS)


def evidence_for(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def extract_budget_preference(text: str) -> dict[str, Any] | None:
    for pattern in BUDGET_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        if len(match.groups()) >= 2 and match.group(2) and match.group(2).isdigit():
            value = f"{match.group(1)}-{match.group(2)}"
        else:
            value = f"人均 {match.group(1)} 以内"
        return {"mode": "single", "value": value, "confidence": 0.7, "evidence": [match.group(0)]}
    if any(keyword in text for keyword in ["别太贵", "省钱", "穷游", "性价比"]):
        return {"mode": "single", "value": "预算敏感", "confidence": 0.7, "evidence": [keyword for keyword in ["别太贵", "省钱", "穷游", "性价比"] if keyword in text]}
    return None


def extract_preferences_from_text(text: str) -> dict[str, Any]:
    if contains_sensitive_text(text):
        text = " ".join(part for part in re.split(r"[，。！？；\s]+", text) if part and not contains_sensitive_text(part))
    extracted: dict[str, Any] = {}
    for dimension, rules in PREFERENCE_RULES.items():
        for mode, value, keywords, confidence in rules:
            evidence = evidence_for(text, keywords)
            if not evidence:
                continue
            if dimension not in extracted:
                extracted[dimension] = {"mode": mode, "value": [] if mode == "multi" else value, "confidence": confidence, "evidence": []}
            if mode == "multi":
                extracted[dimension]["value"] = list(dict.fromkeys(normalize_list(extracted[dimension]["value"]) + [str(value)]))
            else:
                extracted[dimension]["value"] = value
            extracted[dimension]["confidence"] = max(float(extracted[dimension].get("confidence") or 0), confidence)
            extracted[dimension]["evidence"] = list(dict.fromkeys(normalize_list(extracted[dimension].get("evidence")) + evidence))
    budget = extract_budget_preference(text)
    if budget:
        extracted["budget"] = budget
    return extracted


def load_preferences(user_id: str) -> dict[str, Any]:
    data = load_json(preferences_path(user_id), {"user_id": user_id, "preferences": {}, "updated_at": None})
    if not isinstance(data, dict) or not isinstance(data.get("preferences"), dict):
        raise ValueError("preferences.json 格式错误，应包含 preferences 对象。")
    data["user_id"] = user_id
    return data


def merge_preferences(user_id: str, extracted: dict[str, Any]) -> dict[str, Any]:
    data = load_preferences(user_id)
    preferences = data.setdefault("preferences", {})
    for dimension, incoming in extracted.items():
        current = preferences.get(dimension, {})
        mode = incoming.get("mode") or current.get("mode") or "single"
        if mode == "multi":
            value = list(dict.fromkeys(normalize_list(current.get("value")) + normalize_list(incoming.get("value"))))
        else:
            value = incoming.get("value")
        evidence = list(dict.fromkeys(normalize_list(current.get("evidence")) + normalize_list(incoming.get("evidence"))))
        confidence = min(1.0, max(float(current.get("confidence") or 0), float(incoming.get("confidence") or 0)) + 0.05)
        preferences[dimension] = {"mode": mode, "value": value, "confidence": round(confidence, 2), "evidence": evidence[-12:]}
    data["updated_at"] = now_iso()
    save_json(preferences_path(user_id), data)
    return data


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OpenClaw travel memory and plan manager")
    parser.add_argument("--user-id", help="用户标识；不同用户的 plans/preferences 会隔离存储")
    subparsers = parser.add_subparsers(dest="command", required=True)

    save_parser = subparsers.add_parser("save-plan")
    save_parser.add_argument("--input", help="plan JSON 文件路径；不传时读取 stdin")

    recall_parser = subparsers.add_parser("recall")
    recall_parser.add_argument("--query", default="", help="召回查询，例如：杭州 3天 亲子 少排队")
    recall_parser.add_argument("--city")
    recall_parser.add_argument("--days")
    recall_parser.add_argument("--duration")
    recall_parser.add_argument("--trip-type")
    recall_parser.add_argument("--tags", nargs="*")
    recall_parser.add_argument("--anchors", nargs="*")
    recall_parser.add_argument("--limit", type=int, default=5)

    modify_parser = subparsers.add_parser("modify-plan")
    modify_parser.add_argument("--plan-id", required=True)
    modify_parser.add_argument("--input", help="patch JSON 文件路径；不传时读取 stdin")

    preference_parser = subparsers.add_parser("extract-preferences")
    preference_parser.add_argument("--query", default="")
    preference_parser.add_argument("--input", help="包含 query/text 的 JSON 文件路径；不传时可读取 stdin")

    subparsers.add_parser("show-preferences")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if args.command == "save-plan":
            payload = read_payload(args.input)
            user_id = resolve_user_id(args, payload)
            print_json(save_plan(payload, user_id))
        elif args.command == "recall":
            user_id = resolve_user_id(args)
            filters = {key: value for key, value in {
                "city": args.city,
                "days": args.days,
                "duration": args.duration,
                "trip_type": args.trip_type,
                "tags": args.tags,
                "anchors": args.anchors,
            }.items() if value}
            print_json(recall_plans(user_id, args.query, filters, max(args.limit, 1)))
        elif args.command == "modify-plan":
            patch = read_payload(args.input)
            user_id = resolve_user_id(args, patch)
            print_json(modify_plan(user_id, args.plan_id, patch))
        elif args.command == "extract-preferences":
            payload = read_payload(args.input) if args.input else (read_payload(None) if not sys.stdin.isatty() else {})
            query = args.query or payload.get("query") or payload.get("text") or ""
            user_id = resolve_user_id(args, payload)
            extracted = extract_preferences_from_text(query)
            data = merge_preferences(user_id, extracted) if extracted else load_preferences(user_id)
            print_json({"ok": True, "user_id": user_id, "extracted": extracted, "preferences": data})
        elif args.command == "show-preferences":
            user_id = resolve_user_id(args)
            print_json({"ok": True, "user_id": user_id, "preferences": load_preferences(user_id)})
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print_json({"ok": False, "error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
