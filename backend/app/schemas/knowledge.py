from typing import List, Dict, Optional, Any
from pydantic import BaseModel


class EvidenceDocEntry(BaseModel):
    document_type: str
    title: str
    summary: str
    source_file: str


class KnowledgeSummaryResponse(BaseModel):
    total_chunks: int = 0
    code_chunks: int = 0
    evidence_documents: int = 0
    indexed_files: int = 0
    supported_languages: List[str] = []
    build_status: str = "pending"
    embedding_status: str = "offline"
    evidence_docs_list: List[EvidenceDocEntry] = []
    
    summary_description: Optional[str] = None
    architecture_knowledge: Optional[Dict[str, Any]] = None
    timing_metadata: Optional[Dict[str, Any]] = None
    health_metadata: Optional[Dict[str, Any]] = None
    security_metadata: Optional[Dict[str, Any]] = None
    diagnostics: Optional[Dict[str, Any]] = None
    wiki_data: Optional[Dict[str, Any]] = None
    learning_report: Optional[Dict[str, Any]] = None
    knowledge_graph: Optional[Dict[str, Any]] = None
