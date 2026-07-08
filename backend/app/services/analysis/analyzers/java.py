import re
from typing import Any, Dict, List, Set
from app.services.analysis.analyzers.base import JVMLanguageAnalyzer
from app.services.analysis.complexity_engine import ComplexityEngine
from app.services.analysis.smells.detectors import SmellEngine
from app.services.analysis.analyzers.registry import AnalyzerRegistry

class JavaAnalyzer(JVMLanguageAnalyzer):
    # Regex patterns for Java declarations
    CLASS_RE = re.compile(r"\b(?:public|protected|private|static|final|abstract)*\s*class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w\s,]+)?\s*\{")
    INTERFACE_RE = re.compile(r"\b(?:public|protected|private|static|abstract)*\s*interface\s+(\w+)\s*\{")
    ENUM_RE = re.compile(r"\b(?:public|protected|private|static)*\s*enum\s+(\w+)\s*\{")
    
    # Matches Java methods/constructors: e.g. public void myMethod(int a) {
    METHOD_RE = re.compile(
        r"\b(?:public|protected|private|static|final|synchronized|abstract|default)*\s*"
        r"(?:[\w<>\[\]]+\s+)?(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w\s,]+)?\s*\{"
    )
    
    IMPORT_RE = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;")
    PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;")

    def supported_extensions(self) -> Set[str]:
        return {".java"}

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
                method_count = 0
                # Approximate methods in class body
                for j in range(i + 1, end_line):
                    if self.METHOD_RE.search(lines[j]) and not self.CLASS_RE.search(lines[j]):
                        method_count += 1
                classes.append({
                    "name": class_match.group(1),
                    "line": line_num,
                    "method_count": method_count,
                    "loc": end_line - i
                })
                continue

            # Method check
            method_match = self.METHOD_RE.search(line)
            if method_match:
                name = method_match.group(1)
                # Skip control flows that look like method calls
                if name not in ("if", "for", "while", "switch", "catch", "synchronized"):
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

    RECORD_RE = re.compile(r"\b(?:public|protected|private|static|final)*\s*record\s+(\w+)\s*\(([^)]*)\)\s*\{")
    FIELD_RE = re.compile(r"\b(?:private|protected|public)\s+(?:final\s+)?(?:static\s+)?([\w<>\[\]]+)\s+(\w+)\s*(?:=\s*[^;]+)?\s*;")
    ANNOTATION_RE = re.compile(r"^\s*@(\w+)(?:\([^)]*\))?")

    def extract_declarations(self, content: str, extension: str) -> List[Dict[str, Any]]:
        declarations = []
        lines = content.split("\n")
        
        # Keep track of active class stack to associate parent and constructor names
        class_stack = []
        
        for i, line in enumerate(lines):
            line_num = i + 1
            line_stripped = line.strip()
            
            # 1. Annotations
            annot_match = self.ANNOTATION_RE.search(line)
            if annot_match:
                declarations.append({
                    "name": annot_match.group(1),
                    "type": "annotation",
                    "line": line_num,
                    "end_line": line_num,
                    "parent": class_stack[-1] if class_stack else None,
                    "visibility": "public",
                    "signature": line_stripped,
                    "language": "java"
                })
                continue

            # 2. Class
            class_match = self.CLASS_RE.search(line)
            if class_match:
                end_line = self.find_brace_end(lines, i)
                name = class_match.group(1)
                class_stack.append(name)
                declarations.append({
                    "name": name,
                    "type": "class",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": class_stack[-2] if len(class_stack) > 1 else None,
                    "visibility": "public" if "public" in line else "package",
                    "signature": line_stripped.rstrip("{").strip(),
                    "language": "java"
                })
                continue

            # 3. Interface
            int_match = self.INTERFACE_RE.search(line)
            if int_match:
                end_line = self.find_brace_end(lines, i)
                name = int_match.group(1)
                class_stack.append(name)
                declarations.append({
                    "name": name,
                    "type": "interface",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": class_stack[-2] if len(class_stack) > 1 else None,
                    "visibility": "public" if "public" in line else "package",
                    "signature": line_stripped.rstrip("{").strip(),
                    "language": "java"
                })
                continue

            # 4. Record
            record_match = self.RECORD_RE.search(line)
            if record_match:
                end_line = self.find_brace_end(lines, i)
                name = record_match.group(1)
                class_stack.append(name)
                declarations.append({
                    "name": name,
                    "type": "record",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": class_stack[-2] if len(class_stack) > 1 else None,
                    "visibility": "public" if "public" in line else "package",
                    "signature": line_stripped.rstrip("{").strip(),
                    "language": "java"
                })
                continue

            # 5. Enum
            enum_match = self.ENUM_RE.search(line)
            if enum_match:
                end_line = self.find_brace_end(lines, i)
                name = enum_match.group(1)
                class_stack.append(name)
                declarations.append({
                    "name": name,
                    "type": "enum",
                    "line": line_num,
                    "end_line": end_line,
                    "parent": class_stack[-2] if len(class_stack) > 1 else None,
                    "visibility": "public" if "public" in line else "package",
                    "signature": line_stripped.rstrip("{").strip(),
                    "language": "java"
                })
                continue

            # 6. Method/Constructor
            method_match = self.METHOD_RE.search(line)
            if method_match:
                name = method_match.group(1)
                if name not in ("if", "for", "while", "switch", "catch", "synchronized"):
                    end_line = self.find_brace_end(lines, i)
                    visibility = "package"
                    if "public" in line:
                        visibility = "public"
                    elif "protected" in line:
                        visibility = "protected"
                    elif "private" in line:
                        visibility = "private"

                    # Constructor check: name matches active class name
                    decl_type = "method"
                    if class_stack and name == class_stack[-1]:
                        decl_type = "constructor"

                    # Check generic types
                    generic_types = []
                    generic_match = re.search(r"<([^>]+)>", line)
                    if generic_match:
                        generic_types = [t.strip() for t in generic_match.group(1).split(",")]

                    declarations.append({
                        "name": name,
                        "type": decl_type,
                        "line": line_num,
                        "end_line": end_line,
                        "parent": class_stack[-1] if class_stack else None,
                        "visibility": visibility,
                        "signature": line_stripped.rstrip("{").strip(),
                        "generic_types": generic_types,
                        "language": "java"
                    })
                    continue

            # 7. Field
            field_match = self.FIELD_RE.search(line)
            if field_match:
                type_name = field_match.group(1)
                field_name = field_match.group(2)
                if type_name not in ("return", "throw", "else", "new"):
                    declarations.append({
                        "name": field_name,
                        "type": "field",
                        "line": line_num,
                        "end_line": line_num,
                        "parent": class_stack[-1] if class_stack else None,
                        "visibility": "private" if "private" in line else "public" if "public" in line else "protected" if "protected" in line else "package",
                        "signature": f"{type_name} {field_name}",
                        "language": "java"
                    })

            # Check if class/interface/enum brace ended
            if line_stripped == "}" and class_stack:
                class_stack.pop()

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
AnalyzerRegistry.register(JavaAnalyzer())
