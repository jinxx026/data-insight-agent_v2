from __future__ import annotations


LLM_PROVIDER_PRESETS = {
    "DeepSeek": {
        "base_urls": ["https://api.deepseek.com/v1"],
        "models": ["deepseek-chat", "deepseek-reasoner"],
    },
    "OpenAI GPT": {
        "base_urls": ["https://api.openai.com/v1"],
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
    },
    "Google Gemini": {
        "base_urls": ["https://generativelanguage.googleapis.com/v1beta/openai"],
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    },
    "Kimi": {
        "base_urls": ["https://api.moonshot.ai/v1", "https://api.moonshot.cn/v1"],
        "models": ["kimi-k2.6", "kimi-k2.5", "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    },
}


CUSTOM_PROVIDER = "Custom"
