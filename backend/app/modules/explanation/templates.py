from app.db.models import RequirementPriority

STATUS_LABEL_BY_RESULT = {
    "ok": "Current profile alignment is acceptable.",
    "ok_with_must_have_gaps": "Must-have gaps require attention.",
    "not_applicable_no_requirements": "No requirements were defined for this offer.",
}

FALLBACK_STATUS_LABEL = "Matching status is available in raw payload."

DECISION_SUPPORT_NOTICE = (
    "This analysis supports your decision and does not make hiring decisions."
)
MUST_HAVE_NOTICE = "At least one must-have competency is currently missing."
NO_REQUIREMENTS_NOTICE = (
    "This job offer has no defined competency requirements, so no suitability scoring "
    "comparison was possible."
)

SUMMARY_HEADLINE_TEMPLATE = "Current suitability score: {score:.1f}/100."
MATCHED_REASON_TEMPLATE = (
    "Meets expected level for {competency_key} ({priority_label})."
)
MISSING_REASON_TEMPLATE = (
    "Missing {priority_label} competency: {competency_key}."
)
INSUFFICIENT_REASON_TEMPLATE = (
    "{competency_key} is below expected level ({current_level} vs expected "
    "{expected_level})."
)
ROADMAP_TEMPLATE = (
    "Improving {competency_key} to {target_level} would recover about "
    "{point_gain:.1f} points."
)

BASE_TRANSPARENCY_NOTES = [
    "Exact competency key matching only.",
    "Priority weights and expected levels are deterministic.",
    "No semantic inference or hidden scoring is used.",
]
UNKNOWN_ALGORITHM_NOTE_TEMPLATE = (
    "Detailed explanation templates are unavailable for algorithm version "
    "{algorithm_version}; showing minimal summary with raw payload preserved."
)

PRIORITY_LABEL_BY_VALUE = {
    RequirementPriority.MUST_HAVE.value: "must-have",
    RequirementPriority.IMPORTANT.value: "important",
    RequirementPriority.NICE_TO_HAVE.value: "nice-to-have",
}
