#!/usr/bin/env python3
"""
LLM Client Factory — LLM_BACKEND 환경변수로 백엔드 전환

  LLM_BACKEND=claude      → Anthropic API (기본값)
  LLM_BACKEND=local       → LM Studio (OpenAI 호환 로컬 서버)
  LLM_BACKEND=openrouter  → OpenRouter API

디버그 모드:
  LLM_DEBUG=1  요청/응답 요약, 소요 시간, 백엔드 선택 과정을 stderr에 출력
"""
import os
import logging
import time
from abc import ABC, abstractmethod

# 루트 로거 설정: LLM_DEBUG=1 이면 DEBUG, 아니면 WARNING
_debug = os.environ.get("LLM_DEBUG", "0").strip() in ("1", "true", "yes")
logging.basicConfig(
    level=logging.DEBUG if _debug else logging.WARNING,
    format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("llm_client")

# 디버그 모드에서 프롬프트/응답을 잘라낼 최대 문자 수
_MAX_CHARS = int(os.environ.get("LLM_DEBUG_MAX_CHARS", "200"))


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

    def _debug_request(self, model: str, messages: list[dict], system: str, max_tokens: int) -> float:
        """디버그 모드에서 요청 정보를 출력하고 시작 시각을 반환한다."""
        if not _debug:
            return time.monotonic()
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        log.debug(
            "REQUEST  model=%s  max_tokens=%d  msgs=%d  system=%d chars\n"
            "         last_user: %s",
            model, max_tokens, len(messages), len(system),
            repr(last_user[:_MAX_CHARS]) + ("…" if len(last_user) > _MAX_CHARS else ""),
        )
        return time.monotonic()

    def _debug_response(self, text: str, t0: float) -> None:
        """디버그 모드에서 응답 요약과 소요 시간을 출력한다."""
        if not _debug:
            return
        elapsed = time.monotonic() - t0
        log.debug(
            "RESPONSE %.2fs  %d chars\n         %s",
            elapsed, len(text),
            repr(text[:_MAX_CHARS]) + ("…" if len(text) > _MAX_CHARS else ""),
        )


def get_client() -> LLMClient:
    """
    LLM_BACKEND 환경변수에 따라 클라이언트를 반환한다.
    지연 임포트로 사용하지 않는 백엔드 패키지 의존성을 회피한다.
    """
    backend = os.environ.get("LLM_BACKEND", "claude").lower().strip()
    log.debug("get_client: LLM_BACKEND=%r → backend=%r", os.environ.get("LLM_BACKEND"), backend)

    if backend == "local":
        from local_llm_client import LocalLLMClient
        client = LocalLLMClient()
        log.debug("get_client: LocalLLMClient 생성 완료")
        return client

    if backend == "openrouter":
        from local_llm_client import OpenRouterClient
        client = OpenRouterClient()
        log.debug("get_client: OpenRouterClient 생성 완료")
        return client

    if backend != "claude":
        log.warning("get_client: 알 수 없는 LLM_BACKEND=%r — claude 로 폴백", backend)

    from claude_client import ClaudeClient
    client = ClaudeClient()
    log.debug("get_client: ClaudeClient 생성 완료")
    return client


# ── 직접 실행 시 백엔드 선택 확인 ──────────────────────────────────────────
if __name__ == "__main__":
    import sys
    # LLM_DEBUG가 꺼져 있어도 여기서는 강제 활성화
    logging.getLogger().setLevel(logging.DEBUG)

    print(f"LLM_BACKEND={os.environ.get('LLM_BACKEND', '(미설정 → claude)')}")
    try:
        c = get_client()
        print(f"클라이언트 타입: {type(c).__name__}")
        print("ping 전송 중…")
        answer = c.ask("Reply with exactly: pong")
        print(f"응답: {answer!r}")
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        sys.exit(1)
