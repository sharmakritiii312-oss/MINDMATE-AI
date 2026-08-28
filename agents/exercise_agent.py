"""
MindMate AI — Exercise & Activity Agent
Uses Groq API → Ollama → built-in fallback.
"""
from __future__ import annotations
from agents.ai_helper import ai_generate

_SYSTEM = (
    "You are MindMate Fitness Coach — encouraging, knowledgeable, and student-friendly. "
    "Create a DETAILED, PERSONALISED workout plan structured as:\n"
    "**Warm-Up (5 min)** — 3-4 specific movements with duration\n"
    "**Main Workout** — 5-6 exercises with exact reps/sets/duration, matched to energy & stress\n"
    "**Cool-Down (5 min)** — 3-4 stretches with hold times\n"
    "**Why This Helps** — 2-3 sentences on the mental health benefits of this specific workout\n"
    "**Safety Note** — one important tip for this session\n"
    "Use **bold** for section headers. Match intensity to energy level. "
    "High stress → include cortisol-burning cardio. Low energy → gentle movement. 250-320 words."
)


def generate_workout_plan(user_profile: dict, stress_level: int = 5,
                          energy_level: int = 5, available_minutes: int = 30,
                          environment: str = "any") -> dict:
    fitness = user_profile.get("fitness_level", "beginner")
    intensity = "gentle/restorative" if energy_level <= 3 else \
                "moderate" if energy_level <= 6 else "energising/challenging"
    stress_note = "high stress — include cardio to burn cortisol" if stress_level >= 7 else \
                  "moderate stress — balance strength and movement" if stress_level >= 5 else \
                  "low stress — focus on strength and progression"

    prompt = (f"Create a personalised {available_minutes}-minute workout for a {fitness} student.\n"
              f"Energy level: {energy_level}/10 ({intensity})\n"
              f"Stress level: {stress_level}/10 ({stress_note})\n"
              f"Environment: {environment}\n\n"
              f"Provide: warm-up, main workout with exact reps/sets, cool-down, "
              f"mental health benefits, and a safety tip. Be specific and encouraging.")

    plan = ai_generate(_SYSTEM, prompt, max_tokens=400)
    if not plan:
        plan = _builtin_workout(stress_level, energy_level, available_minutes, environment, fitness)

    return {"workout_plan": plan, "estimated_duration": available_minutes}


def _builtin_workout(stress: int, energy: int, mins: int, env: str, fitness: str) -> str:
    if energy <= 3:
        intensity = "gentle"
        main = ("- 10x slow neck rolls each direction\n"
                "- 10x shoulder circles\n"
                "- Seated forward fold: hold 30 seconds\n"
                "- 5x deep spinal twists each side\n"
                "- Child's pose: hold 60 seconds")
        note = "Low energy is your body asking for rest. This gentle routine increases circulation without depleting you further."
    elif energy <= 6:
        intensity = "moderate"
        main = ("- 15x bodyweight squats\n"
                "- 10x push-ups (knees OK)\n"
                "- 20x walking lunges\n"
                "- 30-second plank\n"
                "- 20x glute bridges\n"
                "- Repeat 2 rounds")
        note = "Moderate movement at your energy level releases endorphins without overtaxing your system."
    else:
        intensity = "energising"
        main = ("- 30x jumping jacks\n"
                "- 15x burpees\n"
                "- 20x high knees (30 seconds)\n"
                "- 15x push-ups\n"
                "- 30-second sprint on the spot\n"
                "- Repeat 2–3 rounds")
        note = "High energy is the perfect time to challenge yourself — this burns cortisol and boosts focus for hours."

    stress_tip = ""
    if stress >= 7:
        stress_tip = "\n**Stress Relief Addition**: After your workout, lie down for 2 minutes and do box breathing (inhale 4s, hold 4s, exhale 4s, hold 4s). This completes the stress cycle and signals safety to your nervous system."

    return (f"**Your {mins}-Minute {intensity.title()} Workout**\n\n"
            f"**Warm-Up (5 min)**\n"
            f"- March in place for 2 minutes\n"
            f"- Arm circles: 10 forward, 10 backward\n"
            f"- Hip circles: 10 each direction\n"
            f"- Light leg swings: 10 each leg\n\n"
            f"**Main Workout**\n{main}\n\n"
            f"**Cool-Down (5 min)**\n"
            f"- Standing quad stretch: 30s each leg\n"
            f"- Seated hamstring stretch: 30s each side\n"
            f"- Chest opener: clasp hands behind back, hold 30s\n"
            f"- 5 slow deep breaths to finish\n\n"
            f"**Why This Helps**: {note}"
            f"{stress_tip}\n\n"
            f"*Always stop if you feel pain or dizziness. Stay hydrated — drink water before, during, and after.*")


