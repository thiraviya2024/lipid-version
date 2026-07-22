# lipid-ai/clinical/risk_engine.py
"""
Calculates overall lipid risk level using rule-based logic.
"""

from typing import Dict
from .classifier import classify_value

def calculate_overall_risk(lipid_data: Dict[str, float]) -> Dict:
    """Add classification to each parameter and compute overall risk."""
    result = {}
    high_count = 0
    very_high_count = 0

    for param, value in lipid_data.items():
        classification = classify_value(param, value)
        result[param] = {
            "value": value,
            "status": classification["status"],
            "note": classification.get("note", "")
        }
        
        if "High" in classification["status"] or "Very High" in classification["status"]:
            high_count += 1
        if "Very High" in classification["status"]:
            very_high_count += 1

    # Overall Risk
    if very_high_count >= 1 or high_count >= 3:
        overall = "Very High Risk"
    elif high_count >= 2:
        overall = "High Risk"
    elif high_count == 1:
        overall = "Moderate Risk"
    else:
        overall = "Low Risk"

    result["overall_risk"] = overall
    return result