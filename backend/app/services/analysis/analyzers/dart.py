import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import BraceLanguageAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class DartAnalyzer(BraceLanguageAnalyzer):
    # Regex patterns for Dart declarations
    CLASS_RE = re.compile(r"\bclass\s+(\w+)\b")
    MIXIN_RE = re.compile(r"\bmixin\s+(\w+)\b")
    FUNC_RE = re.compile(r"\b(?:[\w<>]+)?\s*(\w+)\s*\(([^)]*)\)\s*\{")
    IMPORT_RE = re.compile(r"^\s*import\s+['\"]([^'\"]+)['\"]")

    def supported_extensions(self) -> Set[str]:
        return {".dart"}

    def analyze_size(self, content: str, extension: str) -> Dict[str, Any]:
        lines = content.split("\n")
        total_lines = len(lines)
        
        stripped = self.strip_comments(content)
        stripped_lines = stripped.split("\n")
        
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = max(0, total_lines - blank_lines - sum(1 for line in stripped_lines if line.strip()))
        code_lines = total_lines - blank_lines - comment_lines

        functions = []
        classes = []
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Class
            class_match = self.CLASS_RE.search(line)
            if class_match:
                end_line = self.find_brace_end(lines, i)
                classes.append({
                    "name": class_match.group(1),
                    "line": line_num,
                    "loc": end_line - i
                })
                continue

            # Func
            func_match = self.FUNC_RE.search(line)
            if func_match:
                name = func_match.group(1)
                if name not in ("if", "for", "while", "switch", "catch"):
                    end_line = self.find_brace_end(lines, i)
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

    def analyze_complexity(self, content: str, extension: str) -> Dict[str, Any]:
        declarations = self.extract_declarations(content, extension)
        return ComplexityEngine.calculate(content, extension, declarations)

    def extract_declarations(self, content: str, extension: str) -> List[Dict[str, Any]]:
        declarations = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Class
            class_match = self.CLASS_RE.search(line)
            if class_match:
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": class_match.group(1),
                    "type": "class",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "private" if class_match.group(1).startswith("_") else "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "dart"
                })
                continue

            # Mixin
            mixin_match = self.MIXIN_RE.search(line)
            if mixin_match:
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": mixin_match.group(1),
                    "type": "mixin",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "dart"
                })
                continue

            # Func
            func_match = self.FUNC_RE.search(line)
            if func_match:
                name = func_match.group(1)
                if name not in ("if", "for", "while", "switch", "catch"):
                    end_line = self.find_brace_end(lines, i)
                    declarations.append({
                        "name": name,
                        "type": "function",
                        "line": line_num,
                        "end_line": end_line,
                        "parent": None,
                        "visibility": "private" if name.startswith("_") else "public",
                        "signature": line.strip().rstrip("{").strip(),
                        "language": "dart"
                    })

        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            match = self.IMPORT_RE.search(line)
            if match:
                dependencies.append({
                    "type": "import",
                    "target": match.group(1),
                    "line": i + 1
                })
        return dependencies

    def detect_smells(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        declarations = self.extract_declarations(content, extension)
        dependencies = self.extract_dependencies(content, extension)
        return SmellEngine.detect(file_path, content, extension, size_metrics, complexity_metrics, declarations, dependencies)

# Register analyzer
AnalyzerRegistry.register(DartAnalyzer())
