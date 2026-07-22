# lipid-ai/extractor/validator.py
"""
Validates if the report is likely a Lipid Profile.
"""

def is_lipid_report(raw_text: str) -> bool:
    """Simple heuristic to detect lipid report."""
    keywords = ["cholesterol", "hdl", "ldl", "triglyceride", "lipid", "profile"]
    text_lower = raw_text.lower()
    return any(kw in text_lower for kw in keywords)