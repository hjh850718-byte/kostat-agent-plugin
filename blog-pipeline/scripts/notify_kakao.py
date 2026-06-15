#!/usr/bin/env python3
"""
카카오톡 알림 전송 스크립트
KakaoTalk Notify API (kakao.com/link/v2/memo/default/send) 사용

환경변수 (GitHub Secrets):
  KAKAO_ACCESS_TOKEN  - 카카오 OAuth 액세스 토큰 (6시간 유효, 필수)
  KAKAO_CLIENT_ID     - REST API 키 (자동 갱신 시 필요)
  KAKAO_CLIENT_SECRET - Client Secret (앱 설정에서 활성화한 경우 필요)
  KAKAO_REFRESH_TOKEN - refresh_token (60일 유효, 자동 갱신에 사용)

사용법:
  python scripts/notify_kakao.py --status success --pr-url URL --title "포스트 제목"
  python scripts/notify_kakao.py --status failure --run-url URL --reason "오류 내용"
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))
KAKAO_API_URL    = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
TOKEN_URL        = "https://kauth.kakao.com/oauth/token"
TOKEN_FILE       = Path(__file__).parent.parent / ".kakao_tokens.json"


def _load_saved_tokens() -> dict:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    return {}


def _do_refresh(client_id: str, refresh_token_val: str, client_secret: str = "") -> str | None:
    """refresh_token으로 새 access_token을 발급받는다. Client Secret 지원."""
    import time
    payload = {
        "grant_type":    "refresh_token",
        "client_id":     client_id,
        "refresh_token": refresh_token_val,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            new_token = result.get("access_token")
            if new_token and TOKEN_FILE.exists():
                saved = _load_saved_tokens()
                saved["access_token"] = new_token
                saved["access_token_expires"] = int(time.time()) + result.get("expires_in", 21600)
                # refresh_token 잔여 < 30일이면 새 refresh_token도 응답에 포함됨
                if result.get("refresh_token"):
                    saved["refresh_token"] = result["refresh_token"]
                    saved["refresh_token_expires"] = int(time.time()) + result.get(
                        "refresh_token_expires_in", 5_184_000
                    )
                TOKEN_FILE.write_text(
                    json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            return new_token
    except Exception:
        return None


def resolve_access_token() -> str:
    """
    토큰 우선순위:
      1. 환경변수 KAKAO_ACCESS_TOKEN
      2. .kakao_tokens.json (만료 감지 시 자동 갱신)
    자동 갱신에는 KAKAO_CLIENT_ID / KAKAO_REFRESH_TOKEN 환경변수 또는
    .kakao_tokens.json에 저장된 값을 사용한다.
    """
    token = os.environ.get("KAKAO_ACCESS_TOKEN", "").strip()
    client_id      = os.environ.get("KAKAO_CLIENT_ID", "").strip()
    refresh_tok    = os.environ.get("KAKAO_REFRESH_TOKEN", "").strip()
    client_secret  = os.environ.get("KAKAO_CLIENT_SECRET", "").strip()

    # 환경변수 토큰 유효성 확인 → 만료 시 갱신
    if token:
        req = urllib.request.Request(
            "https://kapi.kakao.com/v1/user/access_token_info",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            return token  # 유효
        except urllib.error.HTTPError as e:
            if e.code == 401 and client_id and refresh_tok:
                new = _do_refresh(client_id, refresh_tok, client_secret)
                return new or token  # 갱신 실패 시 원본 토큰으로 재시도
        except Exception:
            return token  # 네트워크 오류 시 그냥 사용

    # 로컬 파일에서 토큰 로드
    saved = _load_saved_tokens()
    token = saved.get("access_token", "")
    if not token:
        return ""

    # 만료 시 refresh
    req = urllib.request.Request(
        "https://kapi.kakao.com/v1/user/access_token_info",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        return token
    except urllib.error.HTTPError as e:
        if e.code == 401 and saved.get("refresh_token") and saved.get("client_id"):
            new = _do_refresh(
                saved["client_id"],
                saved["refresh_token"],
                saved.get("client_secret", ""),
            )
            return new or ""
    except Exception:
        pass
    return token


def send_kakao_message(access_token: str, template: dict) -> bool:
    """카카오 나에게 보내기 API로 메시지를 전송한다."""
    data = urllib.parse.urlencode({
        "template_object": json.dumps(template, ensure_ascii=False)
    }).encode("utf-8")

    req = urllib.request.Request(
        KAKAO_API_URL,
        data=data,
        headers={"Authorization": f"Bearer {access_token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get("result_code") == 0
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"[카카오 API 오류] HTTP {e.code}: {body}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[카카오 연결 오류] {e}", file=sys.stderr)
        return False


def build_success_template(pr_url: str, title: str, score: float) -> dict:
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    return {
        "object_type": "feed",
        "content": {
            "title": "📝 블로그 초안이 준비됐습니다",
            "description": f"{title}\n안전도: {score}/100 · {now}",
            "image_url": "https://via.placeholder.com/800x400/4A90D9/FFFFFF?text=Korea-Asia+Blog",
            "image_width": 800,
            "image_height": 400,
            "link": {
                "web_url": pr_url,
                "mobile_web_url": pr_url,
            },
        },
        "buttons": [
            {
                "title": "PR 검수하기",
                "link": {
                    "web_url": pr_url,
                    "mobile_web_url": pr_url,
                },
            }
        ],
    }


def build_failure_template(run_url: str, reason: str) -> dict:
    now = datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    return {
        "object_type": "text",
        "text": (
            f"❌ [Korea-Asia Blog] 자동 포스팅 실패\n\n"
            f"시각: {now}\n"
            f"원인: {reason}\n\n"
            f"Actions 로그: {run_url}"
        ),
        "link": {
            "web_url": run_url,
            "mobile_web_url": run_url,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="카카오톡 알림 전송")
    parser.add_argument("--status", choices=["success", "failure"], required=True)
    parser.add_argument("--pr-url",   default="", help="PR URL (성공 시)")
    parser.add_argument("--run-url",  default="", help="Actions 실행 URL (실패 시)")
    parser.add_argument("--title",    default="", help="포스트 제목")
    parser.add_argument("--score",    type=float, default=100.0, help="AdSense 안전도 점수")
    parser.add_argument("--reason",   default="알 수 없는 오류", help="실패 원인")
    args = parser.parse_args()

    access_token = resolve_access_token()
    if not access_token:
        print("[경고] KAKAO_ACCESS_TOKEN이 없습니다. 알림을 건너뜁니다.", file=sys.stderr)
        sys.exit(0)  # 토큰 없어도 워크플로우 실패로 이어지지 않도록 0 종료

    if args.status == "success":
        template = build_success_template(args.pr_url, args.title, args.score)
    else:
        template = build_failure_template(args.run_url, args.reason)

    ok = send_kakao_message(access_token, template)
    if ok:
        print("✅ 카카오톡 알림 전송 완료")
    else:
        print("⚠️  카카오톡 알림 전송 실패 (워크플로우는 계속 진행)", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
