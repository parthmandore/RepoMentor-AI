"""
Code duplication detector using rolling hash blocks.

Algorithm:
1. Normalize each file: strip whitespace, skip blank and comment-only lines.
2. Generate hashes for rolling blocks of N consecutive normalized lines.
3. Track which block hashes appear more than once across all files.
4. Calculate duplication percentage: duplicated_lines / total_lines * 100.
"""

import hashlib
import re
from typing import Any

from app.services.analysis.thresholds import DUPLICATION_BLOCK_SIZE


_COMMENT_PATTERNS = [
    re.compile(r"^\s*#"),       # Python comments
    re.compile(r"^\s*//"),      # JS/TS single-line comments
    re.compile(r"^\s*/\*"),     # Block comment start
    re.compile(r"^\s*\*"),      # Block comment continuation
]


def analyze_duplication(
    file_contents: list[tuple[str, str]],
) -> dict[str, Any]:
    """
    Detect code duplication across all provided files.

    Args:
        file_contents: List of (file_path, content) tuples.

    Returns:
        {
            "duplication_percentage": float,
            "duplicated_lines": int,
            "total_lines": int,
        }
    """
    block_size = DUPLICATION_BLOCK_SIZE

    # hash -> list of (file_path, start_line_index) occurrences
    seen_hashes: dict[str, list[tuple[str, int]]] = {}
    total_normalized_lines = 0

    for file_path, content in file_contents:
        normalized = _normalize_lines(content)
        total_normalized_lines += len(normalized)

        if len(normalized) < block_size:
            continue

        for i in range(len(normalized) - block_size + 1):
            block = "\n".join(normalized[i : i + block_size])
            block_hash = hashlib.md5(block.encode(), usedforsecurity=False).hexdigest()

            if block_hash not in seen_hashes:
                seen_hashes[block_hash] = []
            seen_hashes[block_hash].append((file_path, i))

    # Count duplicated lines: lines belonging to any block that appears 2+ times
    duplicated_line_set: set[tuple[str, int]] = set()
    for block_hash, occurrences in seen_hashes.items():
        if len(occurrences) < 2:
            continue
        for file_path, start_index in occurrences:
            for offset in range(block_size):
                duplicated_line_set.add((file_path, start_index + offset))

    duplicated_lines = len(duplicated_line_set)
    total_lines = max(total_normalized_lines, 1)
    duplication_percentage = round(duplicated_lines / total_lines * 100, 2)

    return {
        "duplication_percentage": duplication_percentage,
        "duplicated_lines": duplicated_lines,
        "total_lines": total_lines,
    }


def _normalize_lines(content: str) -> list[str]:
    """
    Normalize source lines for duplication comparison.

    Strips whitespace, removes blank lines and comment-only lines.
    """
    result: list[str] = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if any(pattern.match(stripped) for pattern in _COMMENT_PATTERNS):
            continue
        result.append(stripped)
    return result
