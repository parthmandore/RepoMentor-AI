"""
File contribution analysis engine.
Determines positive and negative file contributors based on metrics, test specs, and smells.
"""

from typing import List, Dict, Any

def analyze_contributors(
    files: List[Any],
    smells: List[Any],
    architecture_knowledge: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns positive and negative file contributors.
    """
    positives = []
    negatives = []
    
    # 1. Check for README
    readme = next((f for f in files if f.path.lower() == "readme.md"), None)
    if readme:
        positives.append({
            "file": "README.md",
            "impact": 8,
            "reason": "Excellent Documentation",
            "evidence": {
                "type": "file",
                "path": "README.md",
                "line": 1,
                "detail": f"README file size is {readme.size_bytes} bytes."
            }
        })
        
    # 2. Check for Test files
    test_files = [f for f in files if "test" in f.path.lower() or "spec" in f.path.lower()]
    for tf in test_files[:4]:
        positives.append({
            "file": tf.path.split("/")[-1],
            "impact": 5,
            "reason": "Strong Testing Support",
            "evidence": {
                "type": "file",
                "path": tf.path,
                "line": 1,
                "detail": f"Test suite containing {tf.lines_of_code} LOC."
            }
        })
        
    # 3. Clean files (0 smells, low complexity)
    clean_files = [f for f in files if f.complexity in [1, 2] and f.lines_of_code < 100]
    # Filter out test files and README
    clean_files = [f for f in clean_files if f not in test_files and f.path.lower() != "readme.md"]
    for cf in clean_files[:4]:
        positives.append({
            "file": cf.path.split("/")[-1],
            "impact": 3,
            "reason": "Clean Code Structure",
            "evidence": {
                "type": "file",
                "path": cf.path,
                "line": 1,
                "detail": f"Complexity: {cf.complexity}. Lines: {cf.lines_of_code}."
            }
        })
        
    # 4. God classes / oversized files
    god_files = [f for f in files if f.lines_of_code > 300]
    for gf in god_files[:4]:
        negatives.append({
            "file": gf.path.split("/")[-1],
            "impact": -7,
            "reason": "High Complexity",
            "evidence": {
                "type": "file",
                "path": gf.path,
                "line": 1,
                "detail": f"God class module contains {gf.lines_of_code} lines of code."
            }
        })
        
    # 5. Smelly files
    smelly_paths = set(s.file_path for s in smells if s.file_path)
    for path in smelly_paths:
        file_smells = [s for s in smells if s.file_path == path]
        first_smell = file_smells[0]
        # Skip if already marked as god file to avoid duplicates
        if any(gf.path == path for gf in god_files):
            continue
        negatives.append({
            "file": path.split("/")[-1],
            "impact": -5,
            "reason": f"Active Smell: {first_smell.smell_type}",
            "evidence": {
                "type": "smell",
                "path": path,
                "line": first_smell.line_number or 1,
                "detail": first_smell.reason
            }
        })
        
    # 6. Circular dependency elements
    cycles = architecture_knowledge.get("circular_dependencies", [])
    cycle_nodes = set(node for cycle in cycles for node in cycle)
    for node in cycle_nodes:
        # Check if already added
        if any(n["file"] == node.split("/")[-1] for n in negatives):
            continue
        negatives.append({
            "file": node.split("/")[-1],
            "impact": -5,
            "reason": "Circular Dependency Node",
            "evidence": {
                "type": "architecture_node",
                "path": node,
                "line": 1,
                "detail": "Participates in a circular import coupling loop."
            }
        })
        
    # Sort lists
    positives = sorted(positives, key=lambda x: x["impact"], reverse=True)
    negatives = sorted(negatives, key=lambda x: x["impact"])
    
    return {
        "positive_contributors": positives,
        "negative_contributors": negatives
    }
