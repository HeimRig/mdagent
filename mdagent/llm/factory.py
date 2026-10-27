"""按 config 里选的 provider 造后端。"""

import config
from .base import LLMBackend

_PRESETS = {
    "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
    "moonshot": ("https://api.moonshot.cn/v1", "moonshot-v1-8k"),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "ollama": ("http://localhost:11434/v1", "qwen25-3b"),
    "siliconflow": ("https://api.siliconflow.cn/v1", "Qwen/Qwen2.5-7B-Instruct"),
}


def build_backend(provider: str | None = None, **overrides) -> LLMBackend:
    provider = (provider or config.LLM_PROVIDER).lower()

    if provider == "offline":
        from .offline import OfflineBackend
        return OfflineBackend()

    if provider not in _PRESETS and not config.LLM_BASE_URL:
        raise ValueError(f"未知 provider: {provider}，且没有配置 LLM_BASE_URL")

    default_url, default_model = _PRESETS.get(provider, ("", ""))
    from .openai_compat import OpenAICompatBackend

    api_key = overrides.get("api_key") or config.LLM_API_KEY
    if not api_key and provider == "ollama":
        api_key = "ollama"

    model = overrides.get("model") or config.LLM_MODEL or default_model
    return OpenAICompatBackend(
        api_key=api_key,
        base_url=overrides.get("base_url") or config.LLM_BASE_URL or default_url,
        model=model,
        temperature=config.LLM_TEMPERATURE,
        max_tokens=config.LLM_MAX_TOKENS,
        timeout=config.LLM_TIMEOUT,
        name=f"{provider}/{model}",
    )
