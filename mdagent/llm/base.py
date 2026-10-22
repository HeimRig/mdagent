"""LLM 后端抽象。所有后端只暴露 chat(system, user) -> LLMReply。"""

from dataclasses import dataclass, field


@dataclass
class LLMReply:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0


@dataclass
class LLMBackend:
    name: str = "base"
    calls: int = 0
    usage: dict[str, int] = field(default_factory=lambda: {"prompt": 0, "completion": 0})

    def chat(self, system: str, user: str, **kwargs) -> LLMReply:
        raise NotImplementedError

    def _account(self, reply: LLMReply) -> LLMReply:
        self.calls += 1
        self.usage["prompt"] += reply.prompt_tokens
        self.usage["completion"] += reply.completion_tokens
        return reply

    def reset(self) -> None:
        self.calls = 0
        self.usage = {"prompt": 0, "completion": 0}
