"""
MindMate AI — Journal Analysis Agent
Uses Groq API → Ollama → built-in fallback.
"""
from __future__ import annotations
import random
from agents.ai_helper import ai_generate

_PROMPTS_BY_TYPE = {
    "reflection": [
        "What was the most significant moment of your day and why?",
        "What emotion has been most present for you today?",
        "What would you tell a good friend going through what you experienced today?",
        "What is one thing you learned about yourself today?",
        "What drained your energy, and what gave you energy today?",
    ],
    "gratitude": [
        "List three things that went well today, however small.",
        "Who made a positive difference in your life recently?",
        "What is one thing about yourself that you are grateful for?",
        "Describe a moment today where you felt at peace or content.",
        "What challenge are you secretly grateful for because of what it taught you?",
    ],
    "anxiety": [
        "What is the specific worry on your mind right now? Write it out fully.",
        "What is the worst realistic outcome, and how would you cope with it?",
        "What evidence supports your worry, and what evidence challenges it?",
        "What would you need to feel more secure right now?",
        "Write a letter of encouragement to yourself from a future version of you who got through this.",
    ],
    "goal": [
        "What is one goal you want to achieve this week, and why does it matter?",
        "What is the smallest first step you could take toward your goal?",
        "What has stopped you from pursuing this goal before?",
        "How will you feel when you achieve this goal?",
        "Who or what could support you on this journey?",
    ],
}

_SYSTEM = (
    "You are MindMate Journal Coach — deeply compassionate, insightful, and non-judgmental. "
    "Read the journal entry carefully and respond with a thoughtful analysis:\n"
    "**Emotional Themes** — Name the emotions you notice, gently and specifically\n"
    "**Strength Observed** — A genuine strength you see in their writing or situation\n"
    "**Gentle Reframe** — One helpful perspective shift or cognitive reframe\n"
    "**Reflection Insight** — A science-backed insight about journaling or their entry type\n"
    "**Next Step** — One small, concrete action they could take today\n"
    "Tone: warm therapist-friend. Use **bold** for section headers. 200-260 words."
)


def _builtin_analysis(content: str, entry_type: str) -> str:
    words = content.lower().split()
    # Simple keyword emotion detection
    emotions = []
    if any(w in words for w in ["stress", "overwhelm", "pressure", "anxious", "worry", "scared"]):
        emotions.append("stress/anxiety")
    if any(w in words for w in ["sad", "unhappy", "down", "depressed", "hurt", "lonely"]):
        emotions.append("sadness")
    if any(w in words for w in ["angry", "frustrated", "upset", "annoyed"]):
        emotions.append("frustration")
    if any(w in words for w in ["happy", "good", "great", "grateful", "thankful", "excited"]):
        emotions.append("positivity")
    if not emotions:
        emotions = ["reflection and self-awareness"]

    emo_str = " and ".join(emotions)

    strengths = []
    if any(w in words for w in ["try", "tried", "working", "effort", "practice"]):
        strengths.append("perseverance")
    if any(w in words for w in ["feel", "feeling", "felt", "emotion", "notice"]):
        strengths.append("strong emotional awareness")
    if any(w in words for w in ["think", "thought", "reflect", "wonder", "question"]):
        strengths.append("reflective thinking")
    if not strengths:
        strengths = ["the courage to write and reflect"]
    strength_str = " and ".join(strengths[:2])

    type_reflections = {
        "reflection": "Writing about your experiences — even difficult ones — is one of the most powerful tools for emotional processing. The act of putting feelings into words activates the prefrontal cortex and literally reduces emotional intensity.",
        "gratitude": "Gratitude journaling consistently ranks among the highest-impact wellbeing practices in research. By noticing what went well, you're training your brain to scan for positives rather than threats.",
        "anxiety": "Externalising your worries onto paper reduces their power — your mind no longer has to hold them. This is the first step in CBT-based worry management.",
        "goal": "Clarity about what you want is more than half the battle. The simple act of writing a goal makes you significantly more likely to take action toward it.",
    }
    reflection = type_reflections.get(entry_type, type_reflections["reflection"])

    return (f"**Emotional Themes**: This entry carries themes of {emo_str}. "
            f"You're clearly processing something real and important here — that takes honesty.\n\n"
            f"**Strength Observed**: I notice {strength_str} in your writing. "
            f"These are genuine assets, especially during challenging times.\n\n"
            f"**Gentle Reflection**: {reflection}\n\n"
            f"Keep writing — every entry builds self-knowledge that stays with you.")


def analyze_journal_entry(content: str, entry_type: str = "reflection") -> dict:
    prompt = (f"Journal entry type: {entry_type}\n\n"
              f"---\n{content[:1000]}\n---\n\n"
              f"Provide a thoughtful, compassionate analysis with emotional themes, "
              f"strengths observed, a gentle reframe, an insight about this type of journaling, "
              f"and one concrete next step.")
    insight = ai_generate(_SYSTEM, prompt, max_tokens=350)
    if not insight:
        insight = _builtin_analysis(content, entry_type)
    next_prompt = random.choice(_PROMPTS_BY_TYPE.get(entry_type, _PROMPTS_BY_TYPE["reflection"]))
    return {"insight": insight, "next_prompt": next_prompt}


def get_guided_prompt(entry_type: str = "reflection") -> str:
    return random.choice(_PROMPTS_BY_TYPE.get(entry_type, _PROMPTS_BY_TYPE["reflection"]))
