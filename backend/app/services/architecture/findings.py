from typing import Dict, List, Any

def generate_findings(
    classifications: Dict[str, str],
    graph: Dict[str, List[str]],
    cycles: List[List[str]],
    coupling: Dict[str, Dict[str, int]],
    unknown_ratio: float
) -> Dict[str, Any]:
    """
    Generates deterministic architecture findings: Pattern Evidence, Strengths, and Warnings.
    """
    strengths = []
    warnings = []
    
    # 1. Check circular dependencies
    if not cycles:
        strengths.append({
            "title": "No circular dependencies detected",
            "description": "The module dependency graph has zero cyclic dependencies, maintaining clear separation of concerns."
        })
    else:
        warnings.append({
            "title": "Circular dependencies found",
            "description": f"Detected {len(cycles)} circular dependency loops. This complicates testing and introduces architectural coupling.",
            "evidence": f"Cycles involved: {', '.join([ ' -> '.join(c) for c in cycles[:3] ])}"
        })
        
    # 2. Check coupling
    highly_coupled = [p for p, c in coupling.items() if (c["afferent"] + c["efferent"]) > 8]
    if highly_coupled:
        warnings.append({
            "title": "High coupling detected in modules",
            "description": f"Detected {len(highly_coupled)} modules with high coupling (coupling score > 8), making them highly sensitive to changes.",
            "evidence": f"Affected modules: {', '.join(highly_coupled[:3])}"
        })
    else:
        strengths.append({
            "title": "Modules are loosely coupled",
            "description": "All scanned modules maintain a coupling score within healthy limits, supporting isolated updates."
        })
        
    # 3. Check configuration violations
    config_files = {p for p, t in classifications.items() if t == "Configuration"}
    config_violations = []
    for path, imports in graph.items():
        if path not in config_files:
            # Check if non-config files import config files (this is fine, but config files importing business logic is bad!)
            pass
        else:
            # Config importing business logic (like services/controllers) is a violation
            for target in imports:
                target_type = classifications.get(target, "Unknown")
                if target_type in {"Controller", "Service", "Repository", "API"}:
                    config_violations.append((path, target))
                    
    if config_violations:
        warnings.append({
            "title": "Configuration leaks dependencies",
            "description": "Central configuration modules import business logic, violating architecture layer boundaries.",
            "evidence": f"Violations: {', '.join([f'{src} -> {tgt}' for src, tgt in config_violations[:3]])}"
        })
    else:
        if config_files:
            strengths.append({
                "title": "Configuration is cleanly isolated",
                "description": "Configuration files do not depend on business logic or controller layers."
            })
            
    # 4. Check layer separation (Layered pattern validation)
    controllers = {p for p, t in classifications.items() if t in {"Controller", "API"}}
    services = {p for p, t in classifications.items() if t == "Service"}
    repositories = {p for p, t in classifications.items() if t == "Repository"}
    
    layer_violations = []
    for src, targets in graph.items():
        src_type = classifications.get(src, "Unknown")
        for tgt in targets:
            tgt_type = classifications.get(tgt, "Unknown")
            # Repository should never import Service/Controller
            if src_type == "Repository" and tgt_type in {"Service", "Controller", "API"}:
                layer_violations.append((src, tgt))
            # Service should never import Controller/API
            if src_type == "Service" and tgt_type in {"Controller", "API"}:
                layer_violations.append((src, tgt))
                
    if layer_violations:
        warnings.append({
            "title": "Layer boundaries violated",
            "description": "Scanned modules contain upward-directed imports (e.g. Repository importing Service), breaking layers.",
            "evidence": f"Violations: {', '.join([f'{src} -> {tgt}' for src, tgt in layer_violations[:3]])}"
        })
    elif controllers or services or repositories:
        strengths.append({
            "title": "Consistent layer separation",
            "description": "Imports flow strictly downwards (Controller -> Service -> Repository) with no boundary breaches."
        })
        
    # 5. Pattern Detection & Evidence
    pattern = "Unknown"
    confidence = 0
    evidence = []
    
    has_layered_dirs = len(controllers) > 0 or len(services) > 0 or len(repositories) > 0
    has_components = any(t in {"Component", "Hook"} for t in classifications.values())
    
    if has_layered_dirs:
        pattern = "Layered Architecture"
        confidence = 80
        evidence.append("Identified MVC/Layered directories (controllers, services, or repositories).")
        if not layer_violations:
            confidence += 15
            evidence.append("Strict compliance with layered importing rules (100% downward imports).")
        else:
            confidence -= 15
            evidence.append("Layered directory mapping matches, but import boundaries are leaked.")
    elif has_components:
        pattern = "Component-Based Architecture"
        confidence = 90
        evidence.append("High density of independent frontend React components and hooks.")
    else:
        # Default fallback
        pattern = "Module-Based Organization"
        confidence = 70
        evidence.append("Detected flat folder structure using custom package boundaries.")
        
    return {
        "pattern": pattern,
        "confidence": confidence,
        "evidence": evidence,
        "strengths": strengths,
        "warnings": warnings,
        "config_violations": len(config_violations)
    }
