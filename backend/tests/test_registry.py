from app.services.analysis.analyzers.registry import AnalyzerRegistry
from app.services.analysis.analyzers.python import PythonAnalyzer
from app.services.analysis.analyzers.java import JavaAnalyzer
from app.services.analysis.analyzers.javascript import JavaScriptAnalyzer

def test_registry_lookup():
    # Verify lookup by extensions works correctly
    python_analyzer = AnalyzerRegistry.get(".py")
    assert isinstance(python_analyzer, PythonAnalyzer)

    java_analyzer = AnalyzerRegistry.get(".java")
    assert isinstance(java_analyzer, JavaAnalyzer)

    js_analyzer = AnalyzerRegistry.get(".js")
    assert isinstance(js_analyzer, JavaScriptAnalyzer)

    jsx_analyzer = AnalyzerRegistry.get(".jsx")
    assert isinstance(jsx_analyzer, JavaScriptAnalyzer)

    # Invalid extension should return None
    invalid = AnalyzerRegistry.get(".unsupported")
    assert invalid is None

def test_registry_supported_extensions():
    exts = AnalyzerRegistry.supported_extensions()
    assert ".py" in exts
    assert ".java" in exts
    assert ".js" in exts
    assert ".ts" in exts
    assert ".cpp" in exts
    assert ".go" in exts
    assert ".rs" in exts
