"""
MindMate AI — Nutrition Coach Agent
Uses Groq API → Ollama → built-in fallback.
"""
from __future__ import annotations
import json
from agents.ai_helper import ai_generate

_SYSTEM = (
    "You are MindMate Nutrition Coach — a warm, practical student nutrition expert. "
    "Create a DETAILED, PERSONALISED daily meal plan. Structure it with these sections:\n"
    "**Breakfast** — specific meal with nutritional reason\n"
    "**Mid-Morning Snack** — quick, healthy option\n"
    "**Lunch** — affordable, filling meal idea\n"
    "**Afternoon Snack** — energy-sustaining choice\n"
    "**Dinner** — simple, nutritious meal\n"
    "**Hydration Goal** — specific ml target with tips\n"
    "**Mood & Stress Nutrition Tip** — science-backed tip matched to their mood/stress level\n"
    "Use **bold** for section headers. Keep meals affordable, quick to make, and specific. 250-320 words."
)


def generate_meal_plan(user_profile: dict, mood_score: int = 5,
                       stress_level: int = 5, diet_logs: list = None) -> dict:
    prefs = user_profile.get("diet_prefs", "[]")
    if isinstance(prefs, str):
        try: prefs = json.loads(prefs)
        except Exception: prefs = []

    stress_context = "very high stress — prioritise calming, magnesium-rich foods" if stress_level >= 8 else \
                     "high stress — include omega-3 rich foods and avoid blood sugar spikes" if stress_level >= 6 else \
                     "moderate stress" if stress_level >= 4 else "low stress — focus on energy and focus"
    mood_context = "low mood — include tryptophan and B-vitamin rich foods" if mood_score <= 4 else \
                   "moderate mood" if mood_score <= 6 else "good mood — maintain with balanced nutrition"

    prompt = (f"Student daily meal plan: mood is {mood_score}/10 ({mood_context}), "
              f"stress is {stress_level}/10 ({stress_context}). "
              f"Diet preferences: {', '.join(prefs) if prefs else 'none specified'}.\n\n"
              f"Create a complete, personalised daily meal plan with all 5 meals + snacks, "
              f"hydration goal, and a specific mood/stress nutrition tip backed by science. "
              f"Make meals affordable (student budget), quick to prepare, and specific.")

    plan = ai_generate(_SYSTEM, prompt, max_tokens=400)
    if not plan:
        plan = _builtin_meal_plan(mood_score, stress_level, prefs)

    return {"meal_plan": plan, "hydration_goal_ml": 2500}


def _builtin_meal_plan(mood: int, stress: int, prefs: list) -> str:
    veg = "vegetarian" in prefs or "vegan" in prefs
    protein = "lentils or chickpeas" if veg else "eggs, Greek yoghurt, or canned tuna"
    main_protein = "tofu or tempeh" if veg else "chicken, eggs, or canned fish"

    stress_tip = ""
    if stress >= 7:
        stress_tip = "\n**High Stress Tip**: Add magnesium-rich foods today — a handful of walnuts, some dark chocolate (70%+), or spinach. Magnesium is depleted by stress and directly affects anxiety levels."
    elif stress >= 5:
        stress_tip = "\n**Mood Tip**: Include omega-3 rich foods where possible — walnuts, flaxseed, or oily fish. They reduce inflammatory markers linked to low mood."
    else:
        stress_tip = "\n**Energy Tip**: Your stress is manageable today — focus on slow-release carbs (oats, brown rice) to maintain steady energy and focus."

    return f"""**Your Student Meal Plan for Today**

**Breakfast** 🌅
Overnight oats with banana and a handful of berries. Oats provide slow-release energy that stabilises blood sugar and mood all morning. Takes 2 minutes to prepare the night before.

**Mid-Morning Snack**
Apple + {protein}. Combines fibre with protein for sustained focus — no 11am energy crash.

**Lunch** 🥗
Wholegrain wrap or rice bowl with {main_protein}, leafy greens, and any veggies you have. Add a squeeze of lemon for vitamin C, which supports stress resilience.

**Afternoon Snack**
A small square of dark chocolate (70%+) and a handful of walnuts. Magnesium + healthy fats = natural mood support.

**Dinner** 🍽️
Stir-fried rice or pasta with {main_protein} and whatever vegetables are in your fridge. Simple, filling, and takes under 20 minutes.

**Hydration Goal**: 8 glasses (2 litres) of water. Set a reminder every 2 hours — dehydration worsens focus and mood faster than almost anything else.
{stress_tip}

*These suggestions are general guidance, not medical nutrition advice.*"""


def analyze_diet_log(description: str, meal_type: str, user_profile: dict) -> str:
    return f"Logged your {meal_type}: '{description}'. Good job tracking your nutrition — consistency is what builds healthy habits over time."


def get_stress_foods() -> list[dict]:
    return [
        {"name": "Dark Chocolate (70%+)", "benefit": "Contains magnesium and flavonoids that reduce cortisol — the stress hormone"},
        {"name": "Blueberries",           "benefit": "Rich in antioxidants shown to reduce anxiety markers in studies"},
        {"name": "Oats",                  "benefit": "Slow-release carbs that stabilise blood sugar — preventing mood crashes"},
        {"name": "Avocado",               "benefit": "Healthy monounsaturated fats and B vitamins that support brain health"},
        {"name": "Chamomile Tea",         "benefit": "Contains apigenin — a compound that binds anxiety receptors in the brain"},
        {"name": "Walnuts",               "benefit": "Omega-3 fatty acids support serotonin production and mood regulation"},
        {"name": "Spinach",               "benefit": "Rich in magnesium — deficiency is directly linked to increased anxiety"},
        {"name": "Salmon / Sardines",     "benefit": "Highest dietary source of omega-3s, shown to reduce depression symptoms"},
        {"name": "Turmeric",              "benefit": "Curcumin has anti-inflammatory effects comparable to some antidepressants in studies"},
        {"name": "Bananas",               "benefit": "Tryptophan + B6 help your body produce serotonin — the mood-stabilising neurotransmitter"},
    ]
