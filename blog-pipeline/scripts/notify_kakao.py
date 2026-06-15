#!/usr/bin/env python3
"""
카카오톡 알림 전송 스크립트
KakaoTalk Notify API (kakao.com/link/v2/memo/default/send) 사용

환경변수:
  KAKAO_ACCESS_TOKEN  - 카카오 OAuth 액세스 토큰
  KAKAO_REFRESH_TOKEN - 리프레시 토큰 (선택, 토큰 갱신 시 사용)

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


def refresh_token(refresh_token_val: str, client_id: str) -> str | None:
    """만료된 access_token을 refresh_token으로 갱신한다."""
    data = urllib.parse.urlencode({
        "grant_type":    "refresh_token",
        "client_id":     client_id,
        "refresh_token": refresh_token_val,
    }).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            new_token = result.get("access_token")
            # 갱신된 토큰을 로컬 파일에도 저장
            if new_token and TOKEN_FILE.exists():
                saved = _load_saved_tokens()
                saved["access_token"] = new_token
                if result.get("refresh_token"):
                    saved["refresh_token"] = result["refresh_token"]
                TOKEN_FILE.write_text(json.dumps(saved, ensure_ascii=False, indent=2))
            return new_token
    except Exception:
        return None


def resolve_access_token() -> str:
    """
    환경변수 KAKAO_ACCESS_TOKEN 우선 사용.
    없으면 .kakao_tokens.json에서 읽고, 만료 시 자동 갱신 시도.
    """
    token = os.environ.get("KAKAO_ACCESS_TOKEN", "").strip()
    if token:
        return token

    saved = _load_saved_tokens()
    token = saved.get("access_token", "")
    if not token:
        return ""

    # 토큰 유효성 빠른 확인 (401이면 refresh)
    req = urllib.request.Request(
        "https://kapi.kakao.com/v1/user/access_token_info",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        urllib.request.urlopen(req, timeout=5)
        return token  # 유효
    except urllib.error.HTTPError as e:
        if e.code == 401 and saved.get("refresh_token") and saved.get("client_id"):
            new = refresh_token(saved["refresh_token"], saved["client_id"])
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
