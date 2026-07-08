"""
Health score and letter-grade calculator for repository analysis.

Uses a weighted scoring model matching exact Phase 6.5 requirements.
"""

from typing import Dict, Any

def calculate_weighted_health_score(
    average_complexity: float,
    total_smells: int,
    security_counts: Dict[str, int],
    cycle_count: int,
    highly_coupled_count: int,
    comment_ratio: float,
    duplication_percentage: float
) -> Dict[str, Any]:
    """
    Calculates health score using weighted sections:
    - Complexity: 25%
    - Maintainability: 25%
    - Security: 20%
    - Architecture: 15%
    - Documentation: 10%
    - Duplication: 5%
    """
    details = []

    # 1. Complexity Score (25 pts)
    comp_deduction = min(15.0, max(0.0, average_complexity - 3.0) * 1.5)
    complexity_score = round(25.0 - comp_deduction)
    if comp_deduction > 0:
        details.append({
            "dimension": "Complexity",
            "type": "deduction",
            "rule": "Average Complexity > 3.0",
            "measured": f"{average_complexity:.2f} complexity",
            "impact": -round(comp_deduction),
            "reason": "Complex decision branches reduce readability and increase testing difficulty."
        })
    else:
        details.append({
            "dimension": "Complexity",
            "type": "bonus",
            "rule": "Low Average Complexity",
            "measured": f"{average_complexity:.2f} complexity",
            "impact": 0,
            "reason": "All decision structures are simple and easily readable."
        })

    # 2. Maintainability Score (25 pts)
    smell_deduction = min(20.0, total_smells * 1.5)
    maintainability_score = round(25.0 - smell_deduction)
    if total_smells > 0:
        details.append({
            "dimension": "Maintainability",
            "type": "deduction",
            "rule": "Active Code Smells",
            "measured": f"{total_smells} smells",
            "impact": -round(smell_deduction),
            "reason": "Code smells indicate anti-patterns that increase long-term technical debt."
        })
    else:
        details.append({
            "dimension": "Maintainability",
            "type": "bonus",
            "rule": "Zero Code Smells",
            "measured": "0 smells",
            "impact": 0,
            "reason": "Outstanding structural quality with no detected anti-patterns."
        })

    # 3. Security Score (20 pts)
    sec_deduction = (
        security_counts.get("Critical", 0) * 5 +
        security_counts.get("High", 0) * 5 +
        security_counts.get("Medium", 0) * 2 +
        security_counts.get("Low", 0) * 1
    )
    security_score = max(0, round(20.0 - sec_deduction))
    total_sec = sum(security_counts.values())
    if total_sec > 0:
        details.append({
            "dimension": "Security",
            "type": "deduction",
            "rule": "Vulnerabilities Detected",
            "measured": f"{total_sec} issues",
            "impact": -round(sec_deduction),
            "reason": f"Found security flaws ({security_counts.get('Critical', 0)} Critical, {security_counts.get('High', 0)} High)."
        })
    else:
        details.append({
            "dimension": "Security",
            "type": "bonus",
            "rule": "Clean Security Scan",
            "measured": "0 issues",
            "impact": 0,
            "reason": "No hardcoded credentials, unsafe APIs, or SQL injection vectors detected."
        })

    # 4. Architecture Score (15 pts)
    arch_deduction = (cycle_count * 3) + (highly_coupled_count * 1)
    architecture_score = max(0, round(15.0 - arch_deduction))
    if arch_deduction > 0:
        details.append({
            "dimension": "Architecture",
            "type": "deduction",
            "rule": "Structural Coupling / Cycles",
            "measured": f"{cycle_count} cycles, {highly_coupled_count} coupled",
            "impact": -round(arch_deduction),
            "reason": "Circular dependencies and high coupling restrict modular reuse."
        })
    else:
        details.append({
            "dimension": "Architecture",
            "type": "bonus",
            "rule": "Symmetric Dependencies",
            "measured": "0 violations",
            "impact": 0,
            "reason": "Strict separation of layer concerns with modular, cycle-free relationships."
        })

    # 5. Documentation Score (10 pts)
    doc_score = min(10.0, round(comment_ratio * 50.0))
    documentation_score = max(0, round(doc_score))
    if comment_ratio < 0.2:
        details.append({
            "dimension": "Documentation",
            "type": "deduction",
            "rule": "Low Comment Density",
            "measured": f"{(comment_ratio * 100):.1f}% comments",
            "impact": -round(10.0 - documentation_score),
            "reason": "Low comment density makes the codebase harder for new developers to onboard."
        })
    else:
        details.append({
            "dimension": "Documentation",
            "type": "bonus",
            "rule": "High Comment Density",
            "measured": f"{(comment_ratio * 100):.1f}% comments",
            "impact": 0,
            "reason": "Adequate inline class/method level documentation."
        })

    # 6. Duplication Score (5 pts)
    dup_deduction = duplication_percentage / 2.0
    duplication_score = max(0, round(5.0 - dup_deduction))
    if duplication_percentage > 5.0:
        details.append({
            "dimension": "Duplication",
            "type": "deduction",
            "rule": "Code Duplication",
            "measured": f"{duplication_percentage:.1f}% duplicated",
            "impact": -round(dup_deduction),
            "reason": "Copy-pasted code segments violate the DRY (Don't Repeat Yourself) principle."
        })
    else:
        details.append({
            "dimension": "Duplication",
            "type": "bonus",
            "rule": "DRY Compliant",
            "measured": f"{duplication_percentage:.1f}% duplicated",
            "impact": 0,
            "reason": "DRY-compliant code structure with minimal duplicated logic."
        })

    final_score = (
        complexity_score +
        maintainability_score +
        security_score +
        architecture_score +
        documentation_score +
        duplication_score
    )
    final_score = max(0, min(100, final_score))

    return {
        "final_score": final_score,
        "breakdown": {
            "complexity": {"score": complexity_score, "max": 25},
            "maintainability": {"score": maintainability_score, "max": 25},
            "security": {"score": security_score, "max": 20},
            "architecture": {"score": architecture_score, "max": 15},
            "documentation": {"score": documentation_score, "max": 10},
            "duplication": {"score": duplication_score, "max": 5}
        },
        "details": details
    }


def calculate_grade(score: int) -> str:
    """Maps a numeric score (0-100) to a letter grade (A-F)."""
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def calculate_health_score(
    average_complexity: float,
    duplication_percentage: float,
    smell_density: float,
    large_file_ratio: float,
) -> int:
    """Backward compatible fallback mapping to weighted model."""
    res = calculate_weighted_health_score(
        average_complexity=average_complexity,
        total_smells=round(smell_density * 5.0),
        security_counts={},
        cycle_count=0,
        highly_coupled_count=0,
        comment_ratio=0.15,
        duplication_percentage=duplication_percentage
    )
    return res["final_score"]
