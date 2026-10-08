
import logging
from typing import Any

from ai_manager import build_prompt, call_api, parse_response

logger = logging.getLogger(__name__)


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

def calculate_historical_frequency(
    record: dict[str, Any],
    existing_records: list[dict[str, Any]]
) -> int:
    """
    Counts previous reports involving the same location
    and asset.
    """

    frequency = 0

    for existing in existing_records:
        same_location = (
            str(record.get("location", "")).strip().lower()
            == str(existing.get("location", "")).strip().lower()
        )

        same_asset = (
            str(record.get("asset_info", "")).strip().lower()
            == str(existing.get("asset_info", "")).strip().lower()
        )

        if same_location and same_asset:
            frequency += 1

    return frequency


def score(record: dict[str, Any]) -> int:
    """
    Produces a numeric priority score from AI-enriched hazard fields.

    Higher scores indicate higher priority.
    """

    severity = str(
        record.get("severity", "low")
    ).strip().lower()

    safety_risk = str(
        record.get("safety_risk", "low")
    ).strip().lower()

    operational_impact = str(
        record.get("operational_impact", "low")
    ).strip().lower()

    historical_frequency = record.get("historical_frequency", 0)

    # Calculate severity score
    if severity == "critical":
        severity_score = 5
    elif severity == "high":
        severity_score = 4
    elif severity == "medium":
        severity_score = 2
    else:
        severity_score = 1

    # Calculate safety risk score
    if safety_risk == "high":
        safety_score = 4
    elif safety_risk == "medium":
        safety_score = 2
    else:
        safety_score = 1

    # Calculate operational impact score
    if operational_impact == "severe":
        operational_score = 4
    elif operational_impact == "high":
        operational_score = 3
    elif operational_impact == "medium":
        operational_score = 2
    else:
        operational_score = 1

    # Calculate historical frequency score
    if historical_frequency >= 5:
        frequency_score = 3
    elif historical_frequency >= 2:
        frequency_score = 2
    elif historical_frequency >= 1:
        frequency_score = 1
    else:
        frequency_score = 0

    # Final calculation
    priority_score = (
        severity_score
        + safety_score
        + operational_score
        + frequency_score
    )

    # Show calculation in terminal
    print("\n--- PRIORITY SCORE CALCULATION ---")
    print(f"Severity: {severity} → +{severity_score}")
    print(f"Safety Risk: {safety_risk} → +{safety_score}")
    print(f"Operational Impact: {operational_impact} → +{operational_score}")
    print(f"Historical Frequency: {historical_frequency} → +{frequency_score}")
    print("----------------------------------")
    print(
        f"Priority Score = {severity_score} + "
        f"{safety_score} + "
        f"{operational_score} + "
        f"{frequency_score} = {priority_score}"
    )

    return priority_score

def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    """
    Runs business rules against an AI-enriched hazard record.

    Returns:
        dict[str, Any]: The business decision for the hazard.
    """

    severity = str(
        record.get("severity", "low")
    ).strip().lower()

    operational_impact = str(
        record.get("operational_impact", "low")
    ).strip().lower()

    priority_score = score(record)

    # Multi-condition business rule:
    # Critical severity AND severe operational impact
    # require immediate emergency response.
    if severity == "critical" and operational_impact == "severe":
        priority = "Critical"
        action = "Immediate Emergency Dispatch"
        reason = (
            "Critical severity combined with severe operational impact."
        )

    elif severity == "high" and operational_impact in ["high", "severe"]:
        priority = "High"
        action = "Urgent Maintenance"
        reason = (
            "High severity combined with significant operational impact."
        )

    elif priority_score >= 8:
        priority = "High"
        action = "Priority Maintenance"
        reason = (
            "Priority score reached the high-risk threshold."
        )

    else:
        priority = "Normal"
        action = "Standard Maintenance"
        reason = (
            "Hazard does not meet the criteria for urgent escalation."
        )

    return {
        "priority": priority,
        "score": priority_score,
        "action": action,
        "reason": reason,
        "route": route(record)
    }

def route(record: dict[str, Any]) -> str:
    """
    Determines the operational dispatch queue based on severity.
    """

    severity = str(
        record.get("severity", "low")
    ).strip().lower()

    if severity in ["critical", "high"]:
        return "Urgent Emergency Dispatch"

    return "Standard Maintenance Queue"

def check_duplicate(
    new_record: dict[str, Any],
    existing_records: list[dict[str, Any]]
) -> str:
    """
    Checks whether a new report potentially duplicates
    an unresolved existing report.
    """

    for r in existing_records:

        loc_match = (
            str(new_record.get("location", "")).strip().lower()
            == str(r.get("location", "")).strip().lower()
        )

        asset_match = (
            str(new_record.get("asset_info", "")).strip().lower()
            == str(r.get("asset_info", "")).strip().lower()
        )

        if loc_match and asset_match and r.get("status") != "Resolved":
            return f"Potential Duplicate of {r.get('incident_id')}"

    return "Unique"
