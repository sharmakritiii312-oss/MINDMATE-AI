"""
MindMate AI — Central Configuration
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# ─── LLM ──────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "phi3:mini")       # phi3:mini (fast) | llama3 | mistral | gemma | qwen2

# ─── Emotion Model ────────────────────────────────────────────────────────────
EMOTION_MODEL_ID: str = os.getenv(
    "EMOTION_MODEL_ID",
    "j-hartmann/emotion-english-distilroberta-base",  # 7-class Ekman model on HF
)
SENTIMENT_MODEL_ID: str = os.getenv(
    "SENTIMENT_MODEL_ID",
    "cardiffnlp/twitter-roberta-base-sentiment-latest",
)

# ─── Embeddings & Vector Store ─────────────────────────────────────────────────
EMBEDDING_MODEL_ID: str = os.getenv(
    "EMBEDDING_MODEL_ID",
    "sentence-transformers/all-MiniLM-L6-v2",
)
CHROMA_PERSIST_DIR: str = str(BASE_DIR / "data" / "chroma_store")

# ─── Memory ────────────────────────────────────────────────────────────────────
MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "20"))

# ─── API ───────────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
# Render injects PORT; API_PORT is the project-specific override; fallback to 8000.
API_PORT: int = int(os.getenv("PORT") or os.getenv("API_PORT") or "8000")

# ─── Safety ────────────────────────────────────────────────────────────────────
CRISIS_HOTLINES: dict[str, str] = {
    "Global": "https://www.befrienders.org",
    "US": "988 Suicide & Crisis Lifeline — call or text 988",
    "UK": "Samaritans — 116 123",
    "India": "iCall — 9152987821",
    "Australia": "Lifeline — 13 11 14",
    "Canada": "Crisis Services Canada — 1-833-456-4566",
}

# ─── Data directory ────────────────────────────────────────────────────────────
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

(BASE_DIR / "data" / "chroma_store").mkdir(parents=True, exist_ok=True)


class AppSettings(BaseModel):
    ollama_base_url: str = Field(default=OLLAMA_BASE_URL)
    ollama_model: str = Field(default=OLLAMA_MODEL)
    emotion_model_id: str = Field(default=EMOTION_MODEL_ID)
    sentiment_model_id: str = Field(default=SENTIMENT_MODEL_ID)
    embedding_model_id: str = Field(default=EMBEDDING_MODEL_ID)
    chroma_persist_dir: str = Field(default=CHROMA_PERSIST_DIR)
    max_history_turns: int = Field(default=MAX_HISTORY_TURNS)
    api_host: str = Field(default=API_HOST)
    api_port: int = Field(default=API_PORT)


settings = AppSettings()
