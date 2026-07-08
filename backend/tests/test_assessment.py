"""
Unit tests for the Phase 7 engineering assessment engine.
"""

import pytest
from app.services.assessment.scorer import calculate_dimensions, get_grade_from_score
from app.services.assessment.explainer import generate_explanations
from app.services.assessment.simulator import run_simulation
from app.services.assessment.contributors import analyze_contributors
from app.services.assessment.improvements import generate_recommendations
from app.services.assessment.confidence import calculate_confidence

# Mock objects for tests
class MockFile:
    def __init__(self, path, lines_of_code, complexity, size_bytes=200, analysis_metadata=None):
        self.path = path
        self.lines_of_code = lines_of_code
        self.complexity = complexity
        self.size_bytes = size_bytes
        self.analysis_metadata = analysis_metadata or {}
        self.coupling_score = 0

class MockSmell:
    def __init__(self, file_path, smell_type, reason, line_number=10):
        self.file_path = file_path
        self.smell_type = smell_type
        self.reason = reason
        self.line_number = line_number

class MockSecurityIssue:
    def __init__(self, category, description, severity="high", file_path="src/main.py", line_number=20):
        self.category = category
        self.description = description
        self.severity = severity
        self.file_path = file_path
        self.line_number = line_number

def test_scorer_and_explainer():
    files = [
        MockFile("src/Controller.java", 150, 8),
        MockFile("src/Service.java", 200, 2),
        MockFile("src/Repository.java", 120, 1),
        MockFile("src/helper.java", 80, 2),
    ]
    smells = [
        MockSmell("src/Controller.java", "LongMethod", "Method exceeds length recommendations")
    ]
    sec_issues = []
    
    arch_knowledge = {
        "layers": {
            "controllers": ["src/Controller.java"],
            "services": ["src/Service.java"],
            "repositories": ["src/Repository.java"]
        },
        "circular_dependencies": []
    }
    
    tech_stack = {
        "languages": {"Java": 90.0, "XML": 10.0},
        "package_manager": "Maven"
    }
    
    # Run Scorer
    scores = calculate_dimensions(
        files=files,
        smells=smells,
        security_issues=sec_issues,
        architecture_knowledge=arch_knowledge,
        tech_stack=tech_stack,
        security_score_from_repo=95
    )
    
    assert scores["overall"] > 50
    assert scores["dimensions"]["architecture"]["score"] == 100 # Capped at 100
    assert scores["dimensions"]["maintainability"]["score"] < 100 # Deducted for average complexity > 3 and smells
    
    # Run Explainer
    explanations = generate_explanations(
        files=files,
        smells=smells,
        security_issues=sec_issues,
        architecture_knowledge=arch_knowledge,
        tech_stack=tech_stack,
        scoring_output=scores
    )
    
    assert "overall_breakdown" in explanations
    assert len(explanations["explanations"]["architecture"]["bonuses"]) == 2
    assert len(explanations["explanations"]["maintainability"]["deductions"]) == 2 # Avg complexity + smell

def test_score_simulator():
    recs = [
        {"id": "fix_security", "gain": 10},
        {"id": "fix_cycles", "gain": 8},
        {"id": "reduce_complexity", "gain": 6}
    ]
    # Enabled fix_security and reduce_complexity
    predicted = run_simulation(80, recs, ["fix_security", "reduce_complexity"])
    assert predicted == 96
    
    # Check max limit capping
    predicted_capped = run_simulation(95, recs, ["fix_security", "reduce_complexity"])
    assert predicted_capped == 100

def test_contributors_and_improvements():
    files = [
        MockFile("README.md", 20, 0, size_bytes=1500),
        MockFile("src/Controller.java", 150, 4),
        MockFile("src/GodClass.java", 350, 12)
    ]
    smells = [
        MockSmell("src/Controller.java", "LongMethod", "Method too long")
    ]
    sec_issues = [
        MockSecurityIssue("HardcodedCredential", "Credential exposed")
    ]
    arch_knowledge = {
        "layers": {},
        "circular_dependencies": [["src/Controller.java", "src/GodClass.java"]]
    }
    
    contribs = analyze_contributors(files, smells, arch_knowledge)
    assert len(contribs["positive_contributors"]) > 0
    assert len(contribs["negative_contributors"]) > 0
    assert contribs["positive_contributors"][0]["file"] == "README.md"
    assert contribs["negative_contributors"][0]["file"] == "GodClass.java"
    
    recs = generate_recommendations(files, smells, sec_issues, arch_knowledge)
    assert len(recs) > 0
    # Security is first in recs (gain 10)
    assert recs[0]["id"] == "fix_security"
    assert recs[0]["gain"] == 10

def test_confidence():
    files = [MockFile("src/Controller.java", 150, 4)]
    tech_stack = {"languages": {"Java": 100.0}}
    
    conf = calculate_confidence(
        files=files,
        tech_stack=tech_stack,
        repo_status="ready",
        knowledge_status="completed",
        security_status="completed",
        architecture_status="completed",
        has_readme=False
    )
    
    assert conf["confidence_percentage"] < 100
    assert any("README.md" in r for r in conf["reasons"])
