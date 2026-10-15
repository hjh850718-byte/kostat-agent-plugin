#!/usr/bin/env bash
# references/output-contract.md(원본)를 이를 인용하는 각 스킬의 references/ 로 복사한다.
# 플러그인은 개별 설치되므로 스킬 폴더 안에 사본이 있어야 한다.
# 사용: scripts/sync-output-contract.sh [--check]
set -euo pipefail
cd "$(dirname "$0")/.."
src=references/output-contract.md
rc=0
for skill in $(grep -rl 'references/output-contract.md' plugins --include=SKILL.md); do
  dest="$(dirname "$skill")/references/output-contract.md"
  if [ "${1:-}" = "--check" ]; then
    cmp -s "$src" "$dest" || { echo "DIFF: $dest"; rc=1; }
  else
    mkdir -p "$(dirname "$dest")"; cp "$src" "$dest"; echo "synced: $dest"
  fi
done
exit $rc
