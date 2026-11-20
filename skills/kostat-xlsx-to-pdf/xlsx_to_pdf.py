#!/usr/bin/env python3
"""KOSTAT xlsx → PDF 변환 (LibreOffice headless 직접 호출).

사용법:
    python xlsx_to_pdf.py <입력.xlsx> [--outdir 폴더] [--overwrite] [--one-page]

    --one-page : 시트마다 PDF 1페이지로 출력 (열이 다음 장으로 밀리는 문제 방지)

동작:
    1. soffice 실행 파일 탐색 (PATH → Windows/macOS/Linux 기본 설치 경로)
    2. 임시 사용자 프로필로 headless 변환 (엑셀/리브레오피스가 열려 있어도 충돌 없음)
    3. 변환된 PDF 검증 (pypdf 설치 시)
       - 수식 오류 문자열: Err:xxx, #REF!, #VALUE!, #DIV/0!, #NAME?, #N/A
       - 한글 폰트: 임베드된 폰트가 한글 폰트인지 확인 (대체 폰트 경고)

종료 코드:
    0 = 변환 + 검증 통과
    1 = 변환 실패 (soffice 없음, 타임아웃 등)
    2 = 변환은 됐지만 검증 실패 (수식 오류 발견) → PDF 사용 금지
    3 = 변환 OK, 경고만 있음 (한글 대체 폰트, pypdf 미설치 등)

CLI-Anything(cli-anything-libreoffice)은 사용하지 않는다.
2026-11-20 테스트에서 xlsx 수식이 Err:510으로 깨지고 서식이 사라졌기 때문.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TIMEOUT_SEC = 120

ERROR_PATTERNS = [
    r"Err:\d{3}",
    r"#REF!",
    r"#VALUE!",
    r"#DIV/0!",
    r"#NAME\?",
    r"#N/A",
    r"#NUM!",
    r"#NULL!",
]

# 한글 글리프가 확실한 폰트 이름 일부 (PDF 임베드 이름 기준, 소문자 비교)
KOREAN_FONT_HINTS = [
    "malgun", "맑은", "gulim", "굴림", "dotum", "돋움", "batang", "바탕",
    "gungsuh", "nanum", "나눔", "noto sans cjk kr", "notosanscjkkr",
    "notosanskr", "noto sans kr", "notoserifkr", "spoqa", "pretendard",
    "applesdgothic", "apple sd gothic", "unbatang", "undotum",
]

WINDOWS_CANDIDATES = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
]
MAC_CANDIDATES = ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
LINUX_CANDIDATES = ["/usr/bin/soffice", "/usr/lib/libreoffice/program/soffice",
                    "/opt/libreoffice/program/soffice"]


def find_soffice() -> str | None:
    env = os.environ.get("SOFFICE_PATH")
    if env and Path(env).exists():
        return env
    for name in ("soffice", "soffice.exe", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for c in WINDOWS_CANDIDATES + MAC_CANDIDATES + LINUX_CANDIDATES:
        if Path(c).exists():
            return c
    return None


ONE_PAGE_FILTER = ('pdf:calc_pdf_Export:'
                   '{"SinglePageSheets":{"type":"boolean","value":"true"}}')


def convert(soffice: str, src: Path, outdir: Path, one_page: bool = False) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="kostat_lo_") as prof:
        profile_url = Path(prof).resolve().as_uri()
        cmd = [
            soffice,
            f"-env:UserInstallation={profile_url}",
            "--headless", "--norestore", "--nolockcheck",
            "--convert-to", ONE_PAGE_FILTER if one_page else "pdf",
            "--outdir", str(outdir),
            str(src),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=TIMEOUT_SEC)
    out = outdir / (src.stem + ".pdf")
    if r.returncode != 0 or not out.exists():
        raise RuntimeError(
            f"soffice 변환 실패 (code={r.returncode})\n"
            f"stdout: {r.stdout.strip()}\nstderr: {r.stderr.strip()}")
    return out


def verify(pdf: Path) -> dict:
    result = {"checked": False, "errors": [], "warnings": [], "fonts": []}
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        result["warnings"].append(
            "pypdf 미설치 → 자동 검증 생략. `python -m pip install pypdf` 후 재실행 권장")
        return result

    reader = PdfReader(str(pdf))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    result["checked"] = True
    result["pages"] = len(reader.pages)

    for pat in ERROR_PATTERNS:
        hits = sorted(set(re.findall(pat, text)))
        if hits:
            result["errors"].append(f"수식 오류 발견: {', '.join(hits)}")

    fonts: set[str] = set()
    for page in reader.pages:
        res = page.get("/Resources") or {}
        font_dict = res.get("/Font") or {}
        for ref in font_dict.values():
            f = ref.get_object()
            name = str(f.get("/BaseFont", ""))
            fonts.add(name.split("+", 1)[-1].lstrip("/"))
    result["fonts"] = sorted(fonts)

    has_korean_text = bool(re.search(r"[\uac00-\ud7a3]", text))
    if has_korean_text:
        lowered = [f.lower() for f in fonts]
        if not any(h in f for f in lowered for h in KOREAN_FONT_HINTS):
            result["warnings"].append(
                "한글 텍스트는 있으나 한글 전용 폰트가 임베드되지 않음 "
                f"(사용 폰트: {', '.join(sorted(fonts)) or '없음'}). "
                "대체 폰트로 출력됐거나 글자가 비어 보일 수 있음 → PDF 눈으로 확인 필요")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="KOSTAT xlsx → PDF (LibreOffice)")
    ap.add_argument("input", help="변환할 .xlsx/.xls/.ods 파일")
    ap.add_argument("--outdir", help="PDF 저장 폴더 (기본: 입력 파일 폴더)")
    ap.add_argument("--overwrite", action="store_true",
                    help="같은 이름 PDF가 있으면 덮어쓰기")
    ap.add_argument("--one-page", action="store_true",
                    help="시트마다 1페이지로 출력 (LibreOffice 7.4 이상)")
    args = ap.parse_args()

    src = Path(args.input).resolve()
    if not src.exists():
        print(json.dumps({"status": "fail", "reason": f"입력 파일 없음: {src}"},
                         ensure_ascii=False))
        return 1
    outdir = Path(args.outdir).resolve() if args.outdir else src.parent
    target = outdir / (src.stem + ".pdf")
    if target.exists() and not args.overwrite:
        print(json.dumps({"status": "fail",
                          "reason": f"이미 존재: {target} (--overwrite 필요)"},
                         ensure_ascii=False))
        return 1

    soffice = find_soffice()
    if not soffice:
        print(json.dumps({
            "status": "fail",
            "reason": "LibreOffice(soffice) 미설치. https://www.libreoffice.org 설치 "
                      "또는 SOFFICE_PATH 환경변수 지정"}, ensure_ascii=False))
        return 1

    try:
        pdf = convert(soffice, src, outdir, args.one_page)
    except (RuntimeError, subprocess.TimeoutExpired) as e:
        print(json.dumps({"status": "fail", "reason": str(e)}, ensure_ascii=False))
        return 1

    v = verify(pdf)
    if v["errors"]:
        status, code = "verify_failed", 2
    elif v["warnings"]:
        status, code = "ok_with_warnings", 3
    else:
        status, code = "ok", 0
    print(json.dumps({"status": status, "pdf": str(pdf), "soffice": soffice, **v},
                     ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
