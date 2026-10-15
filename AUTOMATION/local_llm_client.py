#!/usr/bin/env python3
"""
로컬 LLM 클라이언트 (LM Studio) 및 OpenRouter 클라이언트

LM Studio 권장 설정:
  ① Developer 탭 → 서버 시작 (기본 포트 1234)
  ② K Cache Quantization = Q8_0 / V Cache Quantization = Q4_0
     → VRAM 28.75GB → 22.45GB로 감소
  ③ GPU Offload 슬라이더 최대 (CPU 레이어 = 0)
  ④ 컨텍스트 윈도우 = 100,000~150,000
     (코딩용 시스템 프롬프트 20~40k 소비 → 실질 여유 60~130k)
  ⑤ JIT 로딩 TTL 설정으로 메모리 유지 시간 제어
  ※ 콜드 스타트(모델 미적재 상태 첫 요청): 30~60초 추가 지연

환경변수:
  LOCAL_LLM_BASE_URL    기본값 http://localhost:1234/v1
  LOCAL_LLM_MODEL       기본값 gemma-4-26b-a4b
  LOCAL_LLM_API_KEY     기본값 lm-studio (LM Studio는 키를 검증하지 않음)
  LOCAL_LLM_MAX_TOKENS  기본값 50000
  LOCAL_LLM_TIMEOUT     기본값 120 (초) — 콜드 스타트 포함 여유값
  OPENROUTER_API_KEY    OpenRouter 백엔드 필수
  OPENROUTER_MODEL      기본값 deepseek/deepseek-chat-v3-0324:free
  LLM_DEBUG             1이면 요청/응답/소요시간/재시도 출력
"""
import os
import sys
import time
import logging
import openai
from llm_client import LLMClient

log = logging.getLogger("local_llm_client")

# ── LM Studio 기본값 ────────────────────────────────────────────────────────
_LM_BASE_URL = os.environ.get("LOCAL_LLM_BASE_URL", "http://localhost:1234/v1")
_LM_MODEL    = os.environ.get("LOCAL_LLM_MODEL",    "gemma-4-26b-a4b")
_LM_API_KEY  = os.environ.get("LOCAL_LLM_API_KEY",  "lm-studio")
_LM_TIMEOUT  = int(os.environ.get("LOCAL_LLM_TIMEOUT",    "120"))
_LM_MAX_OUT  = int(os.environ.get("LOCAL_LLM_MAX_TOKENS", "50000"))

# ── OpenRouter 기본값 ───────────────────────────────────────────────────────
_OR_BASE_URL = "https://openrouter.ai/api/v1"
_OR_MODEL    = os.environ.get("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3-0324:free")


