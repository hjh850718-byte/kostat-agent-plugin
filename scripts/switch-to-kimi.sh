#!/bin/bash
# ============================================================
# Kimi K3 보조 백엔드로 전환 (현재 터미널 세션 한정)
# ============================================================
# 사용법 (반드시 source로 실행 — 그냥 실행하면 효과 없음):
#   source scripts/switch-to-kimi.sh
#   . scripts/switch-to-kimi.sh
#
# 되돌리기: source scripts/switch-to-claude.sh
# ============================================================

# source가 아닌 방식(./switch-to-kimi.sh)으로 실행되면 환경변수가
# 서브셸에만 적용되고 현재 세션에는 반영되지 않으므로 경고 후 종료
(return 0 2>/dev/null)
if [ $? -ne 0 ]; then
  echo "⚠️  이 스크립트는 source로 실행해야 합니다."
  echo "   사용법: source scripts/switch-to-kimi.sh"
  exit 1
fi

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env.kimi"

if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env.kimi 파일을 찾을 수 없습니다: $ENV_FILE"
  return 1
fi

# 기존 Claude API 설정을 복원할 수 있도록 백업 (최초 1회만)
if [ -z "$KOSTAT_CLAUDE_BASE_URL_BACKUP_SET" ]; then
  export KOSTAT_CLAUDE_BASE_URL_BACKUP="$ANTHROPIC_BASE_URL"
  export KOSTAT_CLAUDE_API_KEY_BACKUP="$ANTHROPIC_API_KEY"
  export KOSTAT_CLAUDE_BASE_URL_BACKUP_SET=1
fi

# .env.kimi 값을 현재 세션에만 로드 (전역 설정 파일은 건드리지 않음)
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

echo "✅ 현재 터미널 세션이 Kimi K3 백엔드로 전환되었습니다."
echo "   ANTHROPIC_BASE_URL=$ANTHROPIC_BASE_URL"
echo "   (이 세션에만 적용되며, 다른 터미널/프로덕션 작업에는 영향 없음)"
echo "   되돌리려면: source scripts/switch-to-claude.sh"
