import uuid
from typing import List, Dict, Any
from collections import defaultdict

def build_evidence_documents(
    repo_data: Dict[str, Any],
    file_metrics: List[Dict[str, Any]],
    smells: List[Dict[str, Any]],
    sec_issues: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Standardize code quality, architecture, security, and technology facts into common evidence schema.
    Optimizes performance by grouping issues by file to prevent chunk bloat and watchdog timeouts.
    """
    docs = []
    repo_id_str = str(repo_data.get("id"))
    
    # 1. Repository Summary Document
    docs.append({
        "document_id": str(uuid.uuid4()),
        "document_type": "Repository Summary",
        "title": "Repository Overview Metrics",
        "summary": "Deterministic size and file statistics captured during discover engine scan.",
        "evidence": f"Total Files: {repo_data.get('total_files')}, Total Folders: {repo_data.get('total_folders')}, Text Files: {repo_data.get('text_file_count')}, Binary Files: {repo_data.get('binary_file_count')}",
        "source_phase": "Phase 2: Repository Ingestion Pipeline",
        "source_file": "README.md",
        "metadata": {
            "repo_id": repo_id_str,
            "type": "summary"
        }
    })
    
    # 2. Technology Stack Document
    tech_stack = repo_data.get("tech_stack") or {}
    docs.append({
        "document_id": str(uuid.uuid4()),
        "document_type": "Technology Detection",
        "title": "Detected Technology Stack",
        "summary": "Identified frameworks, package managers, and language percentages.",
        "evidence": f"Languages: {repo_data.get('language_breakdown')}, Frameworks: {tech_stack.get('frameworks')}, Package Manager: {tech_stack.get('package_manager')}",
        "source_phase": "Phase 2: Repository Ingestion Pipeline",
        "source_file": "package.json / requirements.txt",
        "metadata": {
            "repo_id": repo_id_str,
            "type": "technology"
        }
    })
    
    # 3. Engineering Assessment Summary
    docs.append({
        "document_id": str(uuid.uuid4()),
        "document_type": "Engineering Assessment",
        "title": "Code Quality Metrics Summary",
        "summary": f"Health score is {repo_data.get('health_score')} (Grade {repo_data.get('health_grade')}) with average complexity {repo_data.get('average_complexity')}.",
        "evidence": f"Total LOC: {repo_data.get('total_lines_of_code')}, Avg Complexity: {repo_data.get('average_complexity')}, Max Complexity: {repo_data.get('max_complexity')}, Duplication: {repo_data.get('duplication_percentage')}%, Code Smells: {repo_data.get('total_smells')}",
        "source_phase": "Phase 3: Deterministic Analysis Engine",
        "source_file": "aggregator.py",
        "metadata": {
            "repo_id": repo_id_str,
            "type": "metrics_summary"
        }
    })
    
    # 4. Detailed Code Smells Grouped by File
    smells_by_file = defaultdict(list)
    for smell in smells:
        if smell.get("smell_type") == "Magic Number":
            continue  # Skip magic numbers in RAG vector database to prevent massive bloat and timeouts
        smells_by_file[smell.get("file_path", "unknown")].append(smell)
        
    for file_path, file_smells in smells_by_file.items():
        # Group smells in batches of 15 to keep chunk sizes reasonable and prevent timeout
        smell_batch_size = 15
        for idx in range(0, len(file_smells), smell_batch_size):
            batch = file_smells[idx:idx+smell_batch_size]
            evidence_lines = []
            for s in batch:
                evidence_lines.append(
                    f"- Line {s.get('line_number')}: {s.get('smell_type')} - {s.get('reason')} (Value: {s.get('measured_value')}, Threshold: {s.get('threshold')})"
                )
            
            docs.append({
                "document_id": str(uuid.uuid4()),
                "document_type": "Engineering Assessment",
                "title": f"Code Smells for {file_path} (Part {idx//smell_batch_size + 1})",
                "summary": f"Detected code quality issues and smells in {file_path}.",
                "evidence": "\n".join(evidence_lines),
                "source_phase": "Phase 3: Deterministic Analysis Engine",
                "source_file": file_path,
                "metadata": {
                    "repo_id": repo_id_str,
                    "category": "Code Quality",
                    "severity": "Grouped",
                    "type": "smells_list"
                }
            })
        
    # 5. Architecture Summary
    arch_sum = repo_data.get("architecture_summary") or {}
    docs.append({
        "document_id": str(uuid.uuid4()),
        "document_type": "Architecture Findings",
        "title": "Software Architecture Structure",
        "summary": f"Identified pattern: {arch_sum.get('pattern')} with {arch_sum.get('confidence')}% confidence. Health: {repo_data.get('architecture_score')} (Grade {repo_data.get('architecture_grade')}).",
        "evidence": f"Total Modules: {arch_sum.get('total_modules')}, Entry Points: {arch_sum.get('entry_points')}, Dependency Cycles: {arch_sum.get('cycles_count')}, Most Coupled: {arch_sum.get('most_coupled_module')}",
        "source_phase": "Phase 4: Software Architecture Explorer",
        "source_file": "pipeline.py",
        "metadata": {
            "repo_id": repo_id_str,
            "type": "architecture_summary"
        }
    })
    
    # 6. Detailed Security Issues Grouped by File
    sec_by_file = defaultdict(list)
    for sec in sec_issues:
        sec_by_file[sec.get("file_path", "unknown")].append(sec)
        
    for file_path, file_sec in sec_by_file.items():
        # Group issues in batches of 15 to keep chunk sizes reasonable and prevent timeout
        sec_batch_size = 15
        for idx in range(0, len(file_sec), sec_batch_size):
            batch = file_sec[idx:idx+sec_batch_size]
            evidence_lines = []
            for s in batch:
                evidence_lines.append(
                    f"- Line {s.get('line_number')}: {s.get('title')} - {s.get('reason')} (Evidence: {s.get('evidence')})"
                )
                
            docs.append({
                "document_id": str(uuid.uuid4()),
                "document_type": "Security Findings",
                "title": f"Security Vulnerabilities for {file_path} (Part {idx//sec_batch_size + 1})",
                "summary": f"Detected security reviews and issues in {file_path}.",
                "evidence": "\n".join(evidence_lines),
                "source_phase": "Phase 5: Security Review Engine",
                "source_file": file_path,
                "metadata": {
                    "repo_id": repo_id_str,
                    "category": "Security",
                    "severity": "Grouped",
                    "type": "security_list"
                }
            })
        
    return docs
