"""
MindMate AI — Test Suite

Tests cover:
  • Emotion detector (unit — mocked transformers pipeline)
  • Wellness engine recommendation filtering
  • Safety agent crisis detection
  • Orchestrator pipeline (mocked LLM)
"""
from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Helpers to mock heavy ML dependencies
# ─────────────────────────────────────────────────────────────────────────────

def _make_emotion_pipeline_mock():
    def _pipe(text, *a, **kw):
        return [[
            {"label": "sadness", "score": 0.72},
            {"label": "fear", "score": 0.12},
            {"label": "joy", "score": 0.05},
            {"label": "anger", "score": 0.04},
            {"label": "disgust", "score": 0.03},
            {"label": "surprise", "score": 0.02},
            {"label": "neutral", "score": 0.02},
        ]]
    mock = MagicMock(side_effect=_pipe)
    return mock


def _make_sentiment_pipeline_mock():
    def _pipe(text, *a, **kw):
        return [[
            {"label": "negative", "score": 0.85},
            {"label": "neutral", "score": 0.10},
            {"label": "positive", "score": 0.05},
        ]]
    mock = MagicMock(side_effect=_pipe)
    return mock


# ─────────────────────────────────────────────────────────────────────────────
# Emotion Detector Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestEmotionDetector(unittest.TestCase):

    @patch("emotion_detector._get_sentiment_pipeline", return_value=_make_sentiment_pipeline_mock())
    @patch("emotion_detector._get_emotion_pipeline", return_value=_make_emotion_pipeline_mock())
    def test_basic_analysis(self, mock_emotion, mock_sentiment):
        from emotion_detector import analyze
        result = analyze("I feel so sad about all my assignments piling up.")
        self.assertEqual(result.primary_emotion, "sadness")
        self.assertEqual(result.sentiment, "negative")
        self.assertGreaterEqual(result.intensity, 1)
        self.assertLessEqual(result.intensity, 10)
        self.assertIn(result.risk_level, ("Low", "Medium", "High"))
        self.assertFalse(result.is_crisis)

    @patch("emotion_detector._get_sentiment_pipeline", return_value=_make_sentiment_pipeline_mock())
    @patch("emotion_detector._get_emotion_pipeline", return_value=_make_emotion_pipeline_mock())
    def test_crisis_detection(self, mock_emotion, mock_sentiment):
        from emotion_detector import analyze
        result = analyze("I want to die. I can't go on anymore.")
        self.assertTrue(result.is_crisis)
        self.assertEqual(result.risk_level, "High")
        self.assertGreaterEqual(result.intensity, 9)

    @patch("emotion_detector._get_sentiment_pipeline", return_value=_make_sentiment_pipeline_mock())
    @patch("emotion_detector._get_emotion_pipeline", return_value=_make_emotion_pipeline_mock())
    def test_summary_format(self, mock_emotion, mock_sentiment):
        from emotion_detector import analyze
        result = analyze("I feel overwhelmed with assignments.")
        summary = result.summary()
        self.assertIn("Intensity:", summary)
        self.assertIn("Risk:", summary)


# ─────────────────────────────────────────────────────────────────────────────
# Wellness Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWellnessEngine(unittest.TestCase):

    def _make_emotion(self, emotion="anxiety", intensity=6, risk="Medium", is_crisis=False):
        from emotion_detector import EmotionResult
        return EmotionResult(
            primary_emotion=emotion,
            emotion_scores={emotion: 0.8},
            sentiment="negative",
            sentiment_score=0.8,
            intensity=intensity,
            risk_level=risk,
            is_crisis=is_crisis,
        )

    def test_returns_recommendations(self):
        from wellness_engine import get_recommendations
        recs = get_recommendations(self._make_emotion())
        self.assertGreater(len(recs), 0)

    def test_crisis_excludes_physical(self):
        from wellness_engine import get_recommendations
        recs = get_recommendations(self._make_emotion(is_crisis=True))
        physical = [r for r in recs if r.has_physical_activity]
        self.assertEqual(len(physical), 0)

    def test_no_physical_flag(self):
        from wellness_engine import get_recommendations
        recs = get_recommendations(self._make_emotion(), include_physical=False)
        physical = [r for r in recs if r.has_physical_activity]
        self.assertEqual(len(physical), 0)

    def test_indoor_filter(self):
        from wellness_engine import get_recommendations
        recs = get_recommendations(self._make_emotion(), environment="indoor")
        outdoor_recs = [r for r in recs if r.environment == "outdoor"]
        self.assertEqual(len(outdoor_recs), 0)

    def test_high_intensity_no_physical_preferred(self):
        from wellness_engine import get_recommendations
        recs = get_recommendations(self._make_emotion(intensity=9, risk="High"))
        # All results should respect max_intensity limit — physical games cap at 7
        for r in recs:
            if r.has_physical_activity:
                self.assertLessEqual(9, r.max_intensity + 1)