STRESS_RELIEF_GAMES: list[dict] = [
    {
        "name": "Balloon Volleyball",
        "category": "indoor_game",
        "participants": "2+",
        "duration_min": 10,
        "energy": "low",
        "space": "small_indoor",
        "benefits": "Social connection, light movement, laughter — all proven stress reducers.",
        "rules": "Keep a balloon in the air without it touching the floor. Add rules for challenge.",
        "suitability": "Perfect for dorm rooms or study breaks with a friend.",
        "low_mobility": True,
    },
    {
        "name": "Campus Frisbee",
        "category": "outdoor_game",
        "participants": "2+",
        "duration_min": 20,
        "energy": "medium",
        "space": "outdoor",
        "benefits": "Fresh air, moderate aerobic exercise, social bonding, vitamin D.",
        "rules": "Toss a frisbee back and forth or play Ultimate Frisbee with a group.",
        "suitability": "Great for sunny days between classes.",
        "low_mobility": False,
    },
    {
        "name": "Dance Break",
        "category": "movement",
        "participants": "solo",
        "duration_min": 5,
        "energy": "low",
        "space": "any_indoor",
        "benefits": "Endorphin release, mood boost, creative self-expression.",
        "rules": "Play one favourite song and move however feels good. No technique required.",
        "suitability": "Perfect 5-minute study break, solo or with friends.",
        "low_mobility": True,
    },
    {
        "name": "Scavenger Hunt Walk",
        "category": "outdoor_game",
        "participants": "solo",
        "duration_min": 15,
        "energy": "low",
        "space": "outdoor",
        "benefits": "Mindful walking, redirects anxious thoughts, gentle exercise.",
        "rules": "Find 5 things: something red, round, natural, that makes a sound, that makes you smile.",
        "suitability": "Solo stress-relief walk with a purpose.",
        "low_mobility": True,
    },
    {
        "name": "Table Tennis Rally",
        "category": "indoor_game",
        "participants": "2",
        "duration_min": 15,
        "energy": "medium",
        "space": "campus_facility",
        "benefits": "Improves focus, hand-eye coordination, aerobic activity, social fun.",
        "rules": "Cooperative rally — aim to keep the ball going as long as possible.",
        "suitability": "Campus recreation rooms or student union.",
        "low_mobility": False,
    },
    {
        "name": "Indoor Bowling",
        "category": "indoor_game",
        "participants": "2+",
        "duration_min": 15,
        "energy": "low",
        "space": "large_indoor",
        "benefits": "Playful competition, light activity, laughter.",
        "rules": "Set up 10 bottles/cups. Use a soft ball to knock them down.",
        "suitability": "Common rooms or large spaces. Great for groups.",
        "low_mobility": True,
    },
    {
        "name": "Stretching Challenge",
        "category": "movement",
        "participants": "solo",
        "duration_min": 5,
        "energy": "low",
        "space": "any_indoor",
        "benefits": "Releases physical tension held from studying, improves circulation.",
        "rules": "Complete: neck rolls, shoulder shrugs, spinal twist, wrist circles, forward fold.",
        "suitability": "At your desk, between study sessions.",
        "low_mobility": True,
    },
    {
        "name": "Badminton",
        "category": "outdoor_game",
        "participants": "2-4",
        "duration_min": 20,
        "energy": "medium",
        "space": "outdoor_or_gym",
        "benefits": "Cardio workout, social play, requires focus which distracts from worry.",
        "rules": "Standard badminton rules or casual rally. Play to enjoy, not to win.",
        "suitability": "Campus sports areas or parks.",
        "low_mobility": False,
    },
]


def get_game_recommendations(energy: int = 5, space: str = "any",
                              participants: int = 1,
                              low_mobility: bool = False) -> list[dict]:
    """Filter stress-relief games based on user constraints."""
    games = STRESS_RELIEF_GAMES
    if low_mobility:
        games = [g for g in games if g["low_mobility"]]
    if space in ("indoor", "dorm", "small"):
        games = [g for g in games if "indoor" in g["space"] or g["space"] == "any_indoor"]
    if space == "outdoor":
        games = [g for g in games if "outdoor" in g["space"]]
    if participants == 1:
        games = [g for g in games if g["participants"] in ("solo", "2+", "2")]
    if energy <= 3:
        games = [g for g in games if g["energy"] == "low"]
    return games[:6]
