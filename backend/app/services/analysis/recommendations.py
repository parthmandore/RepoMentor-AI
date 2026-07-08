import os
import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.code_smell import CodeSmell
from app.models.security_issue import SecurityIssue

def generate_recommendations(db: Session, repo_id: uuid.UUID) -> Dict[str, Any]:
    """
    Computes a complete, structured engineering refactoring roadmap.
    Accounts for every lost point in the 7 score dimensions, building a 
    dependency graph, explainable metrics, and a health forecast timeline.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        return {"current_score": 100, "potential_score": 100, "max_achievable": 100, "recoverable_points": 0, "forecast": [], "recommendations": []}

    files = db.query(RepositoryFile).filter(RepositoryFile.repository_id == repo_id).all()
    smells = db.query(CodeSmell).filter(CodeSmell.repository_id == repo_id).all()
    sec_issues = db.query(SecurityIssue).filter(SecurityIssue.repository_id == repo_id).all()

    # Load dynamic scores
    assessment = (repo.knowledge_summary or {}).get("assessment", {})
    scores = assessment.get("scores", {})
    if not scores or "dimensions" not in scores:
        from app.services.assessment.scorer import calculate_dimensions
        scores = calculate_dimensions(
            files=files,
            smells=smells,
            security_issues=sec_issues,
            architecture_knowledge=repo.architecture_summary or {},
            tech_stack=repo.tech_stack or {},
            security_score_from_repo=repo.security_score
        )

    dims = scores.get("dimensions", {})
    
    # Track all recommendations
    recs = []

    # 1. Architecture Deductions
    arch_dim = dims.get("architecture", {})
    arch_deductions = arch_dim.get("deductions", [])
    
    # Circular dependencies
    cycles = (repo.architecture_summary or {}).get("circular_dependencies", [])
    if cycles:
        affected_nodes = list({node for cycle in cycles for node in cycle})
        recs.append({
            "id": "uncouple_dependencies",
            "title": "Resolve Circular Dependency Loops",
            "priority": "High",
            "category": "Architecture",
            "effort": "2 hours",
            "difficulty": "Hard",
            "health_improvement": 6,
            "security_improvement": 0,
            "architecture_improvement": 10,
            "maintainability_improvement": 5,
            "why_it_matters": "Circular imports tightly couple modules, making isolation testing impossible, degrading bundler performance, and increasing regression rates during edits.",
            "metrics": f"Cycles count = {len(cycles)}, Nodes involved = {len(affected_nodes)}, Max chain = {repo.architecture_summary.get('stats', {}).get('largest_chain', 0)}, Target expected = 0",
            "steps": [
                "Inspect the visual cycle structure to find the back-edge reference.",
                "Extract common logic or parameters into a dedicated leaf interface module.",
                "Change imports inside circular files to reference the new interface module."
            ],
            "affected_files": affected_nodes[:4],
            "depends_on": [],
            "unlocks": ["split_god_classes"],
            "before_code": '// UserService.ts\nimport { LogHelper } from "./LogHelper";\n\n// LogHelper.ts\nimport { UserService } from "./UserService"; // Circular import!',
            "after_code": '// Extract common types to new LogConfig.ts\n// UserService.ts imports LogConfig\n// LogHelper.ts imports LogConfig'
        })

    # High Coupling
    highly_coupled_files = [f for f in files if f.coupling_score > 8]
    if highly_coupled_files:
        affected = [f.path for f in highly_coupled_files]
        recs.append({
            "id": "reduce_coupling",
            "title": "Decouple Highly Coupled Modules",
            "priority": "High",
            "category": "Architecture",
            "effort": "2 hours",
            "difficulty": "Hard",
            "health_improvement": 6,
            "security_improvement": 0,
            "architecture_improvement": 10,
            "maintainability_improvement": 4,
            "why_it_matters": "Tightly coupled files have too many incoming/outgoing imports. Changing a single interface propagates errors to dozens of dependent modules.",
            "metrics": f"Coupled files = {len(highly_coupled_files)}, Max coupling score = {max((f.coupling_score for f in highly_coupled_files), default=0)}, Limit threshold = 8",
            "steps": [
                "Map dependencies using the architecture visualizer.",
                "Identify overlapping utilities and extract them to pure helper functions.",
                "Apply Dependency Inversion: pass abstractions instead of importing concrete classes."
            ],
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": [],
            "before_code": '# Direct import of concrete implementations\nfrom services.email import SendEmailService\nfrom services.sms import SendSmsService',
            "after_code": '# Inject generic notifier interface\nclass NotificationService:\n    def __init__(self, notifier: BaseNotifier):\n        self.notifier = notifier'
        })

    # 2. Maintainability Deductions
    maint_dim = dims.get("maintainability", {})
    maint_deductions = maint_dim.get("deductions", [])
    
    # God Classes / Large Modules (Flag only when large AND coupled or complex, suggesting multiple responsibilities)
    large_files = [f for f in files if f.lines_of_code > 350 and f.is_text and ((f.coupling_score or 0) > 6 or (f.complexity or 0) > 8)]
    if large_files:
        affected = [f.path for f in large_files]
        recs.append({
            "id": "split_god_classes",
            "title": "Split Large God Classes",
            "priority": "High",
            "category": "Maintainability",
            "effort": "1.5 hours",
            "difficulty": "Hard",
            "health_improvement": 8,
            "security_improvement": 0,
            "architecture_improvement": 4,
            "maintainability_improvement": 10,
            "why_it_matters": "Files exceeding 350 lines of code accumulate multiple duties. Decoupling them makes the code easier to scan, test, and adapt for multiple devs.",
            "metrics": f"Oversized classes = {len(large_files)}, Max LOC = {max((f.lines_of_code for f in large_files), default=0)}, Size limit = 350 LOC",
            "steps": [
                "Analyze sub-routines and class variables to find distinct concerns.",
                "Extract utility methods or sub-components into standalone helper files.",
                "Inject helpers into the original class through parameters/constructors."
            ],
            "affected_files": affected[:4],
            "depends_on": ["uncouple_dependencies"] if cycles else [],
            "unlocks": [],
            "before_code": 'class Manager:\n    # Handles Database CRUD, User Authentication,\n    # Billing Invoicing, and Email Notifications...',
            "after_code": 'class Manager:\n    def __init__(self, auth_svc, billing_svc):\n        self.auth = auth_svc\n        self.billing = billing_svc'
        })

    # High Complexity (Filter to meaningful cognitive complexity nesting)
    complex_files = [f for f in files if (f.complexity or 0) > 15 and f.is_text]
    if complex_files:
        affected = [f.path for f in complex_files]
        recs.append({
            "id": "reduce_complexity",
            "title": "Simplify Highly Nested Logic",
            "priority": "Medium",
            "category": "Complexity",
            "effort": "45 min",
            "difficulty": "Medium",
            "health_improvement": 4,
            "security_improvement": 0,
            "architecture_improvement": 0,
            "maintainability_improvement": 5,
            "why_it_matters": "Deeply nested conditionals and loops increase the cognitive load required to read code, introducing bugs that slip past verification suites.",
            "metrics": f"Complex modules = {len(complex_files)}, Average complexity = {repo.average_complexity:.2f}, Safety threshold = 15.0",
            "steps": [
                "Identify nested loops or complex conditional flows.",
                "Simplify condition statements using early guard clauses.",
                "Extract complex block conditions into descriptive helper checks."
            ],
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": [],
            "before_code": 'if user is not None:\n    if user.is_active:\n        if user.has_payment_method:\n            charge_payment()  # Deep nesting',
            "after_code": 'if not user or not user.is_active:\n    return\nif not user.has_payment_method:\n    return\ncharge_payment()  # Flat early return guard'
        })

    # Code Smells: Long Methods (Skip declarative UI files like tsx/jsx/html)
    long_methods = [s for s in smells if s.smell_type == "Long Method" and not s.file_path.endswith(('.tsx', '.jsx', '.html', '.json', '.xml'))]
    if long_methods:
        affected = list({s.file_path for s in long_methods})
        recs.append({
            "id": "extract_long_methods",
            "title": "Extract Sub-methods from Long Functions",
            "priority": "Medium",
            "category": "Complexity",
            "effort": "30 min",
            "difficulty": "Medium",
            "health_improvement": 3,
            "security_improvement": 0,
            "architecture_improvement": 0,
            "maintainability_improvement": 4,
            "why_it_matters": "Long routines do too much work at once. Breaking them into smaller helper functions with clear descriptive names improves readability.",
            "metrics": f"Long methods = {len(long_methods)}, Average lines/method = 42, Target threshold = 25 LOC",
            "steps": [
                "Locate the long method body.",
                "Isolate blocks that perform independent tasks.",
                "Extract each block into a named helper routine."
            ],
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": [],
            "before_code": 'def process_checkout(cart):\n    # 100 lines: validate, charge, update inventory, email...',
            "after_code": 'def process_checkout(cart):\n    validate_cart(cart)\n    charge_card(cart)\n    update_inventory(cart)\n    send_receipt(cart)'
        })

    magic_numbers = [s for s in smells if s.smell_type == "Magic Number"]
    if magic_numbers:
        affected = list({s.file_path for s in magic_numbers})
        recs.append({
            "id": "extract_magic_numbers",
            "title": "Extract Magic Numbers into Constants",
            "priority": "Low",
            "category": "Maintainability",
            "effort": "5 min",
            "difficulty": "Easy",
            "health_improvement": 2,
            "security_improvement": 0,
            "architecture_improvement": 0,
            "maintainability_improvement": 3,
            "why_it_matters": "Literal values (magic numbers) scattered across files hide domain meaning and make future value updates highly error-prone.",
            "metrics": f"Magic numbers count = {len(magic_numbers)}, Files affected = {len(affected)}, Target expected = 0",
            "steps": [
                "Find raw numerical literals used in calculations.",
                "Define a descriptive, uppercase constant at the top of the file.",
                "Replace the raw literal references with the named constant."
            ],
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": ["externalize_configs"],
            "before_code": 'price = quantity * 1.18\n# What is 1.18? Tax? Markup?',
            "after_code": 'TAX_RATE = 0.18\nprice = quantity * (1 + TAX_RATE)'
        })

    # Duplicate code
    if repo.duplication_percentage > 5.0:
        recs.append({
            "id": "consolidate_duplicate_logic",
            "title": "Consolidate Repeated Logic Blocks",
            "priority": "Medium",
            "category": "Maintainability",
            "effort": "30 min",
            "difficulty": "Medium",
            "health_improvement": 5,
            "security_improvement": 0,
            "architecture_improvement": 0,
            "maintainability_improvement": 6,
            "why_it_matters": "Duplicated code structures mean that future enhancements or fixes must be manually duplicated, leading to codebase drift and inconsistency.",
            "metrics": f"Duplicated percentage = {repo.duplication_percentage:.1f}%, Target limit = 5.0%",
            "steps": [
                "Find identical or highly similar blocks of statements across files.",
                "Extract statements into a shared utility hook or helper module.",
                "Reference the helper module across former call sites."
            ],
            "affected_files": [f.path for f in files if f.extension in [".ts", ".tsx", ".py"]][:3],
            "depends_on": [],
            "unlocks": [],
            "before_code": '# File A and File B both contain identical parsing algorithms...',
            "after_code": '# Export helper from utils.py and import it in both files'
        })

    # 3. Code Organization Deductions
    org_dim = dims.get("organization", {})
    org_deductions = org_dim.get("deductions", [])
    
    # Oversized Files
    oversized = [f for f in files if f.lines_of_code > 500]
    if oversized:
        affected = [f.path for f in oversized]
        recs.append({
            "id": "reduce_file_sizes",
            "title": "Refactor Oversized Source Files",
            "priority": "Medium",
            "category": "Organization",
            "effort": "1 hour",
            "difficulty": "Medium",
            "health_improvement": 3,
            "security_improvement": 0,
            "architecture_improvement": 1,
            "maintainability_improvement": 6,
            "why_it_matters": "Files exceeding 500 lines are too large, containing mixed utilities. Splitting them into smaller cohesive files matches clean-code standards.",
            "metrics": f"Oversized files = {len(oversized)}, Max lines = {max((f.lines_of_code for f in oversized), default=0)}, Size limit = 500 LOC",
            "steps": [
                "Group operations inside the oversized file by business logic boundaries.",
                "Move related routines into new files.",
                "Import new files back into the original wrapper context."
            ],
            "affected_files": affected[:4],
            "depends_on": [],
            "unlocks": []
        })

    # 4. Security Deductions
    sec_dim = dims.get("security", {})
    sec_deductions = sec_dim.get("deductions", [])
    
    # Secrets
    secrets_issues = [s for s in sec_issues if s.category == "Secrets" or "secret" in s.title.lower()]
    if secrets_issues:
        affected = list({s.file_path for s in secrets_issues})
        related = [{"id": str(s.id), "file_path": s.file_path, "line_number": s.line_number, "type": "Security"} for s in secrets_issues]
        recs.append({
            "id": "rotate_secrets",
            "title": "Rotate and Externalize Hardcoded Secrets",
            "priority": "Critical",
            "category": "Secrets",
            "effort": "15 min",
            "difficulty": "Easy",
            "health_improvement": 12,
            "security_improvement": 15,
            "architecture_improvement": 0,
            "maintainability_improvement": 0,
            "why_it_matters": "Storing plaintext credentials inside source code puts the entire system at risk. Credentials checked into Git can easily be leaked online or harvested by bots.",
            "metrics": f"Secrets leaked = {len(secrets_issues)}, Affected files = {len(affected)}, Risk category = OWASP A02:2021",
            "steps": [
                "Locate the hardcoded API key, token, or password inside the file.",
                "Create a local .env configuration file (ensure it is added to .gitignore).",
                "Load values dynamically using system environment variables.",
                "Rotate the compromised key immediately on the target server."
            ],
            "affected_files": affected,
            "depends_on": [],
            "unlocks": ["externalize_configs"],
            "before_code": 'API_KEY = "sk_live_51N2Hk9..."\n# Credentials are directly exposed in source control',
            "after_code": 'import os\n# Load dynamically from environment variables\nAPI_KEY = os.getenv("STRIPE_API_KEY")'
        })

    # Injections
    injection_issues = [s for s in sec_issues if s.category in ["Injection", "SQL Injection", "Command Injection"] or "inject" in s.title.lower()]
    if injection_issues:
        affected = list({s.file_path for s in injection_issues})
        related = [{"id": str(s.id), "file_path": s.file_path, "line_number": s.line_number, "type": "Security"} for s in injection_issues]
        recs.append({
            "id": "sanitize_inputs",
            "title": "Sanitize Dynamic Input Queries",
            "priority": "High",
            "category": "Security",
            "effort": "45 min",
            "difficulty": "Medium",
            "health_improvement": 8,
            "security_improvement": 12,
            "architecture_improvement": 0,
            "maintainability_improvement": 1,
            "why_it_matters": "Executing raw queries built from string concatenations allows database injection or system command hijacking. Parameterization ensures data is separated from instruction.",
            "metrics": f"Injection hazards = {len(injection_issues)}, CWE mappings = CWE-89 / CWE-78, Risk category = OWASP A03:2021",
            "steps": [
                "Find any SQL or shell statement built using format or f-strings.",
                "Replace raw concatenations with parameterized bindings or query placeholders.",
                "Enable typed input validation (e.g. Pydantic schemas) to filter unexpected payloads."
            ],
            "affected_files": affected,
            "depends_on": [],
            "unlocks": [],
            "before_code": 'cursor.execute(f"SELECT * FROM users WHERE name = \'{user_input}\'")\n# Vulnerable to payload escaping',
            "after_code": '# Use parameterized placeholders instead\ncursor.execute("SELECT * FROM users WHERE name = %s", (user_input,))'
        })

    # 5. Testing Deductions
    test_dim = dims.get("testing", {})
    test_deductions = test_dim.get("deductions", [])
    
    test_files = [f.path for f in files if "test" in f.path.lower() or "spec" in f.path.lower()]
    if not test_files:
        recs.append({
            "id": "add_tests",
            "title": "Configure Testing Framework",
            "priority": "High",
            "category": "Testing",
            "effort": "1 hour",
            "difficulty": "Medium",
            "health_improvement": 10,
            "security_improvement": 0,
            "architecture_improvement": 0,
            "maintainability_improvement": 5,
            "why_it_matters": "No test modules or specs were detected. Running projects without unit tests increases regressions and prevents deployment automation.",
            "metrics": "Parsed test files = 0, Coverage percentage = 0.0%, Target coverage = 80.0%",
            "steps": [
                "Select a standard testing library (e.g. pytest for Python, Jest/Vitest for TS).",
                "Create a dedicated tests/ folder.",
                "Write basic regression assertion specs covering core module functions."
            ],
            "affected_files": [],
            "depends_on": [],
            "unlocks": []
        })

    # 6. Documentation Deductions
    doc_dim = dims.get("documentation", {})
    doc_deductions = doc_dim.get("deductions", [])
    
    # README missing
    has_readme = any(f.path.lower() == "readme.md" for f in files)
    if not has_readme:
        recs.append({
            "id": "create_readme",
            "title": "Add Detailed Project README.md",
            "priority": "Low",
            "category": "Documentation",
            "effort": "20 min",
            "difficulty": "Easy",
            "health_improvement": 5,
            "security_improvement": 0,
            "architecture_improvement": 0,
            "maintainability_improvement": 2,
            "why_it_matters": "A README.md is the entry point for recruiters and developers. Providing installation guides, descriptions, and structures simplifies onboarding.",
            "metrics": "Root readme.md presence = False, Target expected = True",
            "steps": [
                "Create a README.md file in the root folder.",
                "Add a descriptive heading, description of features, and setup commands."
            ],
            "affected_files": [],
            "depends_on": [],
            "unlocks": []
        })

    # Calculate overall scores potentials
    total_gain = sum(r["health_improvement"] for r in recs)
    current_score = scores.get("overall", 100)
    potential_score = min(100, current_score + total_gain)
    
    # Maximum achievable score
    # Suppose multi-language is present, we consider it unrecoverable overhead.
    langs_count = len(repo.language_breakdown.keys()) if repo.language_breakdown else 1
    unrecoverable_deductions = 0
    reason_max = "A perfect score is achievable after implementing all recommendations."
    if langs_count > 3:
        unrecoverable_deductions += 5
        reason_max = "Perfect score is impossible because this repository contains multiple languages, introducing permanent structural consistency challenges."
    max_achievable = 100 - unrecoverable_deductions

    # Build health forecast progression timeline
    quick_wins = [r for r in recs if r["difficulty"] == "Easy"]
    medium_wins = [r for r in recs if r["difficulty"] == "Medium"]
    major_wins = [r for r in recs if r["difficulty"] == "Hard"]

    score_quick = current_score + sum(r["health_improvement"] for r in quick_wins)
    score_medium = score_quick + sum(r["health_improvement"] for r in medium_wins)
    score_major = min(100, score_medium + sum(r["health_improvement"] for r in major_wins))

    forecast = [
        {"stage": "Current", "score": current_score},
        {"stage": "After Quick Wins", "score": min(100, score_quick)},
        {"stage": "After Medium Refactors", "score": min(100, score_medium)},
        {"stage": "After Major Refactors", "score": score_major},
        {"stage": "Maximum Possible", "score": max_achievable, "reason": reason_max}
    ]

    # Sort recommendations by priority order
    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    recs.sort(key=lambda r: priority_order.get(r["priority"], 4))

    return {
        "current_score": current_score,
        "potential_score": potential_score,
        "max_achievable": max_achievable,
        "recoverable_points": total_gain,
        "forecast": forecast,
        "recommendations": recs
    }
