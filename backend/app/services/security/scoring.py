from app.services.security.thresholds import (
    DEDUCTION_CRITICAL, DEDUCTION_HIGH, DEDUCTION_MEDIUM, DEDUCTION_LOW
)

def calculate_security_score(counts: dict) -> int:
    score = 100.0
    
    score -= counts.get("Critical", 0) * DEDUCTION_CRITICAL
    score -= counts.get("High", 0) * DEDUCTION_HIGH
    score -= counts.get("Medium", 0) * DEDUCTION_MEDIUM
    score -= counts.get("Low", 0) * DEDUCTION_LOW
    
    return max(0, min(100, round(score)))

def calculate_security_grade(score: int) -> str:
    if score >= 90: return "A"
    if score >= 80: return "B"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"
