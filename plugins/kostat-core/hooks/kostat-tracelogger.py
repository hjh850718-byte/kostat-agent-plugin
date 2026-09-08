#!/usr/bin/env python3
"""
KOSTAT TraceLogger - PostToolUse Hook
파일 생성/수정/삭제 작업을 JSON Lines 형식으로 로깅.
로컬 → 추후 Notion DB 자동 기록으로 업그레이드.
"""
import json, sys, os, hashlib
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(r"C:\Users\USER\Desktop\77. CLOUDE 정리용\trace")
EXCEL_EXT = (".xlsx", ".xls")
WATCH_KEYWORDS = [".xlsx", ".xls", ".pdf", ".md", "미국오더", "oor", "커미션", "commission", "kpt"]

def get_session_id() -> str:
    for env_var in ("CLAUDE_SESSION_ID", "CLAUDE_TRANSCRIPT_PATH"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return hashlib.sha256(val.encode("utf-8", errors="replace")).hexdigest()[:8]
    return "unknown"

def detect_skill(file_path: str, tool_input: dict) -> str:
    """파일 경로와 입력으로 스킬 추정"""
    fp = file_path.lower()
    ti = json.dumps(tool_input).lower()
    if "oor" in fp or "bring forward" in ti:
        return "kostat-oor-weekly"
    if "hk" in fp or "amkor" in fp or "po-" in fp:
        return "kostat-hk-po-update"
    if "commission" in fp or "커미션" in fp or "invoice" in fp:
        return "kostat-commission-invoice"
    if "kpt" in fp or "회고" in ti:
        return "kostat-eod-retrospective"
    if ".pdf" in fp and ("po" in fp or any(c.isdigit() for c in file_path)):
        return "kostat-po-update"
    if ".xlsx" in fp and "미국오더" in fp:
        return "kostat-po-update"
    return "unknown"

def should_capture(file_path: str) -> bool:
    fp_lower = file_path.lower()
    return any(kw.lower() in fp_lower for kw in WATCH_KEYWORDS)

def main():
    raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
    try:
        data = json.loads(raw)
    except Exception:
        sys.stdout.write(raw)
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if tool_name not in ("Write", "Edit") or not file_path:
        sys.stdout.write(raw)
        return

    if not should_capture(file_path):
        sys.stdout.write(raw)
        return

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = LOG_DIR / "trace.jsonl"

        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "tool": tool_name,
            "skill": detect_skill(file_path, tool_input),
            "file": str(file_path),
            "file_name": Path(file_path).name,
            "session": get_session_id(),
            "status": "logged"
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    except Exception as e:
        sys.stderr.write(f"[TraceLogger] ⚠️ {e}\n")

    sys.stdout.write(raw)

if __name__ == "__main__":
    main()
