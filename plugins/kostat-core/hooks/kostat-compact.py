#!/usr/bin/env python3
"""
KOSTAT PreCompact Hook
/compact 실행 직전 상태를 AGENT/docs/compaction-log.txt에 저장합니다.
ECC pre-compact.js 패턴을 Python으로 이식.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

LOG_PATH = Path(r"C:\Users\USER\Documents\Claude\AGENT\docs\compaction-log.txt")


def main():
    raw = sys.stdin.read()

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # stdin에서 현재 작업 중인 파일 정보 추출 시도
    working_note = ""
    try:
        data = json.loads(raw) if raw.strip() else {}
        # 필요 시 data에서 추가 컨텍스트 추출 가능
    except Exception:
        data = {}

    entry = f"[{timestamp}] /compact 발생 — 컨텍스트 압축 전 상태 저장{working_note}\n"

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass  # 로그 실패해도 compact는 계속 진행

    # passthrough (PreCompact는 수정 없이 원본 반환)
    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
