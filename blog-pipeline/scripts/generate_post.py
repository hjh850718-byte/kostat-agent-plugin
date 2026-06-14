#!/usr/bin/env python3
"""
Korea-Asia Business Bridge 블로그 자동 포스트 생성기
Claude API를 사용하여 Hugo 호환 마크다운 포스트를 생성한다.

사용법:
  python generate_post.py                    # 랜덤 주제 선택
  python generate_post.py --topic "MLCC 공급망"  # 지정 주제
  python generate_post.py --lang ko          # 한국어만
  python generate_post.py --lang en          # 영어만
  python generate_post.py --lang both        # 바이링구얼 (기본값)
"""

import os
import re
import sys
import random
import argparse
import textwrap
from datetime import datetime, timezone, timedelta
from pathlib import Path

import anthropic

# KST = UTC+9
KST = timezone(timedelta(hours=9))

# 블로그 주제 풀 — 반도체 부품 무역 & APAC 영업
TOPIC_POOL = [
    # 반도체 부품 무역
    "MLCC(적층 세라믹 커패시터) 글로벌 공급망 분석과 바이어 협상 전략",
    "반도체 부품 리드타임 급등 시 재고 관리 베스트 프랙티스",
    "대만 OSAT(후공정) 파트너 발굴: 평가 체크리스트 10가지",
    "일본 전자부품 메이커와의 협상에서 문화적 차이를 극복하는 법",
    "APAC 반도체 부품 가격 동향 2025 H2 — 트렌드와 전망",
    "전력 반도체(SiC/GaN) 수요 폭증 — 해외 공급선 다변화 전략",
    "MOQ(최소 주문 수량) 협상: 소량 바이어가 대형 메이커와 거래하는 법",
    "ITAR/EAR 수출통제 규정이 한국 반도체 수입상에 미치는 영향",

    # APAC 영업 인사이트
    "인도 전자제조(EMS) 시장 진출 — 첫 바이어 미팅 준비 가이드",
    "베트남 공장 이전 트렌드: 부품 공급망 재편 기회와 위기",
    "중국 대체 조달처 발굴: 말레이시아·태국·인도네시아 비교",
    "APAC B2B 무역에서 신뢰(Trust)를 쌓는 관계 영업 5단계",
    "싱가포르 무역 허브 활용법: 거점 설립 없이 동남아 커버하기",
    "한국 수출입 바이어가 자주 저지르는 인코텀즈 실수 TOP 5",

    # B2B 실무 팁
    "무역 서류 자동화: 패킹리스트·인보이스 오류를 줄이는 Excel 팁",
    "HS 코드 분류 오류가 불러오는 관세 리스크와 사전 심사 신청법",
    "LC(신용장) vs TT(전신환) — 신규 거래처 조건 협상 가이드",
    "B2B 영업 이메일 영어 템플릿: 첫 접촉부터 클로징까지",
    "CRM 없이 Excel로 해외 파이프라인 관리하는 실전 방법",
    "무역 보험(KSURE/KEXIM) 활용해 대금 미회수 위험 줄이는 법",
]


def slugify(text: str) -> str:
    """한국어/영어 제목을 URL-안전 slug로 변환한다."""
    # 영문·숫자·하이픈만 남김 (한글은 romanize 대신 제거 후 영단어 활용)
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:60]  # Hugo slug 최대 길이


def build_prompt(topic: str, lang: str) -> str:
    lang_instruction = {
        "ko": "한국어로만 작성하라.",
        "en": "Write in English only.",
        "both": (
            "한국어와 영어 두 언어로 작성하라. "
            "구조: 먼저 한국어 전체 본문을 작성하고, "
            "그 뒤에 `---` 구분선 이후 영어 전체 본문을 작성한다."
        ),
    }[lang]

    return textwrap.dedent(f"""
        당신은 Korea-Asia Business Bridge 블로그의 수석 에디터다.
        독자는 한국 해외영업 담당자와 반도체 업계 실무자다.

        주제: {topic}

        {lang_instruction}

        ## 출력 형식 (Hugo front matter + Markdown)

        ```markdown
        ---
        title: "제목 (따옴표 포함, 60자 이내)"
        date: {datetime.now(KST).strftime('%Y-%m-%dT%H:%M:%S+09:00')}
        draft: true
        categories: ["반도체무역", "APAC영업"]   # 적절히 선택
        tags: []   # 3~5개 구체적 태그
        description: "SEO 메타 설명 (150자 이내)"
        author: "Korea-Asia Business Bridge"
        toc: true
        ---

        ## 소제목1

        본문...

        ## 소제목2

        본문...
        ```

        ## 작성 규칙
        - 실무에서 바로 쓸 수 있는 구체적 내용 포함
        - 숫자, 예시, 체크리스트 활용
        - 전문 용어는 처음 등장 시 설명
        - 광고성 표현·과장 금지 (AdSense 정책 준수)
        - 전체 분량: 800~1200단어 (한국어 기준)
        - front matter의 title 값은 반드시 큰따옴표로 감싸라
    """).strip()


def generate_post(topic: str, lang: str = "both") -> tuple[str, str]:
    """
    Claude API로 포스트를 생성하고 (content, slug)를 반환한다.
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    print(f"[생성 중] 주제: {topic}", file=sys.stderr)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[
            {"role": "user", "content": build_prompt(topic, lang)}
        ],
    )

    raw = message.content[0].text

    # 코드 블록 펜스 제거 (```markdown ... ```)
    raw = re.sub(r"^```(?:markdown)?\n", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\n```\s*$", "", raw, flags=re.MULTILINE)

    # front matter에서 title 추출하여 slug 생성
    title_match = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', raw, re.MULTILINE)
    title = title_match.group(1) if title_match else topic
    slug = slugify(title)

    return raw.strip(), slug


def save_post(content: str, slug: str, output_dir: Path) -> Path:
    """포스트를 파일로 저장하고 경로를 반환한다."""
    today = datetime.now(KST).strftime("%Y-%m-%d")
    filename = f"{today}-{slug}.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename
    out_path.write_text(content, encoding="utf-8")
    print(f"[저장] {out_path}", file=sys.stderr)
    return out_path


def main():
    parser = argparse.ArgumentParser(description="Hugo 블로그 포스트 자동 생성")
    parser.add_argument("--topic", default=None, help="포스트 주제 (미지정 시 랜덤)")
    parser.add_argument("--lang", choices=["ko", "en", "both"], default="both",
                        help="언어 설정 (기본값: both)")
    parser.add_argument("--output-dir", default="content/posts",
                        help="출력 디렉토리 (기본값: content/posts)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("오류: ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)

    topic = args.topic or random.choice(TOPIC_POOL)
    content, slug = generate_post(topic, args.lang)

    output_dir = Path(args.output_dir)
    saved_path = save_post(content, slug, output_dir)

    # GitHub Actions에서 후속 step이 파일 경로를 참조할 수 있도록 출력
    print(f"POST_PATH={saved_path}")
    print(f"POST_SLUG={slug}")
    print(f"POST_TOPIC={topic}")


if __name__ == "__main__":
    main()
