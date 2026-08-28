# 🧠 MindMate AI — Mental Health Companion for Students

An advanced, fully local AI-powered mental health companion that provides empathetic, evidence-based support for students experiencing stress, anxiety, burnout, academic pressure, loneliness, and other emotional challenges.

---

## Architecture

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│              Conversation Orchestrator                  │
│                                                         │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────┐  │
│  │ Emotion      │   │ Safety       │   │ Memory     │  │
│  │ Agent        │──▶│ Agent        │   │ Agent      │  │
│  │ (HF Models)  │   │ (Crisis)     │   │ (ChromaDB) │  │
│  └──────────────┘   └──────────────┘   └────────────┘  │
│          │                  │                  │        │
│          ▼                  │                  ▼        │
│  ┌──────────────┐           │         ┌────────────┐    │
│  │ Wellness     │           │         │ RAG        │    │
│  │ Engine       │           │         │ Retrieval  │    │
│  └──────────────┘           │         └────────────┘    │
│          │                  │                  │        │
│          └──────────────────┼──────────────────┘        │
│                             ▼                           │
│                    ┌──────────────┐                     │
│                    │  LLM Agent   │                     │
│                    │  (Ollama)    │                     │
│                    └──────────────┘                     │
└─────────────────────────────────────────────────────────┘
     │
     ▼
 Response + Emotion Badge
```

---

## Features

| Module | Capability |
|---|---|
| **Emotion Detector** | 7-class emotion (joy/sadness/anger/fear/disgust/surprise/neutral) + 3-class sentiment |
| **Safety Agent** | Rule-based crisis keyword matching + risk-level escalation + hotline display |
| **Memory Manager** | Sliding-window short-term memory + ChromaDB long-term semantic memory |
| **Wellness Engine** | 18 evidence-based recommendations across 8 categories, filtered by emotion/intensity/environment |
| **LLM Agent** | LangChain + Ollama (Llama 3, Mistral, Gemma, DeepSeek, Qwen) with structured 5-step response framework |
| **Orchestrator** | Multi-agent pipeline coordinating all modules per conversation turn |
| **CLI** | Rich terminal UI with emotion badges, markdown rendering, session persistence |
| **REST API** | FastAPI server with `/chat`, `/session/{id}`, `/health` endpoints |

---

## Quick Start

### 1. Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running locally

```bash
# Install Ollama and pull a model
ollama pull llama3
# or: ollama pull mistral | gemma | deepseek-r1 | qwen2
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env to set your preferred model and ports
```

### 4. Run CLI

```bash
python cli.py
```

**CLI options:**

```bash
python cli.py --model mistral             # Use a different LLM
python cli.py --session <id>              # Resume a session
python cli.py --no-physical               # Disable physical activity suggestions
python cli.py --low-mobility              # Only low-mobility-friendly activities
python cli.py --indoor                    # Only indoor activities
python cli.py --outdoor                   # Only outdoor activities
```

### 5. Run API Server

```bash
python api_server.py
# Server starts at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

**API Example:**

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I feel overwhelmed with all my assignments and I cannot sleep.",
    "include_physical": true,
    "environment": "indoor",
    "group_size": "solo"
  }'
```

---

## Project Structure

```
mindmate-ai/
├── config.py               # Central configuration & settings
├── emotion_detector.py     # HuggingFace emotion + sentiment analysis
├── memory_manager.py       # Short-term (sliding window) + long-term (ChromaDB) memory
├── wellness_engine.py      # 18+ evidence-based wellness recommendations
├── safety_agent.py         # Crisis detection & compassionate safety responses
├── llm_agent.py            # LangChain + Ollama LLM integration
├── orchestrator.py         # Multi-agent conversation pipeline
├── api_server.py           # FastAPI REST API
├── cli.py                  # Interactive Rich terminal UI
├── tests.py                # Unit test suite
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── data/
    └── chroma_store/       # Persistent vector memory (auto-created)
```

---

## Wellness Recommendation Categories

| Category | Examples |
|---|---|
| **Breathing** | 4-4-6 Calming Breath, Box Breathing, 5-5-5 Quick Reset |
| **Mindfulness** | 5-4-3-2-1 Grounding, Body Scan, Mindful Minute |
| **CBT** | Thought Record, Worry Time scheduling |
| **Academic** | Pomodoro Method, Brain Dump, Two-Minute Rule |
| **Journaling** | Gratitude journal, Unsent feelings letter |
| **Relaxation** | Progressive Muscle Relaxation, Cold Water Reset |
| **Physical Games** | Balloon Volleyball, Scavenger Hunt Walk, Frisbee, Desk Stretching, Indoor Bowling |
| **Motivational** | Values Compass, One Small Win |

Physical activities are always **optional**, filtered by environment/group size/mobility, and never suggested during a crisis.

---

## Supported LLMs (via Ollama)

| Model | Command |
|---|---|
| Llama 3 (default) | `ollama pull llama3` |
| Mistral | `ollama pull mistral` |
| Gemma | `ollama pull gemma` |
| DeepSeek R1 | `ollama pull deepseek-r1` |
| Qwen 2 | `ollama pull qwen2` |

---

## Running Tests

```bash
python -m pytest tests.py -v
# or
python tests.py
```

Tests mock all HuggingFace and Ollama calls — no GPU or internet required.

---

## Crisis Protocol

When crisis indicators are detected (suicidal ideation, self-harm, severe distress):

1. Physical game suggestions are immediately excluded
2. A compassionate, safety-focused response is returned
3. Country-specific crisis hotlines are displayed
4. The LLM is bypassed to prevent any unsafe generation

**Always encourage users to contact qualified mental health professionals.**

---

## Ethics & Limitations

- MindMate AI is a **supportive tool**, not a replacement for professional mental health care.
- All inference runs **locally** — no data is sent to external servers.
- The system never diagnoses, prescribes, or claims clinical authority.
- Physical activity suggestions respect mobility, energy levels, and health conditions.

---

## Supported Hotlines

| Region | Resource |
|---|---|
| Global | https://www.befrienders.org |
| US | 988 Suicide & Crisis Lifeline — call or text **988** |
| UK | Samaritans — **116 123** |
| India | iCall — **9152987821** |
| Australia | Lifeline — **13 11 14** |
| Canada | Crisis Services Canada — **1-833-456-4566** |
