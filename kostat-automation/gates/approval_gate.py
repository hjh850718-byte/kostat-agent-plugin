#!/usr/bin/env python3
"""
KOSTAT 자동화 — 검수 게이트 모듈

게이트 정책:
  - 읽기 전용 작업 (브리핑, 조회, 분석): 게이트 없음 → 자동 통과
  - 쓰기 작업 (파일 생성, Notion 저장): Telegram Y/N 확인 후 실행
  - 외부 발송 (이메일, 카카오톡):       반드시 사람이 승인
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

# 상위 패키지에서 import (runner.py와 같은 디렉토리에서 실행 시)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from notifier.telegram_notify import (
    send_approval_request,
    send_message,
    poll_updates,
    TELEGRAM_CHAT_ID,
    ICON,
)

log = logging.getLogger("kostat.gate")


# ── 게이트 타입 정의 ──────────────────────────────────────────────────────────
GATE_TYPE_NONE     = None       # 자동 통과
GATE_TYPE_WRITE    = "write"    # Notion/파일 저장 전 확인
GATE_TYPE_SEND     = "send"     # 외부 발송 (이메일/카카오톡) — 반드시 승인

# 게이트 타입별 기본 설명
GATE_DESCRIPTIONS = {
    GATE_TYPE_WRITE: "⚠️ 쓰기 작업입니다. Notion 또는 로컬 파일에 저장됩니다.",
    GATE_TYPE_SEND:  "🚨 외부 발송 작업입니다. 이메일 또는 카카오톡이 전송됩니다.\n반드시 내용을 확인한 뒤 승인하세요.",
}


class GateResult:
    """게이트 통과 결과."""
    def __init__(self, approved: bool, reason: str, response: Optional[str] = None):
        self.approved  = approved
        self.reason    = reason
        self.response  = response  # "Y", "N", "AUTO", "TIMEOUT"
        self.timestamp = datetime.now().isoformat()

    def __bool__(self):
        return self.approved

    def __repr__(self):
        icon = "✅" if self.approved else "❌"
        return f"GateResult({icon} approved={self.approved}, reason='{self.reason}', response='{self.response}')"


def check_gate(
    task_name: str,
    gate_type: Optional[str],
    prompt: Optional[str] = None,
    timeout_sec: int = 60,
    default_action: str = "Y",
) -> GateResult:
    """
    검수 게이트를 실행하고 GateResult를 반환합니다.

    Args:
        task_name:      태스크 식별자
        gate_type:      None / "write" / "send"
        prompt:         Telegram에 보낼 승인 요청 메시지 (None이면 기본값 사용)
        timeout_sec:    응답 대기 시간 (초)
        default_action: 타임아웃 시 기본 동작 ("Y" = 진행, "N" = 취소)

    Returns:
        GateResult
    """
    # 1) 게이트 없음 → 자동 통과
    if gate_type is None:
        log.debug(f"[{task_name}] 게이트 없음 — 자동 통과")
        return GateResult(approved=True, reason="게이트 없음 (읽기 전용)", response="AUTO")

    # 2) 게이트 있음 → Telegram 승인 요청
    desc = GATE_DESCRIPTIONS.get(gate_type, "작업 실행 전 확인이 필요합니다.")
    full_prompt = prompt or f"{desc}\n\n<b>{task_name}</b> 을 실행할까요? (Y/N)"

    log.info(f"[{task_name}] 검수 게이트 활성화 (type={gate_type}, timeout={timeout_sec}s)")

    try:
        send_approval_request(task_name, full_prompt, timeout_sec)
    except Exception as exc:
        # Telegram 전송 실패 → 외부 발송 게이트는 차단, 쓰기는 기본값 사용
        log.error(f"[{task_name}] 승인 요청 전송 실패: {exc}")
        if gate_type == GATE_TYPE_SEND:
            return GateResult(
                approved=False,
                reason=f"Telegram 전송 실패로 외부 발송 차단: {exc}",
                response="ERROR",
            )
        log.warning(f"[{task_name}] 쓰기 게이트 — Telegram 실패, 기본값({default_action}) 사용")
        approved = default_action.upper() == "Y"
        return GateResult(
            approved=approved,
            reason=f"Telegram 실패, 기본값={default_action}",
            response="ERROR_DEFAULT",
        )

    # 3) 응답 폴링
    response = poll_updates(max_wait_sec=timeout_sec)

    # 4) 응답 없음 (타임아웃)
    if response is None:
        approved = default_action.upper() == "Y"
        reason   = f"타임아웃({timeout_sec}s) — 기본값={default_action}"
        log.info(f"[{task_name}] {reason}")
        _notify_timeout(task_name, default_action, approved)
        return GateResult(approved=approved, reason=reason, response="TIMEOUT")

    # 5) 명시적 응답
    approved = response == "Y"
    reason   = f"사용자 응답={response}"
    log.info(f"[{task_name}] {reason}")
    _notify_gate_result(task_name, approved, response)
    return GateResult(approved=approved, reason=reason, response=response)


def _notify_timeout(task_name: str, default: str, approved: bool) -> None:
    """타임아웃 시 자동 처리 알림."""
    icon   = "▶️" if approved else "⏹️"
    action = "자동 진행" if approved else "자동 취소"
    try:
        send_message(
            f"{icon} <b>[검수 게이트]</b> 타임아웃\n"
            f"📌 태스크: <code>{task_name}</code>\n"
            f"📋 처리: {action} (기본값={default})"
        )
    except Exception:
        pass


def _notify_gate_result(task_name: str, approved: bool, response: str) -> None:
    """게이트 결과 확인 알림."""
    icon   = "✅" if approved else "❌"
    action = "승인 — 실행합니다" if approved else "거부 — 이번 실행은 건너뜁니다"
    try:
        send_message(
            f"{icon} <b>[검수 게이트]</b> 응답 수신\n"
            f"📌 태스크: <code>{task_name}</code>\n"
            f"📋 결과: {action}"
        )
    except Exception:
        pass


# ── CLI 테스트용 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="검수 게이트 테스트")
    parser.add_argument("--task",    default="TEST_TASK")
    parser.add_argument("--type",    default="write", choices=["write", "send"])
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    # .env 로드
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        import notifier.telegram_notify as tn
        tn.TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        tn.API_BASE = f"https://api.telegram.org/bot{tn.TELEGRAM_BOT_TOKEN}"

    logging.basicConfig(level=logging.DEBUG)
    result = check_gate(
        task_name=args.task,
        gate_type=args.type,
        timeout_sec=args.timeout,
    )
    print(result)
    sys.exit(0 if result.approved else 1)
