import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import BaseAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class RubyAnalyzer(BaseAnalyzer):
    # Regex patterns for Ruby declarations
    CLASS_RE = re.compile(r"^\s*class\s+(\w+)")
    MODULE_RE = re.compile(r"^\s*module\s+(\w+)")
    METHOD_RE = re.compile(r"^\s*def\s+(\w+)")
    REQUIRE_RE = re.compile(r"^\s*require\s+['\"]([^'\"]+)['\"]")

    def supported_extensions(self) -> Set[str]:
        return {".rb"}

    def analyze_size(self, content: str, extension: str) -> Dict[str, Any]:
        lines = content.split("\n")
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        code_lines = total_lines - blank_lines - comment_lines

        functions = []
        classes = []
        for i, line in enumerate(lines):
            line_num = i + 1
            class_match = self.CLASS_RE.search(line)
            if class_match:
                # Find end matching (crude indent/keyword match for def/class end)
                end_line = self._find_end_keyword(lines, i)
                classes.append({
                    "name": class_match.group(1),
                    "line": line_num,
                    "loc": end_line - i
                })
                continue

            method_match = self.METHOD_RE.search(line)
            if method_match:
                name = method_match.group(1)
                end_line = self._find_end_keyword(lines, i)
                functions.append({
                    "name": name,
                    "line": line_num,
                    "loc": end_line - i
                })

        return {
            "total_lines": total_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "code_lines": code_lines,
            "functions": functions,
            "classes": classes
        }

    def _find_end_keyword(self, lines: List[str], start_index: int) -> int:
        nesting = 1
        for j in range(start_index + 1, len(lines)):
            stripped = lines[j].strip()
            if re.match(r"\b(class|module|def|if|unless|case|while|until|for|begin)\b", stripped):
                # Only increment if it has a block start
                if not stripped.endswith("end"):
                    nesting += 1
            elif stripped == "end" or stripped.startswith("end "):
                nesting -= 1
            if nesting <= 0:
                return j + 1
        return len(lines)

    def analyze_complexity(self, content: str, extension: str) -> Dict[str, Any]:
        declarations = self.extract_declarations(content, extension)
        # Ruby is non-brace, but we can compute line-based branch keyword counts
        return ComplexityEngine.calculate(content, extension, declarations)

    def extract_declarations(self, content: str, extension: str) -> List[Dict[str, Any]]:
        declarations = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Class
            class_match = self.CLASS_RE.search(line)
            if class_match:
                end_line = self._find_end_keyword(lines, i)
                declarations.append({
                    "name": class_match.group(1),
                    "type": "class",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip(),
                    "language": "ruby"
                })
                continue

            # Module
            mod_match = self.MODULE_RE.search(line)
            if mod_match:
                end_line = self._find_end_keyword(lines, i)
                declarations.append({
                    "name": mod_match.group(1),
                    "type": "module",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip(),
                    "language": "ruby"
                })
                continue

            # Method
            method_match = self.METHOD_RE.search(line)
            if method_match:
                name = method_match.group(1)
                end_line = self._find_end_keyword(lines, i)
                declarations.append({
                    "name": name,
                    "type": "method",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public" if not name.startswith("_") else "private",
                    "signature": line.strip(),
                    "language": "ruby"
                })

        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            match = self.REQUIRE_RE.search(line)
            if match:
                dependencies.append({
                    "type": "require",
                    "target": match.group(1),
                    "line": i + 1
                })
        return dependencies

    def detect_smells(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        declarations = self.extract_declarations(content, extension)
        dependencies = self.extract_dependencies(content, extension)
        return SmellEngine.detect(file_path, content, extension, size_metrics, complexity_metrics, declarations, dependencies)

# Register analyzer
AnalyzerRegistry.register(RubyAnalyzer())
