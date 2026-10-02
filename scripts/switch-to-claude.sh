#!/bin/bash
# ============================================================
# 기존 Claude API 백엔드로 되돌리기 (현재 터미널 세션 한정)
# ============================================================
# 사용법 (반드시 source로 실행 — 그냥 실행하면 효과 없음):
#   source scripts/switch-to-claude.sh
#   . scripts/switch-to-claude.sh
# ============================================================

(return 0 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "⚠️  이 스크립트는 source로 실행해야 합니다."
  echo "   사용법: source scripts/switch-to-claude.sh"
  exit 1
fi

if [ -z "$KOSTAT_CLAUDE_BASE_URL_BACKUP_SET" ]; then
  # switch-to-kimi.sh를 먼저 실행한 적이 없는 경우: Kimi 관련 변수만 정리
  unset ANTHROPIC_BASE_URL
  unset ANTHROPIC_API_KEY
  echo "ℹ️  전환 이력이 없어 ANTHROPIC_BASE_URL/ANTHROPIC_API_KEY를 초기화했습니다."
  echo "   (기존 Claude API 기본 설정을 그대로 사용합니다)"
  return 0 2>/dev/null || exit 0
fi

# switch-to-kimi.sh 실행 전 값으로 복원
if [ -n "$KOSTAT_CLAUDE_BASE_URL_BACKUP" ]; then
  export ANTHROPIC_BASE_URL="$KOSTAT_CLAUDE_BASE_URL_BACKUP"
else
  unset ANTHROPIC_BASE_URL
fi

if [ -n "$KOSTAT_CLAUDE_API_KEY_BACKUP" ]; then
  export ANTHROPIC_API_KEY="$KOSTAT_CLAUDE_API_KEY_BACKUP"
else
  unset ANTHROPIC_API_KEY
fi

unset KOSTAT_CLAUDE_BASE_URL_BACKUP
unset KOSTAT_CLAUDE_API_KEY_BACKUP
unset KOSTAT_CLAUDE_BASE_URL_BACKUP_SET

echo "✅ 현재 터미널 세션이 기존 Claude API 백엔드로 복원되었습니다."
echo "   (이 세션에만 적용됨)"
