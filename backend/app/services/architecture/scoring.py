def calculate_architecture_score(
    cycle_count: int,
    highly_coupled_count: int,
    config_violation_count: int,
    unknown_ratio: float
) -> int:
    """
    Deterministic Architecture Health Score (0-100).
    """
    score = 100.0
    
    # Deductions
    score -= cycle_count * 15.0  # -15 per circular dependency chain
    score -= highly_coupled_count * 5.0  # -5 per highly coupled module (>8 coupling)
    score -= config_violation_count * 10.0  # -10 if configuration is leaked
    score -= unknown_ratio * 20.0  # -20 for inconsistent module classifications
    
    return max(0, min(100, round(score)))

def calculate_architecture_grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"
