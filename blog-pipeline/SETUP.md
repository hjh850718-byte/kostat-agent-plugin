# Korea-Asia Business Bridge — 최초 설정 가이드

## 사전 준비

| 항목 | 필요 여부 | 비고 |
|------|----------|------|
| GitHub 계정 | 필수 | 저장소 생성 권한 필요 |
| Anthropic API Key | 필수 | Claude API 사용료 발생 |
| Gmail 계정 (알림용) | 권장 | 실패 알림 이메일 발송 |
| Google AdSense 계정 | 선택 | 수익화 목표 시 |

---

## Step 1 — GitHub 저장소 생성

```bash
# 1-1. 저장소 생성 (GitHub 웹 UI 또는 CLI)
gh repo create korea-asia-blog --public

# 1-2. 이 디렉토리를 로컬 클론
git clone https://github.com/YOUR_USERNAME/korea-asia-blog.git
cd korea-asia-blog

# 1-3. blog-pipeline 파일들을 복사
cp -r /path/to/blog-pipeline/* .
```

---

## Step 2 — Hugo 프로젝트 초기화

```bash
# 2-1. Hugo 설치 (macOS)
brew install hugo

# 2-1. Hugo 설치 (Windows)
winget install Hugo.Hugo.Extended

# 2-1. Hugo 설치 (Ubuntu)
sudo apt install hugo

# 2-2. Hugo 버전 확인 (0.120+ 필요)
hugo version

# 2-3. PaperMod 테마를 서브모듈로 추가
git submodule add --depth=1 https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod
git submodule update --init --recursive

# 2-4. 기본 콘텐츠 폴더 생성
mkdir -p content/posts content/about static/images layouts/partials

# 2-5. About 페이지 생성
cat > content/about/index.md << 'EOF'
---
title: "소개"
date: 2025-01-01
draft: false
---
Korea-Asia Business Bridge는 반도체 부품 무역과 APAC 해외영업 실무자를 위한 블로그입니다.
EOF

# 2-6. 로컬 테스트 실행
hugo server -D   # http://localhost:1313 에서 확인
```

---

## Step 3 — AdSense 광고 삽입

AdSense 승인 후 `layouts/partials/extend_head.html` 파일을 생성한다:

```html
<!-- layouts/partials/extend_head.html -->
<!-- Google AdSense 자동 광고 스크립트 -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-XXXXXXXXXXXXXXXX"
     crossorigin="anonymous"></script>
```

`hugo.toml`의 `googleAdSenseId`에 `ca-pub-XXXXXXXXXXXXXXXX` 형식의 ID를 입력한다.

---

## Step 4 — GitHub Secrets 등록

GitHub 저장소 → **Settings → Secrets and variables → Actions → New repository secret**

