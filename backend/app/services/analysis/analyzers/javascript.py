import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import JavaScriptFamilyAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class JavaScriptAnalyzer(JavaScriptFamilyAnalyzer):
    FUNC_RE = re.compile(
        r"(?:"
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)"
        r"|(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>"
        r"|(\w+)\s*\([^)]*\)\s*\{"
        r")"
    )
    CLASS_RE = re.compile(r"(?:export\s+)?(?:default\s+)?class\s+(\w+)")
    IMPORT_RE = re.compile(
        r"(?:import|export)\s+.*?\s+from\s+['\"]([^'\"]+)['\"]"
        r"|import\s+['\"]([^'\"]+)['\"]"
        r"|require\(\s*['\"]([^'\"]+)['\"]\s*\)"
    )

    def supported_extensions(self) -> Set[str]:
        return {".js", ".jsx"}

    def analyze_full(self, file_path: str, content: str, extension: str) -> Dict[str, Any]:
        lines = content.split("\n")
        total_lines = len(lines)

        blank_lines = 0
        comment_lines = 0
        in_block_comment = False
        declarations = []
        dependencies = []

        opens = [l.count("{") for l in lines]
        closes = [l.count("}") for l in lines]
        brace_stack = []
        line_end_map = {}
        for i, (op, cl) in enumerate(zip(opens, closes)):
            for _ in range(op):
                brace_stack.append(i)
            for _ in range(cl):
                if brace_stack:
                    op_i = brace_stack.pop()
                    line_end_map[op_i] = i + 1

        def fast_brace_end(start_index: int) -> int:
            for j in range(start_index, total_lines):
                if j in line_end_map:
                    return line_end_map[j]
                if opens[j] > 0:
                    brace_count = 0
                    found_open = False
                    for k in range(j, total_lines):
                        brace_count += opens[k] - closes[k]
                        if opens[k] > 0:
                            found_open = True
                        if found_open and brace_count <= 0:
                            return k + 1
            return total_lines

        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
                continue

            if in_block_comment:
                comment_lines += 1
                if "*/" in stripped:
                    in_block_comment = False
                continue
            else:
                if stripped.startswith("/*"):
                    comment_lines += 1
                    if "*/" not in stripped[2:]:
                        in_block_comment = True
                    continue
                elif stripped.startswith("//"):
                    comment_lines += 1
                    continue

            for match in self.IMPORT_RE.finditer(line):
                target = next((g for g in match.groups() if g), "")
                if target:
                    dependencies.append({
                        "type": "import",
                        "target": target,
                        "line": line_num
                    })

            class_match = self.CLASS_RE.search(line)
            if class_match:
                end_line = fast_brace_end(i)
                declarations.append({
                    "name": class_match.group(1),
                    "type": "class",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "javascript"
                })
                continue

            func_match = self.FUNC_RE.search(line)
            if func_match:
                name = next((g for g in func_match.groups() if g), "anonymous")
                end_line = fast_brace_end(i)
                declarations.append({
                    "name": name,
                    "type": "function",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": None,
                    "visibility": "public",
                    "signature": line.strip().rstrip("{").strip(),
                    "language": "javascript"
                })

        code_lines = max(0, total_lines - blank_lines - comment_lines)
        functions = [
            {"name": d["name"], "line": d["line"], "loc": d["end_line"] - d["line"] + 1}
            for d in declarations if d["type"] == "function"
        ]
        classes = [
            {"name": d["name"], "line": d["line"], "loc": d["end_line"] - d["line"] + 1}
            for d in declarations if d["type"] == "class"
        ]

        size_result = {
            "total_lines": total_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "code_lines": code_lines,
            "functions": functions,
            "classes": classes
        }

        complexity_result = ComplexityEngine.calculate_brace_complexity(content, declarations)
        smells = SmellEngine.detect(
            file_path, content, extension, size_result, complexity_result, declarations, dependencies
        )

        return {
            "size_result": size_result,
            "declarations": declarations,
            "dependencies": dependencies,
            "complexity_result": complexity_result,
            "smells": smells
        }

    def analyze_size(self, content: str, extension: str) -> Dict[str, Any]:
        lines = content.split("\n")
        total_lines = len(lines)
        
        # Strip comments to count blank and comment lines
        stripped = self.strip_comments(content)
        stripped_lines = stripped.split("\n")
        
        # Calculate sizes
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = max(0, total_lines - blank_lines - sum(1 for line in stripped_lines if line.strip()))
        code_lines = total_lines - blank_lines - comment_lines

        # Extract functions and classes
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
                    "language": "javascript"
                })
                continue

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
                    "language": "javascript"
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
AnalyzerRegistry.register(JavaScriptAnalyzer())
