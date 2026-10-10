import logging
from typing import Any

from ai_manager import build_prompt, call_api, parse_response, validate_response

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
                "- [Offline Assessment] An image was attached but was not analysed\n"
                "- The reported hazard requires a physical inspection"
            ),
            # Provisional placeholders, not classifications inferred from the image.
            "category": "General Maintenance",
            "severity": "Medium",
            "operational_impact": "Moderate",
            "contextual_insights": (
                "The AI service was unavailable, so the image was not assessed. "
                "Facilities personnel should review the description and evidence, "
                "inspect the site, and escalate any immediate danger under campus procedures. "
                "The severity and impact values are provisional, not verified."
            ),
        }

    return {
            "risk_summary": (
                "- [Offline Assessment] The reported hazard was not assessed by AI\n"
                "- A facilities review is required"
            ),
            "category": "General Maintenance",
            "severity": "Medium",
            "operational_impact": "Moderate",
            "contextual_insights": (
                "AI analysis was unavailable. Facilities personnel should review "
                "the report and verify the risk level; the assigned values are provisional."
            ),
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
    if parsed_response and "error" not in parsed_response and validate_response(parsed_response):
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

def calculate_score_breakdown(record: dict[str, Any]) -> dict[str, int]:
    """
    Calculate each scoring component without displaying terminal output.

    Gemini supplies severity and operational impact. Historical frequency
    is calculated by the business logic from previously stored incidents.
    """
    severity = str(record.get("severity", "Low")).strip().lower()
    operational_impact = str(record.get("operational_impact", "Minor")).strip().lower()

    severity_points = {
        "low": 1,
        "medium": 2,
        "high": 4,
        "critical": 5,
    }
    impact_points = {
        "minor": 1,
        "moderate": 2,
        "severe": 4,
        "catastrophic": 5,
    }

    severity_score = severity_points.get(severity, 1)
    operational_score = impact_points.get(operational_impact, 1)

    try:
        frequency = max(0, int(record.get("historical_frequency", 0)))
    except (TypeError, ValueError):
        frequency = 0

    if frequency >= 5:
        frequency_score = 3
    elif frequency >= 2:
        frequency_score = 2
    elif frequency >= 1:
        frequency_score = 1
    else:
        frequency_score = 0

    return {
        "severity": severity_score,
        "operational_impact": operational_score,
        "historical_frequency": frequency_score,
    }

def score(record: dict[str, Any]) -> int:
    """Return the numerical priority score (higher means more urgent)."""
    return sum(calculate_score_breakdown(record).values())


def evaluate(record: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluates AI-enriched hazard data and determines
    the final priority, recommended action, and routing.
    """

    severity = str(
        record.get("severity", "Low")
    ).strip().lower()

    operational_impact = str(
        record.get("operational_impact", "Minor")
    ).strip().lower()

    # Calculate the individual scoring components
    breakdown = calculate_score_breakdown(record)
    priority_score = sum(breakdown.values())

    # Critical severity combined with severe or catastrophic
    # impact requires immediate attention.
    if severity == "critical" and operational_impact in (
        "severe", "catastrophic"
    ):
        priority = "Critical"
        action = "Immediate Emergency Dispatch"
        reason = (
            "Critical severity combined with severe "
            "or catastrophic operational impact."
        )

    # High severity, severe impact, or a high total score
    # requires priority maintenance.
    elif (
        severity in ("high", "critical")
        or operational_impact in ("severe", "catastrophic")
        or priority_score >= 7
    ):
        priority = "High"
        action = "Priority Maintenance"
        reason = (
            "Hazard severity, operational impact, or "
            "priority score requires urgent attention."
        )

    else:
        priority = "Normal"
        action = "Standard Maintenance"
        reason = (
            "Hazard does not meet the criteria "
            "for urgent escalation."
        )

    return {
        "priority": priority,
        "score": priority_score,
        "action": action,
        "reason": reason,
        "route": route({"priority": priority}),
        "score_breakdown": breakdown
    }


def route(record: dict[str, Any]) -> str:
    """
    Determines the dispatch queue based on
    the evaluated hazard priority.

    Args:
        record (dict[str, Any]): A dictionary containing
            the evaluated priority.

    Returns:
        str: The appropriate dispatch queue.
    """

    priority = str(
        record.get("priority", "Normal")
    ).strip().lower()

    if priority == "critical":
        return "Urgent Emergency Dispatch"

    if priority == "high":
        return "Priority Maintenance Queue"

    return "Standard Maintenance Queue"


def check_duplicate(
    new_record: dict[str, Any],
    existing_records: list[dict[str, Any]]
) -> str:
    """
    Checks whether a new report potentially duplicates
    an unresolved existing report.
    """

    new_location = str(
        new_record.get("location") or ""
    ).strip().lower()

    new_asset = str(
        new_record.get("asset_info") or ""
    ).strip().lower()

    # Prevent missing input fields from creating false matches
    if not new_location or not new_asset:
        return "Unique"

    for existing in existing_records:

        existing_location = str(
            existing.get("location") or ""
        ).strip().lower()

        existing_asset = str(
            existing.get("asset_info") or ""
        ).strip().lower()

        status = str(
            existing.get("status") or ""
        ).strip().lower()

        if (
            new_location == existing_location
            and new_asset == existing_asset
            and status not in ("resolved", "closed")
        ):
            return (
                f"Potential Duplicate of "
                f"{existing.get('incident_id')}"
            )

    return "Unique"


def sort_incidents_by_severity(
    records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Sorts incidents by severity:
    Critical -> High -> Medium -> Low.
    """

    order = {
        "Critical": 0,
        "High": 1,
        "Medium": 2,
        "Low": 3
    }

    return sorted(
        records,
        key=lambda x: order.get(
            str(x.get("severity", "Low")),
            4
        )
    )