| Secret 이름 | 값 | 설명 |
|------------|---|------|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Claude API 키 |
| `NOTIFY_EMAIL` | `your@gmail.com` | 실패 알림 발신/수신 이메일 |
| `NOTIFY_EMAIL_PASSWORD` | Gmail 앱 비밀번호 | [Google 앱 비밀번호 생성](https://myaccount.google.com/apppasswords) |
| `KAKAO_ACCESS_TOKEN` | 카카오 OAuth 토큰 | 선택 — 없으면 카카오 알림 건너뜀 |

> **Gmail 앱 비밀번호**: 2단계 인증 활성화 후 앱 비밀번호를 별도 생성해야 한다.
> 일반 Gmail 비밀번호는 사용 불가.

> **KAKAO_ACCESS_TOKEN 발급 방법**
> 1. [카카오 개발자 콘솔](https://developers.kakao.com) → 내 애플리케이션 생성
> 2. 카카오 로그인 → 동의항목 → "카카오톡 메시지 전송" 활성화
> 3. Redirect URI: `https://example.com` (테스트용)
> 4. [인가 코드 받기 → 액세스 토큰 발급](https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api)
> 5. 발급된 `access_token`을 Secret에 등록

---

## Step 5 — GitHub Pages 설정

1. 저장소 → **Settings → Pages**
2. **Source**: `Deploy from a branch`
3. **Branch**: `gh-pages` / `/ (root)` 선택
4. **Save** 클릭

> 첫 배포 후 `https://YOUR_USERNAME.github.io/korea-asia-blog/` 에서 확인 가능.

`hugo.toml`의 `baseURL`을 실제 URL로 수정하라:
```toml
baseURL = "https://YOUR_USERNAME.github.io/korea-asia-blog/"
```

---

## Step 6 — 워크플로우 활성화

```bash
# 6-1. 워크플로우 파일 커밋
git add .
git commit -m "feat: initial blog pipeline setup"
git push origin main

# 6-2. GitHub → Actions 탭에서 워크플로우 활성화 확인
# 6-3. 수동 테스트 실행: Actions → Daily Blog Post → Run workflow
```

---

## Step 7 — 로컬에서 스크립트 테스트

```bash
# 7-1. 의존성 설치
pip install anthropic

# 7-2. 환경변수 설정
export ANTHROPIC_API_KEY="sk-ant-..."

# 7-3. 포스트 생성 테스트
python scripts/generate_post.py --topic "MLCC 공급망 이슈" --lang ko

# 7-4. 키워드 필터 테스트
python scripts/keyword_filter.py content/posts/2025-01-01-*.md

# 7-5. Hugo 빌드 테스트
hugo --minify
```

---

## 파이프라인 동작 흐름

```
매일 07:00 KST (cron)
    │
    ▼
Claude API → 포스트 초안 생성 (claude-sonnet-4-6)
    │
    ▼
AdSense 키워드 필터 (keyword_filter.py)
    │ 실패 → 이메일 알림 발송 → 종료
    │ 통과
    ▼
새 브랜치 생성 + 파일 커밋 (draft/post-YYYY-MM-DD-slug)
    │
    ▼
Draft PR 생성 + "draft-review" 라벨 부착
    │
    ▼
[사람이 검수] PR 내용 확인 → 수정 가능
    │
    ▼
PR 머지 (main 브랜치)
    │
    ▼
Hugo 빌드 (hugo --minify)
    │
    ▼
GitHub Pages 배포 (gh-pages 브랜치)
    │
    ▼
https://YOUR_USERNAME.github.io/korea-asia-blog/ 에 발행 완료
```

---

## 비용 추정

| 항목 | 비용 |
|------|------|
| GitHub Pages 호스팅 | **무료** |
| GitHub Actions (월 2,000분) | **무료** (공개 저장소 무제한) |
| Claude API (claude-sonnet-4-6) | 포스트 1개당 약 $0.01~0.03 |
| 도메인 (선택) | 연 $10~15 |

월 30개 포스트 기준 API 비용: **약 $0.30~0.90**

---

## 다음 실행 명령어

### 지금 바로 포스트 생성 (로컬)
```bash
export ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"
python scripts/generate_post.py --lang both
```

### GitHub Actions 수동 트리거
```bash
gh workflow run daily-post.yml \
  --field topic="MLCC 글로벌 공급망 분석" \
  --field lang="both"
```

### Hugo 로컬 서버 실행
```bash
hugo server -D --bind 0.0.0.0 --port 1313
# 브라우저: http://localhost:1313
```

### 전체 빌드 및 배포 (수동)
```bash
hugo --minify
# public/ 폴더가 생성됨 — gh-pages 브랜치에 push
```

---

## 트러블슈팅

| 증상 | 원인 | 해결 |
|------|------|------|
| `ANTHROPIC_API_KEY` 오류 | Secret 미등록 | Step 4 재확인 |
| Hugo build 실패 | 테마 서브모듈 없음 | `git submodule update --init` |
| PR 생성 실패 | `contents: write` 권한 없음 | Actions 권한 설정 확인 |
| 이메일 알림 미발송 | Gmail 앱 비밀번호 오류 | `NOTIFY_EMAIL_PASSWORD` 재생성 |
| 배포 후 페이지 빈 화면 | `baseURL` 불일치 | `hugo.toml` baseURL 확인 |
