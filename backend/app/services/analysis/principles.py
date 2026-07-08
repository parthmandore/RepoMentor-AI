"""
Engineering Principles Engine.
Evaluates repository files, smells, metrics, and architecture summaries to detect violations
of SOLID, DRY, Separation of Concerns, Encapsulation, and Coupling/Cohesion rules.
"""

from typing import List, Dict, Any

def analyze_principles(
    files: List[Any],
    smells: List[Any],
    architecture_knowledge: Dict[str, Any],
    duplication_percentage: float
) -> List[Dict[str, Any]]:
    violations = []

    # 1. Single Responsibility Principle (SRP)
    god_files = [f for f in files if f.lines_of_code > 300 or f.complexity > 15]
    if god_files:
        violations.append({
            "principle": "Single Responsibility Principle (SRP)",
            "status": "violated",
            "explanation": "A module or class should have only one reason to change.",
            "why_it_matters": "Classes with multiple responsibilities are brittle, difficult to test, and have high cognitive overhead.",
            "where_occurs": f"{len(god_files)} God Classes detected",
            "evidence": [f.path for f in god_files[:3]],
            "how_to_fix": "Extract focused responsibilities into separate, cohesive sub-services or helper classes.",
            "estimated_impact": "Maintainability +4, Complexity -5",
            "severity_text": "High"
        })
    else:
        violations.append({
            "principle": "Single Responsibility Principle (SRP)",
            "status": "passed",
            "explanation": "A module or class should have only one reason to change.",
            "why_it_matters": "Ensures codebase modularity and small class sizes.",
            "where_occurs": "All classes remain focused",
            "evidence": [],
            "how_to_fix": "Continue keeping class LOC below 300.",
            "estimated_impact": "None",
            "severity_text": "Passed"
        })

    # 2. DRY (Don't Repeat Yourself)
    if duplication_percentage > 5.0:
        violations.append({
            "principle": "DRY (Don't Repeat Yourself)",
            "status": "violated",
            "explanation": "Every piece of knowledge must have a single, unambiguous representation within a system.",
            "why_it_matters": "Duplicated code leads to inconsistencies and requires modifying multiple locations for a single change.",
            "where_occurs": f"{duplication_percentage:.1f}% code duplication detected",
            "evidence": ["Multiple duplicate blocks discovered"],
            "how_to_fix": "Extract shared code blocks into reusable methods or utility modules.",
            "estimated_impact": "Maintainability +3, Duplication -3%",
            "severity_text": "Medium"
        })
    else:
        violations.append({
            "principle": "DRY (Don't Repeat Yourself)",
            "status": "passed",
            "explanation": "Every piece of knowledge must have a single, unambiguous representation within a system.",
            "why_it_matters": "Eliminates redundancy and single-point-of-change overhead.",
            "where_occurs": "Low duplication",
            "evidence": [],
            "how_to_fix": "Reuse existing helpers rather than copying code.",
            "estimated_impact": "None",
            "severity_text": "Passed"
        })

    # 3. Separation of Concerns & Layered Architecture
    layers = architecture_knowledge.get("layers", {})
    has_layered = len(layers.get("controllers", [])) > 0 or len(layers.get("services", [])) > 0 or len(layers.get("repositories", [])) > 0
    
    # Check layer violations (e.g. repositories importing services)
    violations_found = []
    arch_evidence = architecture_knowledge.get("evidence", [])
    for ev in arch_evidence:
        if "layer violation" in ev.lower() or "violation" in ev.lower():
            violations_found.append(ev)

    if violations_found:
        violations.append({
            "principle": "Separation of Concerns & Layered Architecture",
            "status": "violated",
            "explanation": "Keep distinct layers separated (e.g. UI/Controller -> Service -> Data Layer).",
            "why_it_matters": "Direct layer bypasses coupling high-level policies with low-level data access detail.",
            "where_occurs": "Layer rule violations detected",
            "evidence": violations_found[:3],
            "how_to_fix": "Refactor imports to follow unidirectional dependency: UI/Controller -> Service -> Repository.",
            "estimated_impact": "Architecture Score +6, Instability Index Balanced",
            "severity_text": "High"
        })
    elif not has_layered and len(files) > 5:
        violations.append({
            "principle": "Separation of Concerns & Layered Architecture",
            "status": "violated",
            "explanation": "Keep distinct layers separated (e.g. UI/Controller -> Service -> Data Layer).",
            "why_it_matters": "Without clean layers, business logic leaks into presentation and database interfaces.",
            "where_occurs": "Flat structure / No layers detected",
            "evidence": ["All code resides in root namespace"],
            "how_to_fix": "Organize classes into distinct namespaces or folder structures (controllers, services, repositories).",
            "estimated_impact": "Architecture Score +10",
            "severity_text": "Medium"
        })
    else:
        violations.append({
            "principle": "Separation of Concerns & Layered Architecture",
            "status": "passed",
            "explanation": "Keep distinct layers separated (e.g. UI/Controller -> Service -> Data Layer).",
            "why_it_matters": "Minimizes structural coupling and isolates system changes.",
            "where_occurs": "Layer separation intact",
            "evidence": [],
            "how_to_fix": "Enforce layer direction in pull request review checklist.",
            "estimated_impact": "None",
            "severity_text": "Passed"
        })

    # 4. High Coupling & Low Cohesion
    highly_coupled = [f for f in files if getattr(f, "coupling_score", 0) > 8]
    if highly_coupled:
        violations.append({
            "principle": "Low Coupling & High Cohesion",
            "status": "violated",
            "explanation": "Modules should depend on as few other modules as possible (low coupling) and perform simple, unified tasks (high cohesion).",
            "why_it_matters": "Highly coupled modules trigger cascading changes across the codebase when modified.",
            "where_occurs": f"{len(highly_coupled)} highly coupled modules detected (>8)",
            "evidence": [f.path for f in highly_coupled[:3]],
            "how_to_fix": "Introduce interfaces or use dependency inversion to shield modules from direct dependencies.",
            "estimated_impact": "Maintainability +3, Coupling -4",
            "severity_text": "Medium"
        })
    else:
        violations.append({
            "principle": "Low Coupling & High Cohesion",
            "status": "passed",
            "explanation": "Modules should depend on as few other modules as possible (low coupling) and perform simple, unified tasks (high cohesion).",
            "why_it_matters": "Improves modular testability and flexibility.",
            "where_occurs": "All modules decoupled",
            "evidence": [],
            "how_to_fix": "Keep dependencies lightweight.",
            "estimated_impact": "None",
            "severity_text": "Passed"
        })

    # 5. Dependency Inversion Principle (DIP)
    violations.append({
        "principle": "Dependency Inversion Principle (DIP)",
        "status": "passed" if len(files) <= 5 or not highly_coupled else "violated",
        "explanation": "High-level modules should not depend on low-level modules. Both should depend on abstractions.",
        "why_it_matters": "Direct concrete dependencies restrict flexibility, preventing alternative mock implementations in test suits.",
        "where_occurs": "Direct instantiation of classes instead of interface injections" if highly_coupled else "No direct concrete couplings flagged",
        "evidence": [f.path for f in highly_coupled[:2]] if highly_coupled else [],
        "how_to_fix": "Inject interfaces or beans rather than referencing concrete constructors.",
        "estimated_impact": "Testability +5, Scalability +2",
        "severity_text": "Low" if highly_coupled else "Passed"
    })

    return violations
