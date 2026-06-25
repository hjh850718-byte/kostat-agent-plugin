#!/usr/bin/env python3
"""
KOSTAT Handoff Writer — PostToolUse Hook
codexpro의 handoff 패턴을 KOSTAT 에이전트 간 상태 전달에 적용.

역할:
  에이전트(스킬)가 파일을 완성(Write)할 때 .ai-bridge/agent-handoffs/ 에
  핸드오프 요약 파일을 자동 생성한다.
  → 다음 에이전트가 이 파일을 읽어 이전 작업 결과를 파악한다.
  → EOD 회고 스킬은 오늘의 handoff 파일을 모아 회고를 작성한다.

감지 대상 파일:
  .xlsx/.xls  → PO/OOR/Commission 스킬 완료 신호
  *kpt*.md    → EOD 회고 완료 신호
  *oor*.xlsx  → OOR 분석 완료 신호
  *invoice*.* → 커미션 인보이스 완료 신호

환경변수:
  KOSTAT_AI_BRIDGE_DIR  — .ai-bridge 기본 경로 (기본: ~/Documents/Claude/AGENT/.ai-bridge)
  KOSTAT_HANDOFF=off    — 핸드오프 기록 비활성화
"""
import json
import sys
import os
import hashlib
from datetime import datetime
from pathlib import Path

AI_BRIDGE_DIR = Path(
    os.environ.get(
        "KOSTAT_AI_BRIDGE_DIR",
        str(Path.home() / "Documents" / "Claude" / "AGENT" / ".ai-bridge"),
    )
)
HANDOFF_DIR = AI_BRIDGE_DIR / "agent-handoffs"

# 스킬별 감지 규칙 (file_path 패턴 → skill 이름)
_SKILL_PATTERNS: list[tuple[list[str], str]] = [
    (["kpt", "회고", "retrospective"], "kostat-eod-retrospective"),
    (["commission", "커미션", "invoice", "인보이스"], "kostat-commission-invoice"),
    (["oor", "bring forward", "open order"], "kostat-oor-weekly"),
    (["hk", "amkor", "hk-po"], "kostat-hk-po-update"),
    (["미국오더", "us order", "po-"], "kostat-po-update"),
]

# 핸드오프 파일 생성 대상 확장자
_WATCH_EXTENSIONS = (".xlsx", ".xls", ".pdf", ".md")


def detect_skill(file_path: str) -> str | None:
    fp = file_path.lower()
    for patterns, skill in _SKILL_PATTERNS:
        if any(p in fp for p in patterns):
            return skill
    # 일반 Excel/PDF 작업 → po-update로 fallback
    if fp.endswith((".xlsx", ".xls", ".pdf")):
        return "kostat-po-update"
    return None


def get_session_id() -> str:
    for env_var in ("CLAUDE_SESSION_ID", "CLAUDE_TRANSCRIPT_PATH"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return hashlib.sha256(val.encode("utf-8", errors="replace")).hexdigest()[:8]
    return "unknown"


def _write_handoff_md(skill: str, file_path: str, file_name: str, timestamp: str):
    """핸드오프 Markdown 파일 작성 (codexpro current-plan.md 패턴)"""
    HANDOFF_DIR.mkdir(parents=True, exist_ok=True)
    date_str = timestamp[:10]
    handoff_file = HANDOFF_DIR / f"{skill}-{date_str}.md"

    # 기존 파일이 있으면 항목 추가, 없으면 신규 생성
    if handoff_file.exists():
        existing = handoff_file.read_text(encoding="utf-8")
        new_entry = f"| {timestamp[11:]} | {file_name} | `{file_path}` |\n"
        handoff_file.write_text(existing + new_entry, encoding="utf-8")
    else:
        content = f"""\
# Handoff: {skill}

**날짜**: {date_str}
**세션**: {get_session_id()}

## 완료된 파일 목록

| 시각 | 파일명 | 경로 |
|------|--------|------|
| {timestamp[11:]} | {file_name} | `{file_path}` |

## 다음 에이전트에게

이 핸드오프 파일을 읽고 위 목록의 파일을 검토한 후 작업을 이어받으세요.

---
_kostat-handoff-writer hook이 자동 생성합니다._
"""
        handoff_file.write_text(content, encoding="utf-8")


def _update_task_status(skill: str, file_name: str, timestamp: str):
    """task-status.json 에 완료 기록 추가"""
    status_file = AI_BRIDGE_DIR / "task-status.json"
    if not status_file.exists():
        return
    try:
        status_data = json.loads(status_file.read_text(encoding="utf-8"))
        task_key = f"{skill}:{file_name}"
        status_data["tasks"][task_key] = {
            "skill": skill,
            "file": file_name,
            "status": "completed",
            "timestamp": timestamp,
        }
        status_data["updated_at"] = timestamp
        status_file.write_text(
            json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        sys.stderr.write(f"[Handoff] task-status 업데이트 실패: {e}\n")


def main():
    if os.environ.get("KOSTAT_HANDOFF", "").lower() in ("off", "0", "false", "disable"):
        raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        sys.stdout.write(raw)
        return

    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except Exception:
        sys.stdout.write(raw)
        return

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # Write 작업 + 대상 확장자만 처리
    if tool_name != "Write" or not file_path:
        sys.stdout.write(raw)
        return

    if not any(file_path.lower().endswith(ext) for ext in _WATCH_EXTENSIONS):
        sys.stdout.write(raw)
        return

    skill = detect_skill(file_path)
    if not skill:
        sys.stdout.write(raw)
        return

    file_name = Path(file_path).name
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        _write_handoff_md(skill, file_path, file_name, timestamp)
        _update_task_status(skill, file_name, timestamp)
        sys.stderr.write(f"[Handoff] {skill} → {file_name} 핸드오프 기록\n")
    except Exception as e:
        sys.stderr.write(f"[Handoff] ⚠️ {e}\n")

    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
