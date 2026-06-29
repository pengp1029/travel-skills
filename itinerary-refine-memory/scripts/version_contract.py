"""
Versioning contract for itinerary memory.

This module defines states and event shapes only. It does not write storage.
"""

from __future__ import annotations

from typing import Literal, TypedDict

PlanStatus = Literal["draft", "planning", "committed", "confirmed", "archived"]


class PlanVersionRef(TypedDict, total=False):
    plan_id: str
    plan_group_id: str
    parent_plan_id: str
    user_id: str
    session_id: str
    city_key: str
    trip_days: int
    status: PlanStatus
    version: int
    created_at: str
    updated_at: str


class MemoryEvent(TypedDict, total=False):
    event_type: Literal["plan_saved", "plan_modified", "plan_confirmed", "preference_extracted", "feedback_recorded"]
    plan_ref: PlanVersionRef
    summary: str
    refs: dict[str, str]


def default_plan_status_flow() -> list[str]:
    """Return the recommended status progression."""
    return ["draft", "planning", "committed", "confirmed", "archived"]
