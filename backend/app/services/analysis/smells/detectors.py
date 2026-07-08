import re
from typing import Any, Dict, List, Set
from app.services.analysis.smells.base import BaseSmellDetector
from app.services.analysis.thresholds import (
    LONG_METHOD_LOC,
    GOD_CLASS_LOC,
    GOD_CLASS_METHODS,
    LARGE_FILE_LOC,
    DEEP_NESTING_LEVEL,
    MAGIC_NUMBER_EXCEPTIONS,
)

# Constants not in thresholds
LONG_PARAMETER_LIST_THRESHOLD = 5
MAX_MATCH_ARMS = 8

class LongMethodDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        smells = []
        for func in size_metrics.get("functions", []):
            loc = func.get("loc", 0)
            if loc > LONG_METHOD_LOC:
                severity = "Medium" if loc < LONG_METHOD_LOC * 1.5 else "High"
                smells.append({
                    "smell_type": "Long Method",
                    "category": "Size",
                    "severity": severity,
                    "file_path": file_path,
                    "line_number": func.get("line"),
                    "measured_value": loc,
                    "threshold": LONG_METHOD_LOC,
                    "reason": f"Function '{func['name']}' has {loc} lines, exceeding the {LONG_METHOD_LOC}-line threshold."
                })
        return smells


class LargeFileDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        loc = size_metrics.get("code_lines", 0)
        if loc > LARGE_FILE_LOC:
            severity = "Medium" if loc < LARGE_FILE_LOC * 1.5 else "High"
            return [{
                "smell_type": "Large File",
                "category": "Size",
                "severity": severity,
                "file_path": file_path,
                "line_number": None,
                "measured_value": loc,
                "threshold": LARGE_FILE_LOC,
                "reason": f"File has {loc} lines, exceeding the {LARGE_FILE_LOC}-line threshold."
            }]
        return []


class DeepNestingDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        smells = []
        max_flagged_depth = 0
        
        # Calculate nesting from complexity metrics per function
        for func in complexity_metrics.get("functions", []):
            nesting = func.get("metrics", {}).get("nesting", 0)
            if nesting > DEEP_NESTING_LEVEL:
                severity = "Medium" if nesting <= DEEP_NESTING_LEVEL + 2 else "High"
                smells.append({
                    "smell_type": "Deep Nesting",
                    "category": "Complexity",
                    "severity": severity,
                    "file_path": file_path,
                    "line_number": func.get("line"),
                    "measured_value": nesting,
                    "threshold": DEEP_NESTING_LEVEL,
                    "reason": f"Nesting of {nesting} levels detected in '{func['name']}', exceeding threshold {DEEP_NESTING_LEVEL}."
                })
        return smells


class MagicNumbersDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension not in {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".h", ".cpp", ".hpp", ".cs", ".go", ".rs", ".kt", ".php"}:
            return []

        # Standalone numeric literals
        number_re = re.compile(r"(?<![.\w])(-?\d+\.?\d*)(?![.\w])")
        
        # Skip comments and imports
        skip_patterns = [
            re.compile(r"^\s*#"),
            re.compile(r"^\s*//"),
            re.compile(r"^\s*/?\*"),
            re.compile(r"^\s*import\s"),
            re.compile(r"^\s*from\s"),
            re.compile(r"^\s*(?:export\s+)?const\s+[A-Z_]+"),
            re.compile(r"^\s*public\s+static\s+final\s+[A-Z_]+"),
        ]

        smells = []
        for line_num, line in enumerate(content.split("\n"), start=1):
            stripped = line.strip()
            if not stripped or any(p.match(stripped) for p in skip_patterns):
                continue

            for match in number_re.finditer(stripped):
                try:
                    val = float(match.group(1))
                except ValueError:
                    continue
                
                int_val = int(val) if val == int(val) else None
                if int_val is not None and int_val in MAGIC_NUMBER_EXCEPTIONS:
                    continue
                if val in {float(v) for v in MAGIC_NUMBER_EXCEPTIONS}:
                    continue

                smells.append({
                    "smell_type": "Magic Number",
                    "category": "Readability",
                    "severity": "Low",
                    "file_path": file_path,
                    "line_number": line_num,
                    "measured_value": val,
                    "threshold": 0.0,
                    "reason": f"Numeric literal {match.group(1)} should be extracted into a named constant."
                })
                if len(smells) >= 15:
                    break
            if len(smells) >= 15:
                break
        return smells


class LargeClassDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        smells = []
        for cls in size_metrics.get("classes", []):
            loc = cls.get("loc", 0)
            if loc > GOD_CLASS_LOC:
                severity = "Medium" if loc < GOD_CLASS_LOC * 1.5 else "High"
                smells.append({
                    "smell_type": "Large Class",
                    "category": "Size",
                    "severity": severity,
                    "file_path": file_path,
                    "line_number": cls.get("line"),
                    "measured_value": loc,
                    "threshold": GOD_CLASS_LOC,
                    "reason": f"Class '{cls['name']}' has {loc} lines, exceeding the {GOD_CLASS_LOC}-line threshold."
                })
        return smells


class LongParameterListDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        smells = []
        for decl in declarations:
            if decl.get("type") in ("function", "method", "constructor"):
                signature = decl.get("signature", "")
                # Count parameters inside parentheses
                params_match = re.search(r"\((.*?)\)", signature)
                if params_match:
                    params_str = params_match.group(1).strip()
                    param_count = len([p for p in params_str.split(",") if p.strip()]) if params_str else 0
                    if param_count > LONG_PARAMETER_LIST_THRESHOLD:
                        smells.append({
                            "smell_type": "Long Parameter List",
                            "category": "Readability",
                            "severity": "Medium",
                            "file_path": file_path,
                            "line_number": decl.get("line"),
                            "measured_value": param_count,
                            "threshold": LONG_PARAMETER_LIST_THRESHOLD,
                            "reason": f"Function '{decl['name']}' has {param_count} parameters, exceeding the threshold of {LONG_PARAMETER_LIST_THRESHOLD}."
                        })
        return smells


class DeadCodeDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Find local private functions/methods that are defined but never referenced elsewhere in the file
        smells = []
        private_funcs = [d for d in declarations if d.get("type") in ("method", "function") and d.get("visibility") == "private"]
        for pf in private_funcs:
            name = pf["name"]
            # Look for appearances of the name in content, excluding its definition line
            occurrences = len(re.findall(rf"\b{re.escape(name)}\b", content))
            # 1 occurrence is the definition itself
            if occurrences <= 1:
                smells.append({
                    "smell_type": "Dead Code",
                    "category": "Maintainability",
                    "severity": "Medium",
                    "file_path": file_path,
                    "line_number": pf.get("line"),
                    "measured_value": occurrences,
                    "threshold": 2.0,
                    "reason": f"Private function '{name}' is defined but never called inside this file."
                })
        return smells


class DuplicateCodeDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Handled at repository level by duplication analysis
        return []


# --- Language Specific Detectors ---

class PythonMutableDefaultsDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension != ".py":
            return []
        smells = []
        # Matches: def name(..., arg=[] or arg={})
        mutable_re = re.compile(r"def\s+\w+\s*\(.*?\b\w+\s*=\s*(?:\[\]|\{\})\s*.*?\):")
        for line_num, line in enumerate(content.split("\n"), start=1):
            if mutable_re.search(line):
                smells.append({
                    "smell_type": "Mutable Defaults",
                    "category": "Correctness",
                    "severity": "Medium",
                    "file_path": file_path,
                    "line_number": line_num,
                    "measured_value": 1.0,
                    "threshold": 0.0,
                    "reason": "Function uses a mutable default argument ([] or {}), which can lead to unexpected state sharing."
                })
        return smells


class JSCallbackHellDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension not in (".js", ".jsx", ".ts", ".tsx"):
            return []
        smells = []
        # Pattern of nested callbacks: function(...) { ... function(...) { ... function(...) {
        callback_re = re.compile(r"\bfunction\b|\(\s*\)\s*=>")
        nested_count = 0
        for line_num, line in enumerate(content.split("\n"), start=1):
            if callback_re.search(line):
                nested_count += 1
                if nested_count >= 3:
                    smells.append({
                        "smell_type": "Callback Hell",
                        "category": "Readability",
                        "severity": "Medium",
                        "file_path": file_path,
                        "line_number": line_num,
                        "measured_value": nested_count,
                        "threshold": 3.0,
                        "reason": f"Callback nesting exceeds 3 levels at line {line_num}."
                    })
            if "}" in line or "});" in line:
                nested_count = max(0, nested_count - 1)
        return smells


class JSPromiseChainsDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension not in (".js", ".jsx", ".ts", ".tsx"):
            return []
        # Checks for long chain of .then() calls, e.g. 4+ in the file or sequential lines
        smells = []
        then_re = re.compile(r"\.then\s*\(")
        chain_len = 0
        for line_num, line in enumerate(content.split("\n"), start=1):
            if then_re.search(line):
                chain_len += 1
                if chain_len >= 4:
                    smells.append({
                        "smell_type": "Promise Chains",
                        "category": "Complexity",
                        "severity": "Medium",
                        "file_path": file_path,
                        "line_number": line_num,
                        "measured_value": chain_len,
                        "threshold": 4.0,
                        "reason": f"Long promise chain (.then) of length {chain_len} detected."
                    })
            elif ";" in line or "}" in line:
                chain_len = 0
        return smells


class JavaGodClassDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension != ".java":
            return []
        smells = []
        for cls in size_metrics.get("classes", []):
            method_count = cls.get("method_count", 0)
            loc = cls.get("loc", 0)
            if method_count > GOD_CLASS_METHODS and loc > GOD_CLASS_LOC:
                smells.append({
                    "smell_type": "God Class",
                    "category": "Design",
                    "severity": "High",
                    "file_path": file_path,
                    "line_number": cls.get("line"),
                    "measured_value": method_count,
                    "threshold": GOD_CLASS_METHODS,
                    "reason": f"Java Class '{cls['name']}' has {method_count} methods and {loc} LOC, exceeding God Class thresholds."
                })
        return smells


class JavaEmptyCatchDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension != ".java":
            return []
        smells = []
        # Matches: catch(...) { }
        empty_catch_re = re.compile(r"catch\s*\(\s*[\w<>\[\]\s]+\s+\w+\s*\)\s*\{\s*\}")
        for line_num, line in enumerate(content.split("\n"), start=1):
            if empty_catch_re.search(line):
                smells.append({
                    "smell_type": "Empty Catch",
                    "category": "Error Handling",
                    "severity": "Medium",
                    "file_path": file_path,
                    "line_number": line_num,
                    "measured_value": 1.0,
                    "threshold": 0.0,
                    "reason": "Empty catch block suppresses exceptions without logging or handling them."
                })
        return smells


class CGotoDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension not in (".c", ".h", ".cpp", ".hpp"):
            return []
        smells = []
        goto_re = re.compile(r"\bgoto\s+\w+;")
        for line_num, line in enumerate(content.split("\n"), start=1):
            if goto_re.search(line):
                smells.append({
                    "smell_type": "goto Usage",
                    "category": "Complexity",
                    "severity": "Low",
                    "file_path": file_path,
                    "line_number": line_num,
                    "measured_value": 1.0,
                    "threshold": 0.0,
                    "reason": "Usage of goto statement bypasses standard structured control flows."
                })
        return smells


class CUnsafeMemoryDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension not in (".c", ".h", ".cpp", ".hpp"):
            return []
        smells = []
        unsafe_funcs = ("strcpy", "strcat", "sprintf", "gets")
        for line_num, line in enumerate(content.split("\n"), start=1):
            for func in unsafe_funcs:
                if re.search(rf"\b{re.escape(func)}\b\s*\(", line):
                    smells.append({
                        "smell_type": "Unsafe Memory Function",
                        "category": "Security",
                        "severity": "High",
                        "file_path": file_path,
                        "line_number": line_num,
                        "measured_value": 1.0,
                        "threshold": 0.0,
                        "reason": f"Usage of unsafe memory function '{func}' poses potential buffer overflow risks."
                    })
        return smells


class GoIgnoredErrorsDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension != ".go":
            return []
        smells = []
        # Matches assignments like: _, err = foo() or _, _ = foo() where err is ignored, or just _ :=
        ignored_err_re = re.compile(r"\b_\s*,\s*err\s*:=|\b_\s*=\s*\w+\(.*?\)")
        for line_num, line in enumerate(content.split("\n"), start=1):
            if ignored_err_re.search(line):
                smells.append({
                    "smell_type": "Ignored Errors",
                    "category": "Error Handling",
                    "severity": "Medium",
                    "file_path": file_path,
                    "line_number": line_num,
                    "measured_value": 1.0,
                    "threshold": 0.0,
                    "reason": "Go error return value is explicitly ignored with '_'."
                })
        return smells


class RustLargeMatchDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension != ".rs":
            return []
        smells = []
        # Simple match arm counter
        match_start_re = re.compile(r"\bmatch\s+.*?\s*\{")
        lines = content.split("\n")
        for line_num, line in enumerate(lines, start=1):
            if match_start_re.search(line):
                # Count arm symbols =>
                arm_count = 0
                brace_count = 1
                for j in range(line_num, len(lines)):
                    sub_line = lines[j]
                    if "{" in sub_line:
                        brace_count += 1
                    if "}" in sub_line:
                        brace_count -= 1
                    if "=>" in sub_line:
                        arm_count += 1
                    if brace_count <= 0:
                        break
                if arm_count > MAX_MATCH_ARMS:
                    smells.append({
                        "smell_type": "Large Match Expression",
                        "category": "Complexity",
                        "severity": "Medium",
                        "file_path": file_path,
                        "line_number": line_num,
                        "measured_value": arm_count,
                        "threshold": MAX_MATCH_ARMS,
                        "reason": f"Rust match block has {arm_count} arms, exceeding threshold of {MAX_MATCH_ARMS}."
                    })
        return smells


class PHPGlobalStateDetector(BaseSmellDetector):
    def detect(self, file_path: str, content: str, extension: str, size_metrics: Dict[str, Any], complexity_metrics: Dict[str, Any], declarations: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if extension != ".php":
            return []
        smells = []
        global_re = re.compile(r"\bglobal\s+\$\w+|\$GLOBALS\s*\[")
        for line_num, line in enumerate(content.split("\n"), start=1):
            if global_re.search(line):
                smells.append({
                    "smell_type": "Global State",
                    "category": "Design",
                    "severity": "Medium",
                    "file_path": file_path,
                    "line_number": line_num,
                    "measured_value": 1.0,
                    "threshold": 0.0,
                    "reason": "Usage of global variables or $GLOBALS array increases coupling and side effects."
                })
        return smells


# Shared Smell Engine Coordinator
class SmellEngine:
    DETECTORS = [
        LongMethodDetector(),
        LargeFileDetector(),
        DeepNestingDetector(),
        MagicNumbersDetector(),
        LargeClassDetector(),
        LongParameterListDetector(),
        DeadCodeDetector(),
        DuplicateCodeDetector(),
        PythonMutableDefaultsDetector(),
        JSCallbackHellDetector(),
        JSPromiseChainsDetector(),
        JavaGodClassDetector(),
        JavaEmptyCatchDetector(),
        CGotoDetector(),
        CUnsafeMemoryDetector(),
        GoIgnoredErrorsDetector(),
        RustLargeMatchDetector(),
        PHPGlobalStateDetector()
    ]

    @classmethod
    def detect(
        cls,
        file_path: str,
        content: str,
        extension: str,
        size_metrics: Dict[str, Any],
        complexity_metrics: Dict[str, Any],
        declarations: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        all_smells = []
        for detector in cls.DETECTORS:
            try:
                smells = detector.detect(
                    file_path=file_path,
                    content=content,
                    extension=extension,
                    size_metrics=size_metrics,
                    complexity_metrics=complexity_metrics,
                    declarations=declarations,
                    dependencies=dependencies
                )
                all_smells.extend(smells)
            except Exception:
                # Tolerant smell run
                pass
        return all_smells
