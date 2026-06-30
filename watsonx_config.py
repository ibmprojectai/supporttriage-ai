"""Shared WatsonxLLM factory.

All pipeline modules call get_llm() instead of reading credentials themselves.
Returns None when credentials are absent so every caller can enter stub mode
gracefully without raising.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_MODEL_ID = "ibm/granite-3-3-8b-instruct"


def get_llm():
    """Return a configured WatsonxLLM instance, or None if credentials are missing.

    Reads from environment (or .env):
      WATSONX_API_KEY      — IBM Cloud API key
      WATSONX_URL          — watsonx.ai endpoint (e.g. https://us-south.ml.cloud.ibm.com)
      WATSONX_PROJECT_ID   — watsonx.ai project GUID
      WATSONX_MODEL_ID     — foundation model ID (default: ibm/granite-3-3-8b-instruct)
    """
    api_key = os.getenv("WATSONX_API_KEY")
    url = os.getenv("WATSONX_URL")
    project_id = os.getenv("WATSONX_PROJECT_ID")
    model_id = os.getenv("WATSONX_MODEL_ID", _DEFAULT_MODEL_ID)

    if not all([api_key, url, project_id]):
        return None

    try:
        from langchain_ibm import WatsonxLLM

        return WatsonxLLM(
            model_id=model_id,
            url=url,
            apikey=api_key,
            project_id=project_id,
            params={
                "max_new_tokens": 512,
                "temperature": 0.2,
            },
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[watsonx_config] Failed to initialise WatsonxLLM: {exc}")
        return None
