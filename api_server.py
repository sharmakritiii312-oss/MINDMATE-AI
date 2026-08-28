"""
MindMate AI — FastAPI Backend
Frontend is served instantly. Heavy ML models load in the background.
"""
from __future__ import annotations

import threading
import concurrent.futures
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from config import API_HOST, API_PORT

# ─── Load database immediately (pure stdlib — always works) ───────────────────
import database as _db_mod

# ─── App (created immediately — no ML imports yet) ────────────────────────────

app = FastAPI(title="MindMate AI Platform", version="2.0.0",
              description="AI-Powered Mental Health & Wellness Companion for Students")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

_frontend_dir = Path(__file__).parent / "frontend"
_static_dir   = _frontend_dir / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse(str(_frontend_dir / "index.html"))

# ─── Readiness tracking ───────────────────────────────────────────────────────

_ready = {"db": True, "ml": False}   # DB is loaded at import time above
_loading_error: Optional[str] = None

@app.get("/health")
def health():
    return {
        "status": "ok" if all(_ready.values()) else "loading",
        "db_ready": _ready["db"],
        "ml_ready": _ready["ml"],
        "version": "2.0.0",
        "platform": "MindMate AI",
    }

@app.get("/ready")
def ready():
    if not all(_ready.values()):
        pct = (sum(_ready.values()) / len(_ready)) * 100
        return JSONResponse({"ready": False, "progress": int(pct),
                             "message": "AI models loading… please wait."}, status_code=202)
    return {"ready": True}

# ─── Lazy module references (populated after background load) ─────────────────

_db = _db_mod   # already loaded — never None
_orch = _emotion = _sleep_a = _nutr_a = _ex_a = _jour_a = _coach_a = _anal_a = None

def _require_db():
    """No-op — DB is always ready (loaded at import time)."""
    pass

def _require_ml():
    """Raise a friendly error if ML hasn't loaded yet (chat/emotion pipeline only)."""
    if not _ready["ml"]:
        raise HTTPException(503, detail="AI models are still loading. Please wait 30–60 seconds and try again.")

def _require_agents():
    """Ensure the agent modules (sleep/nutrition/exercise) are loaded.
    These don't need the emotion pipeline — they work with Groq or built-in fallback.
    Returns True if agents are ready, False otherwise (caller can still use built-in logic)."""
    return _ready["ml"]

# ─── Schemas ──────────────────────────────────────────────────────────────────

class UserProfileIn(BaseModel):
    name: str = "Student"
    age: Optional[int] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None
    activity_level: str = "moderate"
    fitness_level: str = "beginner"
    diet_prefs: list[str] = []
    wellness_goals: list[str] = []

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    user_id: str = "default"
    include_physical: bool = True
    environment: Optional[str] = None
    group_size: Optional[str] = None
    low_mobility: bool = False

class MoodLogIn(BaseModel):
    user_id: str = "default"
    mood_score: int = Field(..., ge=1, le=10)
    note: str = ""
    stress_score: int = Field(5, ge=0, le=10)
    energy_score: int = Field(5, ge=0, le=10)

class SleepLogIn(BaseModel):
    user_id: str = "default"
    date: str = ""
    bedtime: str = ""
    wake_time: str = ""
    duration_hours: float = Field(..., ge=0, le=24)
    quality_score: int = Field(..., ge=1, le=10)
    notes: str = ""

class JournalEntryIn(BaseModel):
    user_id: str = "default"
    content: str = Field(..., min_length=1)
    entry_type: str = "reflection"
    mood_before: int = Field(5, ge=1, le=10)

class ExerciseLogIn(BaseModel):
    user_id: str = "default"
    activity_type: str
    duration_min: int = Field(..., ge=1)
    intensity: str = "moderate"
    notes: str = ""

class WorkoutRequest(BaseModel):
    user_id: str = "default"
    stress_level: int = Field(5, ge=1, le=10)
    energy_level: int = Field(5, ge=1, le=10)
    available_minutes: int = 30
    environment: str = "any"

class MealPlanRequest(BaseModel):
    user_id: str = "default"
    mood_score: int = 5
    stress_level: int = 5

class GameRequest(BaseModel):
    energy: int = Field(5, ge=1, le=10)
    space: str = "any"
    participants: int = 1
    low_mobility: bool = False

# ─── User ─────────────────────────────────────────────────────────────────────

@app.get("/user/{user_id}")
def get_user(user_id: str):
    _require_db()
    return _db.get_or_create_user(user_id)

