#!/usr/bin/env python3
"""
KOSTAT AI-Bridge — SessionStart / Stop Hook
codexpro의 .ai-bridge/ 패턴을 KOSTAT 오케스트레이터에 적용.

.ai-bridge/ 구조:
  current-plan.md     ← 오케스트레이터가 작성하는 현재 계획
  decisions.md        ← Human Gate 승인/거부 이력
  task-status.json    ← 에이전트별 실행 상태 (JSONL 누적)
  session-context.md  ← 세션 시작 컨텍스트
  agent-handoffs/     ← 에이전트 간 핸드오프 파일 디렉토리

환경변수:
  KOSTAT_AI_BRIDGE_DIR  — .ai-bridge 기본 경로 (기본: ~/Documents/Claude/AGENT/.ai-bridge)
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

_CURRENT_PLAN_TEMPLATE = """\
# 현재 오케스트레이터 계획

**세션**: {session_id}
**날짜**: {date}

## 실행 대기 중인 트리거
_없음_

## 진행 중인 에이전트 팀
_없음_

## 완료된 작업
_없음_

---
_kostat-orchestrator 스킬이 이 파일을 업데이트합니다._
"""

_DECISIONS_TEMPLATE = """\
# 의사결정 이력

**세션**: {session_id}
**날짜**: {date}

| 시각 | 트리거 | 결정 | 근거 |
|------|--------|------|------|

---
_Human Gate 승인/거부 내역이 kostat-orchestrator에 의해 기록됩니다._
"""

_SESSION_CONTEXT_TEMPLATE = """\
# 세션 컨텍스트

**세션 ID**: {session_id}
**시작**: {start_time}
**날짜**: {date}

## 오늘의 목표
_세션 시작 시 입력 필요_

## 전달된 트리거
_없음_

## 미완료 항목
_없음_

---
_kostat-ai-bridge hook이 관리합니다._
"""


def get_session_id() -> str:
    for env_var in ("CLAUDE_SESSION_ID", "CLAUDE_TRANSCRIPT_PATH"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return hashlib.sha256(val.encode("utf-8", errors="replace")).hexdigest()[:8]
    return "unknown"


def init_bridge():
    """SessionStart: .ai-bridge/ 디렉토리 초기화"""
    session_id = get_session_id()
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    start_time = now.strftime("%Y-%m-%d %H:%M:%S")

    AI_BRIDGE_DIR.mkdir(parents=True, exist_ok=True)
    (AI_BRIDGE_DIR / "agent-handoffs").mkdir(exist_ok=True)

    # current-plan.md: 기존 계획이 있으면 덮어쓰지 않음 (오케스트레이터가 작성)
    plan_file = AI_BRIDGE_DIR / "current-plan.md"
    if not plan_file.exists():
        plan_file.write_text(
            _CURRENT_PLAN_TEMPLATE.format(session_id=session_id, date=date_str),
            encoding="utf-8",
        )

    # decisions.md: 기존 이력 보존
    decisions_file = AI_BRIDGE_DIR / "decisions.md"
    if not decisions_file.exists():
        decisions_file.write_text(
            _DECISIONS_TEMPLATE.format(session_id=session_id, date=date_str),
            encoding="utf-8",
        )

    # task-status.json: 세션마다 초기화 (이전 세션 기록은 task-status-{date}.json 으로 보존)
    status_file = AI_BRIDGE_DIR / "task-status.json"
    if status_file.exists():
        # 이전 파일을 날짜별로 보존
        try:
            old_data = json.loads(status_file.read_text(encoding="utf-8"))
            old_date = old_data.get("date", "unknown")
            if old_date != date_str:
                archive = AI_BRIDGE_DIR / f"task-status-{old_date}.json"
                if not archive.exists():
                    status_file.rename(archive)
        except Exception:
            pass

    status_data = {
        "session_id": session_id,
        "date": date_str,
        "started_at": start_time,
        "tasks": {},
        "updated_at": start_time,
    }
    status_file.write_text(
        json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # session-context.md: 매 세션 새로 작성
    context_file = AI_BRIDGE_DIR / "session-context.md"
    context_file.write_text(
        _SESSION_CONTEXT_TEMPLATE.format(
            session_id=session_id,
            start_time=start_time,
            date=date_str,
        ),
        encoding="utf-8",
    )

    sys.stderr.write(f"[AI-Bridge] .ai-bridge/ 초기화 완료 → {AI_BRIDGE_DIR}\n")


def finalize_bridge():
    """Stop: task-status.json에 세션 종료 시각 기록"""
    try:
        status_file = AI_BRIDGE_DIR / "task-status.json"
        if status_file.exists():
            status_data = json.loads(status_file.read_text(encoding="utf-8"))
            status_data["ended_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            status_file.write_text(
                json.dumps(status_data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
    except Exception as e:
        sys.stderr.write(f"[AI-Bridge] 종료 기록 실패: {e}\n")


def main():
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        data = {}

    event = data.get("hook_event_name", os.environ.get("CLAUDE_HOOK_EVENT", ""))

    try:
        if event == "SessionStart":
            init_bridge()
        elif event == "Stop":
            finalize_bridge()
    except Exception as e:
        sys.stderr.write(f"[AI-Bridge] ⚠️ {e}\n")

    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
