#!/usr/bin/env python3
"""
Anthropic Claude API 클라이언트

환경변수:
  ANTHROPIC_API_KEY  필수
  CLAUDE_MODEL       기본값 claude-sonnet-4-6
  LLM_DEBUG          1이면 요청/응답/소요시간 출력
"""
import os
import sys
import logging
import anthropic
from llm_client import LLMClient

log = logging.getLogger("claude_client")

DEFAULT_MODEL      = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
DEFAULT_MAX_TOKENS = 4096


class ClaudeClient(LLMClient):

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다.\n"
                "  export ANTHROPIC_API_KEY=sk-ant-..."
            )
        # 키 앞 8자만 로그에 노출 (유출 방지)
        log.debug("ClaudeClient 초기화  model=%s  key=%.8s…", DEFAULT_MODEL, api_key)
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
        resolved_model = model or DEFAULT_MODEL
        t0 = self._debug_request(resolved_model, messages, system, max_tokens)

        kwargs: dict = {
            "model":      resolved_model,
            "max_tokens": max_tokens,
            "messages":   messages,
        }
        if system:
            kwargs["system"] = system
        # temperature=0은 Anthropic 기본값과 동일하므로 생략해 extended_thinking 호환성 유지
        if temperature > 0:
            kwargs["temperature"] = temperature

        try:
            response = self._client.messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise EnvironmentError(
                f"ANTHROPIC_API_KEY가 올바르지 않습니다: {exc}"
            ) from exc
        except anthropic.RateLimitError as exc:
            raise RuntimeError(f"Claude API 속도 제한 초과: {exc}") from exc
        except anthropic.APIStatusError as exc:
            raise RuntimeError(
                f"Claude API 오류 (HTTP {exc.status_code}): {exc.message}"
            ) from exc

        text = response.content[0].text
        log.debug(
            "USAGE    input_tokens=%d  output_tokens=%d",
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        self._debug_response(text, t0)
        return text


# ── 직접 실행 시 연결 확인 ──────────────────────────────────────────────────
if __name__ == "__main__":
    import os as _os
    logging.getLogger().setLevel(logging.DEBUG)

    model = _os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
    print(f"테스트 모델: {model}")
    try:
        client = ClaudeClient()
        answer = client.ask("Reply with exactly: pong")
        print(f"응답: {answer!r}")
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)
