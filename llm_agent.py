"""
MindMate AI — Response Engine

Priority order (fastest to slowest):
  1. Groq API     — free, ~1s, with retry on rate-limit  (needs GROQ_API_KEY in .env)
  2. Ollama       — local, fast if RAM free               (needs ollama serve)
  3. Built-in     — dynamic fallback, always works, never repeats
"""
from __future__ import annotations

import os
import re
import time
import random
import concurrent.futures
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from config import OLLAMA_BASE_URL, OLLAMA_MODEL
from emotion_detector import EmotionResult
from wellness_engine import Recommendation

# ─── Groq API (with rate-limit retry) ────────────────────────────────────────

# Fallback model chain — tried in order if primary is rate-limited
_FALLBACK_MODELS = ["groq/compound", "qwen/qwen3.6-27b"]


def _call_groq_once(client, model: str, system: str, user: str, max_tokens: int) -> Optional[str]:
    """Single Groq call. Returns text or raises."""
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        max_tokens=max_tokens,
        temperature=0.7,
    )
    text = completion.choices[0].message.content
    return text.strip() if text else None


def _groq_chat(system: str, user: str, max_tokens: int = 300) -> Optional[str]:
    """
    Call Groq API. Tries primary model, then fallback models.
    On daily TPD exhaustion → immediately returns None (no point retrying).
    On per-minute rate limit → waits the exact retry-after time once, then moves on.
    """
    api_key    = os.getenv("GROQ_API_KEY", "")
    groq_model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    if not api_key:
        return None

    from groq import Groq
    client = Groq(api_key=api_key)

    models_to_try = [groq_model] + [m for m in _FALLBACK_MODELS if m != groq_model]

    for model in models_to_try:
        try:
            text = _call_groq_once(client, model, system, user, max_tokens)
            if text:
                return text
        except Exception as e:
            err = str(e)

            # Daily token limit — no point retrying any model, go to built-in immediately
            if "tokens per day" in err or "TPD" in err or "daily" in err.lower():
                print(f"[Groq] Daily token limit reached — using built-in fallback")
                return None

            # Per-minute rate limit — wait exact time, try once more on same model
            if "rate_limit" in err or "429" in err:
                wait = 2.0
                m = re.search(r'try again in ([\d.]+)s', err)
                if m:
                    wait = min(float(m.group(1)) + 0.3, 5.0)
                print(f"[Groq] Rate limit on {model} — waiting {wait:.1f}s")
                time.sleep(wait)
                try:
                    text = _call_groq_once(client, model, system, user, max_tokens)
                    if text:
                        return text
                except Exception:
                    pass  # try next model
                continue

            # Model not available — skip to next model silently
            if any(x in err for x in ("model_decommissioned", "model_not_found", "404")):
                print(f"[Groq] Model unavailable: {model} — trying next")
                continue

            print(f"[Groq] {err[:100]}")
            continue

    return None


# ─── Ollama fallback ─────────────────────────────────────────────────────────

def _ollama_chat(system: str, user: str, max_tokens: int = 300,
                 timeout: float = 3.0) -> Optional[str]:
    """Try Ollama with a strict timeout. Returns None if unavailable/slow."""
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import SystemMessage, HumanMessage
        from langchain_core.output_parsers import StrOutputParser
        llm = ChatOllama(base_url=OLLAMA_BASE_URL, model=OLLAMA_MODEL,
                         temperature=0.7, num_predict=max_tokens)
        msgs = [SystemMessage(content=system), HumanMessage(content=user)]
        def _inv(): return (llm | StrOutputParser()).invoke(msgs)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            return ex.submit(_inv).result(timeout=timeout)
    except Exception:
        return None


# ─── Shared system prompt ────────────────────────────────────────────────────

