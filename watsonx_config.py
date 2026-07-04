"""Shared LLM factory — IBM Granite via OpenRouter (cloud) or Ollama (local).

Backend selection (checked in order):
  1. OpenRouter — if OPENROUTER_API_KEY is set, uses ibm-granite/granite-4.1-8b
                  via the OpenRouter API. No local installation required.
  2. Ollama     — if OPENROUTER_API_KEY is absent, falls back to the local Ollama
                  server. Returns None (stub mode) if Ollama is unreachable.

Provides:
  get_model() → _OpenRouterModel | _OllamaModel | None
  get_llm()   → ChatOpenAI | OllamaLLM | None   (LangChain-compatible)
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
_OPENROUTER_MODEL = "ibm-granite/granite-4.1-8b"
_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

_DEFAULT_MODEL = "llama3.2:1b"
_DEFAULT_BASE_URL = "http://localhost:11434"


def _get_config() -> tuple[str, str]:
    model = os.getenv("OLLAMA_MODEL", _DEFAULT_MODEL)
    base_url = os.getenv("OLLAMA_BASE_URL", _DEFAULT_BASE_URL)
    return model, base_url


def _ollama_reachable(base_url: str) -> bool:
    """Return True if Ollama is running and reachable."""
    try:
        import urllib.request
        urllib.request.urlopen(f"{base_url}/api/tags", timeout=3)
        return True
    except Exception:
        return False


# ── OpenRouter backend ────────────────────────────────────────────────────────

class _OpenRouterModel:
    """Thin wrapper around the OpenRouter chat completions API.

    Exposes .generate_text(prompt) so pipeline modules work identically
    regardless of the backend (OpenRouter or Ollama).
    Uses only urllib.request — no extra dependencies.
    """

    def generate_text(self, prompt: str) -> str:
        """Send prompt to OpenRouter and return the generated text as a plain str."""
        import json
        import urllib.request

        payload = json.dumps({
            "model": _OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()

        req = urllib.request.Request(
            f"{_OPENROUTER_BASE_URL}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            # Always return a plain str — never a LangChain type
            result = data["choices"][0]["message"]["content"]
            return str(result).strip()


# ── Ollama backend ────────────────────────────────────────────────────────────

class _OllamaModel:
    """Thin wrapper around the Ollama HTTP API.

    Exposes .generate_text(prompt) so pipeline modules work identically
    regardless of the backend (watsonx, HuggingFace, or Ollama).
    """

    def __init__(self, model: str, base_url: str) -> None:
        self._model = model
        self._base_url = base_url

    def generate_text(self, prompt: str) -> str:
        """Send prompt to Ollama and return the generated text."""
        import json
        import urllib.request

        payload = json.dumps({
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 512},
        }).encode()

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data.get("response", "").strip()


# ── Public factory functions ──────────────────────────────────────────────────

def get_model() -> _OpenRouterModel | _OllamaModel | None:
    """Return a model client for the active backend, or None in stub mode.

    Priority:
      1. OpenRouter  — when OPENROUTER_API_KEY is set
      2. Ollama      — when local Ollama server is reachable
      3. None        — stub mode (both unavailable)
    """
    if OPENROUTER_API_KEY:
        print(f"[llm_config] Using OpenRouter backend ({_OPENROUTER_MODEL}).")
        return _OpenRouterModel()

    model, base_url = _get_config()
    if not _ollama_reachable(base_url):
        print(
            f"[llm_config] Ollama not reachable at {base_url}. "
            "Running in stub mode. To enable live LLM:\n"
            "  1. Install Ollama: https://ollama.com/download\n"
            f"  2. Run: ollama pull {model}\n"
            "  Or set OPENROUTER_API_KEY for cloud inference."
        )
        return None

    return _OllamaModel(model=model, base_url=base_url)


def get_llm():
    """Deprecated shim — returns the same backend as get_model().

    Previously returned a LangChain ChatOpenAI/OllamaLLM object, which caused
    AIMessage type errors on Streamlit Cloud (Python 3.14 + uvloop).
    Now delegates to get_model() so any old cached caller gets a safe backend.
    """
    return get_model()
