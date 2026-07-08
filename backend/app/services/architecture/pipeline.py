import uuid
import time
import logging
import os
from datetime import datetime, timezone

from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.services.architecture.classifier import classify_file
from app.services.architecture.parser import extract_dependencies
from app.services.architecture.cycles import find_cycles
from app.services.architecture.scoring import calculate_architecture_score, calculate_architecture_grade
from app.services.architecture.findings import generate_findings

logger = logging.getLogger(__name__)

def analyze_architecture(repo_id: uuid.UUID, clone_path: str) -> None:
    db = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            return
            
        # Load all files
        
        # Load all files
        repo_files = db.query(RepositoryFile).filter(RepositoryFile.repository_id == repo_id).all()
        all_file_paths = {rf.path for rf in repo_files}
        
        file_contents = {}
        for rf in repo_files:
            if rf.is_text:
                abs_path = os.path.join(clone_path, rf.path)
                if os.path.isfile(abs_path):
                    try:
                        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                            file_contents[rf.path] = f.read()
                    except OSError:
                        pass
                        
        # Parse imports & Classify
        graph = {}
        classifications = {}
        
        for rf in repo_files:
            content = file_contents.get(rf.path, "")
            rf.module_type = classify_file(rf.path, rf.extension or "", content)
            classifications[rf.path] = rf.module_type
            
            if rf.is_text:
                deps = extract_dependencies(content, rf.path, rf.extension or "", all_file_paths)
                rf.outgoing_dependencies = deps
                graph[rf.path] = deps
            else:
                rf.outgoing_dependencies = []
                graph[rf.path] = []
                
        db.commit()
        
        # Step 3: Measuring coupling & cycles
        
        # Calculate incoming dependencies (Ca - Afferent)
        incoming = {p: [] for p in all_file_paths}
        for src, targets in graph.items():
            for tgt in targets:
                if tgt in incoming:
                    incoming[tgt].append(src)
                    
        for rf in repo_files:
            rf.incoming_dependencies = incoming[rf.path]
            
        db.commit()
        
        # Calculate cycles
        cycles = find_cycles(graph)
        cycle_participants = set()
        for cycle in cycles:
            for node in cycle:
                cycle_participants.add(node)
                
        for rf in repo_files:
            rf.in_dependency_cycle = rf.path in cycle_participants
            
        # Calculate coupling and instability
        coupling_stats = {}
        for rf in repo_files:
            ca = len(rf.incoming_dependencies)
            ce = len(rf.outgoing_dependencies)
            rf.coupling_score = ca + ce
            rf.instability_score = float(ce) / float(ca + ce) if (ca + ce) > 0 else 0.0
            coupling_stats[rf.path] = {"afferent": ca, "efferent": ce}
            
        db.commit()
        
        # Step 4: Calculate architecture health
        
        unknown_count = sum(1 for rf in repo_files if rf.module_type == "Unknown")
        total_count = len(repo_files) if len(repo_files) > 0 else 1
        unknown_ratio = float(unknown_count) / float(total_count)
        
        # Findings
        findings_data = generate_findings(classifications, graph, cycles, coupling_stats, unknown_ratio)
        
        # Score
        highly_coupled_count = sum(1 for rf in repo_files if rf.coupling_score > 8)
        score = calculate_architecture_score(
            cycle_count=len(cycles),
            highly_coupled_count=highly_coupled_count,
            config_violation_count=findings_data.get("config_violations", 0),
            unknown_ratio=unknown_ratio
        )
        grade = calculate_architecture_grade(score)
        
        # Dependency Statistics
        total_edges = sum(len(targets) for targets in graph.values())
        avg_imports = float(total_edges) / float(total_count)
        
        highest_fan_in_rf = max(repo_files, key=lambda rf: len(rf.incoming_dependencies), default=None)
        highest_fan_out_rf = max(repo_files, key=lambda rf: len(rf.outgoing_dependencies), default=None)
        most_coupled_rf = max(repo_files, key=lambda rf: rf.coupling_score, default=None)
        
        # Compute Largest Dependency Chain
        largest_chain = 0
        memo = {}
        def get_max_depth(node: str, visited_nodes: set) -> int:
            if node in memo: return memo[node]
            if node in visited_nodes: return 0  # Break cycle
            max_d = 0
            visited_nodes.add(node)
            for neighbor in graph.get(node, []):
                max_d = max(max_d, get_max_depth(neighbor, visited_nodes))
            visited_nodes.remove(node)
            memo[node] = 1 + max_d
            return memo[node]
            
        for node in graph:
            largest_chain = max(largest_chain, get_max_depth(node, set()))
            
        summary_data = {
            "pattern": findings_data["pattern"],
            "confidence": findings_data["confidence"],
            "evidence": findings_data["evidence"],
            "total_modules": total_count,
            "entry_points": sum(1 for rf in repo_files if len(rf.incoming_dependencies) == 0 and rf.is_text),
            "cycles_count": len(cycles),
            "most_coupled_module": most_coupled_rf.path if most_coupled_rf else "None",
            "stats": {
                "total_edges": total_edges,
                "average_imports": round(avg_imports, 2),
                "highest_fan_in": highest_fan_in_rf.path if highest_fan_in_rf else "None",
                "highest_fan_out": highest_fan_out_rf.path if highest_fan_out_rf else "None",
                "largest_chain": largest_chain,
                "highest_coupling_score": most_coupled_rf.coupling_score if most_coupled_rf else 0
            },
            "cycles_list": cycles
        }
        
        # Step 5: Finalizing architecture overview
        
        repo.architecture_score = score
        repo.architecture_grade = grade
        repo.architecture_summary = summary_data
        repo.architecture_findings = {
            "strengths": findings_data["strengths"],
            "warnings": findings_data["warnings"]
        }
        db.commit()
        logger.info(f"Architecture Explorer complete for {repo_id} - Score: {score}")
        
    except Exception as e:
        logger.error(f"Architecture scan failed: {e}", exc_info=True)
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.error_message = f"Architecture scan error: {str(e)}"
            db.commit()
    finally:
        db.close()
