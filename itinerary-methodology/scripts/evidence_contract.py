"""
Evidence contract for itinerary planning.

The values here are labels and field hints only. They do not fetch or validate
facts. Agents decide which downstream skill/tool to call for each field.
"""

from __future__ import annotations

from typing import Literal, TypedDict

EvidenceLevel = Literal["hard_fact", "structured_signal", "soft_signal", "deliverable_asset"]


class EvidenceRef(TypedDict, total=False):
    element: str
    field: str
    level: EvidenceLevel
    source: str
    source_url: str
    observed_at: str
    confidence: Literal["low", "medium", "high"]
    note: str


EVIDENCE_FIELD_HINTS: dict[str, dict[str, object]] = {
    "poi_location": {
        "level": "hard_fact",
        "fields": ["name", "address", "lat", "lng", "amap_navigation_url"],
        "suggested_sources": ["travel-skill"],
    },
    "route": {
        "level": "hard_fact",
        "fields": ["from", "to", "mode", "distance", "duration", "source"],
        "suggested_sources": ["travel-skill", "amap-route-video"],
    },
    "weather": {
        "level": "hard_fact",
        "fields": ["date", "city", "condition", "temperature", "rain_risk"],
        "suggested_sources": ["travel-skill"],
    },
    "restaurant": {
        "level": "structured_signal",
        "fields": ["name", "address", "rating", "avg_price", "business_hours", "comment_tags"],
        "suggested_sources": ["dianping-info-query"],
    },
    "atmosphere": {
        "level": "soft_signal",
        "fields": ["vibe", "photo_friendly", "recent_notes", "pitfalls"],
        "suggested_sources": ["xiaohongshu-skills"],
    },
    "image_asset": {
        "level": "deliverable_asset",
        "fields": ["image_url", "source_url", "license_hint", "authorized_for_publish"],
        "suggested_sources": ["poi-image-collector"],
    },
}


def get_evidence_field_hints() -> dict[str, dict[str, object]]:
    """Return evidence field hints for agents to adapt."""
    return EVIDENCE_FIELD_HINTS
