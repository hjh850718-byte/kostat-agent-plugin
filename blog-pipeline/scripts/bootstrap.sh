#!/usr/bin/env bash
# Korea-Asia Business Bridge 블로그 저장소 초기 설정 스크립트
# 사용법: bash scripts/bootstrap.sh <github-username> <repo-name>
# 예시:  bash scripts/bootstrap.sh hjh850718-byte korea-asia-blog

set -euo pipefail

USERNAME="${1:-}"
REPO="${2:-korea-asia-blog}"

if [ -z "$USERNAME" ]; then
  echo "사용법: bash scripts/bootstrap.sh <github-username> <repo-name>"
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Korea-Asia Business Bridge 블로그 부트스트랩"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── 1. Hugo 설치 확인 ──────────────────────────────────────────
if ! command -v hugo &>/dev/null; then
  echo "[오류] Hugo가 설치되지 않았습니다."
  echo "  macOS:   brew install hugo"
  echo "  Ubuntu:  sudo snap install hugo"
  echo "  Windows: winget install Hugo.Hugo.Extended"
  exit 1
fi

HUGO_VER=$(hugo version | grep -oP 'v[\d.]+' | head -1)
echo "✅ Hugo $HUGO_VER 확인"

# ── 2. 블로그 디렉토리 생성 ────────────────────────────────────
BLOG_DIR="$HOME/${REPO}"
if [ -d "$BLOG_DIR" ]; then
  echo "[경고] $BLOG_DIR 이미 존재합니다. 건너뜁니다."
else
  mkdir -p "$BLOG_DIR"
fi
cd "$BLOG_DIR"

# ── 3. git 초기화 ──────────────────────────────────────────────
if [ ! -d ".git" ]; then
  git init
  git remote add origin "https://github.com/${USERNAME}/${REPO}.git"
  echo "✅ Git 초기화 완료"
fi

# ── 4. blog-pipeline 파일 복사 ─────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(dirname "$SCRIPT_DIR")"

echo "파일 복사 중: $SOURCE_DIR → $BLOG_DIR"
rsync -av --exclude='.git' --exclude='themes/' --exclude='public/' \
  "$SOURCE_DIR/" "$BLOG_DIR/"

# ── 5. hugo.toml baseURL 자동 교체 ────────────────────────────
BASE_URL="https://${USERNAME}.github.io/${REPO}/"
sed -i "s|https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO_NAME/|${BASE_URL}|g" hugo.toml
sed -i "s|YOUR_GITHUB_USERNAME|${USERNAME}|g" hugo.toml
sed -i "s|YOUR_REPO_NAME|${REPO}|g" hugo.toml
echo "✅ hugo.toml baseURL = $BASE_URL"

# ── 6. PaperMod 테마 서브모듈 추가 ────────────────────────────
if [ ! -d "themes/PaperMod/.git" ]; then
  git submodule add --depth=1 \
    https://github.com/adityatelange/hugo-PaperMod.git themes/PaperMod
  git submodule update --init --recursive
  echo "✅ PaperMod 테마 추가 완료"
else
  echo "✅ PaperMod 테마 이미 존재"
fi

# ── 7. Python 의존성 설치 ──────────────────────────────────────
if command -v pip &>/dev/null; then
  pip install -r requirements.txt -q
  echo "✅ Python 패키지 설치 완료"
fi

# ── 8. 초기 커밋 ───────────────────────────────────────────────
git add -A
git commit -m "feat: initial blog setup — Korea-Asia Business Bridge" || true

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " ✅ 부트스트랩 완료!"
echo ""
echo " 다음 단계:"
echo "  1. GitHub에서 '${REPO}' 저장소 생성 (Public)"
echo "  2. git push -u origin main"
echo "  3. Settings → Secrets에 ANTHROPIC_API_KEY 등록"
echo "  4. Settings → Pages → gh-pages 브랜치 선택"
echo "  5. make serve  → http://localhost:1313 확인"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
