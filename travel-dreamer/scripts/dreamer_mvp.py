#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SKILL_ROOT = Path(__file__).resolve().parents[1]
OPENCLAW_ROOT = SKILL_ROOT.parents[1]
MEMORY_SCRIPT = SKILL_ROOT.parent / "travel-skill" / "scripts" / "memory.py"

WEEKEND_STRONG_WEEKDAYS = {2, 3, 4}  # Wed, Thu, Fri
WEEKEND_LIGHT_WEEKDAYS = {5}  # Sat

OPT_OUT_TOKENS = [
    "不主动推送",
    "不要主动推送",
    "免打扰",
    "关闭主动推荐",
    "停止推荐",
    "frequency=never",
]

INTEREST_KEYWORDS = [
    "二次元",
    "动漫",
    "展览",
    "美术馆",
    "博物馆",
    "live",
    "演出",
    "音乐会",
    "市集",
    "咖啡",
    "citywalk",
    "徒步",
    "露营",
    "夜景",
    "拍照",
]


def load_openclaw_env() -> None:
    env_path = OPENCLAW_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now()
    return datetime.strptime(value, "%Y-%m-%d")


def run_memory(user_id: str, command: str, extra_args: list[str] | None = None) -> dict[str, Any]:
    if not MEMORY_SCRIPT.exists():
        return {"ok": False, "error": f"memory script not found: {MEMORY_SCRIPT}"}
    cmd = [sys.executable, str(MEMORY_SCRIPT), "--user-id", user_id, command]
    if extra_args:
        cmd.extend(extra_args)
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True)
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    raw = proc.stdout.strip() or proc.stderr.strip()
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {"ok": False, "error": "memory script returned non-json", "raw": raw}
    if proc.returncode != 0:
        data.setdefault("ok", False)
    return data


def flatten_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return " ".join(flatten_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_text(v) for v in value)
    return str(value)


def get_nested_bool(payload: dict[str, Any], keys: list[str]) -> bool | None:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    if isinstance(current, bool):
        return current
    if isinstance(current, str):
        lowered = current.lower().strip()
        if lowered in {"false", "no", "never", "off", "0"}:
            return False
        if lowered in {"true", "yes", "on", "1"}:
            return True
    return None


def unwrap_preferences(memory_preferences: dict[str, Any]) -> dict[str, Any]:
    preferences = memory_preferences.get("preferences")
    return preferences if isinstance(preferences, dict) else memory_preferences


def proactive_disabled(preferences: dict[str, Any]) -> bool:
    for path in [
        ["notification_preferences", "proactive_enabled"],
        ["notification", "proactive_enabled"],
        ["主动推荐"],
    ]:
        value = get_nested_bool(preferences, path)
        if value is False:
            return True
    text = flatten_text(preferences)
    return any(token in text for token in OPT_OUT_TOKENS)


def extract_preference_summary(preferences: dict[str, Any], explicit_interests: list[str]) -> list[str]:
    text = flatten_text(preferences)
    found: list[str] = []
    for item in explicit_interests + INTEREST_KEYWORDS:
        if item and (item in text or item in explicit_interests) and item not in found:
            found.append(item)
    for key in ["crowd", "pace", "party", "transport"]:
        value = preferences.get(key)
        if isinstance(value, dict):
            value = value.get("value")
        if isinstance(value, str) and value and value not in found:
            found.append(value)
    return found[:10]


def build_signals(args: argparse.Namespace, date_value: datetime, preference_summary: list[str]) -> list[dict[str, str]]:
    signals: list[dict[str, str]] = []
    weekday = date_value.weekday()
    if args.mode == "weekend":
        title = "临近周末" if weekday in WEEKEND_STRONG_WEEKDAYS else "周末相关观察"
        signals.append({"type": "time", "title": title, "confidence": "hard", "source_note": "由日期和 weekend mode 推断"})
    if args.mode == "holiday":
        title = f"临近{args.holiday_name or '节假日'}"
        if args.days_until_holiday is not None:
            title += f"，还有 {args.days_until_holiday} 天"
        signals.append({"type": "calendar", "title": title, "confidence": "hard", "source_note": "由调用方提供的节假日上下文生成"})
    for interest in args.interest:
        signals.append({"type": "interest", "title": f"用户兴趣：{interest}", "confidence": "soft", "source_note": "由显式参数或用户记忆提供"})
    for signal in args.signal:
        confidence = "soft"
        if any(token in signal for token in ["官方", "预约", "天气", "车票", "放假", "节假日"]):
            confidence = "hard"
        signals.append({"type": "external_signal", "title": signal, "confidence": confidence, "source_note": "由调用方传入，MVP 未联网复核"})
    if preference_summary and not args.interest:
        signals.append({"type": "memory", "title": "存在可用旅行偏好记忆", "confidence": "soft", "source_note": "来自 travel memory preference summary"})
    return signals


