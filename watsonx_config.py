"""Shared LLM factory — local IBM Granite via Ollama.

Provides:
  get_model() → _OllamaModel | None   (used by classify, summarize, draft)
  get_llm()   → OllamaLLM | None      (used by extract via LangChain chain)

Both return None when Ollama is unreachable — every pipeline stage degrades
gracefully to stub mode with no crash.

Setup:
  1. Install Ollama: https://ollama.com/download
  2. Pull the model: ollama pull granite3.1:8b
  3. Ollama runs automatically in the background on http://localhost:11434
  No API key, no account, no internet required after the initial pull.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

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


def get_model() -> _OllamaModel | None:
    """Return an Ollama Granite model client, or None if Ollama is not running.

    Reads from environment (or .env):
      OLLAMA_MODEL     — model name (default: granite3.1:8b)
      OLLAMA_BASE_URL  — Ollama base URL (default: http://localhost:11434)
    """
    model, base_url = _get_config()

    if not _ollama_reachable(base_url):
        print(
            f"[llm_config] Ollama not reachable at {base_url}. "
            "Running in stub mode. To enable live LLM:\n"
            "  1. Install Ollama: https://ollama.com/download\n"
            f"  2. Run: ollama pull {model}"
        )
        return None

    return _OllamaModel(model=model, base_url=base_url)


def get_llm():
    """LangChain-compatible accessor — returns an OllamaLLM or None.

    Used by pipeline/extract.py which uses a LangChain chain.
    """
    model, base_url = _get_config()

    if not _ollama_reachable(base_url):
        print(
            f"[llm_config] Ollama not reachable at {base_url}. "
            "Running in stub mode."
        )
        return None

    try:
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model=model, base_url=base_url, temperature=0.2, num_predict=512)
    except Exception as exc:
        print(f"[llm_config] Failed to initialise OllamaLLM: {exc}")
        return None
