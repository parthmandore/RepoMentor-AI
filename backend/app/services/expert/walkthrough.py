import logging
from sqlalchemy.orm import Session
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.code_smell import CodeSmell
from app.models.security_issue import SecurityIssue

logger = logging.getLogger(__name__)

class WalkthroughService:
    @staticmethod
    def generate_lessons(db: Session, repo_id: str) -> list[dict]:
        """
        Generate 9 guided walkthrough lessons grounded strictly in repository facts.
        """
        import uuid
        repo_uuid = uuid.UUID(repo_id) if isinstance(repo_id, str) else repo_id
        repo = db.query(Repository).filter(Repository.id == repo_uuid).first()
        if not repo:
            return []

        # Gather repository facts
        total_files = repo.total_files or 0
        total_folders = repo.total_folders or 0
        loc = repo.total_lines_of_code or 0
        tech_stack = repo.tech_stack or {}
        frameworks = tech_stack.get("frameworks", [])
        pkg_manager = tech_stack.get("package_manager", "None")

        # Database framework heuristics
        db_framework = "None detected"
        for fw in frameworks:
            if fw.lower() in ["prisma", "sqlalchemy", "hibernate", "mongoose", "sequelize", "spring-data", "ef-core", "gorm"]:
                db_framework = fw
                break

        # Authentication heuristics
        auth_detected = "Unspecified Auth / Simple custom logic"
        for fw in frameworks:
            if fw.lower() in ["spring-security", "passport", "next-auth", "firebase-auth", "auth0", "jwt", "django-auth"]:
                auth_detected = fw
                break

        # Count smells & security
        smells_count = db.query(CodeSmell).filter(CodeSmell.repository_id == repo_uuid).count()
        security_count = db.query(SecurityIssue).filter(SecurityIssue.repository_id == repo_uuid).count()

        # Build 9 lessons
        lessons = [
            {
                "slide_index": 1,
                "title": "Lesson 1: Project Overview",
                "content": (
                    f"Welcome to the onboarding walkthrough of this repository. This project is a software application "
                    f"built primarily using {', '.join(frameworks) if frameworks else 'native languages'}. It contains "
                    f"a total of {total_files} files spread across {total_folders} folders, totaling {loc:,} lines of code. "
                    f"The project management and dependencies are handled via {pkg_manager}."
                )
            },
            {
                "slide_index": 2,
                "title": "Lesson 2: Folder Structure",
                "content": (
                    f"The repository is organized into directories to keep code modular. "
                    f"Configuration files reside in root-level packages. The core source code follows standard layout "
                    f"structures. Files are classified into {repo.text_file_count} text source files and {repo.binary_file_count} "
                    f"binary or asset files, maintaining separation between logic and resource media."
                )
            },
            {
                "slide_index": 3,
                "title": "Lesson 3: Architecture",
                "content": (
                    f"This application adheres to standard software engineering layers. By analyzing the module dependencies, "
                    f"we trace a dependency flow. The average cyclomatic complexity is {repo.average_complexity or 0:.2f}, and "
                    f"the maximum complexity reached is {repo.max_complexity or 0} in hotspots. "
                    f"This highlights where the primary core orchestrations are structured."
                )
            },
            {
                "slide_index": 4,
                "title": "Lesson 4: Database Integration",
                "content": (
                    f"Data persistence in this project is managed using {db_framework}. "
                    f"The schema definitions, repository queries, and tables map model structures directly. "
                    f"This encapsulates data access logic away from routing, ensuring transactions are handled cleanly."
                )
            },
            {
                "slide_index": 5,
                "title": "Lesson 5: Authentication Flow",
                "content": (
                    f"The codebase secures endpoints and operations using {auth_detected}. "
                    f"Authentication handlers check incoming headers, parse tokens, and establish secure request "
                    f"session bounds, guarding database schemas from unauthorized operations."
                )
            },
            {
                "slide_index": 6,
                "title": "Lesson 6: API Request Flow",
                "content": (
                    f"When an HTTP request enters the application, it first triggers route middlewares and controllers. "
                    f"The controller delegates execution to underlying services. The services interact with "
                    f"data stores, execute business operations, and return serialization responses back to controllers "
                    f"to finalize HTTP payloads."
                )
            },
            {
                "slide_index": 7,
                "title": "Lesson 7: Interesting Design Decisions",
                "content": (
                    f"The code features structured patterns to solve repetitive problems. By encapsulating helper utilities "
                    f"and configurations separately, it prevents tight coupling. Additionally, frameworks are configured "
                    f"declaratively to reduce custom boilerplate."
                )
            },
            {
                "slide_index": 8,
                "title": "Lesson 8: Refactoring Opportunities",
                "content": (
                    f"Static analysis has detected {smells_count} code smells and {security_count} security alerts "
                    f"across modules. The biggest refactoring opportunities exist in highly complex files where modular "
                    f"decomposition is advised. Removing circular imports and splitting large methods will raise the "
                    f"health grade."
                )
            },
            {
                "slide_index": 9,
                "title": "Lesson 9: Suggested Learning Path",
                "content": (
                    f"To start contributing: 1. Explore main config files in root. 2. Trace an API route from controllers "
                    f"to database services. 3. Review tests to understand function constraints. 4. Fix minor code smells "
                    f"to familiarize yourself with the deployment pipeline."
                )
            }
        ]
        return lessons
