#!/usr/bin/env python3
"""
CogNebula LLM Client — unified text generation via Poe API (OpenAI-compatible).

Drop-in replacement for direct Gemini API calls. All CogNebula scripts should
import from here instead of calling generativelanguage.googleapis.com directly.

Usage:
    from llm_client import llm_generate, llm_generate_json

    # Simple text generation
    answer = llm_generate("Summarize this tax law...", model="gemini-3.1-pro")

    # JSON-mode generation (returns parsed dict/list)
    data = llm_generate_json("Extract entities...", model="gemini-3.1-flash-lite")

Embedding calls stay on Google API (cheap, Poe doesn't support embeddings).
"""

import os
import json
import time
import urllib.request
import urllib.error
from typing import Optional, Union

# ── Config ───────────────────────────────────────────────────────────
POE_BASE_URL = "https://api.poe.com/v1/chat/completions"
POE_API_KEY = os.environ.get("POE_API_KEY", "")

# Model mapping: short names → Poe bot names
MODEL_MAP = {
    # Gemini family
    "gemini-3.1-pro": "gemini-3.1-pro",
    "gemini-3.1-flash-lite": "gemini-3.1-flash-lite",
    # Aliases for old script references
    "gemini-2.5-flash-lite": "gemini-3.1-flash-lite",  # upgrade path
    "gemini-2.5-pro": "gemini-3.1-pro",                # upgrade path
    "gemini-2.5-flash": "gemini-3.1-flash-lite",       # upgrade path
    "gemini-3-flash-preview": "gemini-3.1-flash-lite",  # upgrade path
    "gemini-3-pro-preview": "gemini-3.1-pro",           # upgrade path
    # Claude family (available on Poe)
    "claude-opus": "Claude-Opus-4.6",
    "claude-sonnet": "Claude-Sonnet-4.6",
    # GPT family
    "gpt-5.4-pro": "gpt-5.4-pro",
    "gpt-5.4": "gpt-5.4",
}

DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_TEMPERATURE = 0.3
DEFAULT_MAX_TOKENS = 4096
MAX_RETRIES = 3
RETRY_DELAY_S = 2.0


def _resolve_model(model: str) -> str:
    """Resolve model alias to Poe bot name."""
    return MODEL_MAP.get(model, model)


def llm_generate(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    api_key: str = "",
) -> str:
    """Generate text via Poe API (OpenAI-compatible).

    Args:
        prompt: User message content.
        system: Optional system instruction.
        model: Model name (accepts old Gemini names, auto-mapped).
        temperature: Sampling temperature (0.0-1.0).
        max_tokens: Maximum output tokens.
        api_key: Override POE_API_KEY env var.

    Returns:
        Generated text string. On error, returns "[ERROR] ..." string.
    """
    key = api_key or POE_API_KEY
    if not key:
        return "[ERROR] POE_API_KEY not set"

    resolved_model = _resolve_model(model)

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = json.dumps({
        "model": resolved_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
    }

    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(POE_BASE_URL, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:300]
            if e.code == 429:
                # Rate limited — back off
                wait = RETRY_DELAY_S * (attempt + 1)
                time.sleep(wait)
                continue
            return f"[ERROR] Poe API HTTP {e.code}: {body}"
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_S)
                continue
            return f"[ERROR] Poe API failed after {MAX_RETRIES} retries: {str(e)[:200]}"

    return "[ERROR] Poe API max retries exceeded"


def llm_generate_json(
    prompt: str,
    system: str = "",
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    api_key: str = "",
) -> Union[dict, list, None]:
    """Generate and parse JSON response.

    Appends JSON instruction to prompt, strips markdown fences, parses result.
    Returns None on parse failure.
    """
    json_prompt = prompt.rstrip() + "\n\nRespond with valid JSON only. No markdown fences, no explanation."
    raw = llm_generate(json_prompt, system=system, model=model,
                       temperature=temperature, max_tokens=max_tokens, api_key=api_key)

    if raw.startswith("[ERROR]"):
        return None

    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last fence lines
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON in the response
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            s = text.find(start_char)
            e = text.rfind(end_char)
            if s != -1 and e != -1 and e > s:
                try:
                    return json.loads(text[s:e + 1])
                except json.JSONDecodeError:
                    continue
        return None


# ── Embedding (stays on Google API — cheap, Poe doesn't support) ────
def embed_text(
    text: str,
    api_key: str = "",
    model: str = "gemini-embedding-2-preview",
    dimensions: int = 768,
) -> Optional[list]:
    """Generate embedding via Google API (not Poe — embeddings are cheap).

    Args:
        text: Text to embed (truncated to 2048 chars).
        api_key: Google AI Studio API key (falls back to GEMINI_API_KEY env).
        model: Embedding model name.
        dimensions: Output vector dimensions.

    Returns:
        List of floats, or None on failure.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_AI_STUDIO_KEY", "")
    if not key:
        return None

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={key}"
    payload = json.dumps({
        "model": f"models/{model}",
        "content": {"parts": [{"text": text[:2048]}]},
        "taskType": "RETRIEVAL_QUERY",
        "outputDimensionality": dimensions,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())["embedding"]["values"]
    except Exception:
        return None


# ── Quick test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== CogNebula LLM Client Test ===")
    print(f"POE_API_KEY: {'SET' if POE_API_KEY else 'NOT SET'}")
    print(f"Default model: {DEFAULT_MODEL} → {_resolve_model(DEFAULT_MODEL)}")
    print()

    # Test generation
    result = llm_generate("What is VAT in China? Answer in one sentence.", model="gemini-3.1-flash-lite")
    print(f"Generation test: {result[:200]}")
    print()

    # Test JSON generation
    jresult = llm_generate_json('Return a JSON object with keys "tax_name" and "rate" for China standard VAT.')
    print(f"JSON test: {jresult}")
