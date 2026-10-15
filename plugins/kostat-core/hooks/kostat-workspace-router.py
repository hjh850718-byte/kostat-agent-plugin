#!/usr/bin/env python3
"""
KOSTAT Workspace Router - UserPromptSubmit Hook

사용자 프롬프트를 분석해 적합한 작업공간(workspace)과 Skill을 추천합니다.
CLAUDE.md의 라우팅맵과 연동하여 Claude가 올바른 컨텍스트로 작업을 시작하도록 유도합니다.

동작:
  1. 프롬프트 키워드 분석 → 라우팅맵 매칭
  2. 매칭된 workspace + 관련 Skill을 stderr로 안내
  3. 세션 내 최초 1회만 안내 (반복 방지)
  4. 이전 세션 요약이 있으면 함께 제공

설치: settings.json UserPromptSubmit 에 아래 형식으로 추가
  {
    "type": "command",
    "command": "python \"...\\kostat-workspace-router.py\"",
    "timeout": 5
  }
"""
import json
import sys
import os
import hashlib
import re
from pathlib import Path
from datetime import datetime

# =====================================================================
# Configuration
# =====================================================================

STATE_DIR = Path(os.environ.get("TEMP", str(Path.home() / "AppData" / "Local" / "Temp"))) / ".kostat-router"

# 라우팅맵 — CLAUDE.md 와 동기화
# (score, workspace_name, context, skills)
ROUTING_TABLE = [
    {
        "workspace": "KOSTAT-AGENT",
        "label": "📊 KOSTAT 해외영업",
        "emoji": "📊",
        "keywords": [
            "po", "oor", "커미션", "인보이스", "commission", "invoice",
            "hynix", "micron", "amkor", "kostat", "해외영업",
            "backlog", "오더", "order", "eod", "회고", "kpt",
            "업무끝", "retrospective", "커미션 인보이스",
            "미국오더", "us order", "atp", "실적", "분석 리포트",
            "bring forward", "working capital",
        ],
        "skills": [
            ("kostat-po-update", "PO PDF → Excel 자동 입력"),
            ("kostat-commission-invoice", "커미션 인보이스 생성/검증"),
            ("kostat-eod-retrospective", "EOD KPT 회고록 자동 생성"),
            ("kostat-hk-po-update", "HK Amkor PO PDF → Excel 입력"),
            ("kostat-oor-weekly", "OOR 주간 분석"),
            ("kostat-tal", "TAL 관련 업무"),
            ("kostat-hr", "PO 번호 단위 영업이익 계산"),
        ],
        "context": "KOSTAT 해외영업 전용 작업공간입니다. 전용 Skill을 우선 사용하세요.",
    },
    {
        "workspace": "AGENT",
        "label": "⚙️ Agent 개발",
        "emoji": "⚙️",
        "keywords": [
            "mcp", "agent", "에이전트", "hook", "스킬", "skill",
            "claude code", "settings", "자동화", "automation",
            "서브에이전트", "sub-agent", "workflow",
        ],
        "skills": [
            ("claude-md-improver", "CLAUDE.md 품질 감사 및 최적화"),
        ],
        "context": "Claude Code 에이전트/MCP/자동화 개발 작업공간입니다.",
    },
    {
        "workspace": "pm-product-discovery",
        "label": "🔍 Product Discovery",
        "emoji": "🔍",
        "keywords": [
            "리서치", "research", "페르소나", "persona", "경쟁사",
            "competitive", "문제 정의", "기회", "opportunity",
            "고객", "customer", "usability", "사용성",
        ],
        "skills": [],
        "context": "제품 발견 단계입니다. 사용자 리서치와 문제 정의에 집중하세요.",
    },
    {
        "workspace": "pm-execution",
        "label": "📋 PM Execution",
        "emoji": "📋",
        "keywords": [
            "prd", "로드맵", "roadmap", "백로그", "backlog", "스프린트",
            "sprint", "유저 스토리", "user story", "보고", "report",
            "일정", "schedule", "마일스톤", "milestone",
        ],
        "skills": [],
        "context": "PM 실행 단계입니다. PRD/로드맵/스프린트 관리에 집중하세요.",
    },
    {
        "workspace": "pm-marketing-growth",
        "label": "📈 Marketing & Growth",
        "emoji": "📈",
        "keywords": [
            "gtm", "런치", "launch", "마케팅", "marketing", "a/b test",
            "캠페인", "campaign", "성장", "growth", "전환", "conversion",
        ],
        "skills": [],
        "context": "GTM/마케팅/성장 단계입니다. 런치 전략과 마케팅 캠페인에 집중하세요.",
    },
]

