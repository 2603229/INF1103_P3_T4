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