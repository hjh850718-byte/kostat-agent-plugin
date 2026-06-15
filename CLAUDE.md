# kostat-agent-plugin — Plugin 작업 규칙

## 정체성
KOSTAT 해외영업 업무 자동화 Claude Code Plugin. 전용 스킬 11개 + Hook 스크립트 제공.

## 디렉토리 구조
@.claude/context/structure.md

## AUTOMATION 연동
@.claude/context/automation.md

## 변경 시 규칙
- skills/ 수정 후 Claude 앱 → Settings → Capabilities → 플러그인 재설치 필요
- hooks/ Python 스크립트는 Documents/Claude/claude-tray/와 동기화 유지
- package.json: semantic versioning 준수
- 주요 변경 시 docs/08. KOSTAT Plugin 패키징 설계.md 함께 업데이트

## Python 호출 규칙
- hooks.json: 항상 `python "..."` 형식 사용 (Windows 호환)
- python3 사용 금지 (Windows에서 인식 안 됨)
- shebang(`#!/usr/bin/env python3`)은 유지 가능 (Windows에서 무시됨)

## 소스 vs 설치본
| 위치 | 역할 | 편집 |
|------|------|------|
| `kostat-agent-plugin/skills/` | 소스 원본 | ✅ 직접 편집 |
| `AppData\Roaming\Claude\...\skills\` | 설치 캐시 | ❌ 재설치로만 갱신 |

## 금지 사항
- Hook 파일 수정 금지
- 기존 스킬 파일 삭제 금지
