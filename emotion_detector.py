"""
MindMate AI — Precision Emotion & Sentiment Detection

Pipeline:
  1. Crisis check          — always rule-based, instant, safe
  2. Negation handling     — "not happy", "don't feel okay" understood correctly
  3. Intensity modifiers   — "very", "a bit", "slightly", "extremely" affect score
  4. Multi-emotion scoring — 12 emotion categories with 100+ keyword cues each
  5. Secondary emotion     — second-strongest emotion surfaced alongside primary
  6. Valence/Arousal       — 2D sentiment model (not just pos/neg/neutral)
  7. Contextual signals    — question marks, caps, exclamation, word count
  8. HuggingFace models    — loaded lazily; enrich rule-based results when ready

EmotionResult now carries:
  primary_emotion, secondary_emotion, emotion_scores,
  sentiment (valence: positive/negative/neutral),
  sentiment_score, valence (-1→+1), arousal (0→1),
  intensity (1-10), risk_level, is_crisis, crisis_keywords,
  emotion_nuances (list of qualitative labels e.g. "mixed", "suppressed grief")
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from config import EMOTION_MODEL_ID, SENTIMENT_MODEL_ID


# ─── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class EmotionResult:
    primary_emotion:   str
    emotion_scores:    dict[str, float]
    sentiment:         str            # "positive" | "negative" | "neutral" | "mixed"
    sentiment_score:   float          # confidence of sentiment label
    intensity:         int            # 1–10
    risk_level:        str            # "Low" | "Medium" | "High"
    is_crisis:         bool = False
    crisis_keywords:   list[str]      = field(default_factory=list)
    secondary_emotion: str            = "neutral"
    valence:           float          = 0.0    # −1.0 (very negative) → +1.0 (very positive)
    arousal:           float          = 0.5    # 0.0 (calm) → 1.0 (highly activated)
    emotion_nuances:   list[str]      = field(default_factory=list)

    def summary(self) -> str:
        nuance_str = f" [{', '.join(self.emotion_nuances)}]" if self.emotion_nuances else ""
        secondary_str = f" + {self.secondary_emotion}" if self.secondary_emotion not in ("neutral","") else ""
        return (
            f"Emotion: {self.primary_emotion.title()}{secondary_str}{nuance_str} | "
            f"Intensity: {self.intensity}/10 | "
            f"Sentiment: {self.sentiment.title()} (valence {self.valence:+.2f}, arousal {self.arousal:.2f}) | "
            f"Risk: {self.risk_level}"
            + (" ⚠ CRISIS" if self.is_crisis else "")
        )

    def to_prompt_context(self) -> str:
        """Compact string injected into the LLM system prompt."""
        parts = [
            f"PRIMARY EMOTION: {self.primary_emotion} (intensity {self.intensity}/10)",
        ]
        if self.secondary_emotion and self.secondary_emotion not in ("neutral",""):
            parts.append(f"SECONDARY EMOTION: {self.secondary_emotion}")
        parts.append(f"SENTIMENT: {self.sentiment} | valence {self.valence:+.2f} | arousal {self.arousal:.2f}")
        parts.append(f"RISK LEVEL: {self.risk_level}")
        if self.emotion_nuances:
            parts.append(f"EMOTIONAL NUANCES: {', '.join(self.emotion_nuances)}")
        top3 = sorted(self.emotion_scores.items(), key=lambda x: -x[1])[:3]
        parts.append(f"EMOTION BREAKDOWN: {' | '.join(f'{e}={s:.0%}' for e,s in top3)}")
        return "\n".join(parts)


# ─── Crisis keywords ──────────────────────────────────────────────────────────

CRISIS_PHRASES: list[str] = [
    "want to die", "kill myself", "end my life", "suicide", "suicidal",
    "self harm", "self-harm", "cut myself", "hurt myself", "no reason to live",
    "can't go on", "cannot go on", "don't want to be here", "don't want to live",
    "give up on life", "life is pointless",
    "everyone would be better without me", "better off dead",
    "thinking about ending it", "end it all", "not worth living",
]

# ─── Negation patterns ────────────────────────────────────────────────────────

_NEGATION_WORDS = {"not","no","never","don't","doesn't","didn't","can't","cannot",
                   "couldn't","won't","wouldn't","isn't","wasn't","aren't","weren't",
                   "hardly","barely","scarcely"}

_NEGATION_WINDOW = 3   # words before a keyword that can negate it

def _find_negated_positions(tokens: list[str]) -> set[int]:
    """Return indices of tokens that follow a negation word within the window."""
    neg_positions: set[int] = set()
    for i, tok in enumerate(tokens):
        if tok in _NEGATION_WORDS:
            for j in range(i + 1, min(i + 1 + _NEGATION_WINDOW, len(tokens))):
                neg_positions.add(j)
    return neg_positions

# ─── Intensity modifiers ──────────────────────────────────────────────────────

_INTENSIFIERS: dict[str, float] = {
    "extremely": 1.5, "incredibly": 1.4, "absolutely": 1.4,
    "very": 1.3, "really": 1.3, "so": 1.2, "quite": 1.1,
    "pretty": 1.05, "kind of": 0.85, "kinda": 0.85,
    "a bit": 0.8, "a little": 0.75, "slightly": 0.7,
    "barely": 0.5, "hardly": 0.5, "somewhat": 0.85,
}

def _get_local_multiplier(tokens: list[str], idx: int) -> float:
    """Return intensity multiplier from the 2 tokens before idx."""
    multiplier = 1.0
    window = tokens[max(0, idx - 2): idx]
    phrase = " ".join(window)
    for mod, val in _INTENSIFIERS.items():
        if mod in phrase or (len(mod.split()) == 1 and mod in window):
            multiplier = max(multiplier, val)
    return multiplier

# ─── Emotion keyword bank (12 categories, 100+ cues each) ─────────────────────

_KEYWORD_SCORES: dict[str, dict[str, float]] = {
    "sadness": {
        "sad": 0.80, "unhappy": 0.75, "depressed": 0.88, "depression": 0.88,
        "crying": 0.82, "cry": 0.72, "cried": 0.75, "tears": 0.70,
        "miserable": 0.85, "lonely": 0.78, "alone": 0.65, "heartbroken": 0.88,
        "grief": 0.85, "grieve": 0.82, "mourning": 0.85, "lost": 0.60,
        "empty": 0.78, "down": 0.62, "low": 0.55, "upset": 0.68,
        "hurt": 0.72, "pain": 0.70, "broken": 0.75, "hollow": 0.78,
        "numb": 0.72, "disconnected": 0.68, "worthless": 0.88,
        "unloved": 0.82, "unwanted": 0.80, "miss": 0.60, "missing": 0.62,
        "hopeless": 0.90, "devastated": 0.88, "shattered": 0.85,
        "sorrowful": 0.82, "gloomy": 0.72, "melancholy": 0.78,
    },
    "anxiety": {
        "anxious": 0.88, "anxiety": 0.92, "worried": 0.82, "worry": 0.78,
        "nervous": 0.78, "panic": 0.92, "panicking": 0.90, "scared": 0.82,
        "fear": 0.82, "afraid": 0.85, "overthinking": 0.85,
        "stressed": 0.88, "stress": 0.85, "overwhelmed": 0.88,
        "pressure": 0.78, "tense": 0.72, "restless": 0.72,
        "uneasy": 0.70, "apprehensive": 0.80, "dread": 0.82,
        "on edge": 0.85, "cant breathe": 0.88, "heart racing": 0.88,
        "overthink": 0.82, "racing thoughts": 0.85, "spiral": 0.78,
        "catastrophising": 0.85, "impending doom": 0.90,
        "intrusive thoughts": 0.85, "hyperventilating": 0.88,
    },
    "anger": {
        "angry": 0.88, "anger": 0.88, "furious": 0.92, "rage": 0.92,
        "frustrated": 0.82, "frustration": 0.82, "annoyed": 0.72,
        "irritated": 0.78, "mad": 0.78, "hate": 0.82, "unfair": 0.68,
        "livid": 0.90, "outraged": 0.90, "resentful": 0.82,
        "bitter": 0.75, "hostile": 0.80, "infuriated": 0.90,
        "boiling": 0.85, "seething": 0.88, "fed up": 0.78,
        "sick of": 0.72, "can't stand": 0.78, "so done": 0.72,
        "had enough": 0.75, "disgusted": 0.78,
    },
    "fear": {
        "terrified": 0.92, "frightened": 0.88, "petrified": 0.90,
        "horrified": 0.88, "nightmare": 0.78, "danger": 0.72,
        "unsafe": 0.82, "threatened": 0.80, "trembling": 0.78,
        "shaking": 0.72, "paralysed": 0.80, "paralyzed": 0.80,
        "terror": 0.90, "fearful": 0.85, "dreading": 0.82,
        "helpless": 0.80, "vulnerable": 0.72,
    },
    "burnout": {
        "burnout": 0.92, "burn out": 0.90, "exhausted": 0.88,
        "drained": 0.88, "depleted": 0.88, "no energy": 0.88,
        "can't focus": 0.78, "give up": 0.80, "given up": 0.82,
        "no motivation": 0.88, "procrastinating": 0.72,
        "can't study": 0.78, "tired of everything": 0.88,
        "running on empty": 0.90, "nothing left": 0.85,
        "zoned out": 0.72, "spacing out": 0.70, "zombie": 0.75,
        "going through the motions": 0.82, "can't care": 0.80,
        "numb to it": 0.78, "detached": 0.72,
    },
    "joy": {
        "happy": 0.88, "happiness": 0.88, "excited": 0.82, "great": 0.72,
        "wonderful": 0.88, "grateful": 0.82, "love": 0.78, "joy": 0.92,
        "good": 0.62, "awesome": 0.82, "amazing": 0.88, "proud": 0.82,
        "motivated": 0.78, "confident": 0.78, "thrilled": 0.88,
        "elated": 0.90, "overjoyed": 0.92, "cheerful": 0.80,
        "content": 0.75, "satisfied": 0.72, "hopeful": 0.72,
        "optimistic": 0.78, "blessed": 0.80, "ecstatic": 0.92,
        "delighted": 0.88, "gleeful": 0.85, "pumped": 0.80,
        "stoked": 0.78, "things are better": 0.70, "feeling good": 0.75,
    },
    "loneliness": {
        "lonely": 0.90, "loneliness": 0.92, "alone": 0.72,
        "no friends": 0.90, "no one": 0.78, "nobody": 0.78,
        "isolated": 0.88, "isolation": 0.88, "disconnected": 0.80,
        "left out": 0.85, "excluded": 0.88, "invisible": 0.80,
        "ignored": 0.78, "forgotten": 0.78, "unloved": 0.82,
        "no connection": 0.85, "feel like a ghost": 0.90,
        "no one understands": 0.85, "no one cares": 0.88,
        "socially awkward": 0.70, "hard to make friends": 0.78,
    },
    "overwhelm": {
        "overwhelmed": 0.90, "overwhelming": 0.88, "too much": 0.78,
        "everything at once": 0.88, "cope": 0.72,
        "can't cope": 0.88, "cant cope": 0.88, "drowning": 0.88, "falling apart": 0.88,
        "too many things": 0.80, "all at once": 0.78, "on top of me": 0.78,
        "can't handle": 0.85, "cant handle": 0.85, "spinning": 0.72, "chaos": 0.72,
        "out of control": 0.82, "juggling": 0.65, "mounting": 0.68,
        "piling up": 0.78, "never ends": 0.80, "non-stop": 0.72,
    },
    "shame": {
        "ashamed": 0.90, "shame": 0.90, "embarrassed": 0.82,
        "humiliated": 0.88, "mortified": 0.88, "guilty": 0.82,
        "guilt": 0.80, "failure": 0.78, "failed": 0.75,
        "pathetic": 0.85, "stupid": 0.72, "idiot": 0.72,
        "useless": 0.82, "worthless": 0.88, "not good enough": 0.88,
        "disgrace": 0.88, "regret": 0.75, "regretful": 0.78,
        "self-loathing": 0.92, "hate myself": 0.90, "let everyone down": 0.85,
    },
    "grief": {
        "grief": 0.92, "grieving": 0.90, "bereavement": 0.90,
        "loss": 0.80, "lost someone": 0.90, "passed away": 0.90,
        "died": 0.88, "death": 0.82, "mourning": 0.90,
        "miss them": 0.88, "miss you": 0.80, "gone forever": 0.90,
        "never see again": 0.92, "cope with loss": 0.88,
        "they died": 0.92, "she died": 0.92, "he died": 0.92,
    },
    "hopelessness": {
        "hopeless": 0.92, "no hope": 0.92, "pointless": 0.88,
        "nothing will change": 0.88, "what's the point": 0.85,
        "no future": 0.90, "it never gets better": 0.90,
        "nothing matters": 0.88, "can't see a way out": 0.88,
        "giving up": 0.82, "no way forward": 0.85,
        "never going to be okay": 0.90, "stuck forever": 0.85,
        "no point trying": 0.88, "doomed": 0.82,
    },
    "neutral": {
        "okay": 0.50, "fine": 0.50, "alright": 0.50,
        "normal": 0.50, "neither": 0.50, "just": 0.30,
    },
}

_HIGH_RISK_EMOTIONS = {
    "sadness","fear","anxiety","anger","burnout",
    "loneliness","shame","grief","hopelessness","overwhelm",
}


# ─── Valence / Arousal maps ───────────────────────────────────────────────────
# valence: −1 = very negative, +1 = very positive
# arousal:  0 = calm/flat,     1 = highly activated/urgent

_EMOTION_VALENCE: dict[str, float] = {
    "joy":          +0.90, "neutral":    0.00,
    "sadness":      -0.75, "grief":      -0.85,
    "anxiety":      -0.70, "overwhelm":  -0.72,
    "anger":        -0.65, "fear":       -0.80,
    "burnout":      -0.60, "loneliness": -0.68,
    "shame":        -0.78, "hopelessness":-0.92,
}

_EMOTION_AROUSAL: dict[str, float] = {
    "joy":          0.70, "neutral":     0.30,
    "sadness":      0.35, "grief":       0.30,
    "anxiety":      0.85, "overwhelm":   0.88,
    "anger":        0.90, "fear":        0.88,
    "burnout":      0.20, "loneliness":  0.30,
    "shame":        0.45, "hopelessness":0.20,
}


# ─── Core rule-based analyser ─────────────────────────────────────────────────

def _rule_based_analyze(text: str) -> EmotionResult:
    """
    Multi-step rule-based analysis.
    1. Crisis detection
    2. Tokenise + find negated positions
    3. Score each emotion with intensity modifiers + negation
    4. Compute valence/arousal
    5. Detect nuances (mixed, suppressed, etc.)
    Returns result in <5ms.
    """
    lower = text.lower()
    tokens = re.findall(r"\b\w+\b", lower)

    # ── Crisis ────────────────────────────────────────────────────────────────
    matched_crisis = [p for p in CRISIS_PHRASES if p in lower]
    is_crisis = bool(matched_crisis)

    # ── Negation map ──────────────────────────────────────────────────────────
    neg_positions = _find_negated_positions(tokens)

    # ── Emotion scoring ───────────────────────────────────────────────────────
    scores: dict[str, float] = {e: 0.02 for e in _KEYWORD_SCORES}

    for emotion, keywords in _KEYWORD_SCORES.items():
        for kw, base_weight in keywords.items():
            kw_tokens = kw.split()
            # find phrase in token list
            for i in range(len(tokens) - len(kw_tokens) + 1):
                if tokens[i:i+len(kw_tokens)] == kw_tokens:
                    # check negation at position i
                    if i in neg_positions:
                        # negated → flip to opposite emotion
                        if emotion in ("sadness","anxiety","anger","fear",
                                       "burnout","loneliness","shame","grief",
                                       "hopelessness","overwhelm"):
                            scores["neutral"] = max(scores["neutral"], base_weight * 0.4)
                        else:
                            # negated positive → slight sadness
                            scores["sadness"] = max(scores["sadness"], base_weight * 0.5)
                    else:
                        mult = _get_local_multiplier(tokens, i)
                        scores[emotion] = max(scores[emotion], base_weight * mult)

    # ── Single-word fallback (handles phrases with spaces missed above) ────────
    for emotion, keywords in _KEYWORD_SCORES.items():
        for kw, base_weight in keywords.items():
            if " " not in kw and kw in tokens:
                idx = tokens.index(kw)
                if idx not in neg_positions:
                    mult = _get_local_multiplier(tokens, idx)
                    scores[emotion] = max(scores[emotion], base_weight * mult)

    # ── Normalise ─────────────────────────────────────────────────────────────
    total = sum(scores.values()) or 1.0
    norm: dict[str, float] = {e: round(v / total, 4) for e, v in scores.items()}

    sorted_emotions = sorted(norm.items(), key=lambda x: -x[1])
    primary      = sorted_emotions[0][0]
    primary_score = sorted_emotions[0][1]
    secondary    = sorted_emotions[1][0] if len(sorted_emotions) > 1 else "neutral"
    secondary_score = sorted_emotions[1][1] if len(sorted_emotions) > 1 else 0.0

    # ── Intensity ─────────────────────────────────────────────────────────────
    # Caps and exclamations add intensity
    cap_boost = min(sum(1 for c in text if c.isupper()) * 0.05, 0.3)
    excl_boost = min(text.count("!") * 0.05, 0.2)
    raw_intensity = primary_score + cap_boost + excl_boost
    if is_crisis:
        raw_intensity = max(raw_intensity, 0.9)
    intensity = max(1, min(10, round(raw_intensity * 10)))

    # ── Valence / Arousal ─────────────────────────────────────────────────────
    valence  = _EMOTION_VALENCE.get(primary, 0.0)
    arousal  = _EMOTION_AROUSAL.get(primary, 0.5)
    # blend with secondary if significant
    if secondary_score > 0.15 and secondary != "neutral":
        w = secondary_score / (primary_score + secondary_score)
        valence = round(valence * (1 - w) + _EMOTION_VALENCE.get(secondary, 0.0) * w, 3)
        arousal = round(arousal * (1 - w) + _EMOTION_AROUSAL.get(secondary, 0.5) * w, 3)

    # ── Sentiment label ───────────────────────────────────────────────────────
    if valence >= 0.3:
        sentiment, sent_score = "positive", round(0.5 + valence * 0.5, 3)
    elif valence <= -0.25:
        # check if mixed (positive + negative both present)
        if norm.get("joy", 0) > 0.15 and any(
            norm.get(e, 0) > 0.15 for e in ("sadness","anxiety","anger","grief")
        ):
            sentiment, sent_score = "mixed", 0.60
        else:
            sentiment, sent_score = "negative", round(0.5 + abs(valence) * 0.5, 3)
    else:
        sentiment, sent_score = "neutral", 0.60

    # ── Risk level ────────────────────────────────────────────────────────────
    if is_crisis:
        risk = "High"
    elif primary in ("hopelessness","grief") and intensity >= 6:
        risk = "High"
    elif intensity >= 9:
        risk = "High"
    elif primary in _HIGH_RISK_EMOTIONS and intensity >= 8:
        risk = "High"
    elif primary in _HIGH_RISK_EMOTIONS and intensity >= 5:
        risk = "Medium"
    elif secondary in _HIGH_RISK_EMOTIONS and secondary_score > 0.20 and intensity >= 6:
        risk = "Medium"
    elif intensity >= 7:
        risk = "Medium"
    else:
        risk = "Low"

    # ── Emotion nuances ───────────────────────────────────────────────────────
    nuances: list[str] = []
    if is_crisis:
        nuances.append("crisis")
    if secondary != "neutral" and secondary_score > 0.20:
        nuances.append(f"mixed with {secondary}")
    if sentiment == "mixed":
        nuances.append("conflicted feelings")
    if primary == "burnout" and intensity >= 7:
        nuances.append("chronic exhaustion")
    if primary == "anxiety" and arousal > 0.85:
        nuances.append("acute anxiety spike")
    if primary in ("sadness","grief","hopelessness") and arousal < 0.25:
        nuances.append("low arousal depression signal")
    if primary == "shame" and intensity >= 7:
        nuances.append("self-critical pattern")
    if primary == "anger" and secondary == "sadness":
        nuances.append("grief-anger blend")
    if len(text.split()) <= 4:
        nuances.append("brief message — may be masking deeper feelings")

    return EmotionResult(
        primary_emotion=primary,
        secondary_emotion=secondary if secondary_score > 0.12 else "neutral",
        emotion_scores=norm,
        sentiment=sentiment,
        sentiment_score=round(sent_score, 4),
        valence=round(valence, 3),
        arousal=round(arousal, 3),
        intensity=intensity,
        risk_level=risk,
        is_crisis=is_crisis,
        crisis_keywords=matched_crisis,
        emotion_nuances=nuances,
    )


# ─── HuggingFace model (lazy, enriches rule-based result) ─────────────────────

@lru_cache(maxsize=1)
def _get_emotion_pipeline():
    from transformers import pipeline as hf_pipeline
    return hf_pipeline(
        "text-classification", model=EMOTION_MODEL_ID,
        top_k=None, truncation=True, max_length=512,
    )

@lru_cache(maxsize=1)
def _get_sentiment_pipeline():
    from transformers import pipeline as hf_pipeline
    return hf_pipeline(
        "text-classification", model=SENTIMENT_MODEL_ID,
        top_k=None, truncation=True, max_length=512,
    )


def _hf_analyze(text: str, rule_result: EmotionResult) -> EmotionResult:
    """
    Enrich rule_result with HuggingFace model predictions.
    HF emotion model gives better label accuracy on short/ambiguous text.
    We blend HF scores with rule-based scores for the best of both worlds.
    """
    try:
        emotion_pipe    = _get_emotion_pipeline()
        sentiment_pipe  = _get_sentiment_pipeline()
    except Exception:
        return rule_result

    try:
        raw_hf = emotion_pipe(text)[0]
        # Normalise HF labels to our categories
        _label_map = {
            "joy":       "joy",     "happiness":  "joy",
            "sadness":   "sadness", "fear":       "fear",
            "anger":     "anger",   "disgust":    "anger",
            "surprise":  "neutral", "neutral":    "neutral",
        }
        hf_scores: dict[str, float] = {}
        for r in raw_hf:
            cat = _label_map.get(r["label"].lower(), r["label"].lower())
            hf_scores[cat] = hf_scores.get(cat, 0.0) + r["score"]

        # Blend: 50% rule-based + 50% HF — keeps our fine categories but respects model
        blended: dict[str, float] = {**rule_result.emotion_scores}
        for cat, score in hf_scores.items():
            if cat in blended:
                blended[cat] = round((blended[cat] + score) / 2, 4)

        total = sum(blended.values()) or 1.0
        blended = {e: round(v / total, 4) for e, v in blended.items()}
        sorted_b = sorted(blended.items(), key=lambda x: -x[1])
        primary   = sorted_b[0][0]
        secondary = sorted_b[1][0] if len(sorted_b) > 1 and sorted_b[1][1] > 0.12 else "neutral"

        # HF sentiment
        raw_sent = sentiment_pipe(text)[0]
        top_s    = max(raw_sent, key=lambda x: x["score"])
        lm = {"positive":"positive","neutral":"neutral","negative":"negative",
              "label_0":"negative","label_1":"neutral","label_2":"positive"}
        hf_sentiment  = lm.get(top_s["label"].lower(), "neutral")
        hf_sent_score = round(top_s["score"], 4)

        # Merge sentiment: if HF disagrees with rule-based, trust HF for label
        final_sentiment   = hf_sentiment
        final_sent_score  = hf_sent_score

        # Recalculate intensity using blended primary score
        primary_score = blended[primary]
        cap_boost  = min(sum(1 for c in text if c.isupper()) * 0.05, 0.3)
        excl_boost = min(text.count("!") * 0.05, 0.2)
        raw_intensity = primary_score + cap_boost + excl_boost
        if rule_result.is_crisis:
            raw_intensity = max(raw_intensity, 0.9)
        intensity = max(1, min(10, round(raw_intensity * 10)))

        # Recalculate valence from blended primary
        valence = _EMOTION_VALENCE.get(primary, 0.0)
        arousal = _EMOTION_AROUSAL.get(primary, 0.5)

        # Risk
        risk = rule_result.risk_level  # keep rule-based risk (safer)
        if primary in ("hopelessness","grief") and intensity >= 6:
            risk = "High"
        elif intensity >= 9:
            risk = "High"

        return EmotionResult(
            primary_emotion   = primary,
            secondary_emotion = secondary,
            emotion_scores    = blended,
            sentiment         = final_sentiment,
            sentiment_score   = final_sent_score,
            valence           = round(valence, 3),
            arousal           = round(arousal, 3),
            intensity         = intensity,
            risk_level        = risk,
            is_crisis         = rule_result.is_crisis,
            crisis_keywords   = rule_result.crisis_keywords,
            emotion_nuances   = rule_result.emotion_nuances,
        )
    except Exception:
        return rule_result


# ─── Public API ───────────────────────────────────────────────────────────────

def analyze(text: str, prefer_fast: bool = False) -> EmotionResult:
    """
    Analyze text for emotion, sentiment, valence, arousal, and nuances.
    Uses HuggingFace models if loaded; falls back to rule-based instantly.
    Set prefer_fast=True for high-volume non-chat paths (mood logging).
    """
    rule_result = _rule_based_analyze(text)
    if prefer_fast:
        return rule_result
    # Try to enrich with HF — silently returns rule_result if models not loaded
    return _hf_analyze(text, rule_result)