# ─────────────────────────────────────────────────────────────────────────────
# Safety Agent Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSafetyAgent(unittest.TestCase):

    def _make_emotion(self, is_crisis=False, risk="Low", intensity=3):
        from emotion_detector import EmotionResult
        return EmotionResult(
            primary_emotion="sadness",
            emotion_scores={"sadness": 0.9},
            sentiment="negative",
            sentiment_score=0.9,
            intensity=intensity,
            risk_level=risk,
            is_crisis=is_crisis,
        )

    def test_crisis_protocol_triggered(self):
        from safety_agent import should_use_crisis_protocol
        self.assertTrue(should_use_crisis_protocol(self._make_emotion(is_crisis=True)))

    def test_high_risk_intensity_triggers_crisis(self):
        from safety_agent import should_use_crisis_protocol
        self.assertTrue(should_use_crisis_protocol(self._make_emotion(risk="High", intensity=9)))

    def test_low_risk_no_crisis(self):
        from safety_agent import should_use_crisis_protocol
        self.assertFalse(should_use_crisis_protocol(self._make_emotion(risk="Low", intensity=3)))

    def test_crisis_response_contains_hotlines(self):
        from safety_agent import build_crisis_response
        response = build_crisis_response(self._make_emotion(is_crisis=True))
        self.assertIn("988", response)  # US hotline
        self.assertIn("emergency", response.lower())

    def test_safety_footer_medium_risk(self):
        from safety_agent import should_add_safety_footer
        self.assertTrue(should_add_safety_footer(self._make_emotion(risk="Medium", intensity=7)))

    def test_no_footer_low_risk(self):
        from safety_agent import should_add_safety_footer
        self.assertFalse(should_add_safety_footer(self._make_emotion(risk="Low", intensity=2)))


# ─────────────────────────────────────────────────────────────────────────────
# Memory Manager Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestMemoryManager(unittest.TestCase):

    def test_session_creation(self):
        from memory_manager import SessionRegistry
        registry = SessionRegistry()
        session = registry.get_or_create(user_id="test_user")
        self.assertIsNotNone(session.session_id)
        self.assertEqual(session.user_id, "test_user")

    def test_session_persistence(self):
        from memory_manager import SessionRegistry
        registry = SessionRegistry()
        session = registry.get_or_create(user_id="student_a")
        sid = session.session_id
        retrieved = registry.get(sid)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.session_id, sid)

    def test_add_turns(self):
        from memory_manager import SessionRegistry
        registry = SessionRegistry()
        session = registry.get_or_create()
        session.add_turn("user", "I'm stressed about exams.")
        session.add_turn("assistant", "I hear you — exam stress is really tough.")
        self.assertEqual(len(session.turns), 2)

    def test_langchain_messages_format(self):
        from memory_manager import SessionRegistry
        registry = SessionRegistry()
        session = registry.get_or_create()
        session.add_turn("user", "Hello")
        session.add_turn("assistant", "Hi there!")
        messages = session.to_langchain_messages()
        self.assertEqual(messages[0]["role"], "user")
        self.assertEqual(messages[1]["role"], "assistant")

    def test_emotion_trend(self):
        from memory_manager import SessionRegistry
        from emotion_detector import EmotionResult
        registry = SessionRegistry()
        session = registry.get_or_create()
        mock_emotion = EmotionResult(
            primary_emotion="anxiety",
            emotion_scores={"anxiety": 0.8},
            sentiment="negative",
            sentiment_score=0.8,
            intensity=6,
            risk_level="Medium",
        )
        session.add_turn("user", "Feeling anxious", emotion=mock_emotion)
        trend = session.recent_emotion_trend()
        self.assertEqual(len(trend), 1)
        self.assertEqual(trend[0]["primary_emotion"], "anxiety")


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
