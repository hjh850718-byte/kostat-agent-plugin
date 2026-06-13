#!/bin/bash
# ============================================================
# KOSTAT 에이전트팀 멀티탭 실행 (tmux)
# 레벨 7 Orchestrator 기반 병렬 에이전트 시스템
# ============================================================
# 사용법:
#   chmod +x kostat-team.sh
#   ./kostat-team.sh
# ============================================================
# REQUIREMENTS: tmux, claude (Claude Code CLI)
# ============================================================

# 세션명
SESSION="kostat"

echo "🚀 KOSTAT Agent Team starting..."
echo "   Session: ${SESSION}"
echo "   Windows: orchestrator | po-agent | oor-agent | validator"
echo ""

# 기존 세션 종료
tmux kill-session -t ${SESSION} 2>/dev/null

# ── Orchestrator Window ──────────────────────────────────────
tmux new-session -d -s ${SESSION} -n orchestrator
tmux send-keys -t ${SESSION}:orchestrator 'echo "=== KOSTAT Orchestrator (Level 7) ==="' Enter
tmux send-keys -t ${SESSION}:orchestrator 'echo "트리거 감지 → 에이전트팀 소집 → 결과 취합"' Enter
tmux send-keys -t ${SESSION}:orchestrator 'claude --dangerously-skip-permissions' Enter
sleep 1

# ── PO Agent Window ──────────────────────────────────────────
tmux new-window -t ${SESSION} -n po-agent
tmux send-keys -t ${SESSION}:po-agent 'echo "=== PO Agent (kostat-po-update) ==="' Enter
tmux send-keys -t ${SESSION}:po-agent 'echo "PO PDF → Excel 입력 + 요약 + Calendar"' Enter
tmux send-keys -t ${SESSION}:po-agent 'claude --dangerously-skip-permissions' Enter
sleep 1

# ── OOR Agent Window ─────────────────────────────────────────
tmux new-window -t ${SESSION} -n oor-agent
tmux send-keys -t ${SESSION}:oor-agent 'echo "=== OOR Agent (kostat-oor-weekly) ==="' Enter
tmux send-keys -t ${SESSION}:oor-agent 'echo "Bring Forward 분석 + PO# 검증 리포트"' Enter
tmux send-keys -t ${SESSION}:oor-agent 'claude --dangerously-skip-permissions' Enter
sleep 1

# ── Validator Window ─────────────────────────────────────────
tmux new-window -t ${SESSION} -n validator
tmux send-keys -t ${SESSION}:validator 'echo "=== Validator Agent ==="' Enter
tmux send-keys -t ${SESSION}:validator 'echo "PO# 불일치 검증 | 데이터 무결성 체크 | 교차 검증"' Enter
tmux send-keys -t ${SESSION}:validator 'claude --dangerously-skip-permissions' Enter
sleep 1

# ── Attach ───────────────────────────────────────────────────
echo "✅ KOSTAT Agent Team is ready!"
echo "   - orchestrator: 트리거 감지 및 팀 소집"
echo "   - po-agent:     PO PDF 파싱 → Excel 업데이트"
echo "   - oor-agent:    OOR Bring Forward 분석"
echo "   - validator:    PO# 불일치 및 데이터 검증"
echo ""
echo "🔄 Attaching to tmux session..."
echo "   (Ctrl+B d 로 detach, Ctrl+B w 로 window 전환)"
echo ""

tmux attach -t ${SESSION}
