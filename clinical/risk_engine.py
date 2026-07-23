"""
clinical/risk_engine.py

Risk Engine for LipidAI.

IMPORTANT: This module no longer contains any hardcoded lipid thresholds.
All per-parameter Normal/Borderline/High classification now comes from
clinical.rule_engine (backed by config/lipid_rules.xlsx). This module's
only job is to aggregate those already-classified results into an overall
risk level for the patient.

Public API
----------
calculate_overall_risk(rule_results: dict) -> dict
    Takes the output of RuleEngine.evaluate() and returns the same
    per-parameter dict with an added "overall_risk" key, e.g.:

    {
        "Total Cholesterol": {"value": 245, "status": "High", "recommendation": "..."},
        "HDL": {"value": 35, "status": "Low", "recommendation": "..."},
        ...
        "overall_risk": "High"
    }
"""

from __future__ import annotations

from typing import Dict, Any

from utils.logger import logger

# Status -> severity weight. This is a generic severity mapping (not a
# medical threshold) used purely to combine already-decided statuses into
# one overall risk label. Any status not listed here defaults to 0.
_STATUS_WEIGHTS = {
    "normal": 0,
    "optimal": 0,
    "near optimal": 1,
    "borderline high": 2,
    "low": 2,
    "high": 3,
    "out of range": 3,
    "unknown": 0,
    "invalid": 0,
}

# Any single parameter with a weight >= this is enough to push the
# overall risk to "High" on its own (e.g. a single "High" reading).
_HIGH_SINGLE_THRESHOLD = 3


def _overall_label(total_score: int, max_single_weight: int, parameter_count: int) -> str:
    """Combine the aggregated severity score into a single overall label."""
    if parameter_count == 0:
        return "Unknown"

    if max_single_weight >= _HIGH_SINGLE_THRESHOLD:
        return "High"

    average_score = total_score / parameter_count
    if average_score >= 1.5:
        return "High"
    if average_score >= 0.5:
        return "Moderate"
    return "Low"


def calculate_overall_risk(rule_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Aggregate Rule Engine results into an overall risk level.

    This function does NOT re-decide whether any individual value is
    Normal/Borderline/High -- that classification already happened in the
    Rule Engine using config/lipid_rules.xlsx. Here we only combine the
    already-assigned statuses into one summary risk level.
    """
    analyzed_data: Dict[str, Any] = {}
    total_score = 0
    max_single_weight = 0
    parameter_count = 0

    for test_name, result in rule_results.items():
        # Pass the Rule Engine's per-parameter result through unchanged.
        analyzed_data[test_name] = result

        status_key = str(result.get("status", "")).strip().lower()
        weight = _STATUS_WEIGHTS.get(status_key, 0)

        total_score += weight
        max_single_weight = max(max_single_weight, weight)
        parameter_count += 1

    overall_risk = _overall_label(total_score, max_single_weight, parameter_count)

    logger.info(
        f"RiskEngine: aggregated {parameter_count} parameters "
        f"(total_score={total_score}, max_single_weight={max_single_weight}) "
        f"-> overall_risk='{overall_risk}'"
    )

    analyzed_data["overall_risk"] = overall_risk
    return analyzed_data
