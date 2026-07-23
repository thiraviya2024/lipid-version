"""
clinical/rule_engine.py

Excel-driven Rule Engine for LipidAI.

This module replaces any hardcoded lipid range logic. All medical
thresholds (Min/Max/Status/Recommendation) are read from
config/lipid_rules.xlsx exactly once, at application startup, and cached
in memory for the lifetime of the process.

Public API
----------
get_rule_engine() -> RuleEngine
    Returns the process-wide singleton RuleEngine instance, loading the
    Excel file on first call only.

RuleEngine.evaluate(lipid_values: dict) -> dict
    Given {"Total Cholesterol": 245, "HDL": 35, ...} returns:
    {
        "Total Cholesterol": {
            "value": 245,
            "status": "High",
            "recommendation": "Consult physician for further evaluation"
        },
        ...
    }
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Dict, Any

import pandas as pd

from utils.logger import logger

# Location of the Excel-based rule set. Resolved relative to project root.
RULES_PATH = Path("config/lipid_rules.xlsx")

REQUIRED_COLUMNS = {"Test", "Min", "Max", "Status", "Recommendation"}


class RuleEngineError(Exception):
    """Raised when the lipid rules file is missing, malformed, or invalid."""


class RuleEngine:
    """
    Loads clinical lipid rules from an Excel file exactly once and answers
    lookups against that in-memory table for the rest of the process
    lifetime.

    Do NOT instantiate this class directly from application code -- use
    get_rule_engine() so the Excel file is loaded a single time and shared.
    """

    def __init__(self, rules_path: Path = RULES_PATH):
        self._rules_path = rules_path
        self._rules_df: pd.DataFrame | None = None
        self._load_rules()

    # ------------------------------------------------------------------ #
    # Loading
    # ------------------------------------------------------------------ #
    def _load_rules(self) -> None:
        if not self._rules_path.exists():
            raise RuleEngineError(
                f"Lipid rules file not found at '{self._rules_path}'. "
                f"Create it with columns: {sorted(REQUIRED_COLUMNS)}."
            )

        try:
            df = pd.read_excel(self._rules_path, engine="openpyxl")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Failed to read lipid rules Excel file: {exc}")
            raise RuleEngineError(f"Could not read '{self._rules_path}': {exc}") from exc

        missing_cols = REQUIRED_COLUMNS - set(df.columns)
        if missing_cols:
            raise RuleEngineError(
                f"'{self._rules_path}' is missing required columns: {sorted(missing_cols)}"
            )

        # Normalize types so comparisons are safe and case-insensitive lookups work.
        df["Test"] = df["Test"].astype(str).str.strip()
        df["Status"] = df["Status"].astype(str).str.strip()
        df["Recommendation"] = df["Recommendation"].astype(str).str.strip()
        df["Min"] = pd.to_numeric(df["Min"], errors="coerce")
        df["Max"] = pd.to_numeric(df["Max"], errors="coerce")

        if df["Min"].isna().any() or df["Max"].isna().any():
            bad_rows = df[df["Min"].isna() | df["Max"].isna()]
            raise RuleEngineError(
                f"'{self._rules_path}' contains non-numeric Min/Max values in rows: "
                f"{bad_rows.index.tolist()}"
            )

        df["_test_key"] = df["Test"].str.lower()

        self._rules_df = df.reset_index(drop=True)
        logger.info(
            f"RuleEngine: loaded {len(df)} lipid rules covering "
            f"{sorted(df['Test'].unique().tolist())} from '{self._rules_path}'"
        )

    def reload(self) -> None:
        """Force a re-read of the Excel file (useful for admin/testing flows)."""
        logger.info("RuleEngine: reload() requested, re-reading Excel rules file")
        self._load_rules()

    # ------------------------------------------------------------------ #
    # Lookups
    # ------------------------------------------------------------------ #
    def _rules_for_test(self, test_name: str) -> pd.DataFrame:
        key = test_name.strip().lower()
        return self._rules_df[self._rules_df["_test_key"] == key]

    def evaluate_value(self, test_name: str, value: float) -> Dict[str, Any]:
        """Evaluate a single lipid parameter value against the Excel rules."""
        matches = self._rules_for_test(test_name)

        if matches.empty:
            logger.warning(f"RuleEngine: no rules defined for test '{test_name}'")
            return {
                "value": value,
                "status": "Unknown",
                "recommendation": "No rule defined for this parameter in lipid_rules.xlsx.",
            }

        for _, row in matches.iterrows():
            if row["Min"] <= value <= row["Max"]:
                return {
                    "value": value,
                    "status": row["Status"],
                    "recommendation": row["Recommendation"],
                }

        # Value fell outside every defined [Min, Max] band for this test.
        logger.warning(
            f"RuleEngine: value {value} for '{test_name}' is outside all defined ranges"
        )
        return {
            "value": value,
            "status": "Out of Range",
            "recommendation": "Value falls outside the defined reference ranges. Please consult a physician.",
        }

    def evaluate(self, lipid_values: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Evaluate a full set of extracted lipid parameters.

        Parameters
        ----------
        lipid_values: dict mapping test name -> numeric value, e.g.
            {"Total Cholesterol": 245, "HDL": 35, "LDL": 150, "Triglycerides": 180}

        Returns
        -------
        dict mapping test name -> {"value", "status", "recommendation"}
        """
        results: Dict[str, Dict[str, Any]] = {}

        for test_name, raw_value in lipid_values.items():
            try:
                numeric_value = float(raw_value)
            except (TypeError, ValueError):
                logger.warning(
                    f"RuleEngine: could not parse numeric value for '{test_name}': {raw_value!r}"
                )
                results[test_name] = {
                    "value": raw_value,
                    "status": "Invalid",
                    "recommendation": "Could not parse a numeric value for this parameter.",
                }
                continue

            results[test_name] = self.evaluate_value(test_name, numeric_value)

        return results


# ---------------------------------------------------------------------- #
# Process-wide singleton so the Excel file is read exactly once.
# ---------------------------------------------------------------------- #
_engine_instance: RuleEngine | None = None
_engine_lock = threading.Lock()


def get_rule_engine() -> RuleEngine:
    """Return the shared RuleEngine, loading the Excel rules on first call."""
    global _engine_instance
    if _engine_instance is None:
        with _engine_lock:
            if _engine_instance is None:  # double-checked locking
                _engine_instance = RuleEngine()
    return _engine_instance