import logging
import json
import os
import uuid
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.code_smell import CodeSmell
from app.models.security_issue import SecurityIssue
from app.services.knowledge.retriever import retrieve_grounded_context
from app.services.expert.citation_tracker import validate_citations
from app.services.expert.confidence import calculate_confidence
from app.services.llm.groq_service import GroqService
from app.repositories.vector_repository import VectorRepository

logger = logging.getLogger(__name__)

EXPERT_PROMPTS = {
    "General": (
        "You are the AI Repository Mentor, an expert senior software architect and engineer who has deeply analyzed the repository. "
        "Analyze the repository code directly, conversationally, and professionally. Speak like an experienced senior developer. "
        "Never use robotic preambles or boilerplate phrases like 'Based on the provided evidence...', 'Based on the repository...', or 'According to the context...'. "
        "Explain files, classes, design patterns, architecture, database schemas, and security topics naturally and directly."
    )
}

EXPLAIN_MODES = {}

class RagPipeline:
    def __init__(self, db: Session, repo_id: str):
        self.db = db
        self.repo_uuid = uuid.UUID(repo_id) if isinstance(repo_id, str) else repo_id
        self.repo = db.query(Repository).filter(Repository.id == self.repo_uuid).first()

    def route_intent(self, question: str) -> str:
        """
        Intent Router: Categorizes the query based on semantic intent rules.
        """
        q = question.lower()
        if any(w in q for w in ["what is this", "purpose", "explain project", "overview", "about", "describe"]):
            return "GENERAL_OVERVIEW"
        elif any(w in q for w in ["tech", "languages", "frameworks", "libraries", "dependencies", "package", "npm", "requirements", "setup"]):
            return "TECH_STACK"
        elif any(w in q for w in ["architecture", "structure", "folder", "dependency", "layer", "module", "mvc", "controller", "service", "coupling", "relations"]):
            return "ARCHITECTURE"
        elif any(w in q for w in ["security", "vulnerability", "secret", "inject", "cve", "threat", "risk", "owasp", "key"]):
            return "SECURITY"
        elif any(w in q for w in ["maintainability", "smell", "complexity", "duplicate", "refactor", "improve", "clean"]):
            return "MAINTAINABILITY"
        else:
            return "CODE_SEMANTIC"

    def retrieve_grounded_evidence(self, question: str) -> tuple[list[dict], list[str]]:
        """
        Runs the production-grade RAG pipeline:
        1. Intent Routing
        2. Metadata Retrieval
        3. README & Architecture Graph Context
        4. Vector Search
        5. Neighbor Expansion
        """
        intent = self.route_intent(question)
        logger.info(f"[Intent Router] Classified query as: {intent}")
        
        retrieval_steps = [f"Intent: {intent}"]
        chunks = []
        seen_texts = set()

        # Step 1: Pre-populate Repository Metadata and README if relevant
        if intent in ["GENERAL_OVERVIEW", "TECH_STACK", "ARCHITECTURE"]:
            # Insert a virtual chunk for Repository structured summary
            summary = self.repo.knowledge_summary or {}
            summary_desc = summary.get("summary_description", "")
            if summary_desc:
                chunks.append({
                    "chunk_id": "virtual_summary",
                    "repo_id": str(self.repo_uuid),
                    "file_path": "Repository Summary",
                    "line_numbers": "1-1",
                    "content": f"Repository Structured Summary:\n{summary_desc}",
                    "similarity_score": 1.0,
                    "source_type": "Summary"
                })
                seen_texts.add(summary_desc)
                retrieval_steps.append("Loaded Repository Summary metadata")

        # Load README if present in DB
        readme_file = self.db.query(RepositoryFile).filter(
            RepositoryFile.repository_id == self.repo_uuid,
            RepositoryFile.path.ilike("readme.md")
        ).first()
        if readme_file and intent in ["GENERAL_OVERVIEW", "TECH_STACK"]:
            content = f"README.md Document:\nSize: {readme_file.size_bytes} bytes."
            chunks.append({
                "chunk_id": "virtual_readme",
                "repo_id": str(self.repo_uuid),
                "file_path": "README.md",
                "line_numbers": "1-1",
                "content": content,
                "similarity_score": 1.0,
                "source_type": "README"
            })
            retrieval_steps.append("Pre-loaded README file headers")

        # Step 2: Vector Search
        vector_limit = 4 if intent == "CODE_SEMANTIC" else 2
        vector_chunks = retrieve_grounded_context(str(self.repo_uuid), question, limit=vector_limit, db=self.db)
        
        # Step 3: Neighbor Expansion (Component 5 & 6)
        file_paths = []
        for vch in vector_chunks:
            content = vch.get("content", "")
            if content not in seen_texts:
                seen_texts.add(content)
                vch["source_type"] = "Code"
                chunks.append(vch)
            
            file_path = vch.get("file_path")
            if file_path and file_path not in ["README.md", "Repository Summary"]:
                file_paths.append(file_path)

        if file_paths:
            retrieval_steps.append(f"Neighbor Expansion: batched query for files {list(set(file_paths))}")
            try:
                vector_repo = VectorRepository(self.db)
                all_neighbors = vector_repo.fetch_neighbor_chunks_multiple(self.repo_uuid, list(set(file_paths)))
                
                for vch in vector_chunks:
                    file_path = vch.get("file_path")
                    if not file_path or file_path in ["README.md", "Repository Summary"]:
                        continue
                    
                    res_chunks = all_neighbors.get(file_path, [])
                    if res_chunks:
                        # Find adjacent lines (within 150 lines)
                        start = vch.get("start_line", 0)
                        for n_ch in res_chunks:
                            mstart = n_ch.get("start_line", 0)
                            if 0 < abs(mstart - start) < 150:
                                n_content = n_ch["content"]
                                if n_content not in seen_texts:
                                    seen_texts.add(n_content)
                                    chunks.append({
                                        "chunk_id": n_ch["chunk_id"],
                                        "repo_id": str(self.repo_uuid),
                                        "file_path": file_path,
                                        "line_numbers": f"{n_ch.get('start_line')}-{n_ch.get('end_line')}",
                                        "content": n_content,
                                        "similarity_score": 0.8,
                                        "source_type": "Code"
                                    })
                                    retrieval_steps.append(f"Expanded neighboring block in {os.path.basename(file_path)} L{n_ch.get('start_line')}")
            except Exception as ex:
                logger.debug(f"Neighbor expansion error: {ex}")

        return chunks, retrieval_steps

    def prepare_context_and_prompt(
        self,
        question: str,
        mode: str = "General",
        explain_mode: str = None,
        history: list[dict] = None
    ) -> tuple[str, str, list[dict], int, list[str]]:
        """
        Runs RAG retrieval and constructs the system instruction and final prompt.
        """
        if not self.repo:
            return "", "", [], 0, []

        # 1. Retrieve evidence
        chunks, steps = self.retrieve_grounded_evidence(question)
        confidence = calculate_confidence(chunks)
        
        # 2. Check citation validity (includes fallbacks)
        if not validate_citations(chunks):
            refusal_prompt = "I couldn't find enough information in the indexed repository to answer that confidently."
            return refusal_prompt, "", [], 0, steps

        # 3. Format prompt context (with character budget to avoid Groq 413 errors)
        MAX_EVIDENCE_CHARS = 8000
        evidence_str = ""
        current_evidence_len = 0
        budgeted_chunks = []
        for i, ch in enumerate(chunks):
            chunk_text = f"\n--- Evidence Chunk {i+1} ({ch.get('file_path')}:{ch.get('line_numbers')}) ---\n{ch.get('content')}\n"
            if current_evidence_len + len(chunk_text) > MAX_EVIDENCE_CHARS and len(budgeted_chunks) >= 1:
                break
            budgeted_chunks.append(ch)
            evidence_str += chunk_text
            current_evidence_len += len(chunk_text)
        chunks = budgeted_chunks
            
        tech_stack = self.repo.tech_stack or {}
        frameworks = tech_stack.get("frameworks", [])
        
        # Historical messages memory
        history_str = ""
        if history:
            for h in history[-3:]: # Keep last 3 turns
                role = "User" if h.get("role") == "user" else "Assistant"
                history_str += f"{role}: {h.get('content')}\n"

        system_instruction = EXPERT_PROMPTS["General"]
        explain_str = ""

        prompt = f"""<SYSTEM>
{system_instruction}
{explain_str}

Ensure you STRICTLY follow these safety guidelines:
1. Only answer using the Repository Code & Context below.
2. Never invent files, methods, classes, APIs, functionality, or vulnerabilities.
3. If repository evidence is insufficient to answer the question, state exactly: "I couldn't find enough information in the indexed repository to answer that confidently."
4. Never speculate or guess. Do not say "I think", "probably", "might", etc.
5. Sound like an experienced senior software engineer. Respond conversationally and directly. Never start your response or sentences with referencing preambles like "Based on the...", "According to the...", "As seen in...", "Looking at...", "Based on the security summary...", or similar. Directly state your engineering findings and analysis.
</SYSTEM>

--- Repository Code & Context ---
{evidence_str}

--- Repository Stats ---
URL: {self.repo.url}
LOC: {self.repo.total_lines_of_code}
Frameworks: {', '.join(frameworks)}
Health Score: {self.repo.health_score} (Grade {self.repo.health_grade})

--- Architectural Blueprint ---
{json.dumps(self.repo.architecture_summary or {})}

--- Security Assessment ---
{json.dumps(self.repo.security_summary or {})}

--- Conversation History ---
{history_str}

Question: {question}
Answer:"""

        return prompt, system_instruction, chunks, confidence, steps

    def execute(self, question: str, mode: str = "General", explain_mode: str = None, history: list[dict] = None) -> tuple[str, list[dict], int, list[str]]:
        """
        Executes the cloud-native RAG pipeline:
        - Route Intent
        - Retrieve Grounded Evidence (using pgvector)
        - Call Groq Service (Component 3)
        """
        if not self.repo:
            return "Repository not found.", [], 0, []

        prompt, system_instruction, chunks, confidence, steps = self.prepare_context_and_prompt(
            question=question,
            mode=mode,
            explain_mode=explain_mode,
            history=history
        )

        if not prompt or not system_instruction:
            return prompt or "I couldn't find enough information in the indexed repository to answer that confidently.", chunks, confidence, steps

        # 4. Invoke LLM (GroqService) (Component 3)
        answer = GroqService.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            history=None  # History is already serialized in the prompt template above
        )

        # Fallback Graceful degradation
        is_error = (
            answer.startswith("[API Error]") or
            answer.startswith("[Connection Error]") or
            answer.startswith("[Timeout Error]") or
            not answer
        )
        if is_error:
            fallback_answer = (
                f"[Offline Mode] AI Repository Mentor is currently offline or unreachable ({answer or 'No response'}). "
                f"Here is the grounded repository evidence gathered for your query:\n\n"
                f"### Grounded Evidence Chunks\n"
            )
            for i, ch in enumerate(chunks):
                fallback_answer += f"- **{ch.get('file_path')}** (Lines {ch.get('line_numbers')}, Similarity: {ch.get('similarity_score')}):\n"
                fallback_answer += f"  ```\n  {ch.get('content')[:120].strip()}...\n  ```\n"
                
            fallback_answer += (
                f"\n### Repository Highlights\n"
                f"- Frameworks: {', '.join(frameworks) if frameworks else 'None detected'}\n"
                f"- Size: {self.repo.total_files} files, {self.repo.total_lines_of_code:,} LOC\n"
                f"- Health Score: {self.repo.health_score}/100 (Grade {self.repo.health_grade})\n"
                f"- Detected Smells: {self.repo.total_smells}\n"
                f"\nPlease verify your Groq API Key and internet connection to enable conversational reviews."
            )
            answer = fallback_answer

        # Proactive teaching prompts append
        proactive_suggestions = []
        if any(w in question.lower() for w in ["auth", "login", "jwt", "token", "session"]):
            proactive_suggestions = [
                "Would you like me to explain JWT token verification in this repo?",
                "Should we discuss authentication security risks or best practices?"
            ]
        elif any(w in question.lower() for w in ["db", "database", "repository", "query", "sql"]):
            proactive_suggestions = [
                "Explain the data transaction pattern used here.",
                "How would we safely parameterize dynamic database queries?"
            ]
        else:
            proactive_suggestions = [
                "Explain the main design patterns in this project.",
                "What refactoring recommendations should I apply first?"
            ]
            
        if proactive_suggestions:
            proactive_block = "\n\n**Proactive Learning Suggestions:**\n" + "\n".join([f"- {s}" for s in proactive_suggestions])
            
        return answer, chunks, confidence, steps
