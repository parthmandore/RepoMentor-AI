import os
import uuid
import tempfile
from app.models.repository import Repository, RepositoryStatus
from app.models.repository_file import RepositoryFile
from app.services.analysis.pipeline import analyze_repository

def test_pipeline_integration(db_session):
    # Setup mock repository record in DB
    repo = Repository(
        id=uuid.uuid4(),
        url="https://github.com/mock/test-repo.git",
        status=RepositoryStatus.ANALYZING,
        health_score=100,
        health_grade="A"
    )
    db_session.add(repo)
    db_session.commit()

    # Create temporary mock files on disk
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a Python file
        py_content = """
def process(val):
    if val > 5:
        return val * 2
    return val
"""
        py_path = "src/process.py"
        os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
        with open(os.path.join(tmpdir, py_path), "w", encoding="utf-8") as f:
            f.write(py_content)

        # Create a Java file
        java_content = """
package com.test;
public class Helper {
    public static int doubleVal(int x) {
        return x * 2;
    }
}
"""
        java_path = "src/Helper.java"
        with open(os.path.join(tmpdir, java_path), "w", encoding="utf-8") as f:
            f.write(java_content)

        # Add file records to DB
        py_file = RepositoryFile(
            id=uuid.uuid4(),
            repository_id=repo.id,
            path=py_path,
            extension=".py",
            size_bytes=len(py_content),
            content_hash="abc1",
            is_text=True
        )
        java_file = RepositoryFile(
            id=uuid.uuid4(),
            repository_id=repo.id,
            path=java_path,
            extension=".java",
            size_bytes=len(java_content),
            content_hash="abc2",
            is_text=True
        )
        db_session.add(py_file)
        db_session.add(java_file)
        db_session.commit()

        # Monkey-patch SessionLocal inside app.services.analysis.pipeline to use our test db_session
        from app.services.analysis import pipeline
        original_session = pipeline.SessionLocal
        
        # Override close to prevent closing test session during test run
        original_close = db_session.close
        db_session.close = lambda: None
        
        pipeline.SessionLocal = lambda: db_session

        try:
            # Run analysis
            analyze_repository(repo.id, tmpdir)
        finally:
            pipeline.SessionLocal = original_session
            db_session.close = original_close

        # Verify results
        db_session.refresh(repo)
        assert repo.status_message is None
        assert repo.knowledge_status == "pending"
        assert repo.knowledge_summary is not None
        
        # Verify architecture layers and packages are correctly generated
        arch_knowledge = repo.knowledge_summary.get("architecture_knowledge", {})
        layers = arch_knowledge.get("layers", {})
        assert java_path in layers.get("utilities", []) or py_path in layers.get("utilities", [])
        
        # Verify file records have metrics and metadata
        db_session.refresh(py_file)
        db_session.refresh(java_file)
        assert py_file.lines_of_code > 0
        assert java_file.lines_of_code > 0
        assert py_file.complexity > 0
        assert java_file.complexity > 0
        assert "declarations" in py_file.analysis_metadata
        assert "declarations" in java_file.analysis_metadata