def decide(args: argparse.Namespace, date_value: datetime, preferences: dict[str, Any], preference_summary: list[str], signals: list[dict[str, str]]) -> tuple[bool, str, str, str, str]:
    if proactive_disabled(preferences):
        return False, "low", "quiet_observation", "用户关闭或限制了主动推送。", "medium"

    weekday = date_value.weekday()
    has_interest_match = bool(args.interest or preference_summary)
    has_external_signal = bool(args.signal)

    if args.mode == "weekend":
        if weekday in WEEKEND_STRONG_WEEKDAYS and has_interest_match:
            return True, "medium", "weekend_inspiration", "临近周末，且已有用户偏好可用于生成轻量出行灵感。", "medium"
        if weekday in WEEKEND_LIGHT_WEEKDAYS and has_external_signal:
            return True, "low", "weekend_inspiration", "周末当天仍有明确活动信号，可轻提醒。", "low"
        return False, "low", "quiet_observation", "当前不是强周末触发窗口，或缺少足够偏好/活动信号。", "medium"

    if args.mode == "holiday":
        days = args.days_until_holiday
        if days is not None and days in {14, 10, 7, 3}:
            priority = "high" if days <= 7 else "medium"
            return True, priority, "holiday_planning_nudge", "临近节假日，适合提前询问出行安排或提醒预约/交通风险。", "medium"
        if days is not None and 0 <= days <= 14 and has_interest_match:
            return True, "medium", "holiday_planning_nudge", "节假日进入可规划窗口，且用户有可用偏好。", "medium"
        return False, "low", "quiet_observation", "节假日触发信息不足，暂不主动打扰。", "low"

    if args.mode == "interest_radar":
        if has_external_signal and has_interest_match:
            return True, "medium", "interest_activity_radar", "发现与用户兴趣相关的活动信号，适合发轻量卡片询问。", "medium"
        return False, "low", "quiet_observation", "兴趣雷达缺少明确活动信号或偏好匹配。", "medium"

    if args.mode == "daily":
        if has_external_signal and has_interest_match and args.force_notify:
            return True, "low", "daily_light_observation", "日常观察中发现匹配信号，且调用方要求强制轻提醒。", "low"
        return False, "low", "quiet_observation", "日常模式默认低打扰，仅记录观察。", "medium"

    return False, "low", "quiet_observation", "未知模式，未触发主动通知。", "low"


def build_main_agent_task(args: argparse.Namespace, trigger_type: str, reason: str, preference_summary: list[str], signals: list[dict[str, str]], should_notify: bool) -> str | None:
    if not should_notify:
        return None
    signal_titles = "；".join(signal["title"] for signal in signals[:5])
    prefs = "、".join(preference_summary[:6]) or "暂无明确偏好"
    if trigger_type == "weekend_inspiration":
        return f"请为用户生成一张轻量飞书周末出行灵感卡片。城市：{args.city or '未指定'}。偏好：{prefs}。信号：{signal_titles}。包含2个偏好内活动和1个邻近探索型活动，语气轻，不要像广告。"
    if trigger_type == "holiday_planning_nudge":
        return f"请生成节假日前出行安排询问/提醒卡片。城市或出发地：{args.city or '未指定'}。偏好：{prefs}。原因：{reason}。提醒交通、预约或酒店风险时必须区分事实和风险判断。"
    if trigger_type == "interest_activity_radar":
        return f"请生成兴趣活动雷达卡片。城市：{args.city or '未指定'}。兴趣/偏好：{prefs}。活动信号：{signal_titles}。先问用户要不要看详情，不要直接输出长行程。"
    return f"请根据 Dreamer 触发器生成一条低打扰旅行建议。偏好：{prefs}。信号：{signal_titles}。"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OpenClaw travel Dreamer MVP trigger decision")
    parser.add_argument("--user-id", default=os.environ.get("OPENCLAW_USER_ID") or "default")
    parser.add_argument("--city", default="")
    parser.add_argument("--mode", choices=["weekend", "holiday", "interest_radar", "daily"], default="daily")
    parser.add_argument("--date", help="YYYY-MM-DD; defaults to today")
    parser.add_argument("--holiday-name", default="")
    parser.add_argument("--days-until-holiday", type=int)
    parser.add_argument("--interest", action="append", default=[])
    parser.add_argument("--signal", action="append", default=[])
    parser.add_argument("--force-notify", action="store_true", help="Only affects daily mode MVP testing")
    parser.add_argument("--include-recall", action="store_true", help="Also include a lightweight memory recall summary")
    return parser.parse_args()


def main() -> int:
    load_openclaw_env()
    args = parse_args()
    date_value = parse_date(args.date)

    memory_result = run_memory(args.user_id, "show-preferences")
    memory_preferences = memory_result.get("preferences") if isinstance(memory_result.get("preferences"), dict) else {}
    preferences = unwrap_preferences(memory_preferences)
    preference_summary = extract_preference_summary(preferences, args.interest)
    signals = build_signals(args, date_value, preference_summary)
    should_notify, priority, trigger_type, reason_or_quiet, confidence = decide(args, date_value, preferences, preference_summary, signals)

    recall_summary: Any = None
    if args.include_recall:
        query_parts = [args.city, args.mode, *preference_summary[:5], *args.interest]
        recall = run_memory(args.user_id, "recall", ["--query", " ".join(part for part in query_parts if part), "--limit", "3"])
        recall_summary = recall.get("matches") or recall.get("plans") or recall

    payload = {
        "ok": True,
        "user_id": args.user_id,
        "city": args.city or None,
        "mode": args.mode,
        "trigger_type": trigger_type,
        "should_notify": should_notify,
        "priority": priority,
        "reason": reason_or_quiet if should_notify else None,
        "confidence": confidence,
        "quiet_reason": None if should_notify else reason_or_quiet,
        "user_context": {
            "preferences": preferences,
            "preference_summary": preference_summary,
            "avoid": [],
            "notification_preferences": preferences.get("notification_preferences", {}) if isinstance(preferences, dict) else {},
        },
        "signals": signals,
        "recommendation_mix": {
            "preference_fit_count": 2,
            "exploration_count": 1,
            "exploration_rule": "偏好邻近探索，不随机跳跃",
        },
        "main_agent_task": build_main_agent_task(args, trigger_type, reason_or_quiet, preference_summary, signals, should_notify),
        "suggested_buttons": ["想看看", "换个方向", "本周不出门", "降低打扰频率"],
        "memory_status": {"ok": bool(memory_result.get("ok", False)), "error": memory_result.get("error")},
        "recall_summary": recall_summary,
        "created_at": now_iso(),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
