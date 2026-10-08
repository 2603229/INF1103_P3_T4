
import logging
from typing import Any

from ai_manager import build_prompt, call_api, parse_response

logger = logging.getLogger(_name_)


def handle_ai_failure(record: dict[str, Any]) -> dict[str, Any]:
    """
    Provides a domain-specific fallback assessment when AI processing
    is unavailable.

    Args:
        record (dict[str, Any]): The hazard report record.

    Returns:
        dict[str, Any]: A fallback hazard assessment.
    """

    visual_evidence_path = record.get("visual_evidence_path")

    has_image = bool(
        visual_evidence_path
        and str(visual_evidence_path).strip().lower()
        not in ["none", "", "n/a"]
    )

    if has_image:
        return {
            "risk_summary": (
                "- [Offline Assessment] Visual evidence requires physical inspection\n"
                "- Potential physical safety hazard to occupants"
            ),
            "category": "Electrical / Infrastructure",
            "severity": "Critical",
            "operational_impact": "Severe",
            "contextual_insights": (
                "Visual evidence indicates potential compromised physical "
                "asset integrity. Cordon off the area and dispatch maintenance "
                "for inspection."
            )
        }

    return {
        "risk_summary": (
            "- [Offline Assessment] Potential hazard reported requiring "
            "facility inspection\n"
            "- Standard operational risk mitigation needed"
        ),
        "category": "General Maintenance",
        "severity": "Medium",
        "operational_impact": "Moderate",
        "contextual_insights": (
            "Standard facility review recommended to ensure campus safety "
            "compliance."
        )
    }


def process_record(record: dict[str, Any]) -> dict[str, Any]:
    """
    Processes a hazard report through the AI processing layer.

    Every record passes through ai_manager before a domain-specific
    fallback is considered.

    Args:
        record (dict[str, Any]): The hazard report record.

    Returns:
        dict[str, Any]: AI-generated or fallback assessment.
    """

    # Build the AI prompt from the record
    prompt = build_prompt(record)

    # Get optional visual evidence
    visual_evidence_path = record.get("visual_evidence_path")

    # Send the record to the AI processing layer
    raw_response = call_api(
        prompt,
        visual_evidence_path
    )

    # Parse the AI response
    parsed_response = parse_response(raw_response)

    # If AI successfully returned a valid assessment, use it
    if parsed_response and "error" not in parsed_response:
        return parsed_response

    # AI processing failed, so apply the domain-specific fallback
    logger.warning(
        "AI processing unavailable. Applying offline fallback assessment."
    )

    return handle_ai_failure(record)


def calculate_score(record):
    severity = record.get("severity", "low")
    safety_risk = record.get("safety_risk", "low")
    operational_impact = record.get("operational_impact", "low")
    historical_frequency = record.get("historical_frequency", 0)

    score = 0

    if severity == "high":
        score += 4
    elif severity == "medium":
        score += 2
    else:
        score += 1

    if safety_risk == "high":
        score += 4
    elif safety_risk == "medium":
        score += 2
    else:
        score += 1

    if operational_impact == "high":
        score += 3
    elif operational_impact == "medium":
        score += 2
    else:
        score += 1

    if historical_frequency >= 5:
        score += 3
    elif historical_frequency >= 2:
        score += 2
    elif historical_frequency >= 1:
        score += 1

    return score