#!/usr/bin/env python3
"""
KOSTAT EOD Detector Hook (UserPromptSubmit)
사용자 메시지에서 업무종료 키워드 실시간 감지 → flag 파일 기록.
Stop Hook(kostat-eod-stop.py)과 협력하여 EOD 회고 트리거 강화.
"""
import sys
import json
from datetime import datetime
from pathlib import Path

# CLAUDE.md의 트리거 조건과 동기화 (v2 — 패턴 확장)
EOD_EXPLICIT = [
    "업무끝", "업무 끝", "퇴근", "오늘 끝", "일 끝났어", "오늘 마무리",
    "오늘 업무 끝", "마무리할게", "정리할게", "퇴근할게", "퇴근합니다",
    "오늘 일 끝", "일 마무리", "업무 마무리",
]

EOD_IMPLICIT = [
    "수고했어", "오늘도", "내일 봐", "내일 보자", "다음에", "쉬어야겠다",
    "여기까지", "그만", "고생했어",
]

EOD_RETRO_INTENT = [
    "오늘 회고", "회고할게", "KPT", "회고 시작", "회고 하자",
]

FLAG_DIR = Path(r"C:\Users\USER\Documents\Claude\claude-tray\.eod")
LOG_PATH = Path(r"C:\Users\USER\Documents\Claude\AGENT\docs\session-log.txt")


def is_pm_session() -> bool:
    """오후 5시 이후인지 확인"""
    return datetime.now().hour >= 17


def detect_eod(text: str) -> str | None:
    """EOD 트리거 감지 → 트리거 타입 반환"""
    # 0순위: 직접 회고 요청 (시간 무관)
    for phrase in EOD_RETRO_INTENT:
        if phrase in text:
            return "retro_intent"

    # 1순위: 명시적 종료
    for phrase in EOD_EXPLICIT:
        if phrase in text:
            return "explicit"

    # 2순위: 묵시적 종료 (5시 이후)
    if is_pm_session():
        for phrase in EOD_IMPLICIT:
            if phrase in text:
                return "implicit"

    return None


def write_flag(trigger_type: str):
    """flag 파일 생성 (EOD 감지 마커)"""
    now = datetime.now()
    FLAG_DIR.mkdir(parents=True, exist_ok=True)
    flag = FLAG_DIR / "eod_detected.flag"
    flag.write_text(
        json.dumps({
            "trigger_type": trigger_type,
            "timestamp": now.isoformat(),
            "hour": now.hour,
            "date": now.strftime("%Y-%m-%d"),
        }, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # 세션 로그에도 기록
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    emoji = {"explicit": "🔴", "implicit": "🟡", "retro_intent": "🟢"}
    entry = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {emoji.get(trigger_type, '⚪')} EOD 감지 ({trigger_type}) — UserPromptSubmit Hook\n"
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")

    if not raw.strip():
        sys.stdout.write(raw)
        return

    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    user_prompt = (
        data.get("message", "")
        or data.get("prompt", "")
        or raw[:2000]
    )

    trigger = detect_eod(user_prompt)
    if trigger:
        write_flag(trigger)

    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
