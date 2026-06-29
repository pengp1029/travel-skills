"""
Build handoff plan templates for itinerary deliverables.

This module does not call downstream skills or create assets. Agents fill the
payload and choose whether to invoke the suggested chain.
"""

from __future__ import annotations

from deliverable_contract import get_deliverable_contract


def build_handoff_plan(deliverable_kind: str, stable: bool = False) -> dict[str, object]:
    """Return a handoff plan template for a deliverable kind."""
    contract = get_deliverable_contract(deliverable_kind)
    if not contract:
        return {
            "deliverable_kind": deliverable_kind,
            "stable": stable,
            "required_inputs": [],
            "optional_inputs": [],
            "suggested_skill_chain": [],
            "missing_blockers": ["Unknown deliverable kind. Agent should classify or ask a short question."],
            "handoff_payload": {},
            "risks": [],
        }

    return {
        "deliverable_kind": deliverable_kind,
        "stable": stable,
        "required_inputs": contract.get("required_inputs", []),
        "optional_inputs": contract.get("optional_inputs", []),
        "suggested_skill_chain": [contract.get("suggested_skill")],
        "missing_blockers": [] if stable else ["Itinerary stability has not been confirmed."],
        "handoff_payload": {},
        "risks": [],
    }
