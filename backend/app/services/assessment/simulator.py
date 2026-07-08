"""
Engineering assessment score simulator.
Enables sandbox recalculations of repository health scores based on toggled recommendations.
Does not persist to database or alter repository data.
"""

from typing import List, Dict, Any

def run_simulation(
    current_score: int,
    recommendations: List[Dict[str, Any]],
    enabled_rec_ids: List[str]
) -> int:
    """
    Reruns the scoring summation with toggled adjustments.
    Returns the predicted score.
    """
    gain = 0
    for rec in recommendations:
        if rec["id"] in enabled_rec_ids:
            gain += rec["gain"]
            
    return min(100, max(0, current_score + gain))
