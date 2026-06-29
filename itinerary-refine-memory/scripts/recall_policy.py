"""
Recall policy contract for itinerary refinement.

This module does not read storage. It exposes deterministic priority and
follow-up detection hints so agents can use whichever memory backend exists.
"""

RECALL_PRIORITY = [
    "target_plan_id",
    "active_plan_id",
    "city_days",
    "plan_group_id",
    "latest_by_user_when_followup",
]

FOLLOWUP_MARKERS = [
    "刚才",
    "上面",
    "上一个",
    "那个",
    "继续",
    "按原来",
    "按刚刚",
    "修改",
    "调整",
    "换成",
    "替换",
    "第一天",
    "第二天",
    "第三天",
    "这版",
    "上次",
]


def infer_is_followup(text: str | None) -> bool:
    """Return whether text explicitly references an existing itinerary."""
    if not text:
        return False
    return any(marker in text for marker in FOLLOWUP_MARKERS)


def recall_policy() -> dict[str, object]:
    """Describe the recommended base-plan recall order."""
    return {
        "priority": RECALL_PRIORITY,
        "rule": "Prefer explicit plan id, then active session plan, then city+days, then plan group, then latest-by-user only for clear follow-ups.",
    }