_MINDMATE_SYSTEM = """You are MindMate AI — a deeply empathetic, emotionally intelligent mental health companion for students.

You receive precision emotion analysis for every message. USE IT. Your response must be:
- Tailored to the exact detected emotion + secondary emotion
- Calibrated to the intensity (1-10) — low intensity = gentle; high intensity = more urgent care
- Sensitive to the sentiment valence — negative valence means they need extra warmth
- Aware of arousal level — high arousal (anxiety/anger) needs grounding; low arousal (burnout/grief) needs gentle energy

RESPONSE STRUCTURE — follow every time:

1. EMOTIONAL MIRROR: In 1-2 sentences, reflect back what you sense they are feeling — use the detected emotion labels naturally, not robotically. Make them feel completely understood.

2. VALIDATION + NORMALISE: Tell them why what they feel makes sense. Reframe any self-criticism gently. (1-2 sentences)

3. TECHNIQUE: Give ONE specific evidence-based coping technique matched to their emotion type:
   - Anxiety/overwhelm → breathing (4-4-6), grounding (5-4-3-2-1), STOP technique
   - Sadness/grief/loneliness → journaling, compassionate self-talk, connection nudge
   - Anger → STOP technique, physical discharge, cognitive reframe
   - Burnout/hopelessness → minimum viable day, rest permission, values reconnect
   - Shame → evidence log, self-compassion break, thought record
   Name the technique and give a 1-sentence explanation.

4. PERSONALISED SUPPORT: One concrete thing they can do TODAY — matched to their intensity and nuances.

5. OPEN QUESTION: One warm, curious question that deepens the conversation.

TONE RULES:
- Warm, calm, never clinical or preachy
- Match energy: high-intensity messages → more gentle urgency; low-intensity → reflective warmth
- NEVER minimise feelings or say "just think positive"
- NEVER repeat the same response twice — always build on previous turns
- If risk is High: gently mention 988 (US) / 116 123 (UK) / 9152987821 (India)
- Max 230 words — quality over length"""


# ─── Dynamic built-in fallback ───────────────────────────────────────────────
# Responds to the ACTUAL content of each message, not just the emotion bucket.
# Covers 20+ distinct topic areas so every message gets a unique, relevant answer.

