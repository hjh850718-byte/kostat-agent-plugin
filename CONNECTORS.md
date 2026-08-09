# KOSTAT Agent — 커넥터 현황

> KOSTAT 해외영업 플러그인이 연결하는 외부 서비스 및 MCP 서버 목록

## MCP 서버

| 서비스 | 용도 | 필수 여부 |
|--------|------|-----------|
| Gmail | 이메일 분류, PO/OOR 메일 감지 | 권장 |
| Google Calendar | PO 납기일 등록 | 선택 |
| Notion | KPT 저장, Memory Ticket 보관 | 선택 |
| KakaoTalk | 알림 수신 / 메시지 발송 | 선택 |

## 외부 API

| 서비스 | 용도 | 인증 방식 |
|--------|------|-----------|
| Telegram Bot | 작업 완료 알림, 에러 알림 | Bot Token (`.env`) |
| 관세청 수출입무역통계 | HS코드·환율 조회 (직접 조회) | 공개 API |

## 로컬 CLI 연동 (MCP 아님)

| 도구 | 용도 | 필수 여부 | 비고 |
|------|------|-----------|------|
| [katok](https://github.com/NomaDamas/katok) | 카카오톡 대화 로컬 검색·조회 (`kostat-katok-search` 스킬) | 선택 | **Apple Silicon macOS 전용.** 이 플러그인의 기본 작업 환경(Windows)에서는 실행 불가 — 현재 설계/문서화 단계이며 실행은 별도 Mac 환경에서만 유효. MCP 서버가 아니라 로컬에 설치하는 Rust CLI. `katok send`(발송)는 통합 범위에서 제외. |

## 로컬 파일 시스템

| 경로 | 용도 |
|------|------|
| `D:\jun\한준희\` | PO PDF, OOR Excel, 커미션 데이터 원본 |
| `C:\Users\USER\Desktop\77. CLOUDE 정리용\` | 작업 파일, 인보이스, KPT, 브리핑 로그 |

## 플러그인 의존성

| 플러그인 | 관계 |
|----------|------|
| anthropics/sales (knowledge-work-plugins) | 계정 리서치, 콜드메일 등 영어권 세일즈 보조 |
| data (knowledge-work-plugins) | 데이터 분석/시각화 |

> **참고**: MCP 서버 연결은 `claude_desktop_config.json`에서 별도 설정합니다.
> 플러그인 설치만으로 자동 연결되지 않습니다.
