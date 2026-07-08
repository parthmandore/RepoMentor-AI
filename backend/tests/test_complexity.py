from app.services.analysis.complexity_engine import ComplexityEngine

def test_python_complexity():
    content = """
def my_func(x):
    if x > 10:
        for i in range(x):
            print(i)
    else:
        try:
            print("x is small")
        except Exception:
            pass
"""
    result = ComplexityEngine.calculate(content, ".py", [])
    assert result["file_complexity"] > 1
    assert len(result["functions"]) == 1
    func = result["functions"][0]
    assert func["name"] == "my_func"
    assert func["metrics"]["branches"] > 0
    assert func["metrics"]["loops"] == 1
    assert func["metrics"]["exceptions"] == 1

def test_brace_complexity():
    content = """
    function calculate(x) {
        if (x > 10) {
            for (let i = 0; i < x; i++) {
                console.log(i);
            }
        } else {
            try {
                console.log("small");
            } catch (e) {
                console.error(e);
            }
        }
    }
    """
    declarations = [{
        "name": "calculate",
        "type": "function",
        "line": 2,
        "end_line": 13
    }]
    result = ComplexityEngine.calculate(content, ".js", declarations)
    assert len(result["functions"]) == 1
    func = result["functions"][0]
    assert func["name"] == "calculate"
    assert func["complexity"] > 1
    assert func["metrics"]["loops"] == 1
    assert func["metrics"]["exceptions"] == 1
    assert func["metrics"]["branches"] == 1
