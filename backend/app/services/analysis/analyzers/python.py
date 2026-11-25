import ast
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import BaseAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class PythonAnalyzer(BaseAnalyzer):
    def supported_extensions(self) -> Set[str]:
        return {".py"}

    def analyze_full(self, file_path: str, content: str, extension: str) -> Dict[str, Any]:
        lines = content.split("\n")
        total_lines = len(lines)
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        code_lines = max(0, total_lines - blank_lines - comment_lines)

        functions = []
        classes = []
        declarations = []
        dependencies = []
        complexity_functions = []

        try:
            tree = ast.parse(content)
            # 1. Walk tree for declarations, functions, classes, complexity
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end_lineno = getattr(node, "end_lineno", node.lineno)
                    loc = end_lineno - node.lineno + 1
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "loc": loc
                    })
                    args = [arg.arg for arg in node.args.args]
                    signature = f"def {node.name}({', '.join(args)})"
                    visibility = "private" if node.name.startswith("_") else "public"
                    declarations.append({
                        "name": node.name,
                        "type": "function",
                        "line": node.lineno,
                        "end_line": end_lineno,
                        "parent": None,
                        "visibility": visibility,
                        "signature": signature,
                        "language": "python"
                    })

                    # Calculate complexity from child nodes
                    complexity = 1
                    decisions = 0
                    loops = 0
                    exceptions = 0
                    branches = 0
                    for child in ast.walk(node):
                        if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler, ast.With, ast.Assert)):
                            complexity += 1
                            decisions += 1
                            if isinstance(child, (ast.For, ast.While)):
                                loops += 1
                            elif isinstance(child, ast.ExceptHandler):
                                exceptions += 1
                            elif isinstance(child, ast.If):
                                branches += 1
                        elif isinstance(child, ast.BoolOp):
                            complexity += len(child.values) - 1
                            decisions += len(child.values) - 1

                    complexity_functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "complexity": complexity,
                        "loc": loc,
                        "metrics": {
                            "nesting": 0,
                            "decisions": decisions,
                            "loops": loops,
                            "exceptions": exceptions,
                            "branches": branches
                        }
                    })

                elif isinstance(node, ast.ClassDef):
                    end_lineno = getattr(node, "end_lineno", node.lineno)
                    method_count = sum(
                        1 for child in ast.iter_child_nodes(node)
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "method_count": method_count,
                        "loc": end_lineno - node.lineno + 1
                    })
                    bases = [getattr(b, "id", "") for b in node.bases]
                    bases = [b for b in bases if b]
                    signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
                    declarations.append({
                        "name": node.name,
                        "type": "class",
                        "line": node.lineno,
                        "end_line": end_lineno,
                        "parent": None,
                        "visibility": "public",
                        "signature": signature,
                        "language": "python"
                    })

                elif isinstance(node, ast.Import):
                    for name in node.names:
                        dependencies.append({
                            "type": "import",
                            "target": name.name,
                            "line": getattr(node, "lineno", 1)
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    dependencies.append({
                        "type": "from_import",
                        "target": module,
                        "line": getattr(node, "lineno", 1)
                    })
        except SyntaxError:
            pass

        size_result = {
            "total_lines": total_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "code_lines": code_lines,
            "functions": functions,
            "classes": classes
        }

        file_complexity = sum(f["complexity"] for f in complexity_functions) or 1
        max_complexity = max((f["complexity"] for f in complexity_functions), default=1)
        avg_complexity = round(file_complexity / len(complexity_functions), 2) if complexity_functions else 1.0

        complexity_result = {
            "file_complexity": file_complexity,
            "functions": complexity_functions,
            "average_complexity": avg_complexity,
            "max_complexity": max_complexity
        }

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
        blank_lines = sum(1 for line in lines if not line.strip())
        comment_lines = sum(1 for line in lines if line.strip().startswith("#"))
        code_lines = total_lines - blank_lines - comment_lines

        # Extract function/class bounds using AST
        functions = []
        classes = []
        try:
            tree = ast.parse(content)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    end_lineno = getattr(node, "end_lineno", node.lineno)
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "loc": end_lineno - node.lineno + 1
                    })
                elif isinstance(node, ast.ClassDef):
                    end_lineno = getattr(node, "end_lineno", node.lineno)
                    method_count = sum(
                        1 for child in ast.iter_child_nodes(node)
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                    )
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "method_count": method_count,
                        "loc": end_lineno - node.lineno + 1
                    })
        except SyntaxError:
            pass

        return {
            "total_lines": total_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "code_lines": code_lines,
            "functions": functions,
            "classes": classes
        }

    def analyze_complexity(self, content: str, extension: str) -> Dict[str, Any]:
        return ComplexityEngine.calculate(content, extension, [])

    def extract_declarations(self, content: str, extension: str) -> List[Dict[str, Any]]:
        declarations = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    parent = None
                    # Find enclosing class if any
                    # Best-effort parent check
                    visibility = "private" if node.name.startswith("_") else "public"
                    
                    # Compute signature
                    args = [arg.arg for arg in node.args.args]
                    signature = f"def {node.name}({', '.join(args)})"

                    declarations.append({
                        "name": node.name,
                        "type": "function" if not parent else "method",
                        "line": node.lineno,
                        "end_line": getattr(node, "end_lineno", node.lineno),
                        "parent": parent,
                        "visibility": visibility,
                        "signature": signature,
                        "language": "python"
                    })
                elif isinstance(node, ast.ClassDef):
                    bases = [getattr(b, "id", "") for b in node.bases]
                    bases = [b for b in bases if b]
                    signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"

                    declarations.append({
                        "name": node.name,
                        "type": "class",
                        "line": node.lineno,
                        "end_line": getattr(node, "end_lineno", node.lineno),
                        "parent": None,
                        "visibility": "public",
                        "signature": signature,
                        "language": "python"
                    })
        except SyntaxError:
            pass
        return declarations

    def extract_dependencies(self, content: str, extension: str) -> List[Dict[str, Any]]:
        dependencies = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        dependencies.append({
                            "type": "import",
                            "target": name.name,
                            "line": node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append({
                            "type": "import",
                            "target": node.module,
                            "line": node.lineno
                        })
        except SyntaxError:
            pass
        return dependencies

    def detect_smells(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        declarations = self.extract_declarations(content, extension)
        dependencies = self.extract_dependencies(content, extension)
        return SmellEngine.detect(file_path, content, extension, size_metrics, complexity_metrics, declarations, dependencies)

# Register analyzer
AnalyzerRegistry.register(PythonAnalyzer())
