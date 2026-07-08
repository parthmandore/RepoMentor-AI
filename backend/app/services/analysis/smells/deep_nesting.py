"""
Detects deeply nested code by scanning indentation levels.

For Python: counts indentation increases (each indent level = 4 spaces or 1 tab).
For JS/TS: counts brace nesting depth.
"""

from typing import Any

from app.services.analysis.thresholds import DEEP_NESTING_LEVEL


def detect_deep_nesting(
    file_path: str,
    content: str,
    extension: str,
) -> list[dict[str, Any]]:
    """
    Flag lines where control-flow nesting exceeds DEEP_NESTING_LEVEL.

    Severity:
    - "Medium" if depth <= threshold + 2
    - "High" otherwise

    Returns a list of standardized smell evidence dicts.
    """
    if extension == ".py":
        return _detect_python_nesting(file_path, content)
    if extension in {".js", ".jsx", ".ts", ".tsx"}:
        return _detect_js_nesting(file_path, content)
    return []


def _detect_python_nesting(file_path: str, content: str) -> list[dict[str, Any]]:
    """Detect deep nesting in Python by measuring indentation levels."""
    smells: list[dict[str, Any]] = []
    flagged_depths: set[int] = set()

    for line_num, line in enumerate(content.split("\n"), start=1):
        if not line.strip():
            continue

        # Calculate indent level: expand tabs to 4 spaces, then count leading spaces
        expanded = line.expandtabs(4)
        indent_chars = len(expanded) - len(expanded.lstrip())
        depth = indent_chars // 4

        if depth > DEEP_NESTING_LEVEL and depth not in flagged_depths:
            flagged_depths.add(depth)
            severity = "Medium" if depth <= DEEP_NESTING_LEVEL + 2 else "High"
            smells.append({
                "smell_type": "Deep Nesting",
                "category": "Complexity",
                "severity": severity,
                "file_path": file_path,
                "line_number": line_num,
                "measured_value": depth,
                "threshold": DEEP_NESTING_LEVEL,
                "reason": (
                    f"Code is nested {depth} levels deep at line {line_num}, "
                    f"exceeding the {DEEP_NESTING_LEVEL}-level threshold."
                ),
            })

    return smells


def _detect_js_nesting(file_path: str, content: str) -> list[dict[str, Any]]:
    """Detect deep nesting in JS/TS by counting brace depth."""
    smells: list[dict[str, Any]] = []
    brace_depth = 0
    max_flagged_depth = 0

    for line_num, line in enumerate(content.split("\n"), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        for char in stripped:
            if char == "{":
                brace_depth += 1
            elif char == "}":
                brace_depth = max(0, brace_depth - 1)

        if brace_depth > DEEP_NESTING_LEVEL and brace_depth > max_flagged_depth:
            max_flagged_depth = brace_depth
            severity = "Medium" if brace_depth <= DEEP_NESTING_LEVEL + 2 else "High"
            smells.append({
                "smell_type": "Deep Nesting",
                "category": "Complexity",
                "severity": severity,
                "file_path": file_path,
                "line_number": line_num,
                "measured_value": brace_depth,
                "threshold": DEEP_NESTING_LEVEL,
                "reason": (
                    f"Code is nested {brace_depth} levels deep at line {line_num}, "
                    f"exceeding the {DEEP_NESTING_LEVEL}-level threshold."
                ),
            })

    return smells
