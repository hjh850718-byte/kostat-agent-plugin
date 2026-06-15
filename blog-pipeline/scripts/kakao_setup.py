#!/usr/bin/env python3
"""
카카오 OAuth 토큰 초기 발급 헬퍼
"나에게 보내기" 권한을 가진 access_token / refresh_token을 최초 1회 발급한다.

사용법 (로컬에서 한 번만 실행):
  python scripts/kakao_setup.py

필요 정보:
  - 카카오 개발자 콘솔(https://developers.kakao.com)에서 앱 생성 후
    REST API 키와 Redirect URI(예: https://example.com) 준비

산출물:
  .kakao_tokens.json  ← 토큰 저장 (gitignore 처리됨)
  → access_token을 GitHub Secret KAKAO_ACCESS_TOKEN에 등록하라.
"""

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
TOKEN_URL     = "https://kauth.kakao.com/oauth/token"
TOKEN_FILE    = Path(__file__).parent.parent / ".kakao_tokens.json"


def get_authorization_url(client_id: str, redirect_uri: str) -> str:
    params = urllib.parse.urlencode({
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "talk_message",   # 나에게 보내기 권한
    })
    return f"{AUTHORIZE_URL}?{params}"


def exchange_code_for_token(client_id: str, redirect_uri: str, code: str) -> dict:
    """인가 코드 → access_token / refresh_token 교환."""
    data = urllib.parse.urlencode({
        "grant_type":   "authorization_code",
        "client_id":    client_id,
        "redirect_uri": redirect_uri,
        "code":         code,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def refresh_access_token(client_id: str, refresh_token: str) -> dict:
    """refresh_token으로 만료된 access_token을 갱신한다."""
    data = urllib.parse.urlencode({
        "grant_type":    "refresh_token",
        "client_id":     client_id,
        "refresh_token": refresh_token,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def save_tokens(tokens: dict, client_id: str, redirect_uri: str) -> None:
    payload = {**tokens, "client_id": client_id, "redirect_uri": redirect_uri}
    TOKEN_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ 토큰 저장: {TOKEN_FILE}")


def load_tokens() -> dict | None:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    return None


def main():
    print("=" * 55)
    print(" 카카오 OAuth 토큰 발급 헬퍼")
    print("=" * 55)
    print()

    # ── 기존 토큰 갱신 시도 ────────────────────────────────────
    existing = load_tokens()
    if existing and existing.get("refresh_token"):
        print(f"기존 토큰 파일 발견: {TOKEN_FILE}")
        answer = input("refresh_token으로 갱신하시겠습니까? [Y/n]: ").strip().lower()
        if answer != "n":
            try:
                result = refresh_access_token(
                    existing["client_id"], existing["refresh_token"]
                )
                merged = {**existing, **result}
                save_tokens(merged, existing["client_id"], existing["redirect_uri"])
                print(f"\n✅ 갱신 완료!")
                print(f"  access_token : {merged['access_token'][:20]}...")
                print(f"\n→ GitHub Secret KAKAO_ACCESS_TOKEN에 아래 값을 등록하세요:")
                print(f"  {merged['access_token']}")
                return
            except Exception as e:
                print(f"갱신 실패: {e} → 신규 발급을 진행합니다.")

    # ── 신규 발급 ──────────────────────────────────────────────
    print("카카오 개발자 콘솔(https://developers.kakao.com)에서")
    print("앱을 생성하고 아래 정보를 입력하세요.\n")

    client_id    = input("REST API 키: ").strip()
    redirect_uri = input("Redirect URI (예: https://example.com): ").strip()

    auth_url = get_authorization_url(client_id, redirect_uri)
    print(f"\n1. 아래 URL을 브라우저에서 열어 카카오 로그인 후 동의하세요:")
    print(f"\n   {auth_url}\n")
    print(f"2. 동의 완료 후 리다이렉트된 URL에서 code= 값을 복사하세요.")
    print(f"   예) https://example.com?code=XXXXXX → 'XXXXXX' 복사\n")

    code = input("인가 코드(code=): ").strip()

    try:
        result = exchange_code_for_token(client_id, redirect_uri, code)
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"\n❌ 토큰 발급 실패: HTTP {e.code}\n{body}")
        sys.exit(1)

    save_tokens(result, client_id, redirect_uri)

    print(f"\n✅ 발급 완료!")
    print(f"  access_token  : {result['access_token'][:20]}...")
    print(f"  expires_in    : {result.get('expires_in', '?')}초")
    print(f"  refresh_token : {result.get('refresh_token', 'N/A')[:20]}...")
    print()
    print("=" * 55)
    print(" GitHub Secret 등록 방법")
    print("=" * 55)
    print("저장소 → Settings → Secrets → Actions → New secret")
    print(f"  이름 : KAKAO_ACCESS_TOKEN")
    print(f"  값   : {result['access_token']}")
    print()
    print("※ access_token 만료(6시간) 시 이 스크립트를 다시 실행하거나")
    print("  notify_kakao.py가 자동으로 refresh_token으로 갱신합니다.")


if __name__ == "__main__":
    main()
