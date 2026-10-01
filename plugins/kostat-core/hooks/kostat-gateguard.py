#!/usr/bin/env python3
"""
KOSTAT GateGuard - PreToolUse Hook
Excel 파일을 처음 수정하려 할 때 사전 확인을 강제합니다.
ECC gateguard-fact-force.js 패턴을 KOSTAT 업무에 맞게 이식.
"""
import json
import sys
import os
import hashlib
from pathlib import Path

EXCEL_EXT = (".xlsx", ".xls")
STATE_DIR = Path(os.environ.get("TEMP", str(Path.home() / "AppData" / "Local" / "Temp"))) / ".kostat-gateguard"


def safe_encode(s: str) -> bytes:
    """서로게이트 포함 문자열을 안전하게 바이트로 변환 (Windows 환경변수 호환)"""
    return s.encode("utf-8", errors="replace")


def get_session_key() -> str:
    """세션별 고유 키 생성 — 재시작 시 상태 초기화"""
    for env_var in ("CLAUDE_SESSION_ID", "CLAUDE_TRANSCRIPT_PATH"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return hashlib.sha256(safe_encode(val)).hexdigest()[:20]
    return hashlib.sha256(str(os.getpid()).encode()).hexdigest()[:20]


def get_state_file() -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"state-{get_session_key()}.json"


def load_checked() -> set:
    sf = get_state_file()
    try:
        if sf.exists():
            return set(json.loads(sf.read_text(encoding="utf-8")))
    except Exception:
        pass
    return set()


def mark_checked(path: str) -> bool:
    """상태 저장 — 실패 시 False 반환 (작업 차단은 호출자가 결정)"""
    try:
        sf = get_state_file()
        checked = load_checked()
        # 파일 경로를 해시로 변환해 저장 (비ASCII 인코딩 문제 방지)
        path_key = hashlib.sha256(safe_encode(path)).hexdigest()[:32]
        checked.add(path_key)
        sf.write_text(json.dumps(list(checked), ensure_ascii=True), encoding="utf-8")
        return True
    except Exception:
        return False


def is_subagent(data: dict) -> bool:
    """서브에이전트 호출 여부 — 에이전트는 자체 검증 로직이 있으므로 게이트 제외"""
    for key in ("agent_id", "agentId", "parent_tool_use_id", "parentToolUseId"):
        if data.get(key):
            return True
    return False


def deny_response(file_name: str) -> str:
    msg = (
        f"[KOSTAT 파일 접근 게이트]\n\n"
        f"{file_name} 수정 전 먼저 제시하세요:\n\n"
        f"1. 수정하려는 시트명과 현재 행 수 (Read로 확인)\n"
        f"2. 영향받는 PO# 목록 또는 신규 추가 행 내용\n"
        f"3. 중복 PO# 없음 확인 (Grep으로 검색)\n"
        f"4. 사용자 지시 원문 인용\n\n"
        f"위 내용 제시 후 재시도.\n"
        f"(우회: 세션에서 KOSTAT_GATE=off 환경변수 설정)"
    )
    return json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": msg
        }
    }, ensure_ascii=False)


def main():
    # Windows에서 비UTF-8 바이트 포함 환경 대응 — buffer로 읽고 명시적 디코딩
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")

    # 게이트 비활성화 옵션
    if os.environ.get("KOSTAT_GATE", "").lower() in ("off", "0", "false", "disable"):
        sys.stdout.write(raw)
        return

    try:
        data = json.loads(raw)
    except Exception:
        sys.stdout.write(raw)
        return

    tool_name = data.get("tool_name", "")
    file_path = (data.get("tool_input") or {}).get("file_path", "")

    # Excel 파일 + Write/Edit 만 게이트
    if tool_name not in ("Write", "Edit") or not file_path:
        sys.stdout.write(raw)
        return

    if not file_path.lower().endswith(EXCEL_EXT):
        sys.stdout.write(raw)
        return

    # 서브에이전트는 자체 검증 로직 있음 → 통과
    if is_subagent(data):
        sys.stdout.write(raw)
        return

    # 해시 기반 비교 (비ASCII 경로 인코딩 문제 방지)
    path_key = hashlib.sha256(safe_encode(file_path)).hexdigest()[:32]
    checked = load_checked()
    if path_key in checked:
        # 이미 확인 완료 → 통과
        sys.stdout.write(raw)
        return

    # 첫 접근: 차단 (상태 저장 성공 시 다음 시도는 통과)
    saved = mark_checked(file_path)
    if not saved:
        # 상태 저장 실패 → 경고만 출력하고 통과 (무한 차단 방지)
        sys.stderr.write("[KOSTAT GateGuard] 상태 저장 실패 — 이번 한 번 통과 허용\n")
        sys.stdout.write(raw)
        return
    sys.stdout.write(deny_response(Path(file_path).name))


if __name__ == "__main__":
    main()
