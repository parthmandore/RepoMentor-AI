"""
Metrics aggregator that combines per-file metrics, duplication results,
and code smells into a single repository-level summary.
"""

from typing import Any
from collections import Counter

from app.services.analysis.scoring import calculate_health_score, calculate_grade
from app.services.analysis.thresholds import LARGE_FILE_LOC


def aggregate_metrics(
    file_metrics: list[dict[str, Any]],
    duplication_result: dict[str, Any],
    smells: list[dict[str, Any]],
    files_analyzed: int,
    files_skipped: int,
) -> dict[str, Any]:
    """
    Combine all per-file metrics into a repository-level summary.

    Args:
        file_metrics: List of dicts with keys like code_lines, file_complexity, etc.
        duplication_result: Output from analyze_duplication().
        smells: List of standardized smell evidence dicts.
        files_analyzed: Number of files that were analyzed.
        files_skipped: Number of files skipped (binary, unsupported, etc).

    Returns:
        Comprehensive summary dict with health score, grade, and rankings.
    """
    total_loc = sum(m.get("code_lines", 0) for m in file_metrics)
    complexities = [m.get("file_complexity", 0) for m in file_metrics]
    average_complexity = (
        round(sum(complexities) / len(complexities), 2) if complexities else 0.0
    )
    max_complexity = max(complexities) if complexities else 0

    large_file_count = sum(
        1 for m in file_metrics if m.get("code_lines", 0) > LARGE_FILE_LOC
    )
    large_file_ratio = (
        large_file_count / len(file_metrics) if file_metrics else 0.0
    )

    total_smells = len(smells)
    duplication_percentage = duplication_result.get("duplication_percentage", 0.0)
    smell_density = (
        round(total_smells / (total_loc / 1000), 2) if total_loc > 0 else 0.0
    )

    health_score = calculate_health_score(
        average_complexity=average_complexity,
        duplication_percentage=duplication_percentage,
        smell_density=smell_density,
        large_file_ratio=large_file_ratio,
    )
    health_grade = calculate_grade(health_score)

    # Rankings: top 10 by various criteria
    top_complex_files = _rank_files(file_metrics, "file_complexity", limit=10)
    top_largest_files = _rank_files(file_metrics, "code_lines", limit=10)
    top_smelly_files = _rank_smelly_files(smells, limit=10)

    return {
        "total_lines_of_code": total_loc,
        "average_complexity": average_complexity,
        "max_complexity": max_complexity,
        "files_analyzed": files_analyzed,
        "files_skipped": files_skipped,
        "total_smells": total_smells,
        "duplication_percentage": duplication_percentage,
        "health_score": health_score,
        "health_grade": health_grade,
        "rankings": {
            "top_complex_files": top_complex_files,
            "top_largest_files": top_largest_files,
            "top_smelly_files": top_smelly_files,
        },
    }


def _rank_files(
    file_metrics: list[dict[str, Any]], key: str, limit: int
) -> list[dict[str, Any]]:
    """Return the top N files ranked by a given metric key, descending."""
    sorted_files = sorted(file_metrics, key=lambda m: m.get(key, 0), reverse=True)
    return [
        {"file_path": m["file_path"], key: m.get(key, 0)}
        for m in sorted_files[:limit]
    ]


def _rank_smelly_files(
    smells: list[dict[str, Any]], limit: int
) -> list[dict[str, Any]]:
    """Return the top N files ranked by total number of smells."""
    counts: Counter[str] = Counter()
    for smell in smells:
        counts[smell["file_path"]] += 1

    return [
        {"file_path": path, "smell_count": count}
        for path, count in counts.most_common(limit)
    ]
