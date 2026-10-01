#!/usr/bin/env python3
"""
KOSTAT EOD SessionStart Hook (신규)
오후 6시 이후 세션 시작 시 pending_retro flag 확인.
CLAUDE.md의 "재접속 후 회고 제안" 트리거를 위한 additionalContext 출력.
"""
import sys
import json
from datetime import datetime
from pathlib import Path

FLAG_DIR = Path(r"C:\Users\USER\Documents\Claude\claude-tray\.eod")
PENDING_RETRO = FLAG_DIR / "pending_retro.flag"
LOG_PATH = Path(r"C:\Users\USER\Documents\Claude\AGENT\docs\session-log.txt")


def check_pending_retro() -> bool:
    """pending_retro flag 존재 확인"""
    if PENDING_RETRO.exists():
        try:
            data = json.loads(PENDING_RETRO.read_text(encoding="utf-8"))
            return data.get("pending", False)
        except Exception:
            return False
    return False


def main():
    now = datetime.now()

    # 6시 이후 + pending_retro flag 있음 → additionalContext 출력
    if now.hour >= 18 and check_pending_retro():
        result = {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": (
                    "⚡ EOD 알림: 지난 세션이 오후 6시 이후 종료되었으나 "
                    "EOD 회고가 기록되지 않았습니다. "
                    "사용자가 '오늘 회고' 요청 시 kostat-eod-retrospective 스킬을 실행하세요."
                )
            }
        }
        print(json.dumps(result, ensure_ascii=False))
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 🔔 pending_retro 감지 — SessionStart additionalContext 전달\n"
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass
    else:
        # 기본: stdin→stdout 패스스루
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        sys.stdout.write(raw)


if __name__ == "__main__":
    main()
