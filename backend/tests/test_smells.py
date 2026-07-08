from app.services.analysis.smells.detectors import (
    SmellEngine,
    LongMethodDetector,
    LargeFileDetector,
    DeepNestingDetector,
    MagicNumbersDetector,
    LongParameterListDetector,
    DeadCodeDetector,
    PythonMutableDefaultsDetector,
    JSCallbackHellDetector,
    JavaGodClassDetector,
    JavaEmptyCatchDetector,
    CGotoDetector,
    GoIgnoredErrorsDetector,
    RustLargeMatchDetector,
)

def test_long_method_detector():
    detector = LongMethodDetector()
    size_metrics = {
        "functions": [{"name": "huge_function", "line": 5, "loc": 50}]
    }
    smells = detector.detect("Main.py", "", ".py", size_metrics, {}, [], [])
    assert len(smells) == 1
    assert smells[0]["smell_type"] == "Long Method"
    assert smells[0]["measured_value"] == 50

def test_large_file_detector():
    detector = LargeFileDetector()
    size_metrics = {"code_lines": 400}
    smells = detector.detect("Main.py", "", ".py", size_metrics, {}, [], [])
    assert len(smells) == 1
    assert smells[0]["smell_type"] == "Large File"

def test_python_mutable_defaults():
    detector = PythonMutableDefaultsDetector()
    content = "def process(data, items=[]):"
    smells = detector.detect("main.py", content, ".py", {}, {}, [], [])
    assert len(smells) == 1
    assert smells[0]["smell_type"] == "Mutable Defaults"

def test_java_empty_catch():
    detector = JavaEmptyCatchDetector()
    content = "try { doSomething(); } catch (Exception e) {}"
    smells = detector.detect("Main.java", content, ".java", {}, {}, [], [])
    assert len(smells) == 1
    assert smells[0]["smell_type"] == "Empty Catch"

def test_c_goto():
    detector = CGotoDetector()
    content = "goto error;"
    smells = detector.detect("main.c", content, ".c", {}, {}, [], [])
    assert len(smells) == 1
    assert smells[0]["smell_type"] == "goto Usage"

def test_go_ignored_errors():
    detector = GoIgnoredErrorsDetector()
    content = "_, err := doWork()\n_, = doWork()"
    smells = detector.detect("main.go", content, ".go", {}, {}, [], [])
    assert len(smells) >= 1
    assert smells[0]["smell_type"] == "Ignored Errors"
