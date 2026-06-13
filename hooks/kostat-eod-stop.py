#!/usr/bin/env python3
"""
KOSTAT EOD Stop Hook (강화)
세션 종료 시 EOD flag 확인 + 오후 6시 이후 재접속 플래그 기록.
UserPromptSubmit Hook(kostat-eod-detector.py)가 남긴 flag를 우선 확인.
"""
import sys
import json
import os
from datetime import datetime
from pathlib import Path

FLAG_DIR = Path(r"C:\Users\USER\Documents\Claude\claude-tray\.eod")
FLAG_FILE = FLAG_DIR / "eod_detected.flag"
PENDING_RETRO = FLAG_DIR / "pending_retro.flag"  # 6시 이후 재접속 판단용
LOG_PATH = Path(r"C:\Users\USER\Documents\Claude\AGENT\docs\session-log.txt")


def check_flag() -> dict | None:
    """UserPromptSubmit Hook이 남긴 EOD flag 확인 후 정리 → flag data 반환"""
    if FLAG_FILE.exists():
        try:
            flag_data = json.loads(FLAG_FILE.read_text(encoding="utf-8"))
            return flag_data
        except Exception:
            return None
        finally:
            try:
                FLAG_FILE.unlink(missing_ok=True)
            except Exception:
                pass
    return None


def check_transcript(transcript_path: str) -> bool:
    """Fallback: transcript 스캔"""
    try:
        content = Path(transcript_path).read_text(encoding="utf-8", errors="replace")
        triggers = [
            "업무끝", "업무 끝", "퇴근", "오늘 끝", "일 끝났어", "오늘 마무리",
            "오늘 업무 끝", "마무리할게", "퇴근할게", "퇴근합니다",
        ]
        return any(t in content for t in triggers)
    except Exception:
        return False


def check_eod_done_today() -> bool:
    """오늘 이미 EOD 회고가 완료되었는지 session-log에서 확인"""
    today = datetime.now().strftime("%Y-%m-%d")
    if LOG_PATH.exists():
        try:
            content = LOG_PATH.read_text(encoding="utf-8")
            return f"EOD 감지 ({today}" in content
        except Exception:
            pass
    return False


def write_pending_retro():
    """6시 이후 세션 종료 but EOD 미감지 → pending_retro flag 기록"""
    now = datetime.now()
    if now.hour >= 18 and not check_eod_done_today():
        FLAG_DIR.mkdir(parents=True, exist_ok=True)
        PENDING_RETRO.write_text(
            json.dumps({
                "pending": True,
                "timestamp": now.isoformat(),
                "date": now.strftime("%Y-%m-%d"),
                "hour": now.hour,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        entry = f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] 🟠 6시 이후 종료 — pending_retro flag 기록\n"
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception:
            pass


def clear_pending_retro():
    """EOD 감지된 경우 pending flag 정리"""
    try:
        PENDING_RETRO.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")

    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    # 1순위: flag 파일 확인 (UserPromptSubmit Hook)
    flag_data = check_flag()
    eod = flag_data is not None

    # 2순위: transcript 스캔 (fallback)
    if not eod:
        transcript_path = (
            data.get("transcript_path")
            or os.environ.get("CLAUDE_TRANSCRIPT_PATH", "")
        )
        eod = check_transcript(transcript_path) if transcript_path else False

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

    if eod:
        clear_pending_retro()
        trigger = flag_data.get("trigger_type", "unknown") if flag_data else "transcript"
        entry = f"[{timestamp}] ✅ EOD 감지 ({trigger_type}) — 회고 대상 세션\n"
    else:
        # 6시 이후 미감지 → pending_retro 기록 (재접속 시 알림)
        write_pending_retro()
        entry = f"[{timestamp}] 세션 종료\n"

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass

    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
