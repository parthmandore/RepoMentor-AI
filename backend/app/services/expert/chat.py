import logging
import uuid
import httpx
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.chat import ChatSession, ChatMessage
from app.core.config import settings

logger = logging.getLogger(__name__)

class ChatManager:
    def __init__(self, db: Session):
        self.db = db

    def create_session(self, repo_id: str) -> ChatSession:
        """
        Create a new chat session.
        """
        session = ChatSession(
            id=uuid.uuid4(),
            repository_id=uuid.UUID(repo_id)
        )
        self.db.add(session)
        try:
            self.db.commit()
            self.db.refresh(session)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create chat session: {e}")
            raise e
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        """
        Retrieve a chat session.
        """
        return self.db.query(ChatSession).filter(ChatSession.id == uuid.UUID(session_id)).first()

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        """
        Retrieve all messages for a session.
        """
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == uuid.UUID(session_id))
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        cited_chunks: list[dict] = None,
        confidence: int = 100,
        expert_mode: str = "General"
    ) -> ChatMessage:
        """
        Save a new message to the database.
        """
        msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=uuid.UUID(session_id),
            role=role,
            content=content,
            cited_chunks=cited_chunks or [],
            confidence=confidence,
            expert_mode=expert_mode
        )
        self.db.add(msg)
        try:
            self.db.commit()
            self.db.refresh(msg)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to add chat message: {e}")
            raise e

        # Trigger automatic summarization if conversation length grows long
        self.check_and_summarize(session_id)

        return msg

    def check_and_summarize(self, session_id: str):
        """
        Automatically summarize conversation if there are more than 10 messages,
        and write a summary record to reduce context size.
        """
        sess_uuid = uuid.UUID(session_id)
        # Count user/assistant messages
        user_assistant_msgs = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == sess_uuid, ChatMessage.role.in_(["user", "assistant"]))
            .all()
        )

        if len(user_assistant_msgs) > 10:
            # Check if we already have a summary generated recently
            has_recent_summary = (
                self.db.query(ChatMessage)
                .filter(ChatMessage.session_id == sess_uuid, ChatMessage.role == "summary")
                .first()
            )
            if not has_recent_summary:
                self.generate_and_store_summary(session_id, user_assistant_msgs)

    def generate_and_store_summary(self, session_id: str, messages: list[ChatMessage]):
        """
        Summarize the dialogue context using Groq LLM service.
        """
        logger.info(f"Summarizing chat session {session_id} to compress history...")
        dialogue = ""
        for m in messages:
            dialogue += f"{m.role.capitalize()}: {m.content}\n"

        prompt = (
            f"Write a short, concise 2-sentence summary of the main points discussed in the following dialogue:\n"
            f"{dialogue}\n"
            f"Summary:"
        )

        summary_content = "The user queried codebase components and the AI Repository Mentor provided evidence-grounded walkthrough code reviews."
        try:
            from app.services.llm.groq_service import GroqService
            res = GroqService.generate(prompt=prompt, temperature=0.0)
            if res and not res.startswith("[API Error]") and not res.startswith("[Connection Error]") and not res.startswith("[Timeout Error]"):
                summary_content = res.strip()
        except Exception as e:
            logger.warning(f"Failed to generate summary via Groq: {e}. Using generic summary.")

        # Save summary message
        summary_msg = ChatMessage(
            id=uuid.uuid4(),
            session_id=uuid.UUID(session_id),
            role="summary",
            content=summary_content,
            cited_chunks=[],
            confidence=100,
            expert_mode="General"
        )
        self.db.add(summary_msg)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save summary message: {e}")
