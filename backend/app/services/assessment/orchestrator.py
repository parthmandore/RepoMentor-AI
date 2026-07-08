"""
Engineering Assessment Orchestrator.
Coordinates scorer, explainer, simulator, contributors, improvements, narrative, and confidence calculators.
"""

import time
import uuid
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.code_smell import CodeSmell
from app.models.security_issue import SecurityIssue

from app.services.assessment.scorer import calculate_dimensions
from app.services.assessment.explainer import generate_explanations
from app.services.assessment.improvements import generate_recommendations
from app.services.assessment.contributors import analyze_contributors
from app.services.assessment.confidence import calculate_confidence
from app.services.assessment.benchmark import get_benchmarks
from app.services.assessment.narrative_gen import generate_narrative_report
from app.services.analysis.principles import analyze_principles

def run_assessment(db: Session, repository_id: uuid.UUID) -> Dict[str, Any]:
    """
    Orchestrates the complete Phase 7 assessment generation.
    Returns the full structured assessment dictionary.
    """
    start_time = time.perf_counter()
    warnings = []
    
    # 1. Load repository and its assets
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repo:
        raise ValueError("Repository not found")
        
    files = db.query(RepositoryFile).filter(RepositoryFile.repository_id == repository_id).all()
    smells = db.query(CodeSmell).filter(CodeSmell.repository_id == repository_id).all()
    sec_issues = db.query(SecurityIssue).filter(SecurityIssue.repository_id == repository_id).all()
    
    # Extract architecture summary
    arch_summary = repo.architecture_summary or {}
    tech_stack = repo.tech_stack or {}
    
    # 2. Run deterministic scoring
    t0 = time.perf_counter()
    try:
        scores = calculate_dimensions(
            files=files,
            smells=smells,
            security_issues=sec_issues,
            architecture_knowledge=arch_summary,
            tech_stack=tech_stack,
            security_score_from_repo=repo.security_score
        )
    except Exception as e:
        logger.error(f"Error in calculate_dimensions: {e}", exc_info=True)
        warnings.append(f"Scoring engine error: {str(e)}")
        scores = {
            "overall": 50,
            "grade": "D",
            "dimensions": {
                k: {"score": 50, "grade": "D", "bonuses": [], "deductions": []}
                for k in ["architecture", "maintainability", "organization", "consistency", "security", "testing", "documentation"]
            }
        }
    duration_scoring = int((time.perf_counter() - t0) * 1000)
    logger.info(f"Assessment stage 'scoring' complete in {duration_scoring}ms")
    
    # 3. Run explainability engine
    t0 = time.perf_counter()
    try:
        explanations = generate_explanations(
            files=files,
            smells=smells,
            security_issues=sec_issues,
            architecture_knowledge=arch_summary,
            tech_stack=tech_stack,
            scoring_output=scores
        )
    except Exception as e:
        logger.error(f"Error in generate_explanations: {e}", exc_info=True)
        warnings.append(f"Explainability engine error: {str(e)}")
        explanations = {
            "overall_score": scores["overall"],
            "overall_breakdown": [{"type": "final", "name": "Final Deterministic Score", "value": scores["overall"], "symbol": "final"}],
            "explanations": {
                k: {"score": 50, "grade": "D", "bonuses": [], "deductions": []}
                for k in ["architecture", "maintainability", "organization", "consistency", "security", "testing", "documentation"]
            }
        }
    duration_explainer = int((time.perf_counter() - t0) * 1000)
    logger.info(f"Assessment stage 'explainability' complete in {duration_explainer}ms")
    
    # 4. Run file contribution engine
    t0 = time.perf_counter()
    try:
        contributors = analyze_contributors(
            files=files,
            smells=smells,
            architecture_knowledge=arch_summary
        )
    except Exception as e:
        logger.error(f"Error in analyze_contributors: {e}", exc_info=True)
        warnings.append(f"Contributors analysis error: {str(e)}")
        contributors = {"positive_contributors": [], "negative_contributors": []}
    duration_contributors = int((time.perf_counter() - t0) * 1000)
    logger.info(f"Assessment stage 'contributors' complete in {duration_contributors}ms")
    
    # 5. Run improvements simulator roadmap
    t0 = time.perf_counter()
    try:
        roadmap = generate_recommendations(
            files=files,
            smells=smells,
            security_issues=sec_issues,
            architecture_knowledge=arch_summary
        )
    except Exception as e:
        logger.error(f"Error in generate_recommendations: {e}", exc_info=True)
        warnings.append(f"Refactoring recommendations error: {str(e)}")
        roadmap = []
    duration_roadmap = int((time.perf_counter() - t0) * 1000)
    logger.info(f"Assessment stage 'roadmap' complete in {duration_roadmap}ms")
    
    # 6. Run confidence calculator
    t0 = time.perf_counter()
    try:
        has_readme = any(f.path.lower() == "readme.md" for f in files)
        confidence_obj = calculate_confidence(
            files=files,
            tech_stack=tech_stack,
            repo_status=repo.status.value if repo.status else "ready",
            knowledge_status=repo.knowledge_status or "completed",
            security_status="completed" if repo.security_findings else "pending",
            architecture_status="completed" if repo.architecture_findings else "pending",
            has_readme=has_readme
        )
    except Exception as e:
        logger.error(f"Error in calculate_confidence: {e}", exc_info=True)
        warnings.append(f"Confidence calculation error: {str(e)}")
        confidence_obj = {"confidence_percentage": 50, "reasons": ["Fallback confidence estimation"]}
    duration_confidence = int((time.perf_counter() - t0) * 1000)
    logger.info(f"Assessment stage 'confidence' complete in {duration_confidence}ms")
    
    # 7. Run static benchmarks comparison
    t0 = time.perf_counter()
    try:
        benchmarks = get_benchmarks(scores["overall"])
    except Exception as e:
        logger.error(f"Error in get_benchmarks: {e}", exc_info=True)
        warnings.append(f"Benchmark comparisons error: {str(e)}")
        benchmarks = {"categories": {}, "explanation": "Fallback benchmark comparison data"}
    duration_benchmarks = int((time.perf_counter() - t0) * 1000)
    logger.info(f"Assessment stage 'benchmarks' complete in {duration_benchmarks}ms")
    
    # 7b. Run SOLID principles engine
    t0 = time.perf_counter()
    try:
        principles = analyze_principles(
            files=files,
            smells=smells,
            architecture_knowledge=arch_summary,
            duplication_percentage=repo.duplication_percentage
        )
    except Exception as e:
        logger.error(f"Error in analyze_principles: {e}", exc_info=True)
        warnings.append(f"Principles engine error: {str(e)}")
        principles = []
    duration_principles = int((time.perf_counter() - t0) * 1000)
    logger.info(f"Assessment stage 'principles' complete in {duration_principles}ms")
    
    # 8. Run AI narrative review generator
    t0 = time.perf_counter()
    try:
        narrative = generate_narrative_report(
            repo_url=repo.url,
            scores_data=scores,
            smells=smells,
            security_issues=sec_issues,
            tech_stack=tech_stack
        )
    except Exception as e:
        logger.error(f"Error in generate_narrative_report: {e}", exc_info=True)
        warnings.append(f"Narrative review generation error: {str(e)}")
        from app.services.assessment.narrative_gen import generate_deterministic_fallback
        narrative = generate_deterministic_fallback(
            repo_url=repo.url,
            scores_data=scores,
            smells=smells,
            security_issues=sec_issues,
            languages=list(tech_stack.get("languages", {}).keys()) if tech_stack else ["Unknown"]
        )
    duration_narrative = int((time.perf_counter() - t0) * 1000)
    logger.info(f"Assessment stage 'narrative' complete in {duration_narrative}ms")
    
    # 9. Track execution duration
    end_time = time.perf_counter()
    duration_ms = int((end_time - start_time) * 1000)
    
    # 10. Assemble structured payload with metadata
    assessment_payload = {
        "metadata": {
            "version": "7.5",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": "deterministic-v2",
            "llm_model": "llama3",
            "knowledge_version": "1.0",
            "assessment_duration_ms": duration_ms,
            "stage_durations_ms": {
                "scoring": duration_scoring,
                "explainability": duration_explainer,
                "contributors": duration_contributors,
                "roadmap": duration_roadmap,
                "confidence": duration_confidence,
                "benchmarks": duration_benchmarks,
                "principles": duration_principles,
                "narrative": duration_narrative
            },
            "warnings": warnings
        },
        "scores": scores,
        "explanations": explanations,
        "contributors": contributors,
        "roadmap": roadmap,
        "confidence": confidence_obj,
        "benchmarks": benchmarks,
        "principles": principles,
        "narrative": narrative
    }
    
    # 11. Store back under repo.knowledge_summary["assessment"]
    summary = dict(repo.knowledge_summary or {})
    
    # Preserve score history evolution (Task 9 Evolution tracking)
    history = summary.get("history", [])
    history.append({
        "generated_at": assessment_payload["metadata"]["generated_at"],
        "overall_score": scores["overall"],
        "dimension_scores": {k: v["score"] for k, v in scores["dimensions"].items()},
        "smells_count": len(smells),
        "vulnerabilities_count": len(sec_issues)
    })
    # Keep only last 10 runs
    summary["history"] = history[-10:]
    summary["assessment"] = assessment_payload
    repo.knowledge_summary = summary
    db.commit()
    
    return assessment_payload
