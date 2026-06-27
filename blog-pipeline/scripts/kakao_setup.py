#!/usr/bin/env python3
"""
카카오 OAuth 토큰 초기 발급 헬퍼
"나에게 보내기" 권한을 가진 access_token / refresh_token을 최초 1회 발급한다.

카카오 OAuth 2.0 플로우:
  1. GET  https://kauth.kakao.com/oauth/authorize  → 인가 코드(code) 발급
  2. POST https://kauth.kakao.com/oauth/token      → access_token / refresh_token
  3. POST https://kauth.kakao.com/oauth/token (refresh) → access_token 갱신

토큰 만료 시간:
  - access_token       : 6시간  (21,600초)
  - refresh_token      : 60일   (5,184,000초)
  - refresh_token 잔여 < 30일이면 응답에 새 refresh_token 포함

사용법 (로컬에서 한 번만 실행):
  python scripts/kakao_setup.py

필요 정보 (카카오 개발자 콘솔 https://developers.kakao.com):
  - REST API 키
  - Redirect URI (예: https://example.com — 실제 서버 불필요)
  - Client Secret (앱 설정에서 활성화 시 필수)

산출물:
  .kakao_tokens.json  ← 토큰 저장 (gitignore 처리됨)
  → access_token을 GitHub Secret KAKAO_ACCESS_TOKEN에 등록
  → client_id / refresh_token을 GitHub Secret에 추가 등록 권장
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL     = "https://kauth.kakao.com/oauth/token"
TOKEN_FILE    = Path(__file__).parent.parent / ".kakao_tokens.json"
KST           = timezone(timedelta(hours=9))

# 토큰 만료 시간 (카카오 공식 문서 기준)
ACCESS_TOKEN_TTL  = 21_600      # 6시간
REFRESH_TOKEN_TTL = 5_184_000   # 60일


def get_authorization_url(client_id: str, redirect_uri: str) -> str:
    """Step 1: 사용자가 브라우저에서 열어 인가 코드를 받는 URL."""
    params = urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        # talk_message: 나에게 보내기, profile: 프로필 조회
        "scope":         "talk_message",
    })
    return f"{AUTHORIZE_URL}?{params}"


def _post_token(payload: dict) -> dict:
    """카카오 토큰 엔드포인트에 POST 요청을 보낸다."""
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def exchange_code_for_token(
    client_id: str, redirect_uri: str, code: str, client_secret: str = ""
) -> dict:
    """Step 2: 인가 코드 → access_token / refresh_token 교환."""
    payload = {
        "grant_type":   "authorization_code",
        "client_id":    client_id,
        "redirect_uri": redirect_uri,
        "code":         code,
    }
    # Client Secret이 앱에 설정된 경우 필수 포함
    if client_secret:
        payload["client_secret"] = client_secret
    return _post_token(payload)


def refresh_access_token(
    client_id: str, refresh_token: str, client_secret: str = ""
) -> dict:
    """Step 3: refresh_token → 새 access_token (+ 필요 시 새 refresh_token)."""
    payload = {
        "grant_type":    "refresh_token",
        "client_id":     client_id,
        "refresh_token": refresh_token,
    }
    if client_secret:
        payload["client_secret"] = client_secret
    return _post_token(payload)


def save_tokens(tokens: dict, client_id: str, redirect_uri: str,
                client_secret: str = "") -> None:
    now_ts = int(time.time())
    payload = {
        **tokens,
        "client_id":            client_id,
        "redirect_uri":         redirect_uri,
        "client_secret":        client_secret,
        "issued_at":            now_ts,
        "access_token_expires": now_ts + tokens.get("expires_in", ACCESS_TOKEN_TTL),
        "refresh_token_expires": now_ts + tokens.get(
            "refresh_token_expires_in", REFRESH_TOKEN_TTL
        ),
    }
    TOKEN_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    print(f"✅ 토큰 저장: {TOKEN_FILE}")


def load_tokens() -> dict | None:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    return None


def expiry_str(ts: int) -> str:
    dt = datetime.fromtimestamp(ts, tz=KST)
    return dt.strftime("%Y-%m-%d %H:%M KST")


def show_token_status(saved: dict) -> None:
    now = int(time.time())
    at_exp = saved.get("access_token_expires", 0)
    rt_exp = saved.get("refresh_token_expires", 0)
    at_left = max(0, at_exp - now)
    rt_left = max(0, rt_exp - now)

    print(f"  access_token  만료: {expiry_str(at_exp)} (잔여 {at_left//3600}시간)")
    print(f"  refresh_token 만료: {expiry_str(rt_exp)} (잔여 {rt_left//86400}일)")


def main():
    print("=" * 58)
    print(" 카카오 OAuth 토큰 발급 헬퍼")
    print("=" * 58)
    print()

    # ── 기존 토큰 갱신 시도 ──────────────────────────────────────
    existing = load_tokens()
    if existing and existing.get("refresh_token"):
        print(f"기존 토큰 파일 발견: {TOKEN_FILE}")
        show_token_status(existing)
        print()
        answer = input("refresh_token으로 access_token 갱신하시겠습니까? [Y/n]: ").strip().lower()
        if answer != "n":
            try:
                result = refresh_access_token(
                    existing["client_id"],
                    existing["refresh_token"],
                    existing.get("client_secret", ""),
                )
                merged = {**existing, **result}
                save_tokens(
                    merged,
                    existing["client_id"],
                    existing["redirect_uri"],
                    existing.get("client_secret", ""),
                )
                print(f"\n✅ 갱신 완료!")
                show_token_status(merged)
                print(f"\n→ GitHub Secret KAKAO_ACCESS_TOKEN 값:")
                print(f"  {merged['access_token']}")
                return
            except Exception as e:
                print(f"갱신 실패: {e}")
                print("→ 신규 발급을 진행합니다.\n")

    # ── 신규 발급 ────────────────────────────────────────────────
    print("카카오 개발자 콘솔(https://developers.kakao.com)에서")
    print("앱을 생성하고 아래 정보를 입력하세요.\n")

    client_id     = input("REST API 키            : ").strip()
    redirect_uri  = input("Redirect URI           : ").strip()
    client_secret = input("Client Secret (없으면 Enter): ").strip()

    auth_url = get_authorization_url(client_id, redirect_uri)
    print()
    print("─" * 58)
    print("STEP 1 — 브라우저에서 아래 URL을 열어 카카오 로그인 후 동의:")
    print()
    print(f"  {auth_url}")
    print()
    print("STEP 2 — 동의 후 리다이렉트된 URL에서 code= 값을 복사:")
    print("  예) https://example.com?code=AbCdEf1234  →  'AbCdEf1234' 복사")
    print("─" * 58)
    print()

    code = input("인가 코드(code=): ").strip()

    try:
        result = exchange_code_for_token(client_id, redirect_uri, code, client_secret)
    except RuntimeError as e:
        print(f"\n❌ 토큰 발급 실패: {e}")
        sys.exit(1)

    save_tokens(result, client_id, redirect_uri, client_secret)

    print()
    print("✅ 발급 완료!")
    show_token_status(result | {
        "access_token_expires":  int(time.time()) + result.get("expires_in", ACCESS_TOKEN_TTL),
        "refresh_token_expires": int(time.time()) + result.get("refresh_token_expires_in", REFRESH_TOKEN_TTL),
    })
    print()
    print("=" * 58)
    print(" GitHub Secrets 등록")
    print(" 저장소 → Settings → Secrets → Actions")
    print("=" * 58)
    print(f"  KAKAO_ACCESS_TOKEN  = {result['access_token']}")
    if client_secret:
        print(f"  KAKAO_CLIENT_ID     = {client_id}")
        print(f"  KAKAO_CLIENT_SECRET = {client_secret}")
        print(f"  KAKAO_REFRESH_TOKEN = {result.get('refresh_token', '')}")
    print()
    print("※ access_token은 6시간 후 만료됩니다.")
    print("  notify_kakao.py가 만료 감지 시 refresh_token으로 자동 갱신합니다.")
    print("  refresh_token은 60일 유효 — 만료 전 이 스크립트를 재실행하세요.")


if __name__ == "__main__":
    main()
