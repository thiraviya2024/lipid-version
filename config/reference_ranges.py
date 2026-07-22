# config/reference_ranges.py
import json
from pathlib import Path

def load_reference_ranges():
    path = Path("config/reference_ranges.json")
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return {}