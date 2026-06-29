"""
Build a suggested evidence plan from itinerary elements.

This script only returns hints. It does not call external services and does not
replace agent judgment.
"""

from __future__ import annotations

from capability_matrix import CAPABILITY_MATRIX


def build_evidence_plan(required_elements: list[str]) -> dict[str, list[dict[str, object]]]:
    """Return suggested evidence tasks for free-form element labels."""
    tasks: list[dict[str, object]] = []
    deferred: list[dict[str, object]] = []

    for element in required_elements:
        matched = False
        for capability, spec in CAPABILITY_MATRIX.items():
            keywords = spec.get("elements", [])
            if any(str(keyword).lower() in element.lower() for keyword in keywords):
                tasks.append(
                    {
                        "element": element,
                        "capability": capability,
                        "suggested_skill": spec["preferred_skill"],
                        "evidence_level": spec["evidence_level"],
                        "reason": spec["required_when"],
                    }
                )
                matched = True
                break
        if not matched:
            deferred.append(
                {
                    "element": element,
                    "reason": "No obvious capability match. Agent should decide whether to ask, skip, or use general travel planning.",
                }
            )

    return {"tasks": tasks, "deferred": deferred, "risks": []}
