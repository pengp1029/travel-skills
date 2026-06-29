"""
Workflow outline for itinerary methodology.

This is a stage checklist, not a runtime. Agents can skip or reorder stages when
context makes that clearly better.
"""

WORKFLOW_STAGES = [
    {
        "stage": "classify_request",
        "goal": "Decide whether the user is creating, modifying, recalling, querying, or requesting a deliverable.",
        "outputs": ["request_type", "followup_hint", "blockers"],
    },
    {
        "stage": "extract_constraints",
        "goal": "Extract hard constraints and preferences, asking only for blockers.",
        "outputs": ["constraints", "defaults", "clarifying_questions"],
    },
    {
        "stage": "model_itinerary_elements",
        "goal": "Represent candidate days, points, route legs, risks, backups, and deletion candidates.",
        "outputs": ["draft_plan"],
    },
    {
        "stage": "plan_evidence",
        "goal": "Identify which facts and signals need downstream skills.",
        "outputs": ["evidence_plan"],
    },
    {
        "stage": "verify_and_rank",
        "goal": "Check executability and rank/delete candidates based on constraints.",
        "outputs": ["ranked_plan", "removed_items", "risks"],
    },
    {
        "stage": "prepare_handoff",
        "goal": "Format the plan so refine, memory, map, and video workflows can consume it.",
        "outputs": ["itinerary_plan", "next_actions"],
    },
]


def get_workflow_outline() -> list[dict[str, object]]:
    """Return recommended itinerary-planning stages."""
    return WORKFLOW_STAGES
