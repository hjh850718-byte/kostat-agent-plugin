#!/usr/bin/env python3
"""
Anthropic Claude API 클라이언트
환경변수: ANTHROPIC_API_KEY
"""
import os
import anthropic
from llm_client import LLMClient

DEFAULT_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = 4096


class ClaudeClient(LLMClient):

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        self._client = anthropic.Anthropic(api_key=api_key)

    def chat(
        self,
        messages: list[dict],
        *,
        system: str = "",
        model: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = 0.0,
    ) -> str:
        kwargs: dict = {
            "model": model or DEFAULT_MODEL,
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system
        # Claude API는 temperature=0을 지원하지만 extended_thinking과 충돌 가능 — 분리
        if temperature > 0:
            kwargs["temperature"] = temperature

        response = self._client.messages.create(**kwargs)
        return response.content[0].text
