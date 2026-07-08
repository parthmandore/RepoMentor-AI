from typing import Any, Dict
from app.services.analysis.analyzers.registry import AnalyzerRegistry

def analyze_complexity(content: str, extension: str) -> Dict[str, Any]:
    """Backward compatible wrapper routing to the new registry-based analyzers."""
    analyzer = AnalyzerRegistry.get(extension)
    if analyzer:
        return analyzer.analyze_complexity(content, extension)
    return {"file_complexity": 0, "functions": []}
