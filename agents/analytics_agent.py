"""
MindMate AI — Analytics Agent
Computes wellness scores, trend analytics, and generates AI-powered insights
from aggregated user data for the dashboard.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from config import OLLAMA_BASE_URL, OLLAMA_MODEL


def _llm() -> ChatOllama:
    return ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL, temperature=0.4)


def compute_wellness_scores(
    mood_logs: list[dict],
    sleep_logs: list[dict],
    exercise_logs: list[dict],
) -> dict:
    """Compute composite wellness scores from raw log data."""
    mood_avg = (
        round(sum(m.get("mood_score", 5) for m in mood_logs[:30]) / max(len(mood_logs[:30]), 1), 1)
        if mood_logs else 5.0
    )
    stress_avg = (
        round(sum(m.get("stress_score", 5) for m in mood_logs[:30]) / max(len(mood_logs[:30]), 1), 1)
        if mood_logs else 5.0
    )
    sleep_avg_dur = (
        round(sum(s.get("duration_hours", 7) for s in sleep_logs[:14]) / max(len(sleep_logs[:14]), 1), 1)
        if sleep_logs else 7.0
    )
    sleep_score = round(min(sleep_avg_dur / 8.0 * 10, 10), 1)

    exercise_days = len(set(e.get("logged_at", "")[:10] for e in exercise_logs[:14]))
    activity_score = round(min(exercise_days / 7.0 * 10, 10), 1)

    wellness = round(
        mood_avg * 0.3 +
        sleep_score * 0.25 +
        (10 - stress_avg) * 0.25 +
        activity_score * 0.2,
        1
    )

    return {
        "wellness_score": wellness,
        "mood_score": mood_avg,
        "sleep_score": sleep_score,
        "stress_score": stress_avg,
        "activity_score": activity_score,
    }


def generate_trend_data(mood_logs: list[dict], sleep_logs: list[dict],
                        days: int = 14) -> dict:
    """Build time-series data arrays for charting."""
    # Mood trend
    mood_by_date: dict[str, list] = {}
    for m in mood_logs:
        d = m.get("logged_at", "")[:10]
        if d:
            mood_by_date.setdefault(d, []).append(m.get("mood_score", 5))

    # Sleep trend
    sleep_by_date: dict[str, float] = {
        s.get("date", "")[:10]: s.get("duration_hours", 0) for s in sleep_logs
    }

    # Last N days
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]

    mood_series = [
        round(sum(mood_by_date.get(d, [5])) / max(len(mood_by_date.get(d, [5])), 1), 1)
        for d in dates
    ]
    sleep_series = [sleep_by_date.get(d, None) for d in dates]

    return {
        "dates": dates,
        "mood_series": mood_series,
        "sleep_series": sleep_series,
    }


def generate_ai_insight(scores: dict, mood_logs: list[dict],
                        sleep_logs: list[dict]) -> str:
    """Generate a 2-3 sentence AI insight paragraph for the analytics dashboard."""
    prompt = f"""Wellness analytics for a student:
- Overall Wellness Score: {scores.get('wellness_score', 5)}/10
- Mood Score: {scores.get('mood_score', 5)}/10
- Sleep Score: {scores.get('sleep_score', 5)}/10
- Stress Level: {scores.get('stress_score', 5)}/10
- Activity Score: {scores.get('activity_score', 5)}/10

Write a 2-3 sentence personalised wellness insight that:
1. Highlights the student's strongest wellness area
2. Identifies one area most needing attention
3. Ends with one specific, actionable recommendation

Be warm, direct, and encouraging. No generic advice."""

    llm = _llm()
    parser = StrOutputParser()
    messages = [HumanMessage(content=prompt)]
    return (llm | parser).invoke(messages)
