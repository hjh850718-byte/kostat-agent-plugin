#!/usr/bin/env python3
"""
AdSense 정책 위반 키워드 필터
Google AdSense 정책 위반 가능성이 있는 키워드를 검사하고
발행 전 콘텐츠를 안전하게 필터링한다.
"""

import re
import sys
import json
from dataclasses import dataclass, field
from pathlib import Path


# AdSense 정책 위반 블랙리스트
# 참고: https://support.google.com/adsense/answer/1348688
BLACKLIST = {
    "adult": [
        "성인", "포르노", "porn", "adult content", "섹스", "성적",
        "nude", "naked", "erotic", "18+", "xxx",
    ],
    "violence": [
        "살인", "폭력", "테러", "murder", "violence", "terrorist",
        "bomb", "폭탄", "총기", "gun", "weapon",
    ],
    "hate_speech": [
        "혐오", "차별", "인종차별", "hate speech", "racism",
        "sexism", "fascism", "nazi",
    ],
    "illegal": [
        "마약", "drug", "hacking", "해킹", "불법", "illegal",
        "counterfeit", "위조", "밀수", "smuggling",
    ],
    "gambling": [
        "도박", "gambling", "casino", "베팅", "betting",
        "슬롯머신", "slot machine",
    ],
    "misleading": [
        "100% 보장", "guaranteed profit", "무조건 수익", "확실한 투자",
        "부업으로 월 천만원", "get rich quick",
    ],
}

# 경고 키워드 (발행은 가능하나 주의 필요)
CAUTION_KEYWORDS = [
    "투자", "수익률", "ROI", "수익 보장", "원금 보장",
    "정치", "선거", "당선", "대통령",
    "의료", "치료", "완치", "의약품",
]


@dataclass
class FilterResult:
    passed: bool
    violations: list[dict] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)
    score: float = 100.0  # 100점 만점, 낮을수록 위험

    def summary(self) -> str:
        if self.passed:
            lines = [f"✅ 필터 통과 (안전도 점수: {self.score:.1f}/100)"]
            if self.cautions:
                lines.append(f"⚠️  주의 키워드 {len(self.cautions)}개: {', '.join(self.cautions)}")
        else:
            lines = [f"❌ 필터 실패 (안전도 점수: {self.score:.1f}/100)"]
            for v in self.violations:
                lines.append(f"  - [{v['category']}] '{v['keyword']}' 발견")
        return "\n".join(lines)


def check_content(text: str) -> FilterResult:
    """콘텐츠를 블랙리스트 및 주의 키워드에 대해 검사한다."""
    text_lower = text.lower()
    violations = []
    cautions_found = []

    # 블랙리스트 검사
    for category, keywords in BLACKLIST.items():
        for kw in keywords:
            pattern = re.compile(re.escape(kw.lower()), re.IGNORECASE)
            if pattern.search(text_lower):
                violations.append({"category": category, "keyword": kw})

    # 주의 키워드 검사
    for kw in CAUTION_KEYWORDS:
        if kw.lower() in text_lower:
            cautions_found.append(kw)

    # 안전도 점수 계산
    score = 100.0
    score -= len(violations) * 20.0   # 위반 항목당 20점 감점
    score -= len(cautions_found) * 3.0  # 주의 항목당 3점 감점
    score = max(0.0, score)

    return FilterResult(
        passed=len(violations) == 0,
        violations=violations,
        cautions=cautions_found,
        score=score,
    )


def check_file(path: str | Path) -> FilterResult:
    """마크다운 파일을 읽어 필터를 실행한다."""
    content = Path(path).read_text(encoding="utf-8")
    return check_content(content)


def main():
    if len(sys.argv) < 2:
        print("Usage: python keyword_filter.py <markdown_file>")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"파일을 찾을 수 없습니다: {file_path}")
        sys.exit(2)

    result = check_file(file_path)

    if "--json" in sys.argv:
        # JSON 모드: stdout에는 JSON만, 사람이 읽는 요약은 stderr로
        print(result.summary(), file=sys.stderr)
        print(json.dumps({
            "passed": result.passed,
            "score": result.score,
            "violations": result.violations,
            "cautions": result.cautions,
        }, ensure_ascii=False, indent=2))
    else:
        print(result.summary())

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
