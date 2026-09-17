---
name: kostat-architecture-diagram
description: "Archify(tt-a1i, MIT) 설치/점검 안내 및 kostat-agent-plugin 구조도 생성 가이드. 트리거: '구조도 그려줘', '아키파이', 'archify'."
---

# kostat-architecture-diagram

## 정체성
[Archify](https://github.com/tt-a1i/archify)는 **tt-a1i의 오픈소스(MIT)** 스킬로,
저장소나 평범한 설명을 인터랙티브 HTML 구조도 한 장으로 그려줍니다.
KOSTAT이 만든 것이 아니며 제휴 관계도 없습니다 — 이 스킬은 설치/점검 절차를
KOSTAT 작업 흐름에 맞게 안내하는 **가이드**일 뿐, Archify 본체를 대신 설치하지 않습니다.

실제 `npx` 설치 명령은 **사용자가 로컬 PC의 터미널 또는 로컬 Claude Code에서 직접 실행**해야
합니다 (전역 `~/.claude/skills`에 설치되므로, 원격/샌드박스 세션에는 의미가 없습니다).

## 트리거
- "구조도 그려줘", "아키파이로 그려줘", "archify 설치해줘"
- "kostat-agent-plugin 구조를 그림으로 보여줘"
- "시퀀스 다이어그램 그려줘", "데이터 흐름 그려줘" 등 5종 다이어그램 요청

## 그릴 수 있는 5종
| 종류 | 용도 |
|------|------|
| architecture | 구성요소·서비스·인프라 경계 (예: AUTOMATION Level 7 시스템 전체) |
| workflow | 업무 흐름·승인 관문·Fan-out 절차 (예: kostat-po-update 3way Fan-out) |
| sequence | API/Hook 호출 순서 (예: kostat_poller → orchestrator_bridge → Skill 실행) |
| dataflow | 데이터 파이프라인 (예: POP3 메일 → trigger_classifier → Excel 반영) |
| lifecycle | 상태 전이 (예: 스킬 candidate→trial→promoted→deprecated) |

## 사전 점검 (설치 전 필수)
```bash
npx --yes reborn-archify --check
```
아래 5칸을 실측합니다. 못 잰 항목은 "없다"가 아니라 "못 쟀다"로 구분해서 보고하세요.
1. Node 18+ 여부
2. Claude Code 설치 여부 (`claude --version`)
3. **Claude Code 스킬 자리** (`~/.claude/skills` 또는 `CLAUDE_CONFIG_DIR/skills`) — 가장 자주 막히는 지점
4. 엉뚱한 자리(`~/.agents/skills`)에만 들어가 있는지 여부
5. 렌더러 정상 동작 (`bin/archify.mjs doctor` → "Archify is ready.")

## 설치 (사용자 로컬에서 1회)
```bash
npx -y skills add tt-a1i/archify -g -y --agent claude-code --skill archify --copy
```
- `--agent claude-code`를 반드시 붙여야 Claude Code가 읽는 자리에 들어갑니다.
- 설치 후 "Installed 1 skill · Done!" 메시지를 믿지 말고, 실제로 `~/.claude/skills/archify/SKILL.md` 존재 여부를 다시 확인하세요.
- 설치 후 Claude Code를 재시작해야 스킬이 인식됩니다 (스킬 목록은 시작 시에만 읽음).

## 사용 예시 (설치 완료 후)
- "이 저장소 구조를 아키파이로 그려줘"
- "kostat_poller → orchestrator_bridge 호출 순서를 시퀀스 다이어그램으로 그려줘"
- "이 머메이드를 아키파이로 다시 그려줘"

결과물은 인라인 SVG가 든 독립 HTML 1장 (다크/라이트, 확대·검색 지원)이며 PNG/JPEG/WebP/SVG/WebM으로 내보낼 수 있습니다.

## 알아둘 것 (한계)
- 뷰어 고정 버튼 텍스트는 영어/중국어만 지원 (그려지는 내용만 한국어)
- 약 72시간마다 업데이트 확인용 네트워크 조회 발생 (끄려면 `ARCHIFY_UPDATE_CHECK_DISABLED=1`)
- 구조도는 검증 절차를 거친 결과일 뿐, 100% 정확성을 보장하지 않음 — 최종 판단은 코드와 사람
- 지원 대상: Claude Code / Cursor / Codex CLI / OpenCode
