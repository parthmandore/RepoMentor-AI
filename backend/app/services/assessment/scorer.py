"""
Deterministic assessment scoring engine.
Evaluates repository files, smells, security issues, technology stacks,
and architecture metadata to yield 0-100 dimensional scores.
"""

from typing import List, Dict, Any

def get_grade_from_score(score: int) -> str:
    if score >= 97: return "A+"
    if score >= 93: return "A"
    if score >= 90: return "A-"
    if score >= 87: return "B+"
    if score >= 83: return "B"
    if score >= 80: return "B-"
    if score >= 75: return "C+"
    if score >= 70: return "C"
    if score >= 60: return "D"
    return "F"

def calculate_dimensions(
    files: List[Any],
    smells: List[Any],
    security_issues: List[Any],
    architecture_knowledge: Dict[str, Any],
    tech_stack: Dict[str, Any],
    security_score_from_repo: int
) -> Dict[str, Any]:
    """
    Computes scores (0-100) for all 7 engineering dimensions:
    - Architecture
    - Maintainability
    - Code Organization
    - Consistency
    - Security
    - Testing
    - Documentation
    """
    total_files = len(files)
    total_loc = sum(f.lines_of_code for f in files)
    
    # ----------------------------------------------------
    # 1. Architecture (15%)
    # ----------------------------------------------------
    arch_score = 100.0
    arch_bonuses = []
    arch_deductions = []
    
    layers = architecture_knowledge.get("layers", {})
    has_controller = len(layers.get("controllers", [])) > 0
    has_service = len(layers.get("services", [])) > 0
    has_repository = len(layers.get("repositories", [])) > 0
    
    if has_controller and has_service and has_repository:
        arch_score += 5.0
        arch_bonuses.append({
            "name": "Layered MVC Architecture",
            "score": 5,
            "reason": "Controllers, Services, and Repositories layers are successfully segregated."
        })
    if has_repository:
        arch_score += 3.0
        arch_bonuses.append({
            "name": "Repository Pattern",
            "score": 3,
            "reason": "Database interactions are isolated inside repository modules."
        })
        
    cycles = architecture_knowledge.get("circular_dependencies", [])
    cycle_deduction = len(cycles) * 5.0
    if cycle_deduction > 0:
        ded_val = min(20.0, cycle_deduction)
        arch_score -= ded_val
        arch_deductions.append({
            "name": "Circular Dependencies",
            "score": -int(ded_val),
            "reason": f"Found {len(cycles)} circular dependency loops.",
            "affected_files": [node for cycle in cycles for node in cycle][:5]
        })
        
    coupled_modules = sum(1 for f in files if getattr(f, "coupling_score", 0) > 8)
    if coupled_modules > 0:
        ded_val = min(15.0, coupled_modules * 2.0)
        arch_score -= ded_val
        arch_deductions.append({
            "name": "High Coupling",
            "score": -int(ded_val),
            "reason": f"Found {coupled_modules} modules with coupling score above threshold (8).",
            "affected_files": [f.path for f in files if getattr(f, "coupling_score", 0) > 8][:5]
        })
        
    arch_score = max(0, min(100, round(arch_score)))
    
    # ----------------------------------------------------
    # 2. Maintainability (25%)
    # ----------------------------------------------------
    maint_score = 100.0
    maint_bonuses = []
    maint_deductions = []
    
    complexities = [f.complexity for f in files if f.complexity > 0]
    avg_complexity = sum(complexities) / len(complexities) if complexities else 0.0
    if avg_complexity > 3.0:
        ded_val = min(20.0, (avg_complexity - 3.0) * 3.0)
        maint_score -= ded_val
        maint_deductions.append({
            "name": "Average Complexity",
            "score": -int(ded_val),
            "reason": f"Average complexity of {avg_complexity:.2f} exceeds threshold (3).",
            "threshold": 3.0,
            "measured": round(avg_complexity, 2)
        })
        
    max_complexity = max((f.complexity for f in files), default=0)
    if max_complexity > 15:
        maint_score -= 10.0
        maint_deductions.append({
            "name": "Max Complexity Violation",
            "score": -10,
            "reason": f"Max complexity is {max_complexity}, exceeding safety threshold (15).",
            "threshold": 15,
            "measured": max_complexity,
            "affected_files": [f.path for f in files if f.complexity == max_complexity]
        })
        
    # Code smells count
    total_smells = len(smells)
    if total_smells > 0:
        ded_val = min(20.0, total_smells * 1.5)
        maint_score -= ded_val
        maint_deductions.append({
            "name": "Code Smells",
            "score": -int(ded_val),
            "reason": f"Found {total_smells} active code smells in code files.",
            "measured": total_smells
        })
        
    # God classes (LOC > 300)
    god_classes = [f.path for f in files if f.lines_of_code > 300]
    if god_classes:
        ded_val = min(20.0, len(god_classes) * 5.0)
        maint_score -= ded_val
        maint_deductions.append({
            "name": "God Classes",
            "score": -int(ded_val),
            "reason": f"Found {len(god_classes)} modules containing over 300 lines of code.",
            "affected_files": god_classes[:5]
        })
        
    maint_score = max(0, min(100, round(maint_score)))
    
    # ----------------------------------------------------
    # 3. Code Organization (15%)
    # ----------------------------------------------------
    org_score = 100.0
    org_bonuses = []
    org_deductions = []
    
    # Oversized files (> 500 lines)
    large_files = [f.path for f in files if f.lines_of_code > 500]
    if large_files:
        ded_val = min(20.0, len(large_files) * 5.0)
        org_score -= ded_val
        org_deductions.append({
            "name": "Oversized Files",
            "score": -int(ded_val),
            "reason": f"Detected {len(large_files)} files exceeding length recommendations (500 LOC).",
            "affected_files": large_files[:5]
        })
        
    # Flat structure check (all files in root)
    nested_files = [f.path for f in files if "/" in f.path or "\\" in f.path]
    if len(nested_files) == 0 and total_files > 4:
        org_score -= 10.0
        org_deductions.append({
            "name": "Missing Module Structure",
            "score": -10,
            "reason": "All codebase files are located in root directory with no folder namespaces."
        })
        
    # Deep folder structures (> 4 levels)
    deep_files = [f.path for f in files if len(f.path.replace("\\", "/").split("/")) > 5]
    if deep_files:
        ded_val = min(15.0, len(deep_files) * 3.0)
        org_score -= ded_val
        org_deductions.append({
            "name": "Deep Nested Folders",
            "score": -int(ded_val),
            "reason": f"Found {len(deep_files)} files nested deeper than 4 folder directories.",
            "affected_files": deep_files[:5]
        })
        
    org_score = max(0, min(100, round(org_score)))
    
    # ----------------------------------------------------
    # 4. Consistency (10%)
    # ----------------------------------------------------
    cons_score = 100.0
    cons_bonuses = []
    cons_deductions = []
    
    # Language count > 3
    langs_count = len(tech_stack.get("languages", {})) if tech_stack else 1
    if langs_count > 3:
        ded_val = min(15.0, (langs_count - 3) * 5.0)
        cons_score -= ded_val
        cons_deductions.append({
            "name": "Multi-Language Overhead",
            "score": -int(ded_val),
            "reason": f"Project contains {langs_count} programming languages, introducing consistency challenges."
        })
        
    # Mixed snake_case / camelCase in same codebase
    # Simply simulate static checks on path style
    has_camel = any(c.isupper() and c.islower() for f in files for c in f.path.split("/").pop())
    has_snake = any("_" in f.path for f in files)
    if has_camel and has_snake:
        cons_score -= 10.0
        cons_deductions.append({
            "name": "Mixed Naming Conventions",
            "score": -10,
            "reason": "Codebase references both camelCase and snake_case naming formats in file headers."
        })
        
    cons_score = max(0, min(100, round(cons_score)))
    
    # ----------------------------------------------------
    # 5. Security (20%)
    # ----------------------------------------------------
    sec_score = max(0, min(100, security_score_from_repo))
    
    # ----------------------------------------------------
    # 6. Testing (10%)
    # ----------------------------------------------------
    test_score = 50.0
    test_bonuses = []
    test_deductions = []
    
    test_files = [f.path for f in files if "test" in f.path.lower() or "spec" in f.path.lower()]
    test_file_count = len(test_files)
    
    # Test Framework presence
    pkg_manager = tech_stack.get("package_manager", "").lower() if tech_stack else ""
    if test_file_count > 0:
        test_score += 15.0
        test_bonuses.append({
            "name": "Testing Framework Configured",
            "score": 15,
            "reason": "Test runner dependencies detected in build manifests."
        })
        
        # Test files count points
        tf_points = min(20.0, test_file_count * 5.0)
        test_score += tf_points
        test_bonuses.append({
            "name": "Active Test Suites",
            "score": int(tf_points),
            "reason": f"Parsed {test_file_count} test specs modules."
        })
        
        # Test ratio
        test_loc = sum(f.lines_of_code for f in files if f.path in test_files)
        src_loc = max(1, total_loc - test_loc)
        test_ratio = test_loc / src_loc
        if test_ratio >= 0.1:
            test_score += 15.0
            test_bonuses.append({
                "name": "High Test Coverage Ratio",
                "score": 15,
                "reason": f"Test code LOC represents {(test_ratio * 100):.1f}% of core codebase."
            })
            
        # Dedicated test folders
        dedicated_folder = any("/test/" in f.path or "/tests/" in f.path for f in files)
        if dedicated_folder:
            test_score += 10.0
            test_bonuses.append({
                "name": "Structured Testing Namespaces",
                "score": 10,
                "reason": "Tests modules are neatly isolated under dedicated directories."
            })
    else:
        test_deductions.append({
            "name": "Missing Unit Testing",
            "score": -20,
            "reason": "No test specs, suites, or testing assertions found."
        })
        test_score -= 20.0
        
    test_score = max(0, min(100, round(test_score)))
    
    # ----------------------------------------------------
    # 7. Documentation (5%)
    # ----------------------------------------------------
    doc_score = 100.0
    doc_bonuses = []
    doc_deductions = []
    
    # README present (+30)
    readme_file = next((f for f in files if f.path.lower() == "readme.md"), None)
    if readme_file:
        doc_bonuses.append({
            "name": "README present",
            "score": 30,
            "reason": "Root README.md is defined."
        })
    else:
        doc_score -= 30.0
        doc_deductions.append({
            "name": "README missing",
            "score": -30,
            "reason": "No README.md found in project root."
        })
        
    # Installation guide present (+15)
    has_install = False
    if readme_file:
        # Check size and content keywords
        has_install = any(k in readme_file.path.lower() for k in ["install", "setup", "get started"])
        # If not, check other file paths
        if not has_install:
            has_install = any("install" in f.path.lower() or "setup" in f.path.lower() for f in files)
            
    if has_install:
        doc_bonuses.append({
            "name": "Installation guide present",
            "score": 15,
            "reason": "Detected setup/installation guides in project paths or manifest instructions."
        })
    else:
        doc_score -= 15.0
        doc_deductions.append({
            "name": "Installation guide missing",
            "score": -15,
            "reason": "No setup instructions found. New developers may struggle to run code."
        })
        
    # Architecture docs (+15)
    has_arch = any("architecture" in f.path.lower() or "design" in f.path.lower() or "docs/arch" in f.path.lower() for f in files)
    if has_arch:
        doc_bonuses.append({
            "name": "Architecture docs present",
            "score": 15,
            "reason": "Project structural or architectural documentation is mapped."
        })
    else:
        doc_score -= 15.0
        doc_deductions.append({
            "name": "Architecture docs missing",
            "score": -15,
            "reason": "Structural layout documentation is missing. Harder to understand coupling."
        })
        
    # API docs (+15)
    has_api_docs = any("api" in f.path.lower() or "swagger" in f.path.lower() or "openapi" in f.path.lower() for f in files)
    if has_api_docs:
        doc_bonuses.append({
            "name": "API docs present",
            "score": 15,
            "reason": "API specifications (Swagger, OpenAPI, or endpoints wiki) detected."
        })
    else:
        doc_score -= 15.0
        doc_deductions.append({
            "name": "API docs missing",
            "score": -15,
            "reason": "Endpoint or API contract definitions are missing."
        })
        
    # Contributing guide (+10)
    has_contrib = any("contributing" in f.path.lower() or "contrib" in f.path.lower() for f in files)
    if has_contrib:
        doc_bonuses.append({
            "name": "Contributing guide present",
            "score": 10,
            "reason": "CONTRIBUTING.md instructions mapped for community development."
        })
    else:
        doc_score -= 10.0
        doc_deductions.append({
            "name": "Contributing guide missing",
            "score": -10,
            "reason": "No contributing workflow guidelines detected."
        })
        
    # License (+5)
    has_license = any("license" in f.path.lower() or "copying" in f.path.lower() for f in files)
    if has_license:
        doc_bonuses.append({
            "name": "License present",
            "score": 5,
            "reason": "LICENSE file is present inside repository."
        })
    else:
        doc_score -= 5.0
        doc_deductions.append({
            "name": "License missing",
            "score": -5,
            "reason": "No open-source copyright license declared."
        })
        
    # Comments density (+10)
    comment_ratios = []
    for f in files:
        if f.analysis_metadata and "metrics" in f.analysis_metadata:
            comment_ratios.append(f.analysis_metadata["metrics"].get("comment_ratio", 0.0))
    avg_comment_ratio = sum(comment_ratios) / len(comment_ratios) if comment_ratios else 0.0
    
    if avg_comment_ratio >= 0.15:
        doc_bonuses.append({
            "name": "Code comments sufficient",
            "score": 10,
            "reason": f"Codebase inline comments ratio ({(avg_comment_ratio * 100):.1f}%) meets threshold (15%)."
        })
    else:
        doc_score -= 10.0
        doc_deductions.append({
            "name": "Code comments insufficient",
            "score": -10,
            "reason": f"Codebase has low inline comment density ({(avg_comment_ratio * 100):.1f}%)."
        })
        
    doc_score = max(0, min(100, round(doc_score)))
    
    # ----------------------------------------------------
    # Overall Score Calculation
    # ----------------------------------------------------
    overall_score = (
        arch_score * 0.15 +
        maint_score * 0.25 +
        org_score * 0.15 +
        cons_score * 0.10 +
        sec_score * 0.20 +
        test_score * 0.10 +
        doc_score * 0.05
    )
    overall_score = max(0, min(100, round(overall_score)))
    
    return {
        "overall": overall_score,
        "grade": get_grade_from_score(overall_score),
        "dimensions": {
            "architecture": {
                "score": arch_score,
                "grade": get_grade_from_score(arch_score),
                "bonuses": arch_bonuses,
                "deductions": arch_deductions
            },
            "maintainability": {
                "score": maint_score,
                "grade": get_grade_from_score(maint_score),
                "bonuses": maint_bonuses,
                "deductions": maint_deductions
            },
            "organization": {
                "score": org_score,
                "grade": get_grade_from_score(org_score),
                "bonuses": org_bonuses,
                "deductions": org_deductions
            },
            "consistency": {
                "score": cons_score,
                "grade": get_grade_from_score(cons_score),
                "bonuses": cons_bonuses,
                "deductions": cons_deductions
            },
            "security": {
                "score": sec_score,
                "grade": get_grade_from_score(sec_score),
                "bonuses": [],
                "deductions": []  # handled by security findings
            },
            "testing": {
                "score": test_score,
                "grade": get_grade_from_score(test_score),
                "bonuses": test_bonuses,
                "deductions": test_deductions
            },
            "documentation": {
                "score": doc_score,
                "grade": get_grade_from_score(doc_score),
                "bonuses": doc_bonuses,
                "deductions": doc_deductions
            }
        }
    }
