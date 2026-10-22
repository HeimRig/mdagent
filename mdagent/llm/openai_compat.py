"""OpenAI 兼容后端。DeepSeek / Moonshot / 通义 / Ollama / vLLM 都走这个。"""

from .base import LLMBackend, LLMReply


class OpenAICompatBackend(LLMBackend):
    def __init__(self, api_key: str, base_url: str, model: str,
                 temperature: float = 0.0, max_tokens: int = 1200, timeout: int = 60,
                 name: str = "openai-compat"):
        super().__init__(name=name)
        from openai import OpenAI

        if not api_key:
            raise ValueError("缺少 API key：请在 config.py 或环境变量 MDA_LLM_API_KEY 中配置")
        self.client = OpenAI(api_key=api_key, base_url=base_url or None, timeout=timeout)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def chat(self, system: str, user: str, **kwargs) -> LLMReply:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
        )
        usage = getattr(resp, "usage", None)
        reply = LLMReply(
            text=(resp.choices[0].message.content or "").strip(),
            prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        )
        return self._account(reply)
