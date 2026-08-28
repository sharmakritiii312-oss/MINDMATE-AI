"""
MindMate AI — Daily Wellness Coach Agent
Uses Groq API → Ollama → built-in fallback.
"""
from __future__ import annotations
from datetime import date
from agents.ai_helper import ai_generate

_COACH_SYSTEM = (
    "You are MindMate Daily Wellness Coach — warm, data-driven, and genuinely caring. "
    "Generate a DETAILED personalised morning wellness briefing. Structure it as:\n"
    "**Good Morning** — personal greeting with their name and date\n"
    "**Wellness Snapshot** — honest 2-3 sentence analysis of their mood/sleep/stress data\n"
    "**Today's 3 Goals** — specific, achievable goals based on their data\n"
    "**Movement Suggestion** — one exercise with duration, matched to their energy/stress\n"
    "**Nutrition Tip** — one specific food/meal tip matched to their stress level\n"
    "**Mental Wellness Technique** — one named technique with brief how-to instructions\n"
    "**Motivational Close** — one warm, genuine sentence (never generic or preachy)\n"
    "Use **bold** for section headers. Be specific to their actual data. 250-320 words."
)




def generate_daily_briefing(
    user_profile: dict,
    mood_history: list[dict],
    sleep_history: list[dict],
    wellness_history: list[dict],
    exercise_history: list[dict],
) -> dict:
    """Generate today's personalised wellness plan."""
    name = user_profile.get("name", "Student")
    today = date.today().strftime("%A, %B %d")

    # Summarise recent data
    mood_avg = round(
        sum(m.get("mood_score", 5) for m in mood_history[:7]) / max(len(mood_history[:7]), 1), 1
    ) if mood_history else 5.0

    sleep_avg = round(
        sum(s.get("duration_hours", 7) for s in sleep_history[:7]) / max(len(sleep_history[:7]), 1), 1
    ) if sleep_history else 7.0

    sleep_score = round(
        sum(s.get("sleep_score", 5) for s in sleep_history[:3]) / max(len(sleep_history[:3]), 1), 1
    ) if sleep_history else 5.0

    stress_avg = round(
        sum(m.get("stress_score", 5) for m in mood_history[:7]) / max(len(mood_history[:7]), 1), 1
    ) if mood_history else 5.0

    overall_wellness = round(
        sum(w.get("overall_score", 5) for w in wellness_history[:7]) / max(len(wellness_history[:7]), 1), 1
    ) if wellness_history else 5.0

    recent_activities = [e.get("activity_type", "unknown") for e in exercise_history[:5]]

    prompt = f"""Generate today's personalised wellness briefing for:
Name: {name}
Date: {today}

Current data summary:
- Average mood (last 7 days): {mood_avg}/10
- Average sleep duration (last 7 days): {sleep_avg}h
- Sleep score: {sleep_score}/10
- Average stress level: {stress_avg}/10
- Overall wellness score: {overall_wellness}/10
- Recent activities: {', '.join(recent_activities) if recent_activities else 'None logged yet'}
- Fitness level: {user_profile.get('fitness_level','beginner')}
- Activity level: {user_profile.get('activity_level','moderate')}

Please generate:
1. Good morning greeting using their name
2. Quick summary of their wellness status (mood/sleep/stress in 2 sentences)
3. Today's top 3 wellness goals (specific, achievable)
4. One exercise suggestion (with duration, matched to their data)
5. One diet tip for today (matched to their stress/mood level)
6. One mental wellness tip or technique for today
7. One motivational sentence to close

Format it as a natural, conversational morning message."""

    briefing_text = ai_generate(_COACH_SYSTEM, prompt, max_tokens=400)
    if not briefing_text:
        briefing_text = _builtin_briefing(name, today, mood_avg, sleep_avg, sleep_score, stress_avg, recent_activities)

    wellness_score = round(
        (mood_avg * 0.25) + (min(sleep_avg / 8.0, 1.0) * 10 * 0.25) +
        ((10 - stress_avg) * 0.25) + (overall_wellness * 0.25), 1
    )
    return {
        "briefing": briefing_text,
        "date": today,
        "scores": {"mood": mood_avg, "sleep": sleep_score,
                   "stress": stress_avg, "wellness": wellness_score},
    }


def _builtin_briefing(name, today, mood, sleep, sleep_sc, stress, activities) -> str:
    mood_str   = "great" if mood >= 7 else "okay" if mood >= 5 else "a bit low"
    sleep_str  = "well-rested" if sleep >= 7 else "a little tired" if sleep >= 5.5 else "quite tired"
    stress_str = "low" if stress <= 3 else "manageable" if stress <= 6 else "high"

    act_str = ", ".join(activities) if activities else "nothing logged yet"

    goal1 = "Take one 5-minute break every 45 minutes of study — your focus will improve dramatically."
    goal2 = "Drink a glass of water first thing and set a reminder every 2 hours."
    if stress >= 7:
        goal3 = "Do the 4-4-6 breathing exercise before your next stressful task: inhale 4s, hold 4s, exhale 6s."
    elif sleep < 6:
        goal3 = "Prioritise sleep tonight — set an alarm 30 minutes earlier to start your wind-down routine."
    else:
        goal3 = "Spend 10 minutes journaling today — reflect on one thing going well and one thing to improve."

    exercise = ("A 10-minute walk outside" if stress >= 6
                else "15 minutes of stretching or yoga" if sleep < 6
                else "A 20-minute moderate workout")
    diet_tip = ("Focus on magnesium-rich foods today (walnuts, dark chocolate, spinach) — they directly reduce cortisol."
                if stress >= 6 else
                "Start with a protein-rich breakfast (eggs, yoghurt, nuts) to stabilise blood sugar and mood all morning.")
    mental_tip = ("Try the 5-4-3-2-1 grounding exercise: name 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste."
                  if stress >= 6 else
                  "Set one clear intention for today — just one thing you want to accomplish. Write it down.")

    return f"""Good morning, {name}! 🌅 It's {today}.

**Your Wellness Snapshot**
You're feeling {mood_str} (mood {mood}/10), {sleep_str} (avg {sleep}h sleep), and your stress is {stress_str} ({stress}/10). Recent activities: {act_str}.

**Today's Top 3 Goals**
1. {goal1}
2. {goal2}
3. {goal3}

**Movement Suggestion** 🏃
{exercise} — matched to your current energy and stress level.

**Nutrition Tip** 🥗
{diet_tip}

**Mental Wellness Tip** 🧘
{mental_tip}

You're doing better than you think. One small step today is enough. 💙"""
