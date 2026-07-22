# extractor/parameter_extractor.py
import re
from typing import Dict, Optional

def extract_lipid_parameters(raw_text: str, structured_data=None) -> Dict[str, float]:
    text = raw_text.lower()
    parameters = {}
    
    patterns = {
        "total_cholesterol": r'(?:total\s*cholesterol|tc|chol)[:\s]*(\d+\.?\d*)',
        "hdl": r'(?:hdl|hdl-c)[:\s]*(\d+\.?\d*)',
        "ldl": r'(?:ldl|ldl-c)[:\s]*(\d+\.?\d*)',
        "triglycerides": r'(?:triglycerides|tg)[:\s]*(\d+\.?\d*)',
    }
    
    for param, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            try:
                parameters[param] = float(match.group(1))
            except:
                pass
                
    return parameters