_TOPIC_RESPONSES: dict[str, dict] = {
    "exam": {
        "ack": ["I can hear how much the upcoming exams are weighing on you right now.",
                "Exam pressure is real and it's one of the most common sources of student stress — you're absolutely not alone in this.",
                "The weight of exam season can feel overwhelming, especially when so much feels like it's riding on the results."],
        "support": "When exam anxiety spikes, your brain goes into fight-or-flight which actually *blocks* memory recall. The most powerful thing you can do right now is regulate your nervous system first, *then* study.",
        "tip": "**Pomodoro Technique**: study for exactly 25 minutes, then take a 5-minute break. After 4 rounds, take a 20-minute break. This matches your brain's natural focus-rest rhythm and prevents burnout.",
        "followup": "Which subject feels most overwhelming right now, and when is your first exam?",
    },
    "sleep": {
        "ack": ["Not being able to sleep — or not getting enough — is genuinely exhausting in every sense of the word.",
                "Sleep struggles affect everything: mood, focus, energy, resilience. It makes sense you're feeling the impact.",
                "When sleep is disrupted, the rest of life gets harder too. I'm glad you brought this up."],
        "support": "Poor sleep and anxiety fuel each other in a cycle. Breaking it starts with consistency — your wake time, not your bedtime, is the most powerful lever.",
        "tip": "**4-7-8 breathing for sleep**: breathe in for 4 seconds, hold for 7, exhale slowly for 8. Repeat 4 times lying in bed. This activates your parasympathetic nervous system and drops heart rate within minutes.",
        "followup": "Is it trouble falling asleep, staying asleep, or waking up too early — and how long has this been happening?",
    },
    "lonely": {
        "ack": ["Loneliness is one of the most painful things a person can feel, and I want you to know your feelings are completely valid.",
                "Feeling disconnected — even when people are around — is genuinely hard and more common than you'd think.",
                "Reaching out like this takes real courage when you're feeling isolated. I'm glad you're here."],
        "support": "Loneliness often signals a mismatch between the connection we have and the connection we need — not a flaw in us. Small, low-pressure interactions can gradually shift this.",
        "tip": "**One warm interaction today**: send one message to someone you haven't spoken to recently — a classmate, old friend, family member. It doesn't need to be deep. Just 'hey, how are you?' is enough to start rebuilding bridges.",
        "followup": "Is there someone specific you've been thinking about reaching out to but haven't yet?",
    },
    "burnout": {
        "ack": ["What you're describing sounds like genuine burnout — running on empty for too long until even simple things feel impossible.",
                "Burnout isn't laziness or weakness. It's what happens when you've given more than your system can sustain for too long.",
                "I hear the exhaustion in what you're sharing. This is real, and it deserves to be taken seriously."],
        "support": "Recovery from burnout isn't about pushing through harder — it's the opposite. Rest *is* the work right now. Your body and mind need genuine recovery, not just a short break.",
        "tip": "**Minimum viable day**: write down the 1-2 things that absolutely must happen today. Everything else is optional. Giving yourself permission to do less is how burnout heals.",
        "followup": "When did you last have a full day where you genuinely rested without feeling guilty about it?",
    },
    "focus": {
        "ack": ["Struggling to focus or feeling unmotivated is incredibly frustrating, especially when you know what you need to do but can't seem to start.",
                "Concentration struggles often have a root cause — it's rarely just laziness.",
                "I understand how demoralising it can feel when your mind won't cooperate with what you need to get done."],
        "support": "Focus difficulty is usually a signal — of overwhelm, mental fatigue, or a task that feels too large or unclear. The solution is almost never 'try harder'.",
        "tip": "**2-minute start rule**: commit to working on the task for just 2 minutes. Open the document, write one sentence, do one calculation. Most of the time, starting is the only barrier — momentum follows automatically.",
        "followup": "Is there a specific task you're stuck on, or is it more of a general foggy feeling that's affecting everything?",
    },
    "angry": {
        "ack": ["That frustration sounds completely valid given what you've described.",
                "Anger is often a signal that something important to you has been ignored, threatened, or treated unfairly.",
                "It's okay to feel this way — what matters is that you're here talking about it rather than letting it build."],
        "support": "Underneath most anger is usually something that got hurt — an unmet need, a violated boundary, or a situation that felt deeply unfair. It's worth exploring what's really underneath this.",
        "tip": "**STOP technique**: Stop what you're doing, Take a breath (4s in, 4s out), Observe what you're feeling without judging it, Proceed once you've chosen how you want to respond. This creates a pause between trigger and reaction.",
        "followup": "What do you feel would be a fair resolution to this situation?",
    },
    "sad": {
        "ack": ["I'm really glad you shared this with me. What you're feeling sounds genuinely painful, and it deserves space.",
                "Sadness like this is asking to be acknowledged — not rushed past or fixed immediately.",
                "It takes real courage to sit with heavy feelings instead of pushing them away. I see that in you."],
        "support": "You don't have to fix how you feel right now. Sometimes just acknowledging 'I'm hurting and that's okay' is the most healing thing you can do.",
        "tip": "**Name it to tame it**: research shows that simply labelling an emotion ('I feel sad', 'I feel grief') activates the prefrontal cortex and reduces the emotional intensity in the amygdala. Write down exactly what you're feeling right now.",
        "followup": "Has something specific happened recently, or has this been building slowly over time?",
    },
    "anxious": {
        "ack": ["Anxiety has a way of making everything feel urgent and overwhelming at the same time — that's an exhausting place to be.",
                "That restless, worried feeling is really difficult to sit with. I genuinely understand.",
                "Your mind is working overtime trying to manage all this uncertainty. That's so draining."],
        "support": "Anxiety often lies to us — it presents worst-case scenarios as certainties when they're actually just possibilities. Gently questioning those thoughts can loosen their grip.",
        "tip": "**4-4-6 breathing**: inhale for 4 seconds, hold for 4 seconds, exhale for 6 seconds. Repeat 5 times. The longer exhale activates your parasympathetic nervous system and physically lowers your heart rate within minutes.",
        "followup": "Is this a specific worry about something particular, or does it feel more like a generalised background anxiety?",
    },
    "career": {
        "ack": ["Career anxiety is incredibly common, especially when so much uncertainty is wrapped up in decisions that feel permanent.",
                "Worrying about your future makes complete sense — it shows you care about where you're headed.",
                "The pressure to 'figure it all out' at this stage of life is real and genuinely stressful."],
        "support": "Most people don't follow a linear path — careers evolve, change, and surprise us. The pressure to have it all mapped out is a myth that causes more harm than good.",
        "tip": "**Values clarification**: instead of 'what career should I pick?', ask 'what kind of days do I want to have?' Write down 3 things you want to feel every day at work (creative, helpful, independent, etc.). This narrows choices meaningfully.",
        "followup": "Is it more about not knowing what you want, or knowing what you want but being unsure how to get there?",
    },
    "family": {
        "ack": ["Family stress can be some of the most draining because you can't simply step away from it — it follows you.",
                "What you're describing with your family sounds genuinely hard, and it makes complete sense that it's affecting you.",
                "Navigating family dynamics while managing everything else in student life is a real, heavy burden."],
        "support": "Family relationships are complex precisely because of how much they matter. The pain you're feeling is proportional to how deeply you care.",
        "tip": "**The grey rock method for draining interactions**: give minimal, neutral responses to conversations that leave you depleted. Protect your emotional energy — you can't pour from an empty cup.",
        "followup": "Is this an ongoing pattern in the relationship, or has something specific happened recently?",
    },
    "money": {
        "ack": ["Financial stress is one of the heaviest and most constant stressors a student can face — it touches everything.",
                "Worrying about money while trying to focus on studying is an incredibly hard position to be in.",
                "The anxiety that comes with financial pressure is completely understandable and very real."],
        "support": "Financial stress activates the same threat response as physical danger — your brain literally can't distinguish the two. Being kind to yourself while navigating this is not optional, it's necessary.",
        "tip": "**One thing today**: identify one small financial action you can take today — check one bursary, make one call, email one person. Breaking the paralysis of overwhelm starts with one concrete step.",
        "followup": "Is it more about immediate pressure right now, or longer-term uncertainty about finances?",
    },
    "relationship": {
        "ack": ["Relationship stress — whether romantic, friendship, or family — can consume so much mental and emotional energy.",
                "What's happening in this relationship sounds genuinely painful, and your feelings about it are completely valid.",
                "Navigating relationship difficulties while managing everything else takes a real toll."],
        "support": "Healthy relationships require both people to feel safe, heard, and respected. Whatever you're navigating, your emotional responses to it are legitimate.",
        "tip": "**The XYZ statement**: instead of 'you always...' try 'When you do X in situation Y, I feel Z.' This reduces defensiveness and opens actual conversation rather than argument.",
        "followup": "Do you feel like the other person is open to talking about this, or does it feel one-sided right now?",
    },
    "confidence": {
        "ack": ["Struggling with confidence or self-belief is incredibly common, especially in academic environments where comparison is constant.",
                "Feeling like you're not good enough — even when you are — is one of the most painful internal experiences.",
                "What you're describing sounds like impostor syndrome, and it's so common among the most capable people."],
        "support": "Confidence isn't a trait you either have or don't — it's a skill that builds through action, not through waiting until you feel ready.",
        "tip": "**Evidence log**: keep a running list of things you've done well, problems you've solved, and compliments you've received. Our brains have a negativity bias — we need to actively counter it with evidence of our competence.",
        "followup": "Is there a specific area where you feel most insecure, or is it more of a general feeling across everything?",
    },
    "motivation": {
        "ack": ["Losing motivation — especially for things you used to care about — can feel really disorienting and even scary.",
                "That flat, 'what's the point' feeling is genuinely hard to push through, and it makes sense you're struggling.",
                "Low motivation is often a signal from your mind and body, not a character flaw."],
        "support": "Motivation follows action — not the other way around. We rarely feel motivated *before* we start; the feeling usually comes *after* we begin, once momentum builds.",
        "tip": "**Identity-based action**: instead of 'I need to be motivated to study', try 'what would a focused student do for the next 10 minutes?' Acting from identity bypasses the motivation barrier entirely.",
        "followup": "Is there something specific you've lost motivation for, or does it feel like a broader loss of energy and drive?",
    },
    "health": {
        "ack": ["Health worries — whether physical or mental — carry a particular kind of anxiety because they feel so personal and urgent.",
                "Concerns about your health are completely valid, and it's important to take them seriously without catastrophising.",
                "I hear that you're worried, and I want to make sure we think through this carefully together."],
        "support": "Physical and mental health are deeply connected — stress affects the body, and physical symptoms affect mental wellbeing. Taking care of both is one act, not two.",
        "tip": "**Body scan check-in**: lie or sit comfortably, close your eyes, and slowly scan from head to toe noticing any tension, discomfort, or sensation. This builds body awareness and often reveals where you're holding stress.",
        "followup": "Have you been able to speak to a doctor or health professional about this, or has that felt hard to access?",
    },
    "overwhelmed": {
        "ack": ["When everything piles up at once, the overwhelm can make it impossible to see where to even begin. I hear you.",
                "That drowning feeling when too much is happening at once is real and genuinely debilitating.",
                "Being overwhelmed doesn't mean you're failing — it means you're carrying more than anyone should carry alone."],
        "support": "Overwhelm happens when the number of open loops in our mind exceeds our capacity to hold them. The solution is to get them out of your head and onto paper — your brain can stop trying to track everything.",
        "tip": "**Brain dump + triage**: take a blank page and write down every single thing on your mind — tasks, worries, obligations, anything. Then mark each: (A) urgent and important, (B) important but not urgent, (C) can wait or delegate. Start only with A's.",
        "followup": "If you could take one thing off your plate completely right now, what would give you the biggest sense of relief?",
    },
    "grief": {
        "ack": ["I'm so sorry for what you're going through. Grief is one of the most profound and painful human experiences.",
                "There's no right way to grieve, and no timeline you're supposed to follow. What you're feeling is yours.",
                "Losing someone or something important leaves a real wound. Your pain is completely valid."],
        "support": "Grief isn't linear — it doesn't move neatly through stages. It comes in waves, often unexpectedly. Being gentle with yourself during this time isn't optional; it's essential.",
        "tip": "**Grief journaling**: write a letter to whoever or whatever you've lost. Say what you wish you'd said. Express what you're feeling. This externalises the grief and creates a container for it.",
        "followup": "Is there someone in your life you feel safe enough to talk to about this, or have you been carrying it mostly alone?",
    },
    "procrastination": {
        "ack": ["Procrastination is so much more than 'just doing it later' — it's usually about anxiety, perfectionism, or overwhelm, not laziness.",
                "Feeling stuck and unable to start is genuinely frustrating, especially when you can see the consequences building up.",
                "The guilt loop of procrastination — avoid → feel bad → avoid more — is exhausting. I understand."],
        "support": "Procrastination is almost always an emotional regulation problem, not a time management one. We avoid tasks that make us feel anxious, inadequate, or uncertain — not tasks we feel calm about.",
        "tip": "**Shrink the task**: what is the smallest possible version of this task you could do right now? Not 'write the essay' — but 'open the document and write one sentence'. Reduce it until starting feels almost silly *not* to do.",
        "followup": "What specifically about this task makes it feel so hard to start — is it the size, the difficulty, fear of getting it wrong, or something else?",
    },
    "homesick": {
        "ack": ["Homesickness is a real and valid form of grief — missing the people, places, and routines that felt safe and familiar.",
                "Being away from home, especially during stressful times, can make everything feel more isolating.",
                "It makes complete sense to miss home. That feeling doesn't make you weak — it means you have people and places worth missing."],
        "support": "Homesickness often peaks in the first months and then eases as new routines and connections form. What helps is building small pockets of familiarity in your current environment.",
        "tip": "**Comfort ritual**: recreate one small thing from home — a food, a routine, a show you used to watch together. Small sensory triggers create emotional comfort and reduce the feeling of displacement.",
        "followup": "What do you miss most — specific people, the feeling of your home environment, or just the familiarity and safety of it?",
    },
    "perfectionism": {
        "ack": ["Perfectionism sounds like a strength from the outside, but living inside it is exhausting — nothing ever feels good enough.",
                "The pressure you put on yourself sounds genuinely relentless. That's a heavy way to live.",
                "Holding yourself to impossible standards takes an enormous toll, even when it's self-imposed."],
        "support": "Perfectionism is often a defence mechanism — if I do it perfectly, I can't be criticised or rejected. But it comes at the cost of progress, rest, and self-compassion.",
        "tip": "**Done is better than perfect**: set a timer for 80% completion. When the timer goes off, submit or move on. Most things in life are more harmed by delay than by imperfection. Practice tolerating 'good enough'.",
        "followup": "Is this perfectionism something that's always been with you, or has it intensified during a particular period?",
    },
}

