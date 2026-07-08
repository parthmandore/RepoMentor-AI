"""
Detects classes exceeding God Class thresholds (method count or LOC).
"""

from typing import Any

from app.services.analysis.thresholds import GOD_CLASS_METHODS, GOD_CLASS_LOC


def detect_god_classes(
    file_path: str,
    size_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Flag classes exceeding GOD_CLASS_METHODS or GOD_CLASS_LOC.

    Severity:
    - "High" if both thresholds are exceeded.
    - "Medium" if only one threshold is exceeded.

    Uses class data extracted by size_metrics analysis.
    Returns a list of standardized smell evidence dicts.
    """
    smells: list[dict[str, Any]] = []

    for cls in size_metrics.get("classes", []):
        method_count = cls.get("method_count", 0)
        loc = cls.get("loc", 0)

        exceeds_methods = method_count > GOD_CLASS_METHODS
        exceeds_loc = loc > GOD_CLASS_LOC

        if not exceeds_methods and not exceeds_loc:
            continue

        severity = "High" if (exceeds_methods and exceeds_loc) else "Medium"

        reasons: list[str] = []
        if exceeds_methods:
            reasons.append(
                f"{method_count} methods (threshold: {GOD_CLASS_METHODS})"
            )
        if exceeds_loc:
            reasons.append(
                f"{loc} lines (threshold: {GOD_CLASS_LOC})"
            )

        measured_value = max(method_count, loc)

        smells.append({
            "smell_type": "God Class",
            "category": "Size",
            "severity": severity,
            "file_path": file_path,
            "line_number": cls.get("line"),
            "measured_value": measured_value,
            "threshold": GOD_CLASS_METHODS if exceeds_methods else GOD_CLASS_LOC,
            "reason": (
                f"Class '{cls['name']}' exceeds thresholds: "
                + ", ".join(reasons) + "."
            ),
        })

    return smells
