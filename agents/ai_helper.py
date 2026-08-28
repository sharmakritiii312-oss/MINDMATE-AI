"""
MindMate AI — Shared AI helper used by all agents.
Priority: Groq API (with retry) → Ollama → returns None (caller uses built-in fallback).
"""
from __future__ import annotations
import os
import time
import concurrent.futures
from typing import Optional

from dotenv import load_dotenv
load_dotenv()


def ai_generate(system: str, prompt: str, max_tokens: int = 300,
                ollama_timeout: float = 3.0) -> Optional[str]:
    """
    Try Groq first, then Ollama. Returns None if both unavailable.
    Immediately bails on daily token limits — no wasted retries.
    """
    groq_api_key    = os.getenv("GROQ_API_KEY", "")
    groq_model      = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model    = os.getenv("OLLAMA_MODEL", "phi3:mini")

    # ── 1. Groq (free, fast, ~1s) ────────────────────────────────────────────
    _fallbacks = ["groq/compound", "qwen/qwen3.6-27b"]
    if groq_api_key:
        from groq import Groq
        client = Groq(api_key=groq_api_key)
        for model in [groq_model] + [m for m in _fallbacks if m != groq_model]:
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": system},
                              {"role": "user",   "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                text = resp.choices[0].message.content
                if text:
                    return text.strip()
            except Exception as e:
                err = str(e)
                if "tokens per day" in err or "TPD" in err:
                    print(f"[Groq] Daily limit reached — using built-in fallback")
                    break                  # skip all models, go to built-in
                if "rate_limit" in err or "429" in err:
                    wait = 2.0
                    import re as _re
                    m = _re.search(r'try again in ([\d.]+)s', err)
                    if m:
                        wait = min(float(m.group(1)) + 0.3, 5.0)
                    print(f"[Groq] Rate limit on {model} — waiting {wait:.1f}s")
                    time.sleep(wait)
                    try:
                        resp = client.chat.completions.create(
                            model=model,
                            messages=[{"role": "system", "content": system},
                                      {"role": "user",   "content": prompt}],
                            max_tokens=max_tokens, temperature=0.7,
                        )
                        text = resp.choices[0].message.content
                        if text: return text.strip()
                    except Exception:
                        pass
                elif any(x in err for x in ("model_decommissioned","model_not_found","404")):
                    continue               # try next model
                else:
                    print(f"[Groq] {err[:80]}")

    # ── 2. Ollama (local, only if fast enough) ───────────────────────────────
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import SystemMessage, HumanMessage
        from langchain_core.output_parsers import StrOutputParser
        llm = ChatOllama(base_url=ollama_base_url, model=ollama_model,
                         temperature=0.7, num_predict=max_tokens)
        msgs = [SystemMessage(content=system), HumanMessage(content=prompt)]
        def _inv(): return (llm | StrOutputParser()).invoke(msgs)
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            text = ex.submit(_inv).result(timeout=ollama_timeout)
            if text:
                return text.strip()
    except Exception:
        pass

    return None
