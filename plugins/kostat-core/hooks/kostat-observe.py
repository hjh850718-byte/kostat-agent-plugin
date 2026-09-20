#!/usr/bin/env python3
"""
KOSTAT Observe - PostToolUse Hook (async)
Excel 파일 변경을 자동으로 캡처해 AGENT/docs/wiki.md에 누적합니다.
ECC observe-runner.js + continuous-learning 패턴을 Python으로 이식.
"""
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# 캡처 대상 키워드 (파일 경로에 포함되면 기록)
WATCH_KEYWORDS = [
    ".xlsx", ".xls",
    "미국오더", "hk po", "커미션", "commission", "oor",
    "invoice", "인보이스"
]

WIKI_PATH = Path(r"C:\Users\USER\Documents\Claude\AGENT\docs\wiki.md")


def should_capture(file_path: str) -> bool:
    fp_lower = file_path.lower()
    return any(kw.lower() in fp_lower for kw in WATCH_KEYWORDS)


def get_agent_label() -> str:
    """환경변수에서 호출 에이전트 이름 추출 (없으면 main)"""
    agent_id = os.environ.get("CLAUDE_AGENT_ID", "")
    if agent_id:
        # agent_id에서 kostat- 접두사 이름 추출
        parts = agent_id.split("-")
        if len(parts) >= 3:
            return f"[{'-'.join(parts[1:])}]"
    return "[main]"


def append_to_wiki(file_name: str, tool_name: str) -> None:
    WIKI_PATH.parent.mkdir(parents=True, exist_ok=True)

    today_header = datetime.now().strftime("## %Y-%m-%d")
    timestamp = datetime.now().strftime("%H:%M")
    agent = get_agent_label()
    entry = f"- [{timestamp}] {agent} `{tool_name}` → `{file_name}`\n"

    if not WIKI_PATH.exists():
        WIKI_PATH.write_text(
            f"# KOSTAT 작업 자동 로그\n\n"
            f"> PostToolUse 훅이 자동 기록. kostat-wiki-agent로 주기적 정제.\n\n"
            f"{today_header}\n{entry}",
            encoding="utf-8"
        )
        return

    content = WIKI_PATH.read_text(encoding="utf-8")

    if today_header in content:
        # 오늘 헤더 존재 → 마지막 줄에 추가
        content = content.rstrip("\n") + "\n" + entry
    else:
        # 새 날짜 헤더 추가
        content = content.rstrip("\n") + f"\n\n{today_header}\n{entry}"

    WIKI_PATH.write_text(content, encoding="utf-8")


def main():
    raw = sys.stdin.read()

    try:
        data = json.loads(raw)
    except Exception:
        sys.stdout.write(raw)
        return

    tool_name = data.get("tool_name", "")
    file_path = (data.get("tool_input") or {}).get("file_path", "")

    if tool_name in ("Write", "Edit") and file_path and should_capture(file_path):
        try:
            append_to_wiki(Path(file_path).name, tool_name)
        except Exception:
            pass  # 로그 실패해도 작업 차단 금지

    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
