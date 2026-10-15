# Korea-Asia Business Bridge — 자동 블로그 파이프라인

반도체 부품 무역·APAC 해외영업 실무 블로그의 **서버비 0원 자동 발행 시스템**.

Claude API로 초안 생성 → 사람이 PR에서 검수 → 머지하면 자동 배포.

---

## 디렉토리 구조

```
blog-pipeline/
├── .github/
│   └── workflows/
│       └── daily-post.yml      # 메인 GitHub Actions 워크플로우
├── scripts/
│   ├── generate_post.py        # Claude API 포스트 생성
│   └── keyword_filter.py       # AdSense 안전 키워드 필터
├── content/
│   └── posts/                  # Hugo 포스트 저장 위치 (자동 생성)
├── themes/
│   └── PaperMod/               # Hugo 테마 (git submodule)
├── hugo.toml                   # Hugo 사이트 설정
├── SETUP.md                    # 최초 설정 가이드
└── README.md                   # 이 파일
```

---

## 파이프라인 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions (ubuntu-latest)                             │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ cron 22:00   │───▶│ generate_    │───▶│ keyword_     │  │
│  │ UTC (07 KST) │    │ post.py      │    │ filter.py    │  │
│  └──────────────┘    │ (Claude API) │    │ (AdSense 안전)│  │
│                      └──────────────┘    └──────┬───────┘  │
│                                                 │ 통과       │
│                                          ┌──────▼───────┐  │
│                                          │ Draft PR 생성  │  │
│                                          │ + 라벨 부착   │  │
│                                          └──────┬───────┘  │
└─────────────────────────────────────────────────┼───────────┘
                                                  │
                              [사람이 검수 후 머지]
                                                  │
┌─────────────────────────────────────────────────▼───────────┐
│  deploy job (main 브랜치 push 시)                            │
│                                                             │
│  Hugo --minify ──▶ GitHub Pages 자동 배포                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 핵심 구성요소

### 1. `generate_post.py` — 포스트 생성기

- **모델**: `claude-sonnet-4-6`
- **주제 풀**: 20개 반도체 무역·APAC 영업 주제 (랜덤 또는 지정)
- **출력**: Hugo front matter 포함 마크다운 (`YYYY-MM-DD-slug.md`)
- **언어**: 한국어, 영어, 바이링구얼 선택 가능

```bash
# 사용 예
python scripts/generate_post.py --topic "MLCC 공급망" --lang both
```

### 2. `keyword_filter.py` — AdSense 안전 필터

- 성인·폭력·혐오·불법·도박·오해 유도 키워드 블랙리스트 검사
- 경고 키워드 감지 (투자·의료·정치 등)
- 안전도 점수 0~100 산출
- 필터 실패 시 PR 생성 차단

```bash
# 사용 예
python scripts/keyword_filter.py content/posts/2025-01-01-post.md --json
```

### 3. `daily-post.yml` — GitHub Actions 워크플로우

| Job | 트리거 | 역할 |
|-----|--------|------|
| `generate-and-pr` | cron / 수동 | 초안 생성 → Draft PR |
| `deploy` | main 브랜치 push | Hugo 빌드 → GitHub Pages |

**필요 Secrets:**

| 이름 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API 인증 키 |
| `NOTIFY_EMAIL` | 실패 알림 이메일 주소 |
| `NOTIFY_EMAIL_PASSWORD` | Gmail 앱 비밀번호 |

---

## 빠른 시작

```bash
# 1. 의존성 설치
pip install anthropic

# 2. API 키 설정
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. 포스트 생성 테스트
python scripts/generate_post.py --lang both

# 4. 필터 테스트
python scripts/keyword_filter.py content/posts/*.md

# 5. Hugo 로컬 서버
hugo server -D
```

전체 설정은 [SETUP.md](./SETUP.md)를 참고하라.

---

## 비용

- GitHub Pages 호스팅: **무료**
- GitHub Actions: **무료** (공개 저장소)
- Claude API: 포스트 1개당 **약 $0.01~0.03**
- 월 30개 포스트 기준 API 비용: **약 $0.30~0.90**

---

## 라이선스

MIT
