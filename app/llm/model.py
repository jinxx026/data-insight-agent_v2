from __future__ import annotations

import os
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 45


def load_llm_config() -> LLMConfig | None:
    """Load OpenAI-compatible chat API settings from environment variables."""
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if not api_key:
        return None

    return LLMConfig(
        api_key=api_key,
        base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").strip().rstrip("/"),
        model=os.getenv("LLM_MODEL", "deepseek-chat").strip(),
    )


def build_llm_config(
    api_key: str,
    base_url: str = "https://api.deepseek.com/v1",
    model: str = "deepseek-chat",
) -> LLMConfig | None:
    """Build runtime LLM config from UI inputs."""
    api_key = api_key.strip()
    if not api_key:
        return None

    return LLMConfig(
        api_key=api_key,
        base_url=(base_url.strip() or "https://api.deepseek.com/v1").rstrip("/"),
        model=model.strip() or "deepseek-chat",
    )


def generate_chat_completion(config: LLMConfig, system_prompt: str, user_prompt: str) -> str:
    """Call an OpenAI-compatible /chat/completions endpoint."""
    response = requests.post(
        f"{config.base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        },
        timeout=config.timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["choices"][0]["message"]["content"].strip()
