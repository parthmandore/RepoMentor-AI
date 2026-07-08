from typing import Any, Dict, List
from app.services.analysis.analyzers.registry import AnalyzerRegistry

def detect_smells(
    file_path: str,
    content: str,
    extension: str,
    size_metrics: Dict[str, Any],
    complexity_metrics: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Backward compatible wrapper routing to the new registry-based analyzers."""
    analyzer = AnalyzerRegistry.get(extension)
    if analyzer:
        return analyzer.detect_smells(file_path, content, extension, size_metrics, complexity_metrics)
    return []
