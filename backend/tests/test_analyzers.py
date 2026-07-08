from app.services.analysis.analyzers.registry import AnalyzerRegistry

def test_java_analyzer():
    content = """
    package com.example;
    import java.util.List;

    public class UserService {
        private String name;

        public UserService(String name) {
            this.name = name;
        }

        public void processUsers(List<String> users) {
            for (String u : users) {
                System.out.println(u);
            }
        }
    }
    """
    analyzer = AnalyzerRegistry.get(".java")
    assert analyzer is not None

    size = analyzer.analyze_size(content, ".java")
    assert size["code_lines"] > 5
    assert len(size["functions"]) == 2  # constructor + method
    assert len(size["classes"]) == 1

    decls = analyzer.extract_declarations(content, ".java")
    assert len(decls) >= 3  # Class + constructor + method
    types = [d["type"] for d in decls]
    assert "class" in types
    assert "method" in types

    deps = analyzer.extract_dependencies(content, ".java")
    assert len(deps) == 2
    dep_types = [d["type"] for d in deps]
    assert "package" in dep_types
    assert "import" in dep_types

def test_go_analyzer():
    content = """
    package main
    import "fmt"

    type Point struct {
        X int
        Y int
    }

    func NewPoint(x int, y int) Point {
        return Point{X: x, Y: y}
    }

    func (p *Point) Print() {
        fmt.Println(p.X, p.Y)
    }
    """
    analyzer = AnalyzerRegistry.get(".go")
    assert analyzer is not None

    size = analyzer.analyze_size(content, ".go")
    assert len(size["classes"]) == 1  # Point struct
    assert len(size["functions"]) == 2  # NewPoint function + Print method

    decls = analyzer.extract_declarations(content, ".go")
    assert len(decls) == 3
    types = [d["type"] for d in decls]
    assert "struct" in types
    assert "function" in types
    assert "method" in types
