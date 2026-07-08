"""
Detects files exceeding the Large File LOC threshold.
"""

from typing import Any

from app.services.analysis.thresholds import LARGE_FILE_LOC


def detect_large_file(
    file_path: str,
    size_metrics: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Flag a file if its code_lines exceed the LARGE_FILE_LOC threshold.

    Returns a list with zero or one standardized smell evidence dict.
    """
    loc = size_metrics.get("code_lines", 0)
    if loc <= LARGE_FILE_LOC:
        return []

    severity = "Medium" if loc < LARGE_FILE_LOC * 1.5 else "High"

    return [{
        "smell_type": "Large File",
        "category": "Size",
        "severity": severity,
        "file_path": file_path,
        "line_number": None,
        "measured_value": loc,
        "threshold": LARGE_FILE_LOC,
        "reason": f"File has {loc} lines, exceeding the {LARGE_FILE_LOC}-line threshold.",
    }]
