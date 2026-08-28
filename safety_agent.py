"""
MindMate AI — Crisis Safety Agent

Only intercepts when is_crisis is True (genuine crisis keywords detected).
For High-risk non-crisis, lets Groq handle it with the safety tip baked into
the system prompt — avoids returning scripted hotline blocks for normal messages.
"""
from __future__ import annotations

from config import CRISIS_HOTLINES
from emotion_detector import EmotionResult


# ─── Hotline formatter ────────────────────────────────────────────────────────

def _format_hotlines() -> str:
    lines = []
    for country, info in CRISIS_HOTLINES.items():
        lines.append(f"  • {country}: {info}")
    return "\n".join(lines)


# ─── Crisis response (only used when is_crisis=True) ─────────────────────────

CRISIS_RESPONSE = """I hear you, and I'm really glad you reached out right now.

What you're going through sounds incredibly painful, and your feelings matter deeply. Please know you are not alone in this.

Talking to someone trained to help can make a real difference right now:

{hotlines}

If you are in immediate danger, please call your local emergency services (911, 999, or 112).

I'm right here with you. Can you tell me a little more about what's going on?
"""


# ─── Public API ───────────────────────────────────────────────────────────────

def build_crisis_response(emotion_result: EmotionResult) -> str:
    """Only called when is_crisis=True — genuine crisis keywords detected."""
    return CRISIS_RESPONSE.format(hotlines=_format_hotlines())


def should_use_crisis_protocol(emotion_result: EmotionResult) -> bool:
    """
    Only intercept for genuine crisis (suicidal/self-harm keywords detected
    by the emotion model). High risk alone does NOT short-circuit — Groq
    handles those with crisis awareness baked into the system prompt.
    """
    return emotion_result.is_crisis


def should_add_safety_footer(emotion_result: EmotionResult) -> bool:
    """
    Append a gentle professional-help nudge only for genuinely high-intensity
    High-risk responses. Threshold raised to avoid triggering on normal stress.
    """
    return emotion_result.risk_level == "High" and emotion_result.intensity >= 8


SAFETY_FOOTER = (
    "\n\n---\n💛 *If things ever feel too heavy, please consider speaking with a counsellor "
    "or trusted person. You deserve real support.*"
)
