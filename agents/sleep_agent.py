"""
MindMate AI — Sleep Coach Agent
Uses Groq API → Ollama → built-in fallback.
"""
from __future__ import annotations
from agents.ai_helper import ai_generate

_SLEEP_SYSTEM = (
    "You are MindMate Sleep Coach — warm, evidence-based, and encouraging. "
    "Generate a PERSONALISED sleep plan with: 1) honest assessment of their data, "
    "2) a specific bedtime routine (with times), 3) three actionable sleep tips, "
    "4) one relaxation technique they can try tonight. "
    "Tone: like a caring friend, not a doctor. Under 200 words. No filler."
)


def generate_sleep_plan(sleep_history: list[dict], user_profile: dict) -> dict:
    if sleep_history:
        recent = sleep_history[:7]
        avg_dur  = round(sum(s.get("duration_hours", 0) for s in recent) / len(recent), 1)
        avg_qual = round(sum(s.get("quality_score", 5) for s in recent) / len(recent), 1)
        history_text = "\n".join(
            f"- {s.get('date','?')}: {s.get('duration_hours','?')}h, quality {s.get('quality_score','?')}/10"
            for s in recent
        )
    else:
        avg_dur, avg_qual = 7.0, 5.0
        history_text = "No sleep history yet."

    sleep_score = min(10.0, round((avg_dur / 8.0) * 5 + (avg_qual / 10.0) * 5, 1))

    prompt = (f"Student: {user_profile.get('name','Student')}, "
              f"avg sleep {avg_dur}h, quality {avg_qual}/10.\n"
              f"Recent logs:\n{history_text}\n\n"
              f"Give a personalised sleep plan: assessment, bedtime routine, 3 tips, one relaxation technique. "
              f"Keep it warm and under 250 words.")

    plan = ai_generate(_SLEEP_SYSTEM, prompt, max_tokens=260)
    if not plan:
        plan = _builtin_sleep_plan(avg_dur, avg_qual, user_profile.get("name", "Student"))

    return {"sleep_score": sleep_score, "avg_duration": avg_dur, "avg_quality": avg_qual, "plan": plan}


def _builtin_sleep_plan(avg_dur: float, avg_qual: float, name: str) -> str:
    parts = [f"**Good news, {name}** — here's your personalised sleep plan based on your data.\n"]

    # Assessment
    if avg_dur < 6:
        parts.append("**Sleep Assessment**: Your average of {:.1f}h is below the recommended 7–9h for students. Chronic short sleep impairs memory consolidation, mood regulation, and immune function.".format(avg_dur))
    elif avg_dur <= 9:
        parts.append("**Sleep Assessment**: Your {:.1f}h average is within a healthy range. Focus now on *quality* — consistent timing and winding down properly.".format(avg_dur))
    else:
        parts.append("**Sleep Assessment**: You're sleeping over 9h on average. Oversleeping can sometimes signal low mood or fatigue worth paying attention to.")

    parts.append("\n**Personalised Bedtime Routine**")
    parts.append("- **9:30 PM** — Put your phone on Do Not Disturb and dim room lights")
    parts.append("- **9:45 PM** — Light stretching or 5 minutes of slow breathing")
    parts.append("- **10:00 PM** — Read a physical book or journal for 15 minutes")
    parts.append("- **10:15 PM** — Lights out, same time every night — even weekends")

    parts.append("\n**3 Sleep Improvements for Students**")
    parts.append("1. **Consistent wake time** is more powerful than bedtime. Pick 7:00 AM and stick to it — your circadian rhythm will follow.")
    parts.append("2. **No caffeine after 2 PM** — caffeine's half-life is 5–7 hours, meaning a 3 PM coffee is still half-active at 10 PM.")
    parts.append("3. **Cool, dark room** (around 18°C) drops your core temperature, which is the biological trigger for deep sleep.")

    parts.append("\n**Tonight's Relaxation Technique — 4-7-8 Breathing**")
    parts.append("Inhale for 4 seconds → hold for 7 → exhale slowly for 8. Repeat 4 cycles. This activates the parasympathetic nervous system and reduces heart rate within minutes.")

    parts.append("\nSleep is not laziness — it's when your brain does its most important work. Protecting it is one of the highest-leverage things you can do for your wellbeing. 🌙")
    return "\n".join(parts)


def score_single_night(duration_hours: float, quality_score: int,
                       bedtime: str = "", wake_time: str = "") -> dict:
    score = min(10.0, round((duration_hours / 8.0) * 5 + (quality_score / 10.0) * 5, 1))
    if duration_hours < 5:
        feedback = "Very short sleep — your brain needs more rest to consolidate memories and regulate mood."
    elif duration_hours < 6.5:
        feedback = "Below recommended for students. Try to get to bed 30–60 minutes earlier tonight."
    elif duration_hours <= 9:
        feedback = "Good duration! Consistency is key — try to keep the same sleep and wake times."
    else:
        feedback = "Longer than average — oversleeping can sometimes indicate fatigue or low mood. How are you feeling?"
    return {"score": score, "feedback": feedback}