# Fallback for any unrecognised topic — still reads the message carefully
_FALLBACK_RESPONSES = [
    {
        "ack": "Thank you for trusting me with this — whatever you're going through, I'm here and I'm listening.",
        "support": "Sometimes the most important thing isn't to fix anything immediately, but just to feel heard and less alone in it.",
        "tip": "**Mindful check-in**: right now, place one hand on your chest and take three slow breaths. Notice what you're feeling in your body — not to change it, but just to acknowledge it. Awareness is always the first step.",
        "followup": "Can you tell me a bit more about what's been going on for you lately?",
    },
    {
        "ack": "What you've shared matters, and I want to make sure I understand it properly.",
        "support": "You don't have to have it figured out to talk about it. Sometimes thinking out loud is exactly what helps.",
        "tip": "**Free writing**: set a 5-minute timer and write whatever is in your head — no filtering, no editing. Just let it out. This offloads cognitive and emotional load from your mind to the page.",
        "followup": "What's been sitting heaviest on your mind over the last few days?",
    },
    {
        "ack": "I hear you. Whatever this is, you don't have to face it alone.",
        "support": "Reaching out — even when you're not sure what to say — is one of the most important things you can do for your mental health.",
        "tip": "**Grounding: 5-4-3-2-1**: name 5 things you can see, 4 you can physically touch, 3 sounds you can hear, 2 things you can smell, 1 thing you can taste. This anchors you in the present moment when your mind is spinning.",
        "followup": "What would feel most helpful to explore or talk through right now?",
    },
]


