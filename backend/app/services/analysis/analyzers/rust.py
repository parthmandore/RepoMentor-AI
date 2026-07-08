import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import BraceLanguageAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class RustAnalyzer(BraceLanguageAnalyzer):
    # Regex patterns for Rust declarations
    STRUCT_RE = re.compile(r"\bstruct\s+(\w+)\b")
    ENUM_RE = re.compile(r"\benum\s+(\w+)\b")
    TRAIT_RE = re.compile(r"\btrait\s+(\w+)\b")
    IMPL_RE = re.compile(r"\bimpl\s+(?:[\w<>]+)?\s*(\w+)\b")
    FUNC_RE = re.compile(r"\bfn\s+(\w+)\s*\(([^)]*)\)")
    USE_RE = re.compile(r"^\s*use\s+([\w:]+)(?:\s*;|\s*\{)")

    def supported_extensions(self) -> Set[str]:
        return {".rs"}

    def analyze_size(self, content: str, extension: str) -> Dict[str, Any]:
        lines = content.split("\n")
        total_lines = len(lines)
        
        stripped = self.strip_comments(content)
        stripped_lines = stripped.split("\n")
        
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = max(0, total_lines - blank_lines - sum(1 for line in stripped_lines if line.strip()))
        code_lines = total_lines - blank_lines - comment_lines

        functions = []
        classes = []  # structs/enums
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Struct or Enum
            struct_match = self.STRUCT_RE.search(line) or self.ENUM_RE.search(line)
            if struct_match:
                end_line = self.find_brace_end(lines, i)
                classes.append({
                    "name": struct_match.group(1),
                    "line": line_num,
                    "loc": end_line - i
                })
                continue

            # Fn
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
                    "visibility": "public" if "pub" in line else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "rust"
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
                    "visibility": "public" if "pub" in line else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "rust"
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
                    "visibility": "public" if "pub" in line else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "rust"
                })
                continue

            # Impl
            impl_match = self.IMPL_RE.search(line)
            if impl_match:
                end_line = self.find_brace_end(lines, i)
                declarations.append({
                    "name": impl_match.group(1),
                    "type": "impl",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "rust"
                })
                continue

            # Fn
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
                    "visibility": "public" if "pub" in line else "private",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "rust"
                })

        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            match = self.USE_RE.search(line)
            if match:
                dependencies.append({
                    "type": "use",
                    "target": match.group(1),
                    "line": i + 1
                })
        return dependencies

    def detect_smells(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        declarations = self.extract_declarations(content, extension)
        dependencies = self.extract_dependencies(content, extension)
        return SmellEngine.detect(file_path, content, extension, size_metrics, complexity_metrics, declarations, dependencies)

# Register analyzer
AnalyzerRegistry.register(RustAnalyzer())
