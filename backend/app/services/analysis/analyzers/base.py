import re
from abc import ABC, abstractmethod
from typing import Any, List, Dict, Set, Optional

class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze_size(self, content: str, extension: str) -> Dict[str, Any]:
        """Returns size metrics (total_lines, blank_lines, comment_lines, code_lines, functions, classes)."""
        pass

    @abstractmethod
    def analyze_complexity(self, content: str, extension: str) -> Dict[str, Any]:
        """Calculates complexity metrics using ComplexityEngine."""
        pass

    @abstractmethod
    def extract_declarations(self, content: str, extension: str) -> List[Dict[str, Any]]:
        """Extracts list of declarations (classes, functions, methods, fields, etc.)."""
        pass

    @abstractmethod
    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        """Extracts dependencies (imports, inheritance, composition, calls)."""
        pass

    @abstractmethod
    def detect_smells(
        self,
        file_path: str,
        content: str,
        extension: str,
        size_metrics: Dict[str, Any],
        complexity_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Runs the smell engine detectors on the file."""
        pass

    @abstractmethod
    def supported_extensions(self) -> Set[str]:
        """Set of supported extensions for this analyzer."""
        pass


class BraceLanguageAnalyzer(BaseAnalyzer):
    """Common analyzer for languages that use curly braces {} for blocks."""
    
    def strip_comments(self, content: str) -> str:
        """Strip C-style block comments /*...*/ and line comments //..."""
        # Block comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Line comments
        lines = []
        for line in content.split('\n'):
            # Simple line comments check
            line = re.sub(r'//.*$', '', line)
            lines.append(line)
        return '\n'.join(lines)

    def count_nesting_depth(self, content: str) -> List[Dict[str, Any]]:
        """
        Calculates brace nesting depth per line.
        Returns a list of nested lines with their depths.
        """
        stripped_content = self.strip_comments(content)
        lines = stripped_content.split('\n')
        depth = 0
        blocks = []
        for i, line in enumerate(lines):
            line_num = i + 1
            for char in line:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth = max(0, depth - 1)
            if depth > 0:
                blocks.append({"line": line_num, "depth": depth})
        return blocks

    def find_brace_end(self, lines: List[str], start_index: int) -> int:
        """Find the 0-indexed line where braces balance out starting from start_index."""
        brace_count = 0
        found_open = False
        for j in range(start_index, len(lines)):
            for char in lines[j]:
                if char == "{":
                    brace_count += 1
                    found_open = True
                elif char == "}":
                    brace_count -= 1
            if found_open and brace_count <= 0:
                return j + 1
        return len(lines)


class CFamilyAnalyzer(BraceLanguageAnalyzer):
    """Common functionality for C and C++."""
    pass


class JVMLanguageAnalyzer(BraceLanguageAnalyzer):
    """Common functionality for Java, Kotlin, and C#."""
    pass


class JavaScriptFamilyAnalyzer(BraceLanguageAnalyzer):
    """Common functionality for JavaScript and TypeScript."""
    pass
