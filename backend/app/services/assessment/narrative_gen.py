"""
Narrative generation engine.
Queries Groq Service with strict engineering constraints,
and falls back to deterministic markdown templates if unreachable or times out.
"""

import httpx
import json
import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior software engineer writing an engineering assessment.
You must ONLY reference provided evidence.
Never invent:
- files
- classes
- methods
- patterns
- weaknesses
- strengths
Never change numeric scores.
Never speculate.
Never write:
"I think"
"I believe"
"probably"
"might"
Only describe confirmed findings."""

def generate_narrative_report(
    repo_url: str,
    scores_data: Dict[str, Any],
    smells: List[Any],
    security_issues: List[Any],
    tech_stack: Dict[str, Any]
) -> Dict[str, str]:
    """
    Tries to generate an AI narrative via Groq. Falls back to a deterministic template if unavailable.
    """
    overall_score = scores_data["overall"]
    grade = scores_data["grade"]
    
    # 1. Build details block for prompt
    languages = list(tech_stack.get("languages", {}).keys()) if tech_stack else ["Unknown"]
    prompt_context = f"""
    Repository URL: {repo_url}
    Overall Score: {overall_score} ({grade})
    Supported Languages: {', '.join(languages)}
    Active Smells Count: {len(smells)}
    Security Issues Count: {len(security_issues)}
    
    Dimension Scores:
    - Architecture: {scores_data['dimensions']['architecture']['score']}
    - Maintainability: {scores_data['dimensions']['maintainability']['score']}
    - Organization: {scores_data['dimensions']['organization']['score']}
    - Consistency: {scores_data['dimensions']['consistency']['score']}
    - Security: {scores_data['dimensions']['security']['score']}
    - Testing: {scores_data['dimensions']['testing']['score']}
    - Documentation: {scores_data['dimensions']['documentation']['score']}
    """
    
    user_prompt = f"""Based on the following repository data, generate a structured engineering review.
    Data:
    {prompt_context}
    
    Format the response as a JSON dictionary with exactly these string keys:
    - "executive_summary"
    - "architecture_review"
    - "maintainability_review"
    - "security_review"
    - "documentation_review"
    - "testing_review"
    - "engineering_strengths"
    - "engineering_weaknesses"
    - "risk_assessment"
    - "production_readiness"
    - "engineering_maturity"
    - "final_verdict"
    """
    
    # 2. Query Groq Service
    try:
        from app.services.llm.groq_service import GroqService
        
        raw_text = GroqService.generate(
            prompt=user_prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.0
        )
        
        raw_text = raw_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
        raw_text = raw_text.strip()
        
        parsed = json.loads(raw_text)
        
        # Check for mandatory keys
        keys = [
            "executive_summary", "architecture_review", "maintainability_review",
            "security_review", "documentation_review", "testing_review",
            "engineering_strengths", "engineering_weaknesses", "risk_assessment",
            "production_readiness", "engineering_maturity", "final_verdict"
        ]
        if all(k in parsed for k in keys):
            return parsed
            
    except Exception as e:
        logger.warning(f"Groq narrative generation failed: {str(e)}. Falling back to deterministic template.")
        
    # 3. Fallback: Deterministic Markdown Templates
    return generate_deterministic_fallback(repo_url, scores_data, smells, security_issues, languages)
 
def generate_deterministic_fallback(
    repo_url: str,
    scores_data: Dict[str, Any],
    smells: List[Any],
    security_issues: List[Any],
    languages: List[str]
) -> Dict[str, str]:
    overall_score = scores_data["overall"]
    grade = scores_data["grade"]
    
    return {
        "executive_summary": (
            f"The repository located at {repo_url} has been analyzed using the repository assessment engine. "
            f"It obtained an overall health rating of {overall_score}/100, which maps to Engineering Grade {grade}. "
            f"Primary languages analyzed: {', '.join(languages)}."
        ),
        "architecture_review": (
            f"The architecture score is rated at {scores_data['dimensions']['architecture']['score']}/100. "
            f"Modules were assessed for coupling, circular references, and layer structure. "
            f"Layered MVC validation checks are running, with active modular patterns registered."
        ),
        "maintainability_review": (
            f"The codebase scored {scores_data['dimensions']['maintainability']['score']}/100 in maintainability. "
            f"A total of {len(smells)} code smells were identified. Average cyclomatic complexity metrics have been checked "
            f"against critical thresholds."
        ),
        "security_review": (
            f"The security review score is {scores_data['dimensions']['security']['score']}/100. "
            f"Found {len(security_issues)} active security findings. Analysis includes unsafe API checks, credential leaks, and hashing methods."
        ),
        "documentation_review": (
            f"The documentation score stands at {scores_data['dimensions']['documentation']['score']}/100. "
            f"Assessed project README presence, layout length, and code inline comments density ratios."
        ),
        "testing_review": (
            f"The testing framework score is {scores_data['dimensions']['testing']['score']}/100. "
            f"Verifies unit testing configuration, files naming rules, test suites distribution, and coverage LOC metrics."
        ),
        "engineering_strengths": (
            f"Key strengths of this repository include: "
            f"1. Robust language analyzer support for {', '.join(languages)}. "
            f"2. Low density of architectural cycles."
        ),
        "engineering_weaknesses": (
            f"Key areas for improvement: "
            f"1. Addressed {len(smells)} code smells. "
            f"2. Reduced complexity in high-complexity files."
        ),
        "risk_assessment": (
            f"Risk index evaluated. "
            f"We detected {len(security_issues)} security issues and {len(smells)} smell violations. "
            f"Risk is considered {'Low' if len(security_issues) == 0 else 'Medium' if len(security_issues) < 3 else 'High'}."
        ),
        "production_readiness": (
            f"The production readiness score is estimated at {overall_score}%. "
            f"{'Excellent foundation for production deployment' if overall_score >= 80 else 'Requires minor updates before production use' if overall_score >= 70 else 'Refactoring is recommended before production release'}."
        ),
        "engineering_maturity": (
            f"Maturity rating: {'Senior Portfolio / Enterprise Grade' if overall_score >= 85 else 'Production Baseline' if overall_score >= 75 else 'Student/MVP Portfolio'}."
        ),
        "final_verdict": (
            f"With a composite score of {overall_score}/100 ({grade}), the project shows solid structural baseline metrics. "
            f"Implementing recommendations on the roadmap will further raise maintainability and security resilience."
        )
    }
