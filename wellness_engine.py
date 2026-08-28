"""
MindMate AI — Wellness Recommendation Engine

Provides:
  • Breathing exercises
  • Mindfulness & grounding techniques
  • CBT-inspired cognitive reframes
  • Study / academic stress tips
  • Journaling & gratitude prompts
  • Relaxation & sleep hygiene tips
  • Physical games & movement activities (optional, non-pressuring)

Each recommendation is tagged with:
  applicable_emotions, min_intensity, max_intensity, environment,
  group_size, energy_level, has_physical_activity
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from emotion_detector import EmotionResult


# ─── Data class ───────────────────────────────────────────────────────────────

@dataclass
class Recommendation:
    category: str           # breathing | mindfulness | cbt | academic | journaling |
                            # relaxation | physical_game | motivational
    title: str
    description: str
    instructions: list[str]
    duration_minutes: int
    applicable_emotions: list[str]   # empty = universal
    min_intensity: int = 1
    max_intensity: int = 10
    environment: str = "any"         # indoor | outdoor | any
    group_size: str = "any"          # solo | pair | group | any
    energy_level: str = "any"        # low | medium | high | any
    has_physical_activity: bool = False
    low_mobility_friendly: bool = True
    safety_note: Optional[str] = None


# ─── Recommendation catalogue ─────────────────────────────────────────────────

RECOMMENDATIONS: list[Recommendation] = [

    # ── Breathing ──────────────────────────────────────────────────────────────
    Recommendation(
        category="breathing",
        title="4-4-6 Calming Breath",
        description="A slow breathing pattern that activates the parasympathetic nervous system, reducing anxiety and stress.",
        instructions=[
            "Sit comfortably with your back straight.",
            "Inhale slowly through your nose for 4 seconds.",
            "Hold your breath gently for 4 seconds.",
            "Exhale fully through your mouth for 6 seconds.",
            "Repeat 5 times. Feel each exhale release tension.",
        ],
        duration_minutes=3,
        applicable_emotions=["anxiety", "stress", "fear", "anger"],
        min_intensity=4,
    ),
    Recommendation(
        category="breathing",
        title="Box Breathing (4-4-4-4)",
        description="Used by Navy SEALs and therapists alike — resets your nervous system within minutes.",
        instructions=[
            "Sit upright and close your eyes if comfortable.",
            "Inhale for 4 counts.",
            "Hold for 4 counts.",
            "Exhale for 4 counts.",
            "Hold empty for 4 counts.",
            "Repeat 4–6 cycles.",
        ],
        duration_minutes=4,
        applicable_emotions=["anxiety", "stress", "anger", "fear"],
        min_intensity=3,
    ),
    Recommendation(
        category="breathing",
        title="5-5-5 Quick Reset",
        description="A rapid 90-second technique for when you need to settle quickly before an exam or presentation.",
        instructions=[
            "Breathe in for 5 seconds.",
            "Hold for 5 seconds.",
            "Breathe out for 5 seconds.",
            "Repeat 3 times.",
        ],
        duration_minutes=2,
        applicable_emotions=["anxiety", "fear", "stress"],
        min_intensity=1,
    ),

    # ── Mindfulness & Grounding ─────────────────────────────────────────────────
    Recommendation(
        category="mindfulness",
        title="5-4-3-2-1 Grounding",
        description="An evidence-based grounding technique that anchors you to the present moment using your five senses.",
        instructions=[
            "Look around and name 5 things you can see.",
            "Identify 4 things you can physically touch.",
            "Notice 3 things you can hear right now.",
            "Find 2 things you can smell (or like the smell of).",
            "Identify 1 thing you can taste.",
            "Take a slow breath. You are here, you are safe.",
        ],
        duration_minutes=5,
        applicable_emotions=["anxiety", "fear", "sadness", "anger"],
        min_intensity=4,
    ),
    Recommendation(
        category="mindfulness",
        title="Body Scan Relaxation",
        description="A mindfulness-based body scan to release physical tension held during stress.",
        instructions=[
            "Lie down or sit comfortably.",
            "Close your eyes and take three slow breaths.",
            "Bring attention to the top of your head. Notice any tension.",
            "Slowly move attention down: forehead → jaw → shoulders → chest → belly → hands → legs → feet.",
            "With each area, breathe in and consciously release tension on the exhale.",
            "Spend 1–2 minutes on areas that feel tight.",
        ],
        duration_minutes=10,
        applicable_emotions=["stress", "anxiety", "sadness", "burnout"],
        min_intensity=3,
    ),
    Recommendation(
        category="mindfulness",
        title="Mindful Minute",
        description="One minute of full presence — suitable even between study sessions.",
        instructions=[
            "Set a 60-second timer.",
            "Sit still and focus only on your breathing.",
            "When a thought arises, gently label it 'thinking' and return to your breath.",
            "Notice the sounds around you without judgment.",
        ],
        duration_minutes=1,
        applicable_emotions=[],
        min_intensity=1,
    ),

    # ── CBT-Inspired Cognitive Reframes ────────────────────────────────────────
    Recommendation(
        category="cbt",
        title="Thought Record — Challenge Negative Thinking",
        description="A classic CBT technique to identify and reframe unhelpful thought patterns.",
        instructions=[
            "Write down the upsetting thought exactly as it came to you.",
            "Ask: What is the evidence FOR this thought?",
            "Ask: What is the evidence AGAINST this thought?",
            "Consider: What would I tell a friend who had this thought?",
            "Write a more balanced, realistic version of the thought.",
            "Notice how your feelings shift slightly with the new thought.",
        ],
        duration_minutes=10,
        applicable_emotions=["sadness", "anxiety", "anger", "fear"],
        min_intensity=5,
    ),
    Recommendation(
        category="cbt",
        title="Worry Time",
        description="Schedule your worries so they don't consume the whole day.",
        instructions=[
            "Choose a fixed 15-minute 'worry slot' each day (not before bed).",
            "When a worry arrives outside that time, write it down briefly.",
            "Tell yourself: 'I'll think about this at worry time.'",
            "During your worry slot, review the list. Many concerns will feel smaller.",
            "For remaining concerns, write one small action you could take.",
        ],
        duration_minutes=15,
        applicable_emotions=["anxiety", "fear", "stress"],
        min_intensity=4,
    ),

    # ── Academic Stress Tips ───────────────────────────────────────────────────
    Recommendation(
        category="academic",
        title="Pomodoro Study Method",
        description="Break study sessions into focused sprints with structured breaks to prevent burnout.",
        instructions=[
            "Choose one task to focus on.",
            "Set a timer for 25 minutes. Work only on that task.",
            "When the timer rings, take a 5-minute break — stand up, stretch, hydrate.",
            "After 4 Pomodoros, take a longer break of 15–30 minutes.",
            "Track your completed Pomodoros to build a sense of progress.",
        ],
        duration_minutes=30,
        applicable_emotions=["stress", "burnout", "anxiety"],
        min_intensity=3,
    ),
    Recommendation(
        category="academic",
        title="Brain Dump Before Studying",
        description="Clear mental clutter before a study session to improve focus and reduce overwhelm.",
        instructions=[
            "Take a blank page or note app.",
            "Write down every task, worry, or distraction on your mind — without filtering.",
            "Review the list and circle the 1–3 most important items.",
            "Set everything else aside for now.",
            "Start your study session only working on the circled items.",
        ],
        duration_minutes=5,
        applicable_emotions=["stress", "anxiety", "burnout"],
        min_intensity=4,
    ),
    Recommendation(
        category="academic",
        title="Two-Minute Rule for Procrastination",
        description="Beat procrastination by committing to just two minutes of a task.",
        instructions=[
            "Identify the task you've been avoiding.",
            "Tell yourself: 'I will only do 2 minutes of this.'",
            "Start immediately — open the document, read the first paragraph.",
            "Most of the time, starting is the hardest part. Keep going if momentum builds.",
            "If you genuinely stop after 2 minutes, that still counts as a win.",
        ],
        duration_minutes=2,
        applicable_emotions=["stress", "burnout", "sadness"],
        min_intensity=2,
    ),

    # ── Journaling & Gratitude ─────────────────────────────────────────────────
    Recommendation(
        category="journaling",
        title="Gratitude Journal (3 Good Things)",
        description="Research from positive psychology shows three daily gratitude entries can improve mood within two weeks.",
        instructions=[
            "Open a notebook or notes app.",
            "Write 3 things that went well today — big or small.",
            "For each one, write one sentence about WHY it went well.",
            "Re-read the list slowly.",
        ],
        duration_minutes=5,
        applicable_emotions=["sadness", "loneliness", "burnout"],
        min_intensity=2,
    ),
    Recommendation(
        category="journaling",
        title="Feelings Letter (Unsent)",
        description="Express difficult emotions freely in a letter you'll never send — a powerful emotional release technique.",
        instructions=[
            "Address the letter to whoever or whatever is causing the pain.",
            "Write without censoring: express anger, sadness, fear, or disappointment.",
            "Include what you wish were different.",
            "End with one thing you are letting go of today.",
            "You do NOT need to send this letter. Tear it up, delete it, or keep it — your choice.",
        ],
        duration_minutes=15,
        applicable_emotions=["anger", "sadness", "fear", "loneliness"],
        min_intensity=6,
    ),

    # ── Relaxation ─────────────────────────────────────────────────────────────
    Recommendation(
        category="relaxation",
        title="Progressive Muscle Relaxation (PMR)",
        description="Systematically tense and release muscle groups to achieve deep physical relaxation.",
        instructions=[
            "Sit or lie in a comfortable position.",
            "Starting with your feet: tense the muscles tightly for 5 seconds.",
            "Release and notice the relaxation for 10 seconds.",
            "Move upward: calves → thighs → abdomen → fists → arms → shoulders → face.",
            "Breathe slowly throughout.",
        ],
        duration_minutes=10,
        applicable_emotions=["stress", "anxiety", "anger"],
        min_intensity=4,
    ),
    Recommendation(
        category="relaxation",
        title="Cold Water Reset",
        description="A quick physiological technique — cold water on the face activates the dive reflex, slowing heart rate.",
        instructions=[
            "Go to a sink and run cold water.",
            "Splash cold water on your face 3–5 times.",
            "Hold your wrists under cold water for 30 seconds.",
            "Take three slow breaths.",
        ],
        duration_minutes=2,
        applicable_emotions=["anger", "anxiety", "stress", "fear"],
        min_intensity=6,
    ),

    # ── Physical Games & Movement ──────────────────────────────────────────────
    Recommendation(
        category="physical_game",
        title="Music & Movement Break",
        description="A short dance/stretch break. Movement releases endorphins and breaks the stress cycle.",
        instructions=[
            "Put on one song you enjoy (3–4 minutes).",
            "Stand up and gently stretch your arms, neck, and back.",
            "Move to the rhythm — no technique required.",
            "Walk around the room if dancing feels like too much.",
            "Stop immediately if you feel dizzy, short of breath, or pain.",
        ],
        duration_minutes=5,
        applicable_emotions=["sadness", "burnout", "stress", "loneliness"],
        min_intensity=2,
        max_intensity=7,
        environment="indoor",
        group_size="solo",
        energy_level="low",
        has_physical_activity=True,
        safety_note="Stop if you feel pain, dizziness, or discomfort. Stay hydrated.",
    ),
    Recommendation(
        category="physical_game",
        title="Balloon Volleyball",
        description="A cooperative indoor game requiring no equipment beyond a balloon. Fun, low-impact, and social.",
        instructions=[
            "Inflate a balloon.",
            "With a friend or small group, keep it in the air without letting it touch the floor.",
            "Add challenges: only use one hand, only use your head, count how long you can keep it up.",
            "Play for 5–10 minutes.",
            "Stop if anyone feels tired or unwell.",
        ],
        duration_minutes=10,
        applicable_emotions=["loneliness", "sadness", "burnout", "stress"],
        min_intensity=2,
        max_intensity=7,
        environment="indoor",
        group_size="pair",
        energy_level="low",
        has_physical_activity=True,
        low_mobility_friendly=True,
        safety_note="Use a light balloon. Avoid if you have breathing difficulties. Stay hydrated.",
    ),
    Recommendation(
        category="physical_game",
        title="Outdoor Walk Scavenger Hunt",
        description="A gamified walk that redirects anxious mental energy into gentle curiosity and exploration.",
        instructions=[
            "Step outside for a 10–15 minute walk.",
            "Find: something red, something round, something that makes a sound, a shadow, and something that makes you smile.",
            "Take a photo of each item on your phone.",
            "Walk at your own pace — no rush.",
        ],
        duration_minutes=15,
        applicable_emotions=["anxiety", "stress", "loneliness", "sadness"],
        min_intensity=2,
        max_intensity=6,
        environment="outdoor",
        group_size="solo",
        energy_level="low",
        has_physical_activity=True,
        safety_note="Walk in a safe, familiar area. Take water. Stop if you feel unwell.",
    ),
    Recommendation(
        category="physical_game",
        title="Badminton or Table Tennis Rally",
        description="A friendly rally-based game that combines light aerobic activity with social connection.",
        instructions=[
            "Find a partner and a clear space.",
            "Set a goal to keep the rally going as long as possible — cooperative, not competitive.",
            "Rest between rallies.",
            "Play for 15–20 minutes.",
        ],
        duration_minutes=20,
        applicable_emotions=["burnout", "loneliness", "stress"],
        min_intensity=3,
        max_intensity=7,
        environment="any",
        group_size="pair",
        energy_level="medium",
        has_physical_activity=True,
        low_mobility_friendly=False,
        safety_note="Warm up first. Stop if you feel pain or shortness of breath. Drink water.",
    ),
    Recommendation(
        category="physical_game",
        title="Desk Stretching Circuit",
        description="A 5-minute seated or standing stretch routine perfect for study breaks.",
        instructions=[
            "Neck rolls: slowly roll your head in a half-circle, left and right. 5 each side.",
            "Shoulder shrugs: raise shoulders to ears, hold 3s, release. Repeat 5 times.",
            "Chest opener: clasp hands behind your back, gently open your chest. Hold 10s.",
            "Seated spinal twist: sit upright, twist gently to each side. Hold 10s each.",
            "Wrist circles: extend arms and rotate wrists. 10 circles each direction.",
        ],
        duration_minutes=5,
        applicable_emotions=["stress", "burnout", "anxiety"],
        min_intensity=1,
        environment="indoor",
        group_size="solo",
        energy_level="low",
        has_physical_activity=True,
        low_mobility_friendly=True,
        safety_note="Move gently. Stop if any movement causes pain.",
    ),
    Recommendation(
        category="physical_game",
        title="Campus Frisbee or Catch",
        description="A casual outdoor game to decompress with a friend and get fresh air.",
        instructions=[
            "Grab a frisbee, ball, or rolled-up socks.",
            "Find an open outdoor space.",
            "Toss back and forth at a comfortable distance for 15 minutes.",
            "Chat naturally — the game is the excuse to connect.",
        ],
        duration_minutes=15,
        applicable_emotions=["loneliness", "burnout", "stress", "sadness"],
        min_intensity=2,
        max_intensity=6,
        environment="outdoor",
        group_size="pair",
        energy_level="medium",
        has_physical_activity=True,
        low_mobility_friendly=False,
        safety_note="Stay hydrated. Avoid playing in extreme heat or rain.",
    ),
    Recommendation(
        category="physical_game",
        title="Indoor Bowling (DIY)",
        description="Set up household items as pins and roll a soft ball — a playful, low-effort indoor activity.",
        instructions=[
            "Line up 6–10 plastic bottles, cups, or rolled socks as 'pins'.",
            "Stand 2–3 metres back with a soft ball.",
            "Take turns bowling. Keep score or play cooperatively.",
            "Play 5–10 rounds.",
        ],
        duration_minutes=15,
        applicable_emotions=["loneliness", "sadness", "burnout"],
        min_intensity=2,
        max_intensity=6,
        environment="indoor",
        group_size="group",
        energy_level="low",
        has_physical_activity=True,
        low_mobility_friendly=True,
        safety_note="Use a soft ball. Clear the floor of tripping hazards first.",
    ),

    # ── Motivational ──────────────────────────────────────────────────────────
    Recommendation(
        category="motivational",
        title="Values Compass",
        description="Reconnect with what matters most to restore a sense of purpose.",
        instructions=[
            "On a piece of paper, write answers to: 'What matters most to me in life?'",
            "List 3–5 core values (e.g. connection, growth, creativity, kindness).",
            "Choose one value and write one small thing you can do TODAY that aligns with it.",
        ],
        duration_minutes=5,
        applicable_emotions=["burnout", "sadness", "loneliness"],
        min_intensity=4,
    ),
    Recommendation(
        category="motivational",
        title="One Small Win",
        description="Break the inertia of feeling stuck by identifying a single achievable action.",
        instructions=[
            "Ask yourself: 'What is the smallest possible step I could take right now?'",
            "It might be: drinking a glass of water, opening a notebook, sending one message.",
            "Do that one thing. Celebrate it — seriously. Progress starts with momentum.",
        ],
        duration_minutes=2,
        applicable_emotions=["burnout", "sadness", "stress"],
        min_intensity=3,
    ),
]


# ─── Recommendation engine ────────────────────────────────────────────────────

def get_recommendations(
    emotion_result: EmotionResult,
    include_physical: bool = True,
    environment: Optional[str] = None,        # "indoor" | "outdoor" | None
    group_size: Optional[str] = None,         # "solo" | "pair" | "group" | None
    low_mobility: bool = False,
    max_suggestions: int = 4,
) -> list[Recommendation]:
    """
    Return a ranked list of recommendations tailored to the detected emotion state.

    Rules:
    - Crisis state → no physical games; return only grounding/breathing/safety recs.
    - High intensity → prioritise breathing + grounding.
    - Filter by environment / group_size / mobility constraints if provided.
    """
    emotion = emotion_result.primary_emotion
    intensity = emotion_result.intensity
    is_crisis = emotion_result.is_crisis

    candidates: list[Recommendation] = []

    for rec in RECOMMENDATIONS:
        # Hard exclusion: no physical games during crisis
        if is_crisis and rec.has_physical_activity:
            continue

        # Respect user's physical preference
        if not include_physical and rec.has_physical_activity:
            continue

        # Mobility filter
        if low_mobility and not rec.low_mobility_friendly:
            continue

        # Environment filter
        if environment and rec.environment not in (environment, "any"):
            continue

        # Group size filter
        if group_size and rec.group_size not in (group_size, "any"):
            continue

        # Intensity range
        if not (rec.min_intensity <= intensity <= rec.max_intensity):
            continue

        # Emotion relevance score
        score = 0
        if emotion in rec.applicable_emotions:
            score += 3
        if rec.applicable_emotions == []:  # universal
            score += 1

        # Prioritise non-physical for high intensity
        if intensity >= 7 and not rec.has_physical_activity:
            score += 2

        candidates.append((score, rec))

    # Sort by score descending, then shuffle within same score for variety
    candidates.sort(key=lambda x: -x[0])

    # Select diverse categories
    seen_categories: set[str] = set()
    selected: list[Recommendation] = []
    for _, rec in candidates:
        if rec.category not in seen_categories or len(selected) < 2:
            selected.append(rec)
            seen_categories.add(rec.category)
        if len(selected) >= max_suggestions:
            break

    return selected


def format_recommendation(rec: Recommendation) -> str:
    """Format a single recommendation as readable text for the LLM context."""
    lines = [f"**{rec.title}** ({rec.category.replace('_', ' ').title()} · ~{rec.duration_minutes} min)"]
    lines.append(rec.description)
    lines.append("\nHow to do it:")
    for i, step in enumerate(rec.instructions, 1):
        lines.append(f"  {i}. {step}")
    if rec.has_physical_activity:
        lines.append(f"\n⚡ This is a physical activity — it's completely optional.")
        if rec.environment != "any":
            lines.append(f"  Space needed: {rec.environment}")
        if rec.group_size != "any":
            lines.append(f"  Best for: {rec.group_size}")
    if rec.safety_note:
        lines.append(f"\n⚠ Safety note: {rec.safety_note}")
    return "\n".join(lines)