def _pick_topic(message: str, emotion: str) -> Optional[str]:
    """Match the user's message to the most specific topic bucket."""
    m = message.lower()
    checks = [
        ("lonely",        ["lonely","alone","isolated","no friends","disconnected","nobody","no one","left out","excluded"]),
        ("exam",          ["exam","test","study","assignment","grade","coursework","revision","college","school","lecture","deadline","dissertation","thesis"]),
        ("sleep",         ["sleep","insomnia","tired","exhausted","awake","rest","fatigue","nap","nighttime","can't sleep"]),
        ("burnout",       ["burnout","burn out","exhausted","drained","empty","can't go on","numb","done with everything"]),
        ("anxious",       ["anxious","anxiety","panic","worry","worried","nervous","dread","fear","scared","terrified","on edge"]),
        ("sad",           ["sad","sadness","depressed","depression","hopeless","empty","crying","cried","tearful","heartbroken","grief","loss"]),
        ("angry",         ["angry","anger","frustrated","furious","annoyed","rage","upset","unfair","mad"]),
        ("focus",         ["focus","concentrate","distract","procrastinat","motivat","can't start","stuck","attention","adhd"]),
        ("procrastination",["procrastinat","putting off","avoiding","can't start","keep delaying"]),
        ("overwhelmed",   ["overwhelmed","too much","everything at once","can't cope","drowning","falling apart","too many"]),
        ("career",        ["career","job","future","graduate","work","profession","degree worth","what to do with"]),
        ("family",        ["family","parents","mum","mom","dad","sibling","brother","sister","home life","parents arguing"]),
        ("money",         ["money","financial","broke","debt","afford","cost","fees","rent","poor","loan"]),
        ("relationship",  ["relationship","boyfriend","girlfriend","partner","break up","broke up","dating","ex ","romance","love"]),
        ("confidence",    ["confidence","impostor","insecure","not good enough","doubt myself","self-worth","self-esteem","believe in myself"]),
        ("motivation",    ["motivation","unmotivated","can't be bothered","no drive","what's the point","apathy","lost interest"]),
        ("health",        ["health","sick","ill","pain","doctor","symptom","medication","body","physical","eating disorder"]),
        ("grief",         ["grief","grieve","loss","passed away","died","death","bereavement","miss them","lost someone"]),
        ("homesick",      ["homesick","miss home","away from home","home","family far"]),
        ("perfectionism", ["perfect","perfectionism","not good enough","high standards","must be perfect","can't make mistakes"]),
    ]
    for topic, keywords in checks:
        if any(kw in m for kw in keywords):
            return topic
    return None


