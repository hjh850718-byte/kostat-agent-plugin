#!/bin/bash
# KOSTAT 장기세션 리마인더 (UserPromptSubmit 훅) — VFF reminder.sh 기반 커스터마이징
# 동작: transcript가 THRESHOLD 초과할 때 KOSTAT 검증 체크포인트를 컨텍스트에 주입.
#   조건1 (긴 세션): transcript 파일이 THRESHOLD 바이트 초과.
#   조건2: output style이 kostat-vff이거나, 세션 내 KOSTAT 스킬 마커가 존재.
# 조건 미충족 시 침묵(비용 0).

THRESHOLD=600000

input=$(cat)
tp=$(printf '%s' "$input" | sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -z "$tp" ] && exit 0
[ -f "$tp" ] || exit 0

size=$(wc -c < "$tp" 2>/dev/null | tr -d ' ')
[ "${size:-0}" -lt "$THRESHOLD" ] && exit 0

style_on=0
cwd=$(printf '%s' "$input" | sed -n 's/.*"cwd"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
for f in "$HOME/.claude/settings.json" "$cwd/.claude/settings.local.json" "$cwd/.claude/settings.json"; do
  [ -f "$f" ] && grep -qsiE '"outputStyle"[[:space:]]*:[[:space:]]*"(kostat-agent:)?kostat-vff"' "$f" && style_on=1 && break
done

# KOSTAT 스킬 실행 마커 탐지 (리터럴 및 \uXXXX 이스케이프 양쪽)
if [ "$style_on" -eq 0 ]; then
  on=$(grep -nF \
    -e 'kostat-po-update' \
    -e 'kostat-hk-po-update' \
    -e 'kostat-oor-weekly' \
    -e 'kostat-commission-invoice' \
    -e 'kostat-morning-briefing' \
    -e 'kostat-eod-retrospective' \
    "$tp" 2>/dev/null | tail -1 | cut -d: -f1)
  [ -z "$on" ] && exit 0
fi

printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"<kostat-reminder>KOSTAT 체크: 첫 문장=결론(건수·결과), PO번호·거래처코드 확인 후 처리, 환율·관세 수치는 날짜+출처 명시, 직접 확인한 것만 단정.</kostat-reminder>"}}'
exit 0
