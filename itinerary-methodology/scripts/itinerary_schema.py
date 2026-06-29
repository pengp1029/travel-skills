"""
Itinerary schema contract and workflow scaffold.

This script intentionally does not plan trips, call external services, rank
final itineraries, invent POI facts, persist user data, or generate final prose.
Agents should use these shapes as a stable interface, then freely choose
appropriate skills/tools and fill fields with verified evidence.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class ItineraryConstraint(TypedDict, total=False):
    city: str
    dates: list[str]
    days: int
    party: str
    pace: Literal["relaxed", "balanced", "intensive"]
    budget: str
    base_location: str
    must_go: list[str]
    avoid: list[str]
    food_preferences: list[str]
    queue_tolerance: Literal["low", "medium", "high"]
    transport_preferences: list[str]


class ItineraryPoint(TypedDict, total=False):
    name: str
    type: Literal["spot", "food", "drink", "hotel", "transport", "district", "backup"]
    city: str
    address: str
    lat: float
    lng: float
    time_hint: str
    duration_minutes: int
    detail_url: str
    image_url: str
    dianping_url: str
    xhs_url: str
    amap_navigation_url: str
    source_note: str
    risk_notes: list[str]


class ItineraryDay(TypedDict, total=False):
    day_id: str
    theme: str
    main_area: str
    points: list[ItineraryPoint]
    route_notes: list[str]
    meal_notes: list[str]
    backup_points: list[ItineraryPoint]
    removed_items: list[dict[str, Any]]


class ItineraryPlan(TypedDict, total=False):
    plan_id: str
    title: str
    constraints: ItineraryConstraint
    days: list[ItineraryDay]
    evidence_refs: list[dict[str, Any]]
    removed_items: list[dict[str, Any]]
    risks: list[str]
    next_actions: list[str]


def empty_plan_template() -> ItineraryPlan:
    """Return the canonical itinerary shape agents can fill freely."""
    return {
        "title": "",
        "constraints": {},
        "days": [],
        "evidence_refs": [],
        "removed_items": [],
        "risks": [],
        "next_actions": [],
    }