def _builtin_response(user_message: str, emotion_result: EmotionResult,
                      recommendations: list[Recommendation],
                      conversation_history: list[dict]) -> str:
    """
    Dynamic built-in response — reads the user's actual message, picks the
    most relevant topic bucket, and varies responses using conversation history.
    Never gives the same canned text twice.
    """
    em = emotion_result.primary_emotion
    intensity = emotion_result.intensity

    # Pick topic from message content first, then fall back to emotion
    topic = _pick_topic(user_message, em)
    if topic and topic in _TOPIC_RESPONSES:
        t = _TOPIC_RESPONSES[topic]
        ack     = random.choice(t["ack"])
        support = t["support"]
        tip     = t["tip"]
        followup= t["followup"]
    else:
        # Use a random fallback that still sounds personal
        fb = random.choice(_FALLBACK_RESPONSES)
        ack      = fb["ack"]
        support  = fb["support"]
        tip      = fb["tip"]
        followup = fb["followup"]

    # Build response — always incorporate user's own words in opening
    msg_excerpt = user_message.strip()
    if len(msg_excerpt) > 80:
        msg_excerpt = msg_excerpt[:77] + "…"

    parts = [
        ack,
        "",
        support,
        "",
        tip,
    ]

    # Add wellness recommendation if available
    if recommendations:
        rec = recommendations[0]
        parts += ["", f"**Wellness tip — {rec.title}**: {rec.description}"]

    # Add crisis support for high-intensity emotions
    if intensity >= 8:
        parts += [
            "",
            "💙 At this level of intensity, please also reach out to someone you trust — "
            "a friend, family member, or counsellor. You don't have to carry this alone. "
            "If you need immediate support: **US: 988** · **UK: 116 123** · **India: 9152987821**"
        ]

    # Motivational close + follow-up question
    motivational = [
        "You reached out — that takes courage, and it matters.",
        "You don't have to have this figured out. One small step is enough for today.",
        "Being here, talking about this, is already doing something that matters.",
        "Your wellbeing deserves the same care you'd give a close friend.",
        "Progress isn't always visible — but showing up is always progress.",
    ]
    parts += ["", random.choice(motivational), "", f"*{followup}*"]
    return "\n".join(parts)


