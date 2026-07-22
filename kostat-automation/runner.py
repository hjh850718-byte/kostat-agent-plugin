#!/usr/bin/env python3
"""
KOSTAT 자동화 — 메인 실행 래퍼 (runner.py)

사용법:
  python runner.py <task_name>
  python runner.py KOSTAT_MorningBriefing

Windows Task Scheduler에서 각 루틴마다 이 파일을 호출합니다.
"""

import os
import sys
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent.resolve()
LOG_DIR     = Path(r"C:\Users\USER\Desktop\77. CLOUDE 정리용\logs")
CLAUDE_DIR  = Path(r"C:\Users\USER\Documents\Claude\AGENT")
TASK_DEF    = SCRIPT_DIR / "scheduler" / "task_definitions.json"
ENV_FILE    = SCRIPT_DIR / ".env"

# ── .env 로드 (환경변수 우선) ──────────────────────────────────────────────────
def _load_env() -> None:
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ── notifier / gate import (환경변수 로드 후) ─────────────────────────────────
sys.path.insert(0, str(SCRIPT_DIR))

import notifier.telegram_notify as tg
tg.TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", tg.TELEGRAM_BOT_TOKEN)
tg.API_BASE = f"https://api.telegram.org/bot{tg.TELEGRAM_BOT_TOKEN}"

from gates.approval_gate import check_gate

# ── 로깅 설정 ─────────────────────────────────────────────────────────────────
def _setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    today    = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"{today}.log"

    fmt = logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler    = logging.FileHandler(log_file, encoding="utf-8")
    console_handler = logging.StreamHandler(sys.stdout)
    for h in (file_handler, console_handler):
        h.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    return logging.getLogger("kostat.runner")


log = _setup_logging()


# ── 태스크 정의 로드 ──────────────────────────────────────────────────────────
def load_task(task_name: str) -> dict:
    if not TASK_DEF.exists():
        raise FileNotFoundError(f"task_definitions.json 없음: {TASK_DEF}")
    with open(TASK_DEF, encoding="utf-8") as f:
        defs = json.load(f)
    for task in defs.get("tasks", []):
        if task["name"] == task_name:
            return task
    raise ValueError(f"태스크 '{task_name}'를 task_definitions.json에서 찾을 수 없습니다.")


# ── Claude CLI 실행 ───────────────────────────────────────────────────────────
def run_claude(prompt: str, timeout_minutes: int) -> tuple[int, str, str]:
    """
    claude CLI를 subprocess로 실행합니다.

    Returns:
        (returncode, stdout, stderr)
    """
    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "-p", prompt,
    ]
    log.info(f"Claude 실행: {' '.join(cmd[:3])} \"{prompt[:80]}...\"")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_minutes * 60,
            cwd=str(CLAUDE_DIR),
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        log.error(f"Claude 타임아웃 ({timeout_minutes}분)")
        return -1, "", f"TimeoutExpired after {timeout_minutes}m"
    except FileNotFoundError:
        log.error("'claude' 명령어를 찾을 수 없습니다. npm global 설치를 확인하세요.")
        return -2, "", "claude CLI not found"


# ── 메인 실행 루프 ────────────────────────────────────────────────────────────
def run_task(task_name: str) -> bool:
    """
    태스크를 로드 → 게이트 확인 → 실행 → 알림 순서로 처리합니다.
    최대 retry_count 횟수 재시도 후 최종 결과 반환.
    """
    log.info(f"{'='*60}")
    log.info(f"태스크 시작: {task_name}")
    log.info(f"{'='*60}")

    # 1) 태스크 정의 로드
    try:
        task = load_task(task_name)
    except (FileNotFoundError, ValueError) as exc:
        log.error(str(exc))
        _safe_telegram(tg.send_message, f"❌ [KOSTAT 자동화] 태스크 로드 실패\n{task_name}\n{exc}")
        return False

    description    = task.get("description", task_name)
    prompt         = task["claude_prompt"]
    gate_type      = task.get("approval_type") if task.get("approval_gate") else None
    gate_prompt    = task.get("approval_prompt")
    gate_timeout   = task.get("approval_timeout_seconds", 60)
    gate_default   = task.get("approval_default", "Y")
    max_attempts   = task.get("retry_count", 3) + 1  # 첫 시도 + retry
    timeout_min    = task.get("timeout_minutes", 10)
    notify_start   = task.get("telegram_on_start", False)
    notify_done    = task.get("telegram_on_complete", True)

    # 2) 시작 알림 (옵션)
    if notify_start:
        _safe_telegram(tg.send_task_start, task_name, description)

    # 3) 검수 게이트
    gate_result = check_gate(
        task_name    = task_name,
        gate_type    = gate_type,
        prompt       = gate_prompt,
        timeout_sec  = gate_timeout,
        default_action = gate_default,
    )
    log.info(f"게이트 결과: {gate_result}")

    if not gate_result:
        log.info(f"게이트 거부 — 태스크 건너뜀: {task_name}")
        return False

    # 4) 실행 + 재시도
    t_start    = time.time()
    last_error = ""

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            wait = 2 ** (attempt - 1)   # 2s, 4s, 8s …
            log.info(f"재시도 대기 {wait}초… (시도 {attempt}/{max_attempts})")
            time.sleep(wait)

        log.info(f"Claude 실행 시도 {attempt}/{max_attempts}")
        rc, stdout, stderr = run_claude(prompt, timeout_min)

        if rc == 0:
            elapsed = time.time() - t_start
            log.info(f"성공 (소요: {elapsed:.1f}초)")
            log.info(f"[stdout 앞 500자]\n{stdout[:500]}")
            if notify_done:
                _safe_telegram(tg.send_task_success, task_name, stdout.strip(), elapsed)
            return True

        # 실패
        last_error = stderr.strip() or f"returncode={rc}"
        log.warning(f"시도 {attempt} 실패: {last_error[:200]}")
        if notify_done:
            _safe_telegram(tg.send_task_failure, task_name, last_error, attempt, max_attempts)

    # 최종 실패
    log.error(f"태스크 최종 실패 ({max_attempts}회 모두 실패): {task_name}")
    return False


def _safe_telegram(fn, *args, **kwargs) -> None:
    """Telegram 알림 실패가 메인 흐름을 막지 않도록 래핑."""
    try:
        fn(*args, **kwargs)
    except Exception as exc:
        log.warning(f"Telegram 알림 실패 (무시): {exc}")


# ── 진입점 ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python runner.py <task_name>")
        print("\n사용 가능한 태스크:")
        try:
            with open(TASK_DEF, encoding="utf-8") as f:
                defs = json.load(f)
            for t in defs.get("tasks", []):
                print(f"  - {t['name']:40s}  {t['description']}")
        except Exception:
            print("  (task_definitions.json을 읽을 수 없습니다)")
        sys.exit(1)

    task_name = sys.argv[1]
    success   = run_task(task_name)

    log.info(f"{'='*60}")
    log.info(f"최종 결과: {'SUCCESS' if success else 'FAILED'} — {task_name}")
    log.info(f"{'='*60}")

    sys.exit(0 if success else 1)
