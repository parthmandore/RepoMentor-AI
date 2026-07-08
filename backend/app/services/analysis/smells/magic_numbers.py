"""
Detects magic number literals not in the allowed exceptions set.

Skips comment lines, import statements, and constant definitions
to reduce false positives.
"""

import re
from typing import Any

from app.services.analysis.thresholds import MAGIC_NUMBER_EXCEPTIONS


# Matches standalone numeric literals (integers and floats)
_NUMBER_RE = re.compile(r"(?<![.\w])(-?\d+\.?\d*)(?![.\w])")

# Lines to skip entirely
_SKIP_PATTERNS = [
    re.compile(r"^\s*#"),           # Python comments
    re.compile(r"^\s*//"),          # JS/TS single-line comments
    re.compile(r"^\s*/?\*"),        # Block comments
    re.compile(r"^\s*import\s"),    # Import statements
    re.compile(r"^\s*from\s"),      # Python from-imports
    re.compile(r"^\s*[A-Z_]+\s*="), # CONSTANT_NAME = value (Python)
    re.compile(r"^\s*(?:export\s+)?const\s+[A-Z_]+"), # JS/TS constants
]


def detect_magic_numbers(
    file_path: str,
    content: str,
    extension: str,
) -> list[dict[str, Any]]:
    """
    Flag numeric literals that are not in MAGIC_NUMBER_EXCEPTIONS.

    Severity is always "Low" since magic numbers are a minor code smell.
    Returns a list of standardized smell evidence dicts.
    """
    if extension not in {".py", ".js", ".jsx", ".ts", ".tsx"}:
        return []

    smells: list[dict[str, Any]] = []

    for line_num, line in enumerate(content.split("\n"), start=1):
        stripped = line.strip()
        if not stripped:
            continue

        if any(pattern.match(stripped) for pattern in _SKIP_PATTERNS):
            continue

        for match in _NUMBER_RE.finditer(stripped):
            try:
                value = float(match.group(1))
            except ValueError:
                continue

            # Check integer equivalence for the exceptions set
            int_value = int(value) if value == int(value) else None
            if int_value is not None and int_value in MAGIC_NUMBER_EXCEPTIONS:
                continue
            if value in {float(v) for v in MAGIC_NUMBER_EXCEPTIONS}:
                continue

            smells.append({
                "smell_type": "Magic Number",
                "category": "Readability",
                "severity": "Low",
                "file_path": file_path,
                "line_number": line_num,
                "measured_value": value,
                "threshold": 0,
                "reason": (
                    f"Numeric literal {match.group(1)} at line {line_num} "
                    f"should be extracted into a named constant."
                ),
            })

    return smells
