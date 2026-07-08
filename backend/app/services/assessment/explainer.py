"""
Assessment explainability engine.
Fleshes out detailed, traceable bonuses and deductions from scorer results.
"""

from typing import Dict, List, Any

def generate_explanations(
    files: List[Any],
    smells: List[Any],
    security_issues: List[Any],
    architecture_knowledge: Dict[str, Any],
    tech_stack: Dict[str, Any],
    scoring_output: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Builds structured explainability datasets detailing bonuses, deductions, rules,
    thresholds, measured values, and evidence mappings.
    """
    overall_score = scoring_output["overall"]
    dimensions = scoring_output["dimensions"]
    
    overall_breakdown = []
    overall_breakdown.append({
        "type": "start",
        "name": "Base Score Baseline",
        "value": 100,
        "symbol": "start"
    })
    
    detailed_explanations = {}
    
    # Trace each dimension's bonuses and deductions
    for dim_name, dim_data in dimensions.items():
        dim_bonuses = []
        dim_deductions = []
        
        # Structure bonuses
        for b in dim_data.get("bonuses", []):
            bonus_obj = {
                "name": b["name"],
                "score": b["score"],
                "reason": b["reason"],
                "evidence": {
                    "type": "project" if "README" in b["name"] or "Framework" in b["name"] else "symbol",
                    "path": "README.md" if "README" in b["name"] else "package.json",
                    "detail": b["reason"]
                }
            }
            dim_bonuses.append(bonus_obj)
            
            # Map dimension impact to overall breakdown
            overall_breakdown.append({
                "type": "bonus",
                "name": b["name"],
                "value": b["score"],
                "symbol": "+"
            })
            
        # Structure deductions
        for d in dim_data.get("deductions", []):
            affected_files = d.get("affected_files", [])
            evidence_refs = []
            
            # Link evidence
            if affected_files:
                for path in affected_files:
                    evidence_refs.append({
                        "type": "file",
                        "path": path,
                        "line": 1,
                        "detail": f"Violation identified in file: {path}"
                    })
            else:
                evidence_refs.append({
                    "type": "project",
                    "path": "",
                    "detail": d["reason"]
                })
                
            deduction_obj = {
                "name": d["name"],
                "score": d["score"],
                "reason": d["reason"],
                "rule_triggered": d.get("name", "Threshold Violation"),
                "threshold": d.get("threshold", "N/A"),
                "measured": d.get("measured", "N/A"),
                "affected_files": affected_files,
                "evidence_references": evidence_refs
            }
            dim_deductions.append(deduction_obj)
            
            overall_breakdown.append({
                "type": "deduction",
                "name": d["name"],
                "value": d["score"],
                "symbol": "-"
            })
            
        detailed_explanations[dim_name] = {
            "score": dim_data["score"],
            "grade": dim_data["grade"],
            "bonuses": dim_bonuses,
            "deductions": dim_deductions
        }
        
    # Inject security findings as deductions if any
    sec_deductions = []
    if len(security_issues) > 0:
        sec_points = int(len(security_issues) * 3)
        overall_breakdown.append({
            "type": "deduction",
            "name": "Security Issues",
            "value": -sec_points,
            "symbol": "-"
        })
        for issue in security_issues:
            sec_deductions.append({
                "name": f"Security finding: {issue.category}",
                "score": -3,
                "reason": issue.reason or issue.title,
                "rule_triggered": "Unsafe API, credentials, or injection hazard detected",
                "threshold": 0,
                "measured": 1,
                "affected_files": [issue.file_path] if issue.file_path else [],
                "evidence_references": [{
                    "type": "security_issue",
                    "path": issue.file_path or "",
                    "line": issue.line_number or 1,
                    "detail": f"Category: {issue.category}. Severity: {issue.severity}"
                }]
            })
    detailed_explanations["security"]["deductions"] = sec_deductions
    
    # Compile final result in the breakdown
    overall_breakdown.append({
        "type": "final",
        "name": "Final Deterministic Score",
        "value": overall_score,
        "symbol": "final"
    })
    
    return {
        "overall_score": overall_score,
        "overall_breakdown": overall_breakdown,
        "explanations": detailed_explanations
    }
