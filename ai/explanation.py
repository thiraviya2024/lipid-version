"""
ai/explanation.py

Groq-powered explanation generator for LipidAI.

IMPORTANT: The AI never decides whether a value is Normal / Borderline /
High. That decision has already been made upstream by clinical.rule_engine
(driven by config/lipid_rules.xlsx) and combined by clinical.risk_engine.
This module's only job is to turn those already-decided, structured
findings into a clear, friendly, plain-language explanation for the
patient. The prompt explicitly forbids the model from re-classifying or
contradicting the supplied statuses.
"""

from __future__ import annotations

import os
from typing import Dict, Any

from utils.logger import logger

try:
    from groq import Groq
except ImportError:  # pragma: no cover
    Groq = None  # type: ignore

try:
    from config.settings import GROQ_API_KEY, GROQ_MODEL
except ImportError:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _get_groq_client():
    if Groq is None:
        logger.warning("groq package not installed; falling back to offline explanation.")
        return None
    if not GROQ_API_KEY:
        logger.warning("GROQ_API_KEY not set; falling back to offline explanation.")
        return None
    try:
        return Groq(api_key=GROQ_API_KEY)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Failed to initialize Groq client: {exc}")
        return None


def _build_prompt(analyzed_data: Dict[str, Any]) -> str:
    """
    Build a prompt that hands the model already-decided findings and asks
    it ONLY to explain them -- never to re-diagnose or re-classify.
    """
    overall_risk = analyzed_data.get("overall_risk", "Unknown")

    findings_lines = []
    for test_name, result in analyzed_data.items():
        if test_name == "overall_risk":
            continue
        value = result.get("value")
        status = result.get("status")
        recommendation = result.get("recommendation")
        findings_lines.append(
            f"- {test_name}: value={value}, status(already determined)={status}, "
            f"recommendation(already determined)={recommendation}"
        )
    findings_block = "\n".join(findings_lines)

    prompt = f"""You are a medical communication assistant helping a patient understand
their lipid profile report.

The clinical classification (Normal / Borderline / High / etc.) for every
parameter below has ALREADY been determined by a rule-based clinical
engine using physician-defined reference ranges. Overall risk has already
been computed as: {overall_risk}.

Your ONLY task is to explain these already-decided findings in simple,
warm, non-alarming, plain language that a non-medical person can
understand. Do NOT change, second-guess, or re-derive any status,
threshold, or recommendation. Do NOT invent new numeric ranges. Do NOT
state a different status than the one given. Simply explain what each
already-determined finding means for the patient's health, why it
matters, and restate the given recommendation in friendlier wording.

Structure your response in Markdown with:
1. A short (2-3 sentence) overall summary referencing the given overall
   risk level.
2. A bullet list, one bullet per parameter, explaining its already-given
   status and recommendation in plain language.
3. A brief closing note encouraging the patient to discuss the report
   with their physician.

Findings (already classified -- do not alter):
{findings_block}
"""
    return prompt


def _offline_fallback_explanation(analyzed_data: Dict[str, Any]) -> str:
    """
    Deterministic, template-based explanation used when Groq is
    unavailable (no API key, network issue, etc.), so the app keeps
    working end-to-end without the AI dependency.
    """
    overall_risk = analyzed_data.get("overall_risk", "Unknown")

    lines = [
        f"**Overall Risk Level: {overall_risk}**",
        "",
        "Here's a plain-language summary of your report:",
        "",
    ]

    for test_name, result in analyzed_data.items():
        if test_name == "overall_risk":
            continue
        value = result.get("value")
        status = result.get("status")
        recommendation = result.get("recommendation")
        lines.append(f"- **{test_name}** ({value}): classified as **{status}**. {recommendation}.")

    lines.append("")
    lines.append(
        "_Note: This explanation was generated offline because the AI service "
        "was unavailable. Please consult a qualified physician to discuss these results._"
    )
    return "\n".join(lines)


def generate_clinical_explanation(analyzed_data: Dict[str, Any]) -> str:
    """
    Generate a plain-language explanation of already rule-classified
    lipid findings.

    Parameters
    ----------
    analyzed_data: output of clinical.risk_engine.calculate_overall_risk(),
        i.e. a dict of {test_name: {"value", "status", "recommendation"}}
        plus an "overall_risk" key.

    Returns
    -------
    Markdown-formatted explanation string.
    """
    client = _get_groq_client()
    if client is None:
        return _offline_fallback_explanation(analyzed_data)

    prompt = _build_prompt(analyzed_data)

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You explain already-determined clinical lab findings in simple "
                        "language. You never re-classify or contradict the given status "
                        "or recommendation for any parameter."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=800,
        )
        explanation = response.choices[0].message.content.strip()
        if not explanation:
            raise ValueError("Empty response from Groq")
        return explanation
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Groq explanation generation failed, using offline fallback: {exc}")
        return _offline_fallback_explanation(analyzed_data)
