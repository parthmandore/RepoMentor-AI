"""
Detects functions exceeding the Long Method LOC threshold.
"""

from typing import Any

from app.services.analysis.thresholds import LONG_METHOD_LOC


def detect_long_methods(
    file_path: str,
    size_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Flag functions whose LOC exceeds LONG_METHOD_LOC.

    Uses function data extracted by size_metrics analysis.
    Returns a list of standardized smell evidence dicts.
    """
    smells: list[dict[str, Any]] = []

    for func in size_metrics.get("functions", []):
        loc = func.get("loc", 0)
        if loc <= LONG_METHOD_LOC:
            continue

        severity = "Medium" if loc < LONG_METHOD_LOC * 1.5 else "High"

        smells.append({
            "smell_type": "Long Method",
            "category": "Size",
            "severity": severity,
            "file_path": file_path,
            "line_number": func.get("line"),
            "measured_value": loc,
            "threshold": LONG_METHOD_LOC,
            "reason": (
                f"Function '{func['name']}' has {loc} lines, "
                f"exceeding the {LONG_METHOD_LOC}-line threshold."
            ),
        })

    return smells
