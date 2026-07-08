"""
Assessment static reference benchmarks.
Configurable constant bands for comparing repository scores safely.
Not derived from live web queries.
"""

from typing import Dict, Any

BENCHMARK_BANDS = {
    "student_portfolio": {
        "name": "Student Portfolio",
        "min": 55,
        "max": 70,
        "description": "Standard learning exercises, single developer prototypes, or course submissions."
    },
    "production_repository": {
        "name": "Production Repository",
        "min": 75,
        "max": 90,
        "description": "Enterprise microservices, business applications, and team-maintained codebases."
    },
    "open_source": {
        "name": "High Quality Open Source",
        "min": 90,
        "max": 100,
        "description": "Widely adopted libraries, frameworks, and exceptionally documented projects."
    }
}

def get_benchmarks(score: int) -> Dict[str, Any]:
    """
    Returns reference ranges relative to the current repository score.
    """
    return {
        "categories": BENCHMARK_BANDS,
        "explanation": "Benchmark categories are static reference bands, not live comparisons."
    }