# =====================================================================
# Session state (중복 안내 방지)
# =====================================================================

def get_session_key() -> str:
    """세션별 고유 키 — 동일 세션 내에서는 일관된 값 반환"""
    for env_var in ("CLAUDE_SESSION_ID", "CLAUDE_TRANSCRIPT_PATH"):
        val = os.environ.get(env_var, "").strip()
        if val:
            return hashlib.sha256(val.encode("utf-8", errors="replace")).hexdigest()[:16]
    # 환경변수가 없으면 고정 키 사용 (세션 내 모든 호출이 동일 파일 공유)
    return "default"


STATE_FILE = STATE_DIR / "router-state.json"
# 최근 안내 타임스탬프 (같은 workspace 재안내 방지)
GUIDANCE_COOLDOWN_S = 180  # 3분


def read_state() -> dict:
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"guided": {}, "last_cleanup": 0}


def write_state(state: dict):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=True), encoding="utf-8")
    except Exception:
        pass


def is_on_cooldown(workspace: str) -> bool:
    """같은 workspace 안내를 cooldown 시간 내에 이미 했는지 확인"""
    import time
    now = time.time()
    state = read_state()
    last = state.get("guided", {}).get(workspace, 0)
    return (now - last) < GUIDANCE_COOLDOWN_S


def mark_guided(workspace: str):
    """안내 시각 기록"""
    import time
    state = read_state()
    state.setdefault("guided", {})
    state["guided"][workspace] = time.time()

    # 주기적 cleanup (24시간 지난 항목 제거)
    now = time.time()
    if now - state.get("last_cleanup", 0) > 86400:
        state["guided"] = {k: v for k, v in state["guided"].items() if now - v < 86400}
        state["last_cleanup"] = now

    write_state(state)


# =====================================================================
# Prompt Analysis
# =====================================================================

STOP_WORDS = {
    "the", "a", "an", "this", "that", "is", "are", "was", "were",
    "to", "for", "of", "in", "on", "at", "with", "by", "and", "or",
    "it", "its", "my", "your", "please", "can", "could", "will",
    "would", "should", "may", "might", "do", "does", "did", "has",
    "have", "had", "not", "no", "but", "so", "if", "as", "from",
    "있습니다", "합니다", "하다", "있는", "그리고", "위해",
    "수", "있게", "대한", "통해", "통한",
}

def extract_keywords(prompt: str, max_keywords: int = 8) -> list:
    """프롬프트에서 의미 있는 키워드 추출"""
    # 한글/영문 분리
    korean = re.findall(r'[가-힣]{2,}', prompt)
    english = re.findall(r'[a-zA-Z][a-zA-Z0-9._-]+', prompt)

    keywords = []

    # 한글 키워드 (2글자 이상, 불용어 제외)
    for kw in korean:
        if kw.lower() not in STOP_WORDS:
            keywords.append(kw)

    # 영문 키워드 (불용어 제외, 소문자화)
    for kw in english:
        lower = kw.lower()
        if lower not in STOP_WORDS and len(kw) > 1:
            keywords.append(lower)

    return keywords[:max_keywords]


def match_routing(prompt: str) -> list:
    """프롬프트 → 라우팅맵 매칭 (점수순 정렬)"""
    prompt_lower = prompt.lower()
    matches = []

    for entry in ROUTING_TABLE:
        score = 0
        matched_kw = []
        for kw in entry["keywords"]:
            if kw.lower() in prompt_lower:
                score += 1
                matched_kw.append(kw)

        if score > 0:
            matches.append({
                "workspace": entry["workspace"],
                "label": entry["label"],
                "emoji": entry["emoji"],
                "score": score,
                "matched_keywords": matched_kw,
                "skills": entry["skills"],
                "context": entry["context"],
            })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches


