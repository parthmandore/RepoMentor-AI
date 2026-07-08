from app.services.analysis.analyzers.base import BaseAnalyzer
from app.services.analysis.analyzers.registry import AnalyzerRegistry, discover_analyzers

# Run discovery of concrete analyzers
discover_analyzers()
