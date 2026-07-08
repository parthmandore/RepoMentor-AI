import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import JavaScriptFamilyAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class TypeScriptAnalyzer(JavaScriptFamilyAnalyzer):
    FUNC_RE = re.compile(
        r"(?:"
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)"
        r"|(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>"
        r"|(\w+)\s*\([^)]*\)\s*.*?\s*\{"
        r")"
    )
    CLASS_RE = re.compile(r"(?:export\s+)?(?:default\s+)?class\s+(\w+)")
    INTERFACE_RE = re.compile(r"(?:export\s+)?interface\s+(\w+)")
    ENUM_RE = re.compile(r"(?:export\s+)?enum\s+(\w+)")
    IMPORT_RE = re.compile(
        r"(?:import|export)\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
        r"|import\s+['\"]([^'\"]+)['\"]"
        r"|require\(\s*['\"]([^'\"]+)['\"]\s*\)"
    )

    def supported_extensions(self) -> Set[str]:
        return {".ts", ".tsx"}

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
            class_match = self.CLASS_RE.search(line)
            if class_match:
                end_line = self.find_brace_end(lines, i)
                classes.append({
                    "name": class_match.group(1),
                    "line": line_num,
                    "loc": end_line - i
                })
                continue

            func_match = self.FUNC_RE.search(line)
            if func_match:
                name = next((g for g in func_match.groups() if g), "anonymous")
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
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "typescript"
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
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "typescript"
                })
                continue

            # Enum
            enum_match = self.ENUM_RE.search(line)
            if enum_match:
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": enum_match.group(1),
                    "type": "enum",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "typescript"
                })
                continue

            # Function
            func_match = self.FUNC_RE.search(line)
            if func_match:
                name = next((g for g in func_match.groups() if g), "anonymous")
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": name,
                    "type": "function",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "typescript"
                })

        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            for match in self.IMPORT_RE.finditer(line):
                target = next((g for g in match.groups() if g), "")
                if target:
                    dependencies.append({
                        "type": "import",
                        "target": target,
                        "line": i + 1
                    })
        return dependencies

    def detect_smells(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        declarations = self.extract_declarations(content, extension)
        dependencies = self.extract_dependencies(content, extension)
        return SmellEngine.detect(file_path, content, extension, size_metrics, complexity_metrics, declarations, dependencies)

# Register analyzer
AnalyzerRegistry.register(TypeScriptAnalyzer())
