import os
import importlib
from typing import Dict, Optional, Set
from app.services.analysis.analyzers.base import BaseAnalyzer

class AnalyzerRegistry:
    _registry: Dict[str, BaseAnalyzer] = {}

    @classmethod
    def register(cls, analyzer: BaseAnalyzer) -> None:
        """Register an analyzer instance for all its supported extensions."""
        for ext in analyzer.supported_extensions():
            cls._registry[ext.lower()] = analyzer

    @classmethod
    def get(cls, extension: str) -> Optional[BaseAnalyzer]:
        """Look up and return the registered analyzer for the extension."""
        if not extension:
            return None
        return cls._registry.get(extension.lower())

    @classmethod
    def supported_extensions(cls) -> Set[str]:
        """Return the set of all registered extensions."""
        return set(cls._registry.keys())

# We will dynamically load all modules in the analyzers directory to auto-trigger @register
def discover_analyzers() -> None:
    current_dir = os.path.dirname(__file__)
    for filename in os.listdir(current_dir):
        if filename.endswith(".py") and filename not in ("__init__.py", "base.py", "registry.py"):
            module_name = filename[:-3]
            importlib.import_module(f"app.services.analysis.analyzers.{module_name}")
