"""
Patch and diff schema for itinerary refinement.

This module describes edit operations only. It does not mutate or persist plans.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

PatchOp = Literal[
    "add_point",
    "remove_point",
    "replace_point",
    "move_point",
    "change_pace",
    "change_budget",
    "change_transport",
    "add_backup",
    "rerank",
]


class PlanPatch(TypedDict, total=False):
    op: PatchOp
    target_day: str
    target_point: str
    new_point: dict[str, Any]
    reason: str
    constraints_delta: dict[str, Any]
    evidence_needed: list[str]


class PlanDiff(TypedDict, total=False):
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    replaced: list[dict[str, Any]]
    moved: list[dict[str, Any]]
    risk_changes: list[str]
    unchanged: list[str]


def empty_patch_bundle() -> dict[str, object]:
    """Return an empty patch+diff bundle for agents to fill."""
    return {
        "patches": [],
        "diff": {
            "added": [],
            "removed": [],
            "replaced": [],
            "moved": [],
            "risk_changes": [],
            "unchanged": [],
        },
    }
