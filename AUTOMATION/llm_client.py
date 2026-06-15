#!/usr/bin/env python3
"""
LLM Client Factory — LLM_BACKEND 환경변수로 백엔드 전환
  LLM_BACKEND=claude      → Anthropic API (기본값)
  LLM_BACKEND=local       → LM Studio (OpenAI 호환 로컬 서버)
  LLM_BACKEND=openrouter  → OpenRouter API
"""
import os
from abc import ABC, abstractmethod


class LLMClient(ABC):
    """모든 LLM 백엔드가 구현해야 하는 공통 인터페이스"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        *,
        system: str = "",
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
    ) -> str:
        """
        messages: [{"role": "user"|"assistant", "content": "..."}]
        반환값: assistant 응답 텍스트
        """

    def ask(self, prompt: str, *, system: str = "", **kwargs) -> str:
        """단일 user 턴 편의 메서드"""
        return self.chat([{"role": "user", "content": prompt}], system=system, **kwargs)


def get_client() -> LLMClient:
    """
    LLM_BACKEND 환경변수에 따라 클라이언트 반환.
    import는 필요한 백엔드만 지연 로딩해 불필요한 패키지 의존성을 회피한다.
    """
    backend = os.environ.get("LLM_BACKEND", "claude").lower().strip()

    if backend == "local":
        from local_llm_client import LocalLLMClient
        return LocalLLMClient()

    if backend == "openrouter":
        from local_llm_client import OpenRouterClient
        return OpenRouterClient()

    from claude_client import ClaudeClient
    return ClaudeClient()