@app.post("/user/{user_id}")
def upsert_user(user_id: str, body: UserProfileIn):
    _require_db()
    import json
    _db.get_or_create_user(user_id, name=body.name)
    _db.update_user_profile(
        user_id, name=body.name, age=body.age,
        weight_kg=body.weight_kg, height_cm=body.height_cm,
        activity_level=body.activity_level, fitness_level=body.fitness_level,
        diet_prefs=json.dumps(body.diet_prefs),
        wellness_goals=json.dumps(body.wellness_goals),
    )
    return {"status": "ok"}

# ─── Chat ─────────────────────────────────────────────────────────────────────

_AI_TIMEOUT = 120  # seconds — max time to wait for any LLM response

def _run_with_timeout(fn, *args, timeout=_AI_TIMEOUT, error_msg="AI is thinking too long", **kwargs):
    """Run fn(*args, **kwargs) in a thread with a hard timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise HTTPException(504, detail=f"{error_msg}. Please try again.")
        except Exception as e:
            raise HTTPException(500, detail=str(e))


@app.post("/chat")
def chat(req: ChatRequest):
    _require_db()
    _require_ml()
    result = _run_with_timeout(
        _orch.orchestrator.chat,
        user_message=req.message, session_id=req.session_id,
        user_id=req.user_id, include_physical=req.include_physical,
        environment=req.environment, group_size=req.group_size,
        low_mobility=req.low_mobility,
    )
    try:
        _db.log_mood(
            req.user_id,
            mood_score=max(1, 10 - result.emotion.intensity + 2),
            primary_emotion=result.emotion.primary_emotion,
            emotions_json=result.emotion.emotion_scores,
            stress_score=result.emotion.intensity,
        )
    except Exception:
        pass
    return {
        "session_id": result.session_id,
        "response": result.assistant_response,
        "emotion": {
            "primary_emotion":   result.emotion.primary_emotion,
            "secondary_emotion": result.emotion.secondary_emotion,
            "intensity":         result.emotion.intensity,
            "risk_level":        result.emotion.risk_level,
            "sentiment":         result.emotion.sentiment,
            "sentiment_score":   result.emotion.sentiment_score,
            "valence":           result.emotion.valence,
            "arousal":           result.emotion.arousal,
            "is_crisis":         result.emotion.is_crisis,
            "emotion_scores":    result.emotion.emotion_scores,
            "emotion_nuances":   result.emotion.emotion_nuances,
        },
        "recommendations": [
            {"category": r.category, "title": r.title,
             "duration_minutes": r.duration_minutes,
             "has_physical_activity": r.has_physical_activity}
            for r in result.recommendations
        ],
        "was_crisis": result.was_crisis,
    }

# ─── Mood ─────────────────────────────────────────────────────────────────────

@app.post("/mood/log")
def log_mood_entry(body: MoodLogIn):
    _require_db()
    emotion_data = {}
    if body.note and _ready["ml"]:
        try:
            er = _emotion.analyze(body.note)
            emotion_data = er.emotion_scores
        except Exception:
            pass
    entry_id = _db.log_mood(
        body.user_id, body.mood_score,
        emotions_json=emotion_data, note=body.note,
        stress_score=body.stress_score, energy_score=body.energy_score,
    )
    return {"id": entry_id, "status": "logged"}

@app.get("/mood/history")
def mood_history(user_id: str = Query("default"), days: int = Query(30)):
    _require_db()
    return _db.get_mood_history(user_id, days)

@app.get("/mood/analytics")
def mood_analytics(user_id: str = Query("default")):
    _require_db()
    import json
    logs = _db.get_mood_history(user_id, 30)
    if not logs:
        return {"avg_mood": 5, "avg_stress": 5, "count": 0, "top_emotion": "neutral"}
    avg_mood = round(sum(l["mood_score"] for l in logs) / len(logs), 1)
    avg_stress = round(sum(l.get("stress_score", 5) for l in logs) / len(logs), 1)
    all_emotions: dict[str, int] = {}
    for l in logs:
        try:
            ej = json.loads(l.get("emotions_json", "{}")) if isinstance(l.get("emotions_json"), str) else (l.get("emotions_json") or {})
            for k in ej:
                all_emotions[k] = all_emotions.get(k, 0) + 1
        except Exception:
            pass
    top_emotion = max(all_emotions, key=all_emotions.get) if all_emotions else "neutral"
    return {"avg_mood": avg_mood, "avg_stress": avg_stress, "count": len(logs), "top_emotion": top_emotion}

# ─── Sleep ────────────────────────────────────────────────────────────────────

@app.post("/sleep/log")
def log_sleep_entry(body: SleepLogIn):
    _require_db()
    # score_single_night is pure math — no ML needed
    from agents.sleep_agent import score_single_night as _score_night
    scored = _score_night(body.duration_hours, body.quality_score)
    date_str = body.date or date.today().isoformat()
    entry_id = _db.log_sleep(
        body.user_id, date_str, body.bedtime, body.wake_time,
        body.duration_hours, body.quality_score, body.notes, sleep_score=scored["score"],
    )
    return {"id": entry_id, "sleep_score": scored["score"], "feedback": scored["feedback"]}

@app.get("/sleep/history")
def sleep_history(user_id: str = Query("default"), days: int = Query(14)):
    _require_db()
    return _db.get_sleep_history(user_id, days)

@app.get("/sleep/plan")
def sleep_plan(user_id: str = Query("default")):
    # Works without ML: uses Groq API → built-in fallback
    from agents import sleep_agent as _sa
    user = _db.get_or_create_user(user_id)
    history = _db.get_sleep_history(user_id, 7)
    return _run_with_timeout(_sa.generate_sleep_plan, history, user,
                             error_msg="Sleep plan timed out")

# ─── Nutrition ────────────────────────────────────────────────────────────────

@app.post("/nutrition/meal-plan")
def meal_plan(body: MealPlanRequest):
    # Works without ML: uses Groq API → built-in fallback
    from agents import nutrition_agent as _na
    user = _db.get_or_create_user(body.user_id)
    return _run_with_timeout(_na.generate_meal_plan, user, body.mood_score, body.stress_level,
                             error_msg="Meal plan timed out")

@app.get("/nutrition/stress-foods")
def stress_foods():
    # Static data — no LLM needed at all
    from agents.nutrition_agent import get_stress_foods
    return get_stress_foods()

# ─── Exercise ─────────────────────────────────────────────────────────────────

@app.post("/exercise/plan")
def workout_plan(body: WorkoutRequest):
    # Works without ML: uses Groq API → built-in fallback
    from agents import exercise_agent as _ea
    user = _db.get_or_create_user(body.user_id)
    return _run_with_timeout(_ea.generate_workout_plan,
                             user, body.stress_level, body.energy_level,
                             body.available_minutes, body.environment,
                             error_msg="Workout plan timed out")

@app.post("/exercise/log")
def log_exercise_entry(body: ExerciseLogIn):
    _require_db()
    entry_id = _db.log_exercise(body.user_id, body.activity_type,
                                body.duration_min, body.intensity, body.notes)
    return {"id": entry_id, "status": "logged"}

@app.get("/exercise/history")
def exercise_history(user_id: str = Query("default"), days: int = Query(14)):
    _require_db()
    return _db.get_exercise_history(user_id, days)

@app.post("/exercise/games")
def recommend_games(body: GameRequest):
    # Static catalogue — no LLM needed
    from agents.exercise_agent import get_game_recommendations
    return get_game_recommendations(body.energy, body.space,
                                    body.participants, body.low_mobility)

# ─── Journal ─────────────────────────────────────────────────────────────────

@app.post("/journal/entry")
def create_journal_entry(body: JournalEntryIn):
    # Works without ML: uses Groq API → built-in fallback
    from agents import journal_agent as _ja
    analysis = _run_with_timeout(_ja.analyze_journal_entry, body.content, body.entry_type,
                                 error_msg="Journal analysis timed out")
    entry_id = _db.save_journal_entry(
        body.user_id, body.content, body.entry_type,
        ai_insight=analysis["insight"], mood_before=body.mood_before,
    )
    return {"id": entry_id, "insight": analysis["insight"], "next_prompt": analysis["next_prompt"]}

@app.get("/journal/entries")
def journal_entries(user_id: str = Query("default"), limit: int = Query(20)):
    _require_db()
    return _db.get_journal_entries(user_id, limit)

@app.get("/journal/prompt")
def journal_prompt(entry_type: str = Query("reflection")):
    # Static prompts — no LLM needed
    from agents.journal_agent import get_guided_prompt
    return {"prompt": get_guided_prompt(entry_type)}

# ─── Wellness Coach ───────────────────────────────────────────────────────────

@app.get("/wellness/daily-briefing")
def daily_briefing(user_id: str = Query("default")):
    # Works without ML: uses Groq API → built-in fallback
    from agents import daily_coach_agent as _ca
    _require_db()
    user = _db.get_or_create_user(user_id)
    mood     = _db.get_mood_history(user_id, 7)
    sleep    = _db.get_sleep_history(user_id, 7)
    wellness = _db.get_wellness_history(user_id, 7)
    exercise = _db.get_exercise_history(user_id, 7)
    # Run LLM with a 90-second timeout so the endpoint never hangs forever
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(_ca.generate_daily_briefing, user, mood, sleep, wellness, exercise)
            result = future.result(timeout=90)
    except concurrent.futures.TimeoutError:
        raise HTTPException(504, detail="Briefing timed out. Please try again.")
    except Exception as e:
        raise HTTPException(500, detail=f"Briefing error: {e}")
    today = date.today().isoformat()
    sc = result["scores"]
    _db.save_wellness_score(user_id, today, overall=sc["wellness"], mood=sc["mood"],
                            sleep=sc["sleep"], stress=sc["stress"],
                            activity=0, nutrition=0, summary=result["briefing"][:500])
    return result

@app.get("/wellness/toolkit")
def wellness_toolkit():
    return {
        "breathing": [
            {"name": "4-4-6 Calm Breath", "steps": ["Inhale 4s", "Hold 4s", "Exhale 6s"], "duration": "3 min"},
            {"name": "Box Breathing",      "steps": ["Inhale 4s", "Hold 4s", "Exhale 4s", "Hold 4s"], "duration": "4 min"},
            {"name": "5-5-5 Quick Reset",  "steps": ["Inhale 5s", "Hold 5s", "Exhale 5s", "Repeat 3x"], "duration": "2 min"},
        ],
        "mindfulness": [
            {"name": "5-4-3-2-1 Grounding", "steps": ["5 things you see", "4 you can touch", "3 you hear", "2 you smell", "1 you taste"], "duration": "5 min"},
            {"name": "Body Scan", "steps": ["Lie down", "Close eyes", "Scan head to toe", "Release tension on each exhale"], "duration": "10 min"},
            {"name": "Mindful Minute", "steps": ["Set 60s timer", "Focus only on breath", "Label thoughts 'thinking' and return"], "duration": "1 min"},
        ],
        "cbt": [
            {"name": "Thought Record", "steps": ["Write the upsetting thought", "Evidence for it", "Evidence against it", "Write a balanced thought"], "duration": "10 min"},
            {"name": "Worry Time", "steps": ["Schedule 15min worry slot", "Postpone worries until then", "Review list during slot", "Write one small action"], "duration": "15 min"},
        ],
    }

# ─── Analytics ────────────────────────────────────────────────────────────────

@app.get("/analytics/dashboard")
def analytics_dashboard(user_id: str = Query("default")):
    """Fast endpoint — scores + trends only, NO LLM call. Always returns immediately."""
    _require_db()
    from datetime import datetime, timedelta
    mood_logs     = _db.get_mood_history(user_id, 30)
    sleep_logs    = _db.get_sleep_history(user_id, 30)
    exercise_logs = _db.get_exercise_history(user_id, 30)

    # Always compute scores inline (no LLM, instant)
    mood_avg   = round(sum(m.get("mood_score", 5) for m in mood_logs[:30]) / max(len(mood_logs[:30]), 1), 1) if mood_logs else 5.0
    stress_avg = round(sum(m.get("stress_score", 5) for m in mood_logs[:30]) / max(len(mood_logs[:30]), 1), 1) if mood_logs else 5.0
    sleep_dur  = round(sum(s.get("duration_hours", 7) for s in sleep_logs[:14]) / max(len(sleep_logs[:14]), 1), 1) if sleep_logs else 7.0
    sleep_sc   = round(min(sleep_dur / 8.0 * 10, 10), 1)
    ex_days    = len(set(e.get("logged_at", "")[:10] for e in exercise_logs[:14]))
    act_sc     = round(min(ex_days / 7.0 * 10, 10), 1)
    scores = {
        "wellness_score": round(mood_avg * 0.3 + sleep_sc * 0.25 + (10 - stress_avg) * 0.25 + act_sc * 0.2, 1),
        "mood_score": mood_avg, "sleep_score": sleep_sc,
        "stress_score": stress_avg, "activity_score": act_sc,
    }
    dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
    mood_by_date: dict = {}
    for m in mood_logs:
        d = m.get("logged_at", "")[:10]
        if d: mood_by_date.setdefault(d, []).append(m.get("mood_score", 5))
    sleep_by_date = {s.get("date", "")[:10]: s.get("duration_hours", 0) for s in sleep_logs}
    trends = {
        "dates": dates,
        "mood_series":  [round(sum(mood_by_date.get(d, [5])) / max(len(mood_by_date.get(d, [5])), 1), 1) for d in dates],
        "sleep_series": [sleep_by_date.get(d, None) for d in dates],
    }
    # Always use inline insight — fast, no LLM blocking the dashboard
    insight = _inline_insight(scores)
    return {"scores": scores, "trends": trends, "ai_insight": insight}


def _inline_insight(scores: dict) -> str:
    """Rule-based insight — instant, no LLM."""
    w = scores.get("wellness_score", 5)
    m = scores.get("mood_score", 5)
    sl = scores.get("sleep_score", 5)
    st = scores.get("stress_score", 5)
    ac = scores.get("activity_score", 5)
    best = max({"Mood": m, "Sleep": sl, "Activity": ac}, key={"Mood": m, "Sleep": sl, "Activity": ac}.get)
    worst = min({"Mood": m, "Sleep": sl, "Stress management": 10 - st, "Activity": ac},
                key={"Mood": m, "Sleep": sl, "Stress management": 10 - st, "Activity": ac}.get)
    tips = {
        "Mood": "Try a 10-minute walk or write 3 things you're grateful for today.",
        "Sleep": "Aim for a consistent bedtime — even 30 minutes earlier makes a difference.",
        "Stress management": "Practice the 4-4-6 breathing technique: inhale 4s, hold 4s, exhale 6s.",
        "Activity": "Even a 5-minute stretch break between study sessions boosts energy.",
    }
    return (f"Your strongest area is **{best}** — keep it up! "
            f"The area most needing attention right now is **{worst}**. "
            f"{tips.get(worst, 'Keep logging daily for more personalised insights.')}")


@app.get("/analytics/insight")
def analytics_insight(user_id: str = Query("default")):
    """Separate slow endpoint for LLM-powered insight — called asynchronously by the frontend."""
    _require_ml()
    _require_db()
    mood_logs     = _db.get_mood_history(user_id, 30)
    sleep_logs    = _db.get_sleep_history(user_id, 30)
    exercise_logs = _db.get_exercise_history(user_id, 30)
    if _ready["ml"]:
        scores = _anal_a.compute_wellness_scores(mood_logs, sleep_logs, exercise_logs)
        return {"insight": _anal_a.generate_ai_insight(scores, mood_logs, sleep_logs)}
    return {"insight": "Log mood and sleep data to unlock personalised AI insights."}

# ─── Background model loader ──────────────────────────────────────────────────

def _load_models_background():
    """Load heavy ML modules in a background thread. DB is already loaded."""
    global _orch, _emotion, _sleep_a, _nutr_a, _ex_a, _jour_a, _coach_a, _anal_a
    global _loading_error

    try:
        print("⏳ Loading AI models (first run may take 1-2 min to download)...")
        import orchestrator as orch_mod
        import emotion_detector as em_mod
        from agents import sleep_agent, nutrition_agent, exercise_agent
        from agents import journal_agent, daily_coach_agent, analytics_agent

        _orch    = orch_mod
        _emotion = em_mod
        _sleep_a = sleep_agent
        _nutr_a  = nutrition_agent
        _ex_a    = exercise_agent
        _jour_a  = journal_agent
        _coach_a = daily_coach_agent
        _anal_a  = analytics_agent

        _ready["ml"] = True
        print("✅ All AI models ready — full platform is live!")

    except Exception as e:
        _loading_error = str(e)
        print(f"❌ Error loading AI models: {e}")
        import traceback; traceback.print_exc()


@app.on_event("startup")
async def startup_event():
    print("✅ Database ready (loaded at startup)")
    t = threading.Thread(target=_load_models_background, daemon=True)
    t.start()
    print("🚀 MindMate AI server started. Frontend available immediately.")
    print("⏳ AI models loading in background — /health shows progress.")


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # PORT is injected by Render (and other PaaS hosts).
    # API_PORT is the local/config override. config.py already resolves both,
    # so API_PORT here is already the correct value.
    uvicorn.run("api_server:app", host=API_HOST, port=API_PORT, reload=False)
