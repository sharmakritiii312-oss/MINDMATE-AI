"""
MindMate AI — Conversation Orchestrator (Multi-Agent Pipeline)

Pipeline for every user turn:
  1. EmotionAgent    → detect emotion & sentiment
  2. SafetyAgent     → check for crisis; short-circuit if true
  3. MemoryAgent     → retrieve relevant past context (RAG)
  4. WellnessAgent   → select personalised recommendations
  5. LLMAgent        → generate empathetic response
  6. MemoryAgent     → store turn in both short- and long-term memory

The ConversationOrchestrator is the single public interface used by the CLI and API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from emotion_detector import EmotionResult, analyze as detect_emotion
from memory_manager import Session, session_registry, long_term_memory
from safety_agent import (
    build_crisis_response,
    should_use_crisis_protocol,
    should_add_safety_footer,
    SAFETY_FOOTER,
)
from wellness_engine import get_recommendations, Recommendation
from llm_agent import generate_response


# ─── Turn result ──────────────────────────────────────────────────────────────

@dataclass
class TurnResult:
    session_id: str
    user_message: str
    assistant_response: str
    emotion: EmotionResult
    recommendations: list[Recommendation]
    was_crisis: bool


# ─── Orchestrator ─────────────────────────────────────────────────────────────

class ConversationOrchestrator:
    """
    Stateless orchestrator — state lives in SessionRegistry and LongTermMemory.
    Thread-safe as long as each request carries its session_id.
    """

    def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        user_id: str = "anonymous",
        # User preference hints (optional, from UI/API params)
        include_physical: bool = True,
        environment: Optional[str] = None,    # "indoor" | "outdoor"
        group_size: Optional[str] = None,     # "solo" | "pair" | "group"
        low_mobility: bool = False,
    ) -> TurnResult:
        # ── 1. Resolve session ──────────────────────────────────────────────
        session: Session = session_registry.get_or_create(session_id, user_id)

        # ── 2. Emotion Detection Agent ──────────────────────────────────────
        emotion: EmotionResult = detect_emotion(user_message)

        # ── 3. Safety Agent ─────────────────────────────────────────────────
        if should_use_crisis_protocol(emotion):
            response = build_crisis_response(emotion)
            self._store_turn(session, user_message, response, emotion)
            return TurnResult(
                session_id=session.session_id,
                user_message=user_message,
                assistant_response=response,
                emotion=emotion,
                recommendations=[],
                was_crisis=True,
            )

        # ── 4. Memory Agent — retrieve long-term context ─────────────────────
        retrieved_memories: list[str] = long_term_memory.retrieve(
            query=user_message,
            session_id=session.session_id,
            n_results=5,
        )

        # ── 5. Wellness Agent ───────────────────────────────────────────────
        recommendations: list[Recommendation] = get_recommendations(
            emotion_result=emotion,
            include_physical=include_physical,
            environment=environment,
            group_size=group_size,
            low_mobility=low_mobility,
            max_suggestions=4,
        )

        # ── 6. LLM Agent ────────────────────────────────────────────────────
        conversation_history = session.to_langchain_messages(n=10)
        emotion_trend = session.recent_emotion_trend(n=5)

        response: str = generate_response(
            user_message=user_message,
            emotion_result=emotion,
            conversation_history=conversation_history,
            recommendations=recommendations,
            retrieved_memories=retrieved_memories,
            emotion_trend=emotion_trend,
        )

        # Append safety footer for medium/high risk (non-crisis)
        if should_add_safety_footer(emotion):
            response += SAFETY_FOOTER

        # ── 7. Memory Agent — store ──────────────────────────────────────────
        self._store_turn(session, user_message, response, emotion)

        return TurnResult(
            session_id=session.session_id,
            user_message=user_message,
            assistant_response=response,
            emotion=emotion,
            recommendations=recommendations,
            was_crisis=False,
        )

    @staticmethod
    def _store_turn(
        session: Session,
        user_message: str,
        response: str,
        emotion: EmotionResult,
    ) -> None:
        session.add_turn("user", user_message, emotion=emotion)
        session.add_turn("assistant", response)
        long_term_memory.store(session.session_id, user_message, emotion=emotion)


# ─── Singleton ────────────────────────────────────────────────────────────────

orchestrator = ConversationOrchestrator()
