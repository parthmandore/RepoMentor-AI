import re
import ast
from typing import Any, Dict, List, Optional

class ComplexityEngine:
    # Regex patterns for branch detection in brace languages
    BRACE_PATTERNS = {
        "if": re.compile(r"\bif\s*\("),
        "else_if": re.compile(r"\belse\s+if\s*\("),
        "for": re.compile(r"\bfor\s*\(|\bforeach\s*\("),
        "while": re.compile(r"\bwhile\s*\("),
        "catch": re.compile(r"\bcatch\s*\("),
        "case": re.compile(r"\bcase\s+"),
        "logical_and": re.compile(r"&&"),
        "logical_or": re.compile(r"\|\|"),
        "ternary": re.compile(r"[^?]\?[^?.:]"),
        "switch": re.compile(r"\bswitch\s*\("),
        "throw": re.compile(r"\bthrow\b|\braise\b"),
    }

    # Python AST complexity mapping
    @classmethod
    def calculate_python_complexity(cls, content: str) -> Dict[str, Any]:
        """Calculates complexity using AST parsing for Python files."""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return {"file_complexity": 1, "functions": [], "average_complexity": 1.0, "max_complexity": 1}

        functions = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                complexity = 1
                nesting = 0
                decisions = 0
                loops = 0
                exceptions = 0
                branches = 0

                # Trace children for complexity
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

                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "complexity": complexity,
                    "loc": getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                    "metrics": {
                        "nesting": nesting,
                        "decisions": decisions,
                        "loops": loops,
                        "exceptions": exceptions,
                        "branches": branches
                    }
                })

        file_complexity = sum(f["complexity"] for f in functions) or 1
        max_complexity = max((f["complexity"] for f in functions), default=1)
        avg_complexity = round(file_complexity / len(functions), 2) if functions else 1.0

        return {
            "file_complexity": file_complexity,
            "functions": functions,
            "average_complexity": avg_complexity,
            "max_complexity": max_complexity
        }

    @classmethod
    def calculate_brace_complexity(cls, content: str, declarations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculates complexity using regex pattern matching for brace-based languages."""
        lines = content.split("\n")
        functions = []
        
        # Filter declarations to functions/methods/constructors
        func_declarations = [
            d for d in declarations 
            if d.get("type") in ("function", "method", "constructor")
        ]

        for func in func_declarations:
            start_line = func.get("line", 1)
            end_line = func.get("end_line", len(lines))
            func_lines = lines[start_line - 1 : end_line]
            func_text = "\n".join(func_lines)

            # Count decisions/branches
            decisions = 0
            loops = 0
            exceptions = 0
            branches = 0
            switches = 0

            # Count branch points
            branch_points = 0
            for name, pattern in cls.BRACE_PATTERNS.items():
                matches = len(pattern.findall(func_text))
                if name in ("if", "else_if"):
                    branches += matches
                    decisions += matches
                elif name in ("for", "while"):
                    loops += matches
                    decisions += matches
                elif name == "catch":
                    exceptions += matches
                    decisions += matches
                elif name == "case":
                    branch_points += matches
                elif name in ("logical_and", "logical_or", "ternary"):
                    decisions += matches
                elif name == "switch":
                    switches += matches

            complexity = 1 + decisions + branch_points

            # Maximum Nesting calculation using braces count
            nesting = 0
            current_nesting = 0
            for line in func_lines:
                for char in line:
                    if char == "{":
                        current_nesting += 1
                        nesting = max(nesting, current_nesting)
                    elif char == "}":
                        current_nesting = max(0, current_nesting - 1)

            functions.append({
                "name": func.get("name", "anonymous"),
                "line": start_line,
                "complexity": complexity,
                "loc": end_line - start_line + 1,
                "metrics": {
                    "nesting": nesting,
                    "decisions": decisions + branch_points,
                    "loops": loops,
                    "exceptions": exceptions,
                    "branches": branches,
                    "switches": switches
                }
            })

        file_complexity = sum(f["complexity"] for f in functions) or 1
        max_complexity = max((f["complexity"] for f in functions), default=1)
        avg_complexity = round(file_complexity / len(functions), 2) if functions else 1.0

        return {
            "file_complexity": file_complexity,
            "functions": functions,
            "average_complexity": avg_complexity,
            "max_complexity": max_complexity
        }

    @classmethod
    def calculate(cls, content: str, extension: str, declarations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Entry point for complexity calculations across all supported languages."""
        if extension == ".py":
            return cls.calculate_python_complexity(content)
        else:
            return cls.calculate_brace_complexity(content, declarations)
