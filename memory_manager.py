"""
MindMate AI — Conversation Memory Manager

Dual-layer memory:
  1. Short-term: sliding window of the last N message pairs (in-process dict)
  2. Long-term:  ChromaDB vector store for semantic retrieval of past context

Each session is identified by a unique session_id.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional

from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL_ID, MAX_HISTORY_TURNS
from emotion_detector import EmotionResult


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class Turn:
    role: str            # "user" | "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    emotion: Optional[dict] = None   # serialised EmotionResult (user turns only)


@dataclass
class Session:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = "anonymous"
    turns: list[Turn] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    emotion_history: list[dict] = field(default_factory=list)   # lightweight emotion log

    def add_turn(self, role: str, content: str, emotion: Optional[EmotionResult] = None) -> None:
        emotion_dict = None
        if emotion:
            emotion_dict = {
                "primary_emotion": emotion.primary_emotion,
                "intensity": emotion.intensity,
                "risk_level": emotion.risk_level,
                "sentiment": emotion.sentiment,
                "is_crisis": emotion.is_crisis,
            }
            self.emotion_history.append(emotion_dict)
        self.turns.append(Turn(role=role, content=content, emotion=emotion_dict))
        # Trim to sliding window
        if len(self.turns) > MAX_HISTORY_TURNS * 2:
            self.turns = self.turns[-(MAX_HISTORY_TURNS * 2):]

    def last_n_turns(self, n: int = 10) -> list[Turn]:
        return self.turns[-n * 2:]

    def to_langchain_messages(self, n: int = 10) -> list[dict]:
        """Return recent turns formatted for LangChain chat history."""
        return [{"role": t.role, "content": t.content} for t in self.last_n_turns(n)]

    def recent_emotion_trend(self, n: int = 5) -> list[dict]:
        return self.emotion_history[-n:]


# ─── In-memory session registry ───────────────────────────────────────────────

class SessionRegistry:
    """Holds all active sessions in memory."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_or_create(self, session_id: Optional[str] = None, user_id: str = "anonymous") -> Session:
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        session = Session(user_id=user_id)
        if session_id:
            session.session_id = session_id
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def all_sessions(self) -> list[Session]:
        return list(self._sessions.values())


# ─── Long-term vector memory ──────────────────────────────────────────────────

class LongTermMemory:
    """
    Stores user messages in ChromaDB for semantic retrieval.
    All heavy dependencies are loaded lazily on first use.
    """

    COLLECTION_NAME = "mindmate_memory"

    def __init__(self) -> None:
        self._client = None
        self._collection = None
        self._embedder = None

    def _ensure_loaded(self) -> bool:
        """Load ChromaDB + SentenceTransformer on first call. Returns False if unavailable."""
        if self._client is not None:
            return True
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            from sentence_transformers import SentenceTransformer
            self._client = chromadb.PersistentClient(
                path=CHROMA_PERSIST_DIR,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            self._embedder = SentenceTransformer(EMBEDDING_MODEL_ID)
            return True
        except Exception:
            return False

    def store(self, session_id: str, user_message: str, emotion: Optional[EmotionResult] = None) -> None:
        if not self._ensure_loaded():
            return  # silently skip if not available yet
        doc_id = str(uuid.uuid4())
        embedding = self._embedder.encode(user_message).tolist()
        metadata: dict = {
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if emotion:
            metadata["emotion"] = emotion.primary_emotion
            metadata["intensity"] = emotion.intensity
            metadata["risk_level"] = emotion.risk_level
        self._collection.add(
            ids=[doc_id], embeddings=[embedding],
            documents=[user_message], metadatas=[metadata],
        )

    def retrieve(self, query: str, session_id: Optional[str] = None, n_results: int = 5) -> list[str]:
        if not self._ensure_loaded():
            return []  # return empty if not available yet
        embedding = self._embedder.encode(query).tolist()
        where: Optional[dict] = {"session_id": session_id} if session_id else None
        results = self._collection.query(
            query_embeddings=[embedding], n_results=n_results, where=where,
        )
        return results.get("documents", [[]])[0]


# ─── Singletons ───────────────────────────────────────────────────────────────

session_registry = SessionRegistry()
long_term_memory = LongTermMemory()
