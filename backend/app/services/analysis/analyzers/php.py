import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import BraceLanguageAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class PHPAnalyzer(BraceLanguageAnalyzer):
    # Regex patterns for PHP declarations
    CLASS_RE = re.compile(r"\bclass\s+(\w+)\b")
    INTERFACE_RE = re.compile(r"\binterface\s+(\w+)\b")
    TRAIT_RE = re.compile(r"\btrait\s+(\w+)\b")
    FUNC_RE = re.compile(r"\bfunction\s+(\w+)\s*\(([^)]*)\)")
    
    # Matches requires, includes, namespaces, uses
    DEP_RE = re.compile(
        r"\b(?:require|require_once|include|include_once)\s*\(?\s*['\"]([^'\"]+)['\"]"
        r"|^\s*use\s+([\w\\]+)"
        r"|^\s*namespace\s+([\w\\]+)"
    )

    def supported_extensions(self) -> Set[str]:
        return {".php"}

    def strip_php_comments(self, content: str) -> str:
        # Strip standard C-style
        content = self.strip_comments(content)
        # Strip shell-style # comments
        lines = []
        for line in content.split("\n"):
            line = re.sub(r'#.*$', '', line)
            lines.append(line)
        return "\n".join(lines)

    def analyze_size(self, content: str, extension: str) -> Dict[str, Any]:
        lines = content.split("\n")
        total_lines = len(lines)
        
        stripped = self.strip_php_comments(content)
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

            # Function
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
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "php"
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
                    "language": "php"
                })
                continue

            # Trait
            trait_match = self.TRAIT_RE.search(line)
            if trait_match:
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": trait_match.group(1),
                    "type": "trait",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "php"
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
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "php"
                })

        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            line_num = i + 1
            for match in self.DEP_RE.finditer(line):
                # Group 1 = file requirement, Group 2 = use namespace, Group 3 = namespace declaration
                target = next((g for g in match.groups() if g), "")
                if target:
                    dependencies.append({
                        "type": "import" if "use" in line else ("package" if "namespace" in line else "require"),
                        "target": target,
                        "line": line_num
                    })
        return dependencies

    def detect_smells(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        declarations = self.extract_declarations(content, extension)
        dependencies = self.extract_dependencies(content, extension)
        return SmellEngine.detect(file_path, content, extension, size_metrics, complexity_metrics, declarations, dependencies)

# Register analyzer
AnalyzerRegistry.register(PHPAnalyzer())
