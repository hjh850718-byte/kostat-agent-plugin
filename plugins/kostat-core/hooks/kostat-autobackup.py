#!/usr/bin/env python3
"""
KOSTAT AutoBackup - PreToolUse Hook
Excel 파일 Write/Edit 전 자동 백업 생성.
원본과 동일한 디렉토리에 _backup_YYYYMMDD 접미사 추가.
"""
import json, sys, os, shutil, hashlib
from datetime import datetime
from pathlib import Path

EXCEL_EXT = (".xlsx", ".xls")
BACKUP_DIR = Path(os.environ.get("TEMP", "")) / ".kostat-backups"

def get_session_key() -> str:
    for env_var in ("CLAUDE_SESSION_ID", "CLAUDE_TRANSCRIPT_PATH"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return hashlib.sha256(val.encode("utf-8", errors="replace")).hexdigest()[:12]
    return "default"

def main():
    raw = sys.stdin.buffer.read().decode("utf-8-sig", errors="replace")
    try:
        data = json.loads(raw)
    except Exception:
        sys.stdout.write(raw)
        return

    tool_name = data.get("tool_name", "")
    file_path = (data.get("tool_input") or {}).get("file_path", "")

    if tool_name not in ("Write", "Edit") or not file_path:
        sys.stdout.write(raw)
        return

    if not file_path.lower().endswith(EXCEL_EXT):
        sys.stdout.write(raw)
        return

    src = Path(file_path)
    if not src.exists():
        sys.stdout.write(raw)
        return

    try:
        date_str = datetime.now().strftime("%Y%m%d")
        session = get_session_key()

        # 로컬 TEMP에 백업 (원본 디렉토리 쓰레기 방지)
        backup_dir = BACKUP_DIR / f"{session}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_name = f"{src.stem}_backup_{date_str}{src.suffix}"
        backup_path = backup_dir / backup_name

        if not backup_path.exists():
            shutil.copy2(src, backup_path)
            sys.stderr.write(f"[AutoBackup] ✅ → {backup_path}\n")
        else:
            sys.stderr.write(f"[AutoBackup] ⏭ 이미 존재: {backup_path}\n")
    except Exception as e:
        sys.stderr.write(f"[AutoBackup] ⚠️ 실패: {e}\n")

    sys.stdout.write(raw)

if __name__ == "__main__":
    main()
