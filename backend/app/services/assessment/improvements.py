"""
Unified engineering roadmap improvements generator.
Generates explainable, prioritized refactoring suggestions that match recommendations.py.
"""

import os
from typing import List, Dict, Any

def generate_recommendations(
    files: List[Any],
    smells: List[Any],
    security_issues: List[Any],
    architecture_knowledge: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Returns sorted lists of explainable refactoring recommendations.
    """
    recs = []
    
    # 1. Security Check
    secrets_issues = [s for s in security_issues if s.category == "Secrets" or "secret" in s.title.lower()]
    if secrets_issues:
        affected = list({s.file_path for s in secrets_issues if s.file_path})
        recs.append({
            "id": "rotate_secrets",
            "title": "Rotate and Externalize Hardcoded Secrets",
            "gain": 12,
            "difficulty": "Easy",
            "effort": "15 min",
            "priority": "Critical",
            "engineering_principle": "Security by Design",
            "why_it_matters": "Storing plaintext credentials inside source code puts the entire system at risk. Credentials checked into Git can easily be leaked online or harvested by bots.",
            "metrics": f"Secrets leaked = {len(secrets_issues)}, Risk category = OWASP A02:2021",
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": ["externalize_configs"],
            "evidence": {
                "type": "security_issue",
                "path": secrets_issues[0].file_path or "README.md",
                "line": secrets_issues[0].line_number or 1,
                "detail": f"Hardcoded credential exposed in source file: {secrets_issues[0].title}."
            }
        })

    injection_issues = [s for s in security_issues if s.category in ["Injection", "SQL Injection", "Command Injection"] or "inject" in s.title.lower()]
    if injection_issues:
        affected = list({s.file_path for s in injection_issues if s.file_path})
        recs.append({
            "id": "sanitize_inputs",
            "title": "Sanitize Dynamic Input Queries",
            "gain": 8,
            "difficulty": "Medium",
            "effort": "45 min",
            "priority": "High",
            "engineering_principle": "Input Validation & Query Parameterization",
            "why_it_matters": "Executing raw queries built from string concatenations allows database injection or system command hijacking. Parameterization ensures data is separated from instruction.",
            "metrics": f"Injection hazards = {len(injection_issues)}, CWE mappings = CWE-89 / CWE-78",
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": [],
            "evidence": {
                "type": "security_issue",
                "path": injection_issues[0].file_path or "README.md",
                "line": injection_issues[0].line_number or 1,
                "detail": f"Dynamic query vulnerability: {injection_issues[0].title}."
            }
        })

    # 2. Circular Dependencies
    cycles = architecture_knowledge.get("circular_dependencies", [])
    if cycles:
        affected_nodes = list({node for cycle in cycles for node in cycle})
        recs.append({
            "id": "uncouple_dependencies",
            "title": "Resolve Circular Dependency Loops",
            "gain": 6,
            "difficulty": "Hard",
            "effort": "2 hours",
            "priority": "High",
            "engineering_principle": "Separation of Concerns & Acyclic Dependencies",
            "why_it_matters": "Circular imports tightly couple modules, making isolation testing impossible, degrading bundler performance, and increasing regression rates during edits.",
            "metrics": f"Cycles count = {len(cycles)}, Nodes involved = {len(affected_nodes)}, Target expected = 0",
            "affected_files": affected_nodes[:4],
            "depends_on": [],
            "unlocks": ["split_god_classes"],
            "evidence": {
                "type": "architecture_node",
                "path": cycles[0][0] if len(cycles[0]) > 0 else "README.md",
                "line": 1,
                "detail": f"Uncouple imports between nodes forming {len(cycles)} loops."
            }
        })

    # 3. God Classes / Large Modules
    god_classes = [f.path for f in files if f.lines_of_code > 300]
    if god_classes:
        recs.append({
            "id": "split_god_classes",
            "title": "Split Large God Classes",
            "gain": 5,
            "difficulty": "Medium",
            "effort": "1 hour",
            "priority": "Medium",
            "engineering_principle": "Single Responsibility Principle (SRP)",
            "why_it_matters": "Files exceeding 300 lines of code accumulate multiple duties. Decoupling them makes the code easier to scan, test, and adapt for multiple devs.",
            "metrics": f"Oversized classes = {len(god_classes)}, Size limit = 300 LOC",
            "affected_files": god_classes[:4],
            "depends_on": ["uncouple_dependencies"] if cycles else [],
            "unlocks": [],
            "evidence": {
                "type": "file",
                "path": god_classes[0],
                "line": 1,
                "detail": f"This module contains over 300 lines of code. Split into smaller sub-services."
            }
        })

    # 4. Complexity Check
    complex_files = [f.path for f in files if f.complexity > 10]
    if complex_files:
        recs.append({
            "id": "reduce_complexity",
            "title": "Simplify Highly Nested Logic",
            "gain": 4,
            "difficulty": "Medium",
            "effort": "30 min",
            "priority": "Medium",
            "engineering_principle": "Keep It Simple, Stupid (KISS)",
            "why_it_matters": "Deeply nested conditionals and loops increase the cognitive load required to read code, introducing bugs that slip past verification suites.",
            "metrics": f"Complex modules = {len(complex_files)}, average complexity threshold = 3.0",
            "affected_files": complex_files[:4],
            "depends_on": [],
            "unlocks": [],
            "evidence": {
                "type": "file",
                "path": complex_files[0],
                "line": 1,
                "detail": "Reduce branching factor by using early return guards."
            }
        })

    # 5. Long Method Smells
    long_methods = [s for s in smells if s.smell_type == "Long Method"]
    if long_methods:
        affected = list({s.file_path for s in long_methods if s.file_path})
        recs.append({
            "id": "extract_long_methods",
            "title": "Extract Sub-methods from Long Functions",
            "gain": 3,
            "difficulty": "Easy",
            "effort": "15 min",
            "priority": "Medium",
            "engineering_principle": "Single Responsibility Principle (SRP)",
            "why_it_matters": "Long routines do too much work at once. Breaking them into smaller helper functions with clear descriptive names improves readability.",
            "metrics": f"Long methods = {len(long_methods)}, Target threshold = 25 LOC",
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": [],
            "evidence": {
                "type": "file",
                "path": long_methods[0].file_path,
                "line": long_methods[0].line_number or 1,
                "detail": f"Method exceeds target lines (25 LOC). Extract helpers."
            }
        })

    # 6. Magic Numbers
    magic_numbers = [s for s in smells if s.smell_type == "Magic Number"]
    if magic_numbers:
        affected = list({s.file_path for s in magic_numbers if s.file_path})
        recs.append({
            "id": "extract_magic_numbers",
            "title": "Extract Magic Numbers into Constants",
            "gain": 2,
            "difficulty": "Easy",
            "effort": "5 min",
            "priority": "Low",
            "engineering_principle": "Configuration over Hardcoding",
            "why_it_matters": "Literal values (magic numbers) scattered across files hide domain meaning and make future value updates highly error-prone.",
            "metrics": f"Magic numbers count = {len(magic_numbers)}, Target expected = 0",
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": ["externalize_configs"],
            "evidence": {
                "type": "file",
                "path": magic_numbers[0].file_path,
                "line": magic_numbers[0].line_number or 1,
                "detail": "Define uppercase named constants for raw numerical literals."
            }
        })

    # 7. Testing
    test_files = [f.path for f in files if "test" in f.path.lower() or "spec" in f.path.lower()]
    if not test_files:
        manifest_file = "package.json"
        if any(f.path.endswith(".py") for f in files):
            manifest_file = "requirements.txt"
        elif any(f.path.endswith(".java") for f in files):
            manifest_file = "pom.xml"

        recs.append({
            "id": "add_tests",
            "title": "Configure Testing Framework",
            "gain": 10,
            "difficulty": "Medium",
            "effort": "1 hour",
            "priority": "High",
            "engineering_principle": "Regression Safety",
            "why_it_matters": "No test modules or specs were detected. Running projects without unit tests increases regressions and prevents deployment automation.",
            "metrics": "Parsed test files = 0, Coverage percentage = 0.0%",
            "affected_files": [],
            "depends_on": [],
            "unlocks": [],
            "evidence": {
                "type": "project",
                "path": manifest_file,
                "line": 1,
                "detail": "No unit tests found. Setup pytest or Jest."
            }
        })

    # 8. Documentation
    has_readme = any(f.path.lower() == "readme.md" for f in files)
    if not has_readme:
        recs.append({
            "id": "create_readme",
            "title": "Add Detailed Project README.md",
            "gain": 5,
            "difficulty": "Easy",
            "effort": "20 min",
            "priority": "Low",
            "engineering_principle": "Clear Onboarding Documentation",
            "why_it_matters": "A README.md is the entry point for recruiters and developers. Providing installation guides, descriptions, and structures simplifies onboarding.",
            "metrics": "Root readme.md presence = False, Target expected = True",
            "affected_files": [],
            "depends_on": [],
            "unlocks": [],
            "evidence": {
                "type": "file",
                "path": "README.md",
                "line": 1,
                "detail": "Create root README.md to describe setup guidelines."
            }
        })

    # Sort recommendations by priority (Critical first, then High, Medium, Low)
    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    recs.sort(key=lambda r: priority_order.get(r["priority"], 4))

    return recs
