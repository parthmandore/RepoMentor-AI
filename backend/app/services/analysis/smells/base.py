from abc import ABC, abstractmethod
from typing import Any, Dict, List

class BaseSmellDetector(ABC):
    @abstractmethod
    def detect(
        self,
        file_path: str,
        content: str,
        extension: str,
        size_metrics: Dict[str, Any],
        complexity_metrics: Dict[str, Any],
        declarations: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run code smell detection.
        Returns a list of standardized code smell dicts.
        """
        pass
