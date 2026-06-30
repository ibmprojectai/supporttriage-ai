"""Shared LLM factory — IBM Granite via watsonx.ai.

Provides two accessors:
  get_llm()   — returns a LangChain WatsonxLLM (for chain-based pipeline stages)
  get_model() — returns a native ibm-watsonx-ai ModelInference client (direct SDK calls)

Both return None when credentials are absent so every caller degrades to stub mode
without raising.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

_DEFAULT_MODEL_ID = "ibm/granite-3-8b-instruct"


def _credentials() -> tuple[str | None, str | None, str | None, str]:
    """Return (api_key, url, project_id, model_id) from environment."""
    return (
        os.getenv("WATSONX_API_KEY"),
        os.getenv("WATSONX_URL"),
        os.getenv("WATSONX_PROJECT_ID"),
        os.getenv("WATSONX_MODEL_ID", _DEFAULT_MODEL_ID),
    )


def get_llm():
    """Return a LangChain WatsonxLLM instance, or None if credentials are missing.

    Env vars:
      WATSONX_API_KEY      — IBM Cloud API key
      WATSONX_URL          — watsonx.ai endpoint (e.g. https://us-south.ml.cloud.ibm.com)
      WATSONX_PROJECT_ID   — watsonx.ai project GUID
      WATSONX_MODEL_ID     — model ID (default: ibm/granite-3-8b-instruct)
    """
    api_key, url, project_id, model_id = _credentials()
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
                "decoding_method": "greedy",
            },
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[watsonx_config] Failed to initialise WatsonxLLM: {exc}")
        return None


def get_model():
    """Return a native ibm-watsonx-ai ModelInference client, or None if credentials missing.

    Use this when you need direct SDK control (streaming, token counts, etc.)
    instead of going through the LangChain wrapper.
    """
    api_key, url, project_id, model_id = _credentials()
    if not all([api_key, url, project_id]):
        return None

    try:
        from ibm_watsonx_ai import APIClient, Credentials
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

        credentials = Credentials(url=url, api_key=api_key)
        client = APIClient(credentials)

        return ModelInference(
            model_id=model_id,
            api_client=client,
            project_id=project_id,
            params={
                GenParams.MAX_NEW_TOKENS: 512,
                GenParams.TEMPERATURE: 0.2,
                GenParams.DECODING_METHOD: "greedy",
            },
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[watsonx_config] Failed to initialise ModelInference: {exc}")
        return None
