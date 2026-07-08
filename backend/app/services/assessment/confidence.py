"""
Assessment confidence calculator.
Yields a percentage (0-100) and reasoning detail based on file coverage,
languages, knowledge graph completeness, and security scan states.
"""

from typing import List, Dict, Any

def calculate_confidence(
    files: List[Any],
    tech_stack: Dict[str, Any],
    repo_status: str,
    knowledge_status: str,
    security_status: str,
    architecture_status: str,
    has_readme: bool
) -> Dict[str, Any]:
    """
    Computes score confidence based on metrics completeness.
    """
    confidence = 100.0
    reasons = []
    
    # 1. Check analyzed files count
    total_files = len(files)
    if total_files == 0:
        confidence -= 50.0
        reasons.append("Empty repository or no files successfully parsed.")
    elif total_files < 3:
        confidence -= 15.0
        reasons.append("Very small repository size restricts pattern extraction.")
        
    # 2. Check languages coverage
    if tech_stack:
        langs = tech_stack.get("languages", {})
        # If there is a language with "Unknown" or unsupported extensions
        if "Unknown" in langs or not langs:
            confidence -= 15.0
            reasons.append("Repository contains unsupported or unknown programming languages.")
            
    # 3. Check knowledge base status
    if knowledge_status != "completed":
        confidence -= 20.0
        reasons.append("Knowledge Graph indexing has not fully completed.")
        
    # 4. Check security scan status
    if security_status != "completed":
        confidence -= 10.0
        reasons.append("Security vulnerabilities scan did not complete or was skipped.")
        
    # 5. Check readme presence
    if not has_readme:
        confidence -= 10.0
        reasons.append("Missing README.md makes onboarding review lower accuracy.")
        
    confidence = max(10.0, min(100.0, confidence))
    
    if not reasons:
        reasons.append("Repository fully analyzed. Knowledge graph and security scans completed with high coverage.")
        
    return {
        "confidence_percentage": int(confidence),
        "reasons": reasons
    }
