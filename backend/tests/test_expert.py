import pytest
import uuid
from sqlalchemy.orm import Session
from app.models.repository import Repository
from app.models.repository_file import RepositoryFile
from app.models.chat import ChatSession, ChatMessage
from app.services.expert.citation_tracker import validate_citations
from app.services.expert.confidence import calculate_confidence
from app.services.expert.walkthrough import WalkthroughService
from app.services.expert.chat import ChatManager
from app.services.expert.rag_pipeline import RagPipeline

def test_citation_tracker():
    # Below 0.30 threshold should fail validation
    chunks_low = [{"similarity_score": 0.25}, {"similarity_score": 0.10}]
    assert not validate_citations(chunks_low)

    # At or above 0.30 threshold should pass
    chunks_high = [{"similarity_score": 0.35}, {"similarity_score": 0.20}]
    assert validate_citations(chunks_high)

    # Empty chunks should fail
    assert not validate_citations([])

def test_confidence_calculator():
    # Empty
    assert calculate_confidence([]) == 0

    # High similarity, high diversity
    chunks = [
        {"similarity_score": 0.90, "file_path": "src/main.py"},
        {"similarity_score": 0.85, "file_path": "src/helper.py"},
        {"similarity_score": 0.70, "file_path": "src/utils.py"}
    ]
    conf = calculate_confidence(chunks)
    assert conf > 50
    assert conf <= 100

def test_walkthrough_lessons(db_session: Session):
    # Create test repository
    repo_id = uuid.uuid4()
    repo = Repository(
        id=repo_id,
        url=f"https://github.com/test/repo-{repo_id}",
        total_files=10,
        total_folders=3,
        total_lines_of_code=1500,
        text_file_count=8,
        binary_file_count=2,
        tech_stack={"frameworks": ["Django", "React"], "package_manager": "pip"},
        average_complexity=2.5,
        max_complexity=8,
        health_score=85,
        health_grade="B"
    )
    db_session.add(repo)
    db_session.commit()

    lessons = WalkthroughService.generate_lessons(db_session, str(repo_id))
    assert len(lessons) == 9
    assert lessons[0]["title"] == "Lesson 1: Project Overview"
    assert "Django" in lessons[0]["content"] or "React" in lessons[0]["content"]

def test_chat_manager_and_history(db_session: Session):
    # Setup test repo
    repo_id = uuid.uuid4()
    repo = Repository(id=repo_id, url=f"https://github.com/test/repo-{repo_id}")
    db_session.add(repo)
    db_session.commit()

    manager = ChatManager(db_session)
    session = manager.create_session(str(repo_id))
    assert session.id is not None

    # Add message
    msg = manager.add_message(str(session.id), "user", "Hello codebase!")
    assert msg.role == "user"
    assert msg.content == "Hello codebase!"

    # Retrieve history
    history = manager.get_messages(str(session.id))
    assert len(history) == 1
    assert history[0].content == "Hello codebase!"

def test_rag_pipeline_retrieval(db_session: Session):
    # Setup repo and files
    repo_id = uuid.uuid4()
    repo = Repository(id=repo_id, url=f"https://github.com/test/repo-{repo_id}")
    db_session.add(repo)
    
    file1 = RepositoryFile(
        id=uuid.uuid4(),
        repository_id=repo_id,
        path="src/AuthController.py",
        size_bytes=500,
        content_hash="abc",
        is_text=True,
        lines_of_code=100,
        analysis_metadata={
            "declarations": [
                {"name": "AuthController", "type": "class", "start_line": 1, "end_line": 50}
            ],
            "dependencies": [
                {"target": "JwtService", "type": "import"}
            ]
        }
    )
    db_session.add(file1)
    db_session.commit()

    pipeline = RagPipeline(db_session, str(repo_id))
    decls, deps = pipeline._get_declarations_and_dependencies()
    assert "AuthController" in decls
    assert decls["AuthController"]["file_path"] == "src/AuthController.py"
