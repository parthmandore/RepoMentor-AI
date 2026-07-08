from typing import Any, Dict
from app.services.analysis.analyzers.registry import AnalyzerRegistry

def analyze_size(content: str, extension: str) -> Dict[str, Any]:
    """Backward compatible wrapper routing to the new registry-based analyzers."""
    analyzer = AnalyzerRegistry.get(extension)
    if analyzer:
        return analyzer.analyze_size(content, extension)
    return {
        "total_lines": 0,
        "blank_lines": 0,
        "comment_lines": 0,
        "code_lines": 0,
        "functions": [],
        "classes": [],
    }
