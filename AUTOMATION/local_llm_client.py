#!/usr/bin/env python3
"""
로컬 LLM 클라이언트 (LM Studio) 및 OpenRouter 클라이언트

LM Studio 설정 (기사 권장값):
  - KV 캐시 양자화: K=Q8_0, V=Q4_0  → VRAM 28GB → 22GB로 감소
  - 컨텍스트 윈도우: 100,000~150,000 토큰 (코딩용 시스템 프롬프트 20~40k 차지)
  - GPU Offload 슬라이더: 최대
  - JIT 로딩 TTL: 원하는 유지 시간 설정

환경변수:
  LOCAL_LLM_BASE_URL   기본값 http://localhost:1234/v1
  LOCAL_LLM_MODEL      기본값 gemma-4-26b-a4b (LM Studio에서 로드된 모델명)
  LOCAL_LLM_API_KEY    기본값 lm-studio (LM Studio는 키를 검증하지 않음)
  LOCAL_LLM_MAX_TOKENS 기본값 50000
  LOCAL_LLM_TIMEOUT    기본값 120 (초) — 콜드 스타트 30초 포함 여유값
  OPENROUTER_API_KEY   OpenRouter 백엔드 사용 시 필수
"""
import os
import time
import openai
from llm_client import LLMClient

# ── LM Studio 기본값 ────────────────────────────────────────────────────────
_LM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")
_LM_MODEL    = os.environ.get("LOCAL_LLM_MODEL", "gemma-4-26b-a4b")
_LM_API_KEY  = os.environ.get("LOCAL_LLM_API_KEY", "lm-studio")
_LM_TIMEOUT  = int(os.environ.get("LOCAL_LLM_TIMEOUT", "120"))

# 코딩용 시스템 프롬프트가 20~40k를 차지하므로 50k를 기본 출력 한도로 설정
_LM_MAX_OUT  = int(os.environ.get("LOCAL_LLM_MAX_TOKENS", "50000"))

# ── OpenRouter 기본값 ───────────────────────────────────────────────────────
_OR_BASE_URL = "https://openrouter.ai/api/v1"
_OR_MODEL    = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")


class LocalLLMClient(LLMClient):
    """
    LM Studio (또는 Ollama 등) OpenAI 호환 로컬 서버 클라이언트.

    콜드 스타트 주의:
      LM Studio JIT 로딩 시 첫 요청이 최대 30~60초 지연될 수 있음.
      timeout을 충분히 크게 (기본 120초) 설정해 TTFT 측정 왜곡을 방지한다.
    """

    def __init__(
        self,
        base_url: str = _LM_BASE_URL,
        model: str = _LM_MODEL,
        api_key: str = _LM_API_KEY,
        timeout: int = _LM_TIMEOUT,
    ):
        self._model   = model
        self._timeout = timeout
        self._client  = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    def chat(
        self,
        messages: list[dict],
        *,
        system: str = "",
        model: str | None = None,
        max_tokens: int = _LM_MAX_OUT,
        temperature: float = 0.0,
    ) -> str:
        full_messages = _prepend_system(messages, system)
        response = self._client.chat.completions.create(
            model=model or self._model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    def chat_with_retry(
        self,
        messages: list[dict],
        *,
        system: str = "",
        model: str | None = None,
        max_tokens: int = _LM_MAX_OUT,
        temperature: float = 0.0,
        retries: int = 2,
        retry_delay: float = 5.0,
    ) -> str:
        """
        콜드 스타트 타임아웃에 대비한 재시도 래퍼.
        첫 번째 실패 후 retry_delay 초 대기 후 재시도한다.
        """
        last_exc: Exception | None = None
        for attempt in range(retries):
            try:
                return self.chat(
                    messages,
                    system=system,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            except (openai.APITimeoutError, openai.APIConnectionError) as exc:
                last_exc = exc
                if attempt < retries - 1:
                    wait = retry_delay * (2 ** attempt)  # 5s → 10s
                    time.sleep(wait)
        raise last_exc  # type: ignore[misc]


class OpenRouterClient(LLMClient):
    """
    OpenRouter 통합 API 클라이언트.
    단일 API 키로 수백 개 모델 접근 가능 (무료 모델 포함).

    비용 폭주 방지:
      OpenRouter 대시보드에서 max credit=$1/월, 허용 모델 목록 제한 권장.
      새 API 키 생성 시 max credit=0 설정.

    프라이버시:
      무료 모델은 OpenRouter가 학습에 활용할 수 있음.
      ZDR(Zero Data Retention) 옵션 또는 유료 모델 사용 시 미수집.
    """

    def __init__(self, model: str = _OR_MODEL):
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENROUTER_API_KEY가 설정되지 않았습니다.")
        self._model  = model
        self._client = openai.OpenAI(
            base_url=_OR_BASE_URL,
            api_key=api_key,
            default_headers={
                # OpenRouter 라우팅 식별용 — 필수는 아님
                "HTTP-Referer": "https://github.com/hjh850718-byte/kostat-agent-plugin",
                "X-Title": "KOSTAT Agent Plugin",
            },
        )

    def chat(
        self,
        messages: list[dict],
        *,
        system: str = "",
        model: str | None = None,
        max_tokens: int = 50000,
        temperature: float = 0.0,
    ) -> str:
        full_messages = _prepend_system(messages, system)
        response = self._client.chat.completions.create(
            model=model or self._model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


# ── 내부 헬퍼 ───────────────────────────────────────────────────────────────

def _prepend_system(messages: list[dict], system: str) -> list[dict]:
    """
    OpenAI 호환 API는 system role을 messages 배열 첫 번째 항목으로 전달한다.
    Anthropic과 달리 별도 파라미터가 없음.
    """
    if not system:
        return messages
    return [{"role": "system", "content": system}] + list(messages)
