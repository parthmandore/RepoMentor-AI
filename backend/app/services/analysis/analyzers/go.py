import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import BraceLanguageAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class GoAnalyzer(BraceLanguageAnalyzer):
    # Regex patterns for Go declarations
    STRUCT_RE = re.compile(r"\btype\s+(\w+)\s+struct\b")
    INTERFACE_RE = re.compile(r"\btype\s+(\w+)\s+interface\b")
    FUNC_RE = re.compile(r"\bfunc\s+(\w+)\s*\(([^)]*)\)")
    METHOD_RE = re.compile(r"\bfunc\s*\(([^)]+)\)\s*(\w+)\s*\(([^)]*)\)")
    IMPORT_RE = re.compile(r'^\s*(?:import\s+)?["\']([^"\']+)["\']')

    def supported_extensions(self) -> Set[str]:
        return {".go"}

    def analyze_size(self, content: str, extension: str) -> Dict[str, Any]:
        lines = content.split("\n")
        total_lines = len(lines)
        
        stripped = self.strip_comments(content)
        stripped_lines = stripped.split("\n")
        
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = max(0, total_lines - blank_lines - sum(1 for line in stripped_lines if line.strip()))
        code_lines = total_lines - blank_lines - comment_lines

        functions = []
        classes = []  # structs
        for i, line in enumerate(lines):
            line_num = i + 1
            struct_match = self.STRUCT_RE.search(line)
            if struct_match:
                end_line = self.find_brace_end(lines, i)
                classes.append({
                    "name": struct_match.group(1),
                    "line": line_num,
                    "loc": end_line - i
                })
                continue

            method_match = self.METHOD_RE.search(line)
            if method_match:
                name = method_match.group(2)
                end_line = self.find_brace_end(lines, i)
                functions.append({
                    "name": name,
                    "line": line_num,
                    "loc": end_line - i
                })
                continue

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
            
            # Struct
            struct_match = self.STRUCT_RE.search(line)
            if struct_match:
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": struct_match.group(1),
                    "type": "struct",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public" if struct_match.group(1)[0].isupper() else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "go"
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
                    "visibility": "public" if int_match.group(1)[0].isupper() else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "go"
                })
                continue

            # Method
            method_match = self.METHOD_RE.search(line)
            if method_match:
                name = method_match.group(2)
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": name,
                    "type": "method",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": method_match.group(1),
                    "visibility": "public" if name[0].isupper() else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "go"
                })
                continue

            # Function
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
                    "visibility": "public" if name[0].isupper() else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "go"
                })

        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        # Find imports inside Go source
        lines = content.split("\n")
        in_import_block = False
        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()
            if stripped.startswith("import ("):
                in_import_block = True
                continue
            elif in_import_block and stripped == ")":
                in_import_block = False
                continue
            
            if in_import_block:
                match = re.search(r'"([^"]+)"', stripped)
                if match:
                    dependencies.append({
                        "type": "import",
                        "target": match.group(1),
                        "line": line_num
                    })
            else:
                # Single line import: import "fmt"
                match = re.search(r'import\s+"([^"]+)"', stripped)
                if match:
                    dependencies.append({
                        "type": "import",
                        "target": match.group(1),
                        "line": line_num
                    })
        return dependencies

    def detect_smells(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        declarations = self.extract_declarations(content, extension)
        dependencies = self.extract_dependencies(content, extension)
        return SmellEngine.detect(file_path, content, extension, size_metrics, complexity_metrics, declarations, dependencies)

# Register analyzer
AnalyzerRegistry.register(GoAnalyzer())
