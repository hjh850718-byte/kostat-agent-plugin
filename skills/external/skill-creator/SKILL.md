---
name: skill-creator
description: KOSTAT 스킬 생성/개선/eval 실행 전담. "스킬 만들어", "eval 추가", "스킬 개선", "테스트 케이스", "벤치마크" 요청 시 사용.
---

# Skill Creator (KOSTAT 커스텀)

## 목적
기존 kostat-* 스킬들의 품질을 평가하고 개선하는 메타 스킬.
새 스킬 초안 작성 → eval 케이스 생성 → 반복 개선 루프를 실행한다.

## KOSTAT 스킬 목록 (eval 대상)
- kostat-po-update: PO PDF → Excel 자동 입력
- kostat-hk-po-update: HK PO PDF → Excel 자동 입력
- kostat-oor-weekly: OOR xlsx 컬러코딩 + 불일치 표기
- kostat-commission-invoice: RAW DATA → 커미션 인보이스 생성
- kostat-eod-retrospective: 업무끝 → KPT 회고 → Notion 저장
- kostat-morning-briefing: /morning → Google Calendar + PO 브리핑
- kostat-memory-loader: 세션 초기화 시 컨텍스트 주입

## eval 실행 프로세스
1. 대상 스킬 선택
2. 테스트 케이스 3~5개 작성 (입력 예시 + 기대 출력)
3. Claude Code로 각 케이스 실행 후 결과 비교
4. 실패 패턴 → SKILL.md 개선안 작성
5. 개선 후 재실행으로 검증

## 출력 형식
- 배경 → 현황 → 실패 패턴 → 개선안 표 형태로 보고
- 개선된 SKILL.md는 원본 경로에 덮어쓰기 전 diff 먼저 제시

## 트리거 키워드
"스킬 eval", "스킬 테스트", "스킬 개선", "벤치마크 실행", "kostat 스킬 점검"
