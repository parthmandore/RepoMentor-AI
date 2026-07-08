"""
Evidence Linker module.
Resolves visual anchor links for scores, smells, security findings, and roadmap items.
"""

from typing import Dict, Any

def link_evidence(
    item_type: str,
    path: str,
    line: int = 1,
    detail: str = ""
) -> Dict[str, Any]:
    """
    Constructs a traceable evidence link object.
    Valid item_types: 'file', 'symbol', 'smell', 'security_issue', 'architecture_node'
    """
    return {
        "type": item_type,
        "path": path,
        "line": line,
        "detail": detail,
        "link": f"/repositories/files/{path}?line={line}" if item_type in ["file", "symbol", "smell", "security_issue"] else f"/repositories/architecture?node={path}"
    }