def format_guidance(matches: list, keywords: list, compact_context: str = "") -> str:
    """매칭 결과 → stderr 안내 메시지"""
    if not matches:
        return ""

    top = matches[0]
    lines = []
    lines.append("")
    lines.append("=" * 54)
    lines.append(f"  {top['emoji']} Workspace Router: {top['label']}")
    lines.append("=" * 54)
    lines.append(f"  인식 키워드: {', '.join(keywords[:5])}")
    if top["matched_keywords"]:
        kw_display = [k for k in top["matched_keywords"] if k not in ("", " ")]
        if kw_display:
            lines.append(f"  매칭: {', '.join(kw_display[:6])}")
    lines.append(f"  → {top['context']}")

    if top["skills"]:
        lines.append("")
        lines.append("  사용 가능한 Skill:")
        for skill_name, skill_desc in top["skills"]:
            lines.append(f"   • /{skill_name} — {skill_desc}")

    if len(matches) > 1:
        lines.append("")
        others = [f"{m['emoji']} {m['workspace']}" for m in matches[1:3]]
        lines.append(f"  유사 매칭: {', '.join(others)}")

    if compact_context:
        lines.append("")
        lines.append(f"  📋 이전 세션:")
        # compact context가 너무 길면 자르기
        ctx = compact_context.strip()
        if len(ctx) > 300:
            ctx = ctx[:300] + "..."
        for line in ctx.split("\n"):
            line = line.strip()
            if line:
                lines.append(f"    {line}")

    lines.append("")
    lines.append("=" * 54)
    lines.append("")

    return "\n".join(lines)


def try_inject_compact_context() -> str:
    """이전 세션 compact 요약이 있으면 주입"""
    # 일반적인 compact 요약 파일 위치들
    candidate_dirs = [
        Path(os.environ.get("CLAUDE_COMPACT_DIR", "")),
        Path.home() / ".claude" / "compact",
        Path(os.environ.get("TEMP", "")) / ".claude-compact",
    ]

    for d in candidate_dirs:
        if not d.exists():
            continue
        try:
            summaries = sorted(d.glob("*summary*"), key=lambda p: p.stat().st_mtime, reverse=True)
            if summaries:
                content = summaries[0].read_text(encoding="utf-8", errors="replace").strip()
                if content and len(content) < 2000:
                    return content
        except Exception:
            continue

    return ""


# =====================================================================
# Main
# =====================================================================

def main():
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")

    try:
        data = json.loads(raw)
    except Exception:
        # 파싱 실패 → passthrough
        sys.stdout.write(raw)
        return

    # UserPromptSubmit은 prompt 필드에 사용자 입력이 있음
    prompt = data.get("prompt", "") or data.get("text", "") or ""

    # 프롬프트가 없거나 너무 짧으면 무시
    if not prompt or len(prompt.strip()) < 5:
        sys.stdout.write(raw)
        return

    # 라우팅 매칭
    matches = match_routing(prompt)
    keywords = extract_keywords(prompt)

    if not matches:
        # 매칭 없음 → 침묵 (방해 금지)
        sys.stdout.write(raw)
        return

    top_workspace = matches[0]["workspace"]

    # 같은 workspace 최근 안내했으면 생략 (cooldown)
    if is_on_cooldown(top_workspace):
        sys.stdout.write(raw)
        return

    # 안내 문구 구성 + 이전 세션 컨텍스트
    compact_ctx = try_inject_compact_context()
    guidance = format_guidance(matches, keywords, compact_ctx)

    if guidance:
        # stderr → Claude가 볼 수 있음 (hook runner가 stderr를 Claude에 전달)
        sys.stderr.write(guidance)
        mark_guided(top_workspace)

    # passthrough (UserPromptSubmit는 stdin을 그대로 stdout으로)
    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
