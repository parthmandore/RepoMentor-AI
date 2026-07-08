import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import JVMLanguageAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class CSharpAnalyzer(JVMLanguageAnalyzer):
    # Regex patterns for C# declarations
    CLASS_RE = re.compile(r"\bclass\s+(\w+)\b")
    INTERFACE_RE = re.compile(r"\binterface\s+(\w+)\b")
    ENUM_RE = re.compile(r"\benum\s+(\w+)\b")
    NAMESPACE_RE = re.compile(r"\bnamespace\s+([\w.]+)")
    
    # Matches C# methods: e.g. public void MyMethod(int a) {
    METHOD_RE = re.compile(
        r"\b(?:public|protected|private|internal|static|virtual|override|async|final)*\s*"
        r"(?:[\w<>\[\]]+\s+)?(\w+)\s*\(([^)]*)\)\s*\{"
    )
    
    USING_RE = re.compile(r"^\s*using\s+([\w.]+)\s*;")

    def supported_extensions(self) -> Set[str]:
        return {".cs"}

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

            method_match = self.METHOD_RE.search(line)
            if method_match:
                name = method_match.group(1)
                if name not in ("if", "for", "while", "switch", "catch", "using"):
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
            
            # Namespace
            ns_match = self.NAMESPACE_RE.search(line)
            if ns_match:
                declarations.append({
                    "name": ns_match.group(1),
                    "type": "namespace",
                    "line": line_num,
                    "end_line": line_num,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip(),
                    "language": "csharp"
                })
                continue

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
                    "visibility": "public" if "public" in line else "internal",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "csharp"
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
                    "visibility": "public" if "public" in line else "internal",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "csharp"
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
                    "visibility": "public" if "public" in line else "internal",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "csharp"
                })
                continue

            # Method
            method_match = self.METHOD_RE.search(line)
            if method_match:
                name = method_match.group(1)
                if name not in ("if", "for", "while", "switch", "catch", "using"):
                    end_line = self.find_brace_end(lines, i)
                    visibility = "internal"
                    if "public" in line:
                        visibility = "public"
                    elif "private" in line:
                        visibility = "private"
                    elif "protected" in line:
                        visibility = "protected"

                    declarations.append({
                        "name": name,
                        "type": "method",
                        "line": line_num,
                        "end_line": end_line,
                        "parent": None,
                        "visibility": visibility,
                        "signature": line.strip().rstrip("{").strip(),
                        "language": "csharp"
                    })

        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            match = self.USING_RE.search(line)
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
AnalyzerRegistry.register(CSharpAnalyzer())
