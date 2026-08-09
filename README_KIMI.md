# Kimi K3 보조 백엔드 연결 가이드

KOSTAT-AGENT에서 Kimi K3를 보조 백엔드로 사용하기 위한 설정입니다.
**현재 터미널 세션에만** 적용되며, 전역 설정이나 다른 프로덕션 세션에는 영향을 주지 않습니다.

## 1. 사전 준비

1. [platform.kimi.ai](https://platform.kimi.ai)에서 API 키를 발급받습니다.
2. 프로젝트 루트의 `.env.kimi` 파일을 열어 `ANTHROPIC_API_KEY` 값을 발급받은 키로 채웁니다.

```
ANTHROPIC_BASE_URL=https://api.kimi.ai/v1
ANTHROPIC_API_KEY=발급받은_KIMI_API_KEY
```

> `.env.kimi`는 `.gitignore`에 등록되어 있어 커밋되지 않습니다.

## 2. Kimi K3로 전환

**반드시 `source`로 실행**해야 합니다 (그냥 실행하면 서브셸에서만 적용되고 사라집니다).

```bash
source scripts/switch-to-kimi.sh
```

- `.env.kimi`의 값을 현재 터미널 세션에만 로드합니다.
- 전환 전 기존 `ANTHROPIC_BASE_URL` / `ANTHROPIC_API_KEY` 값을 자동 백업합니다.
- 다른 터미널 창이나 이미 실행 중인 프로덕션 작업에는 영향을 주지 않습니다.

## 3. 기존 Claude API로 복귀

```bash
source scripts/switch-to-claude.sh
```

- 전환 전 백업해둔 값으로 복원합니다.
- 새 터미널을 열면 자동으로 기존 설정이므로, 이 스크립트는 같은 세션 안에서 되돌릴 때만 필요합니다.

## 주의사항

- `./scripts/switch-to-kimi.sh`처럼 `source` 없이 직접 실행하면 경고만 출력되고 아무 효과가 없습니다.
- API 키는 절대 커밋하지 마세요 (`.env.kimi`는 이미 `.gitignore`에 포함되어 있습니다).
- 이 스크립트들은 환경변수만 다루며, 실제 API 호출이나 실행은 수행하지 않습니다.
