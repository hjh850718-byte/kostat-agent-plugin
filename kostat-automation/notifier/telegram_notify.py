#!/usr/bin/env python3
"""
KOSTAT 자동화 — Telegram 알림 모듈
Telegram Bot API를 통해 한준희 과장(@Junheehanbot)에게 메시지를 전송합니다.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
from typing import Optional

# ── 봇 설정 (환경변수 우선, fallback은 config.json) ──────────────────────────
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "8761375155")
API_BASE           = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# 한국 이모지 아이콘 매핑
ICON = {
    "start":   "🚀",
    "success": "✅",
    "failure": "❌",
    "retry":   "🔄",
    "gate":    "🔑",
    "info":    "ℹ️",
    "warn":    "⚠️",
    "morning": "🌅",
    "oor":     "📋",
    "invoice": "💰",
    "eod":     "🌙",
}

TASK_ICON = {
    "KOSTAT_MorningBriefing":    ICON["morning"],
    "KOSTAT_OOR_WeeklyCheck":    ICON["oor"],
    "KOSTAT_CommissionInvoice":  ICON["invoice"],
    "KOSTAT_EOD_Retrospective":  ICON["eod"],
}


def _api_call(method: str, payload: dict, timeout: int = 10) -> dict:
    """Telegram Bot API 호출 (재시도 없음 — 호출자가 관리)."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN 환경변수가 설정되지 않았습니다.\n"
            ".env 파일을 확인하세요: kostat-automation/.env"
        )

    url  = f"{API_BASE}/{method}"
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def send_message(
    text: str,
    chat_id: Optional[str] = None,
    parse_mode: str = "HTML",
    silent: bool = False,
) -> dict:
    """
    Telegram 메시지 전송.
    실패 시 최대 3회 재시도 (2s, 4s, 8s 백오프).
    """
    target = chat_id or TELEGRAM_CHAT_ID
    payload = {
        "chat_id":              target,
        "text":                 text,
        "parse_mode":           parse_mode,
        "disable_notification": silent,
    }

    last_error = None
    for attempt, wait in enumerate([0, 2, 4, 8], start=1):
        if wait:
            time.sleep(wait)
        try:
            result = _api_call("sendMessage", payload)
            return result
        except Exception as exc:
            last_error = exc
            print(f"[Telegram] 전송 실패 {attempt}/4: {exc}", file=sys.stderr)

    raise RuntimeError(f"Telegram 전송 최종 실패: {last_error}") from last_error


def send_task_start(task_name: str, description: str) -> None:
    """태스크 시작 알림 (approval_gate가 있는 태스크에만 사용)."""
    icon = TASK_ICON.get(task_name, ICON["start"])
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    text = (
        f"{icon} <b>[KOSTAT 자동화]</b> 태스크 시작\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 태스크: <code>{task_name}</code>\n"
        f"📝 설명: {description}\n"
        f"🕐 시각: {now}"
    )
    send_message(text)


def send_task_success(task_name: str, summary: str, elapsed_sec: float) -> None:
    """태스크 성공 알림."""
    icon = TASK_ICON.get(task_name, ICON["success"])
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    # 출력이 너무 길면 앞 1000자만 표시
    if len(summary) > 1000:
        summary = summary[:1000] + "\n…(이하 생략)"
    text = (
        f"{icon} <b>[KOSTAT 자동화]</b> ✅ 완료\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 태스크: <code>{task_name}</code>\n"
        f"⏱️ 소요: {elapsed_sec:.1f}초\n"
        f"🕐 시각: {now}\n\n"
        f"<pre>{_escape_html(summary)}</pre>"
    )
    send_message(text)


def send_task_failure(
    task_name: str,
    error: str,
    attempt: int,
    max_attempts: int,
) -> None:
    """태스크 실패/재시도 알림."""
    is_final = attempt >= max_attempts
    icon     = ICON["failure"] if is_final else ICON["retry"]
    now      = datetime.now().strftime("%Y-%m-%d %H:%M")
    status   = "최종 실패 — 수동 확인 필요" if is_final else f"재시도 중 ({attempt}/{max_attempts})"
    text = (
        f"{'❌' if is_final else '🔄'} <b>[KOSTAT 자동화]</b> {status}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 태스크: <code>{task_name}</code>\n"
        f"💬 오류: <code>{_escape_html(str(error)[:400])}</code>\n"
        f"🕐 시각: {now}"
    )
    send_message(text)


def send_approval_request(
    task_name: str,
    prompt: str,
    timeout_sec: int,
) -> None:
    """승인 요청 메시지 전송."""
    icon = TASK_ICON.get(task_name, ICON["gate"])
    text = (
        f"{icon} <b>[KOSTAT 자동화]</b> 승인 요청\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 태스크: <code>{task_name}</code>\n\n"
        f"{prompt}\n\n"
        f"⏱️ <i>{timeout_sec}초 내 미응답 시 기본값으로 자동 처리됩니다.</i>"
    )
    send_message(text)


def poll_updates(
    after_update_id: int = 0,
    timeout_sec: int = 30,
    max_wait_sec: int = 60,
) -> Optional[str]:
    """
    Telegram getUpdates 폴링으로 사용자 응답(Y/N) 수집.
    max_wait_sec 내에 응답이 없으면 None 반환.
    """
    deadline  = time.time() + max_wait_sec
    offset    = after_update_id + 1

    while time.time() < deadline:
        remaining = max(1, int(deadline - time.time()))
        wait      = min(timeout_sec, remaining)
        try:
            result = _api_call(
                "getUpdates",
                {"offset": offset, "timeout": wait, "allowed_updates": ["message"]},
                timeout=wait + 5,
            )
            updates = result.get("result", [])
            for upd in updates:
                offset = upd["update_id"] + 1
                msg    = upd.get("message", {})
                text   = msg.get("text", "").strip().upper()
                cid    = str(msg.get("chat", {}).get("id", ""))
                # 같은 채팅방에서 온 Y/N만 수락
                if cid == TELEGRAM_CHAT_ID and text in ("Y", "N", "YES", "NO"):
                    return "Y" if text.startswith("Y") else "N"
        except Exception as exc:
            print(f"[Telegram] 폴링 오류: {exc}", file=sys.stderr)
            time.sleep(2)

    return None  # 타임아웃


def _escape_html(text: str) -> str:
    """Telegram HTML 모드용 특수문자 이스케이프."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


# ── CLI 테스트용 ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Telegram 알림 테스트")
    parser.add_argument("message", nargs="?", default="✅ KOSTAT 자동화 시스템 연결 테스트 성공!")
    args = parser.parse_args()

    # .env 파일 로드 (있으면)
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
        # 환경변수 재로드 후 API_BASE 갱신
        TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    try:
        send_message(args.message)
        print("✅ 전송 성공!")
    except Exception as e:
        print(f"❌ 전송 실패: {e}")
        sys.exit(1)
