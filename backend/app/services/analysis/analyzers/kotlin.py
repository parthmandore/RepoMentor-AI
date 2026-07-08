import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import JVMLanguageAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class KotlinAnalyzer(JVMLanguageAnalyzer):
    # Regex patterns for Kotlin declarations
    CLASS_RE = re.compile(r"\b(?:open|data|sealed|enum|inner)*\s*class\s+(\w+)\b")
    INTERFACE_RE = re.compile(r"\binterface\s+(\w+)\b")
    OBJECT_RE = re.compile(r"\b(?:companion\s+)?object\s+(\w+)?\b")
    FUNC_RE = re.compile(r"\bfun\s+(?:[\w<>.]+)?\s*(\w+)\s*\(([^)]*)\)")
    IMPORT_RE = re.compile(r"^\s*import\s+([\w.*]+)")
    PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)")

    def supported_extensions(self) -> Set[str]:
        return {".kt", ".kts"}

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

            # Fun
            func_match = self.FUNC_RE.search(line)
            if func_match:
                name = func_match.group(1)
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
                    "visibility": "public" if "private" not in line else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "kotlin"
                })
                continue

            # Interface
            int_match = self.INTERFACE_RE.search(line)
            if int_match:
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": int_match.group(1),
                    "type": "interface",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public" if "private" not in line else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "kotlin"
                })
                continue

            # Object
            obj_match = self.OBJECT_RE.search(line)
            if obj_match:
                name = obj_match.group(1) or "companion"
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": name,
                    "type": "object",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public" if "private" not in line else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "kotlin"
                })
                continue

            # Fun
            func_match = self.FUNC_RE.search(line)
            if func_match:
                name = func_match.group(1)
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": name,
                    "type": "function",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public" if "private" not in line else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "kotlin"
                })

        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Package declaration
            pkg_match = self.PACKAGE_RE.search(line)
            if pkg_match:
                dependencies.append({
                    "type": "package",
                    "target": pkg_match.group(1),
                    "line": line_num
                })
                continue

            # Import declaration
            imp_match = self.IMPORT_RE.search(line)
            if imp_match:
                dependencies.append({
                    "type": "import",
                    "target": imp_match.group(1),
                    "line": line_num
                })
        return dependencies

    def detect_smells(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        declarations = self.extract_declarations(content, extension)
        dependencies = self.extract_dependencies(content, extension)
        return SmellEngine.detect(file_path, content, extension, size_metrics, complexity_metrics, declarations, dependencies)

# Register analyzer
AnalyzerRegistry.register(KotlinAnalyzer())