class LocalLLMClient(LLMClient):
    """
    LM Studio (또는 Ollama 등) OpenAI 호환 로컬 서버 클라이언트.
    콜드 스타트 대비 재시도는 chat_with_retry()를 사용한다.
    """

    def __init__(
        self,
        base_url: str = _LM_BASE_URL,
        model: str    = _LM_MODEL,
        api_key: str  = _LM_API_KEY,
        timeout: int  = _LM_TIMEOUT,
    ):
        self._model    = model
        self._timeout  = timeout
        self._base_url = base_url
        self._client   = openai.OpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )
        log.debug(
            "LocalLLMClient 초기화  url=%s  model=%s  timeout=%ds",
            base_url, model, timeout,
        )

    def chat(
        self,
        messages: list[dict],
        *,
        system: str     = "",
        model: str | None = None,
        max_tokens: int = _LM_MAX_OUT,
        temperature: float = 0.0,
    ) -> str:
        resolved_model = model or self._model
        t0 = self._debug_request(resolved_model, messages, system, max_tokens)

        full_messages = _prepend_system(messages, system)
        try:
            response = self._client.chat.completions.create(
                model=resolved_model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except openai.APIConnectionError as exc:
            raise ConnectionError(
                f"LM Studio 서버에 연결할 수 없습니다 ({self._base_url}).\n"
                f"  → LM Studio Developer 탭에서 서버가 기동 중인지 확인하세요.\n"
                f"  원인: {exc}"
            ) from exc
        except openai.APITimeoutError as exc:
            raise TimeoutError(
                f"LM Studio 응답 시간 초과 (timeout={self._timeout}s).\n"
                f"  → 콜드 스타트(모델 최초 로딩)가 길 수 있습니다. LOCAL_LLM_TIMEOUT 값을 높이세요.\n"
                f"  원인: {exc}"
            ) from exc
        except openai.APIStatusError as exc:
            raise RuntimeError(
                f"LM Studio API 오류 (HTTP {exc.status_code}): {exc.message}"
            ) from exc

        text = response.choices[0].message.content or ""
        self._debug_response(text, t0)
        return text

    def chat_with_retry(
        self,
        messages: list[dict],
        *,
        system: str       = "",
        model: str | None = None,
        max_tokens: int   = _LM_MAX_OUT,
        temperature: float = 0.0,
        retries: int      = 2,
        retry_delay: float = 5.0,
    ) -> str:
        """
        콜드 스타트 타임아웃/연결 오류에 대비한 재시도 래퍼.
        retry_delay초 → 2×retry_delay초 지수 백오프.
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
            except (TimeoutError, ConnectionError) as exc:
                last_exc = exc
                if attempt < retries - 1:
                    wait = retry_delay * (2 ** attempt)
                    log.warning(
                        "chat_with_retry: attempt %d/%d 실패 — %.0fs 후 재시도\n  %s",
                        attempt + 1, retries, wait, exc,
                    )
                    time.sleep(wait)
        raise last_exc  # type: ignore[misc]

    def health_check(self) -> bool:
        """
        LM Studio 서버 연결 확인.
        /v1/models 엔드포인트를 조회해 서버 응답 여부를 반환한다.
        """
        try:
            models = self._client.models.list()
            names  = [m.id for m in models.data]
            log.debug("health_check OK — 사용 가능한 모델: %s", names)
            print(f"[health_check] 서버 응답 OK — 모델 목록: {names}")
            return True
        except Exception as exc:
            log.warning("health_check 실패: %s", exc)
            print(f"[health_check] 연결 실패: {exc}", file=sys.stderr)
            return False


class OpenRouterClient(LLMClient):
    """
    OpenRouter 통합 API 클라이언트.
    단일 API 키로 수백 개 모델 접근 가능 (무료 모델 포함).

    비용 폭주 방지:
      OpenRouter 대시보드 → Limits에서 $1/월 상한 + 허용 모델 목록 설정 권장.
      신규 API 키 생성 시 max_credit=0 으로 시작.

    프라이버시:
      무료 모델은 OpenRouter가 학습에 활용할 수 있음.
      ZDR(Zero Data Retention) 플랜 또는 유료 모델 사용 시 수집 안 됨.
    """

    def __init__(self, model: str = _OR_MODEL):
        api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError(
                "OPENROUTER_API_KEY가 설정되지 않았습니다.\n"
                "  export OPENROUTER_API_KEY=sk-or-..."
            )
        self._model  = model
        self._client = openai.OpenAI(
            base_url=_OR_BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/hjh850718-byte/kostat-agent-plugin",
                "X-Title": "KOSTAT Agent Plugin",
            },
        )
        log.debug("OpenRouterClient 초기화  model=%s", model)

    def chat(
        self,
        messages: list[dict],
        *,
        system: str       = "",
        model: str | None = None,
        max_tokens: int   = 50000,
        temperature: float = 0.0,
    ) -> str:
        resolved_model = model or self._model
        t0 = self._debug_request(resolved_model, messages, system, max_tokens)

        full_messages = _prepend_system(messages, system)
        try:
            response = self._client.chat.completions.create(
                model=resolved_model,
                messages=full_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except openai.AuthenticationError as exc:
            raise EnvironmentError(
                f"OPENROUTER_API_KEY가 올바르지 않습니다: {exc}"
            ) from exc
        except openai.APIStatusError as exc:
            raise RuntimeError(
                f"OpenRouter API 오류 (HTTP {exc.status_code}): {exc.message}\n"
                f"  모델={resolved_model} — 무료 모델은 사용량 제한이 있을 수 있습니다."
            ) from exc

        text = response.choices[0].message.content or ""
        self._debug_response(text, t0)
        return text


# ── 내부 헬퍼 ───────────────────────────────────────────────────────────────

def _prepend_system(messages: list[dict], system: str) -> list[dict]:
    """
    OpenAI 호환 API는 system role을 messages 첫 번째 항목으로 전달한다.
    Anthropic과 달리 별도 system 파라미터가 없다.
    """
    if not system:
        return messages
    return [{"role": "system", "content": system}] + list(messages)


# ── 직접 실행 시 연결/응답 확인 ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    logging.getLogger().setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser(description="로컬 LLM 클라이언트 디버그")
    parser.add_argument(
        "--backend", choices=["local", "openrouter"], default="local",
        help="테스트할 백엔드 (기본값: local)",
    )
    parser.add_argument(
        "--health-only", action="store_true",
        help="LM Studio health check만 실행 (응답 테스트 없음)",
    )
    args = parser.parse_args()

    if args.backend == "local":
        print(f"=== LocalLLMClient 테스트 ===")
        print(f"서버: {_LM_BASE_URL}  모델: {_LM_MODEL}  타임아웃: {_LM_TIMEOUT}s")
        client = LocalLLMClient()

        ok = client.health_check()
        if not ok or args.health_only:
            sys.exit(0 if ok else 1)

        print("\nping 전송 중 (콜드 스타트 시 최대 60초)…")
        try:
            answer = client.chat_with_retry([{"role": "user", "content": "Reply with exactly: pong"}])
            print(f"응답: {answer!r}")
        except Exception as exc:
            print(f"오류: {exc}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"=== OpenRouterClient 테스트 ===")
        print(f"모델: {_OR_MODEL}")
        try:
            client = OpenRouterClient()
            answer = client.ask("Reply with exactly: pong")
            print(f"응답: {answer!r}")
        except Exception as exc:
            print(f"오류: {exc}", file=sys.stderr)
            sys.exit(1)