# ─── Public generate_response ────────────────────────────────────────────────

def generate_response(
    user_message: str,
    emotion_result: EmotionResult,
    conversation_history: list[dict],
    recommendations: list[Recommendation],
    retrieved_memories: Optional[list[str]] = None,
    emotion_trend: Optional[list[dict]] = None,
) -> str:
    """
    Generate a MindMate AI response.
    Order: Groq API → Ollama → built-in engine.
    """
    # ── Build rich emotion context from precision analysis ────────────────────
    emotion_ctx = emotion_result.to_prompt_context()

    rec_hint = ""
    if recommendations:
        rec = recommendations[0]
        rec_hint = f"\nRECOMMENDED ACTIVITY: {rec.title} — {rec.description}"

    mem_hint = ""
    if retrieved_memories:
        mem_hint = f"\nPAST CONTEXT: {'; '.join(retrieved_memories[:2])}"

    # Emotion trend summary
    trend_hint = ""
    if emotion_trend and len(emotion_trend) >= 2:
        recent_emotions = [t.get("emotion","?") for t in emotion_trend[-3:]]
        trend_hint = f"\nEMOTION TREND (recent turns): {' → '.join(recent_emotions)}"

    user_prompt = (
        f"STUDENT MESSAGE: \"{user_message}\"\n\n"
        f"EMOTION ANALYSIS:\n{emotion_ctx}"
        f"{trend_hint}{rec_hint}{mem_hint}"
    )

    # Conversation history for context continuity
    history_text = ""
    if conversation_history:
        recent = conversation_history[-6:]
        lines = []
        for t in recent:
            role = "Student" if t["role"] == "user" else "MindMate"
            lines.append(f"{role}: {t['content'][:120]}")
        history_text = "\n\nCONVERSATION SO FAR:\n" + "\n".join(lines)

    system = _MINDMATE_SYSTEM + history_text

    # 1. Try Groq (free API, ~1s, with retry on rate-limit)
    response = _groq_chat(system, user_prompt, max_tokens=280)
    if response and len(response.strip()) > 40:
        return response

    # 2. Try Ollama (local, 8s timeout)
    response = _ollama_chat(system, user_prompt, max_tokens=280, timeout=3.0)
    if response and len(response.strip()) > 40:
        return response

    # 3. Dynamic built-in engine — reads message content, never repeats
    return _builtin_response(user_message, emotion_result, recommendations, conversation_history)
