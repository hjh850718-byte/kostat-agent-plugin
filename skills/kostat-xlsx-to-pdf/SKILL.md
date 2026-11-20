---
name: kostat-xlsx-to-pdf
description: "Excel(xlsx) → PDF 변환 + 자동 검증. 트리거: 'PDF로 뽑아줘', 'PDF 변환', '인보이스 PDF', 'xlsx to pdf', 커미션 인보이스 Phase 3 PDF 출력. LibreOffice headless 직접 호출, 수식 오류(Err:/#REF!/#DIV/0!)와 한글 폰트 대체를 PDF에서 검사."
---

# kostat-xlsx-to-pdf — Excel → PDF 변환 + 검증

커미션 인보이스 등 KOSTAT Excel 결과물을 PDF로 출력한다.
변환 후 PDF 텍스트를 다시 읽어 **수식 오류**와 **한글 폰트 대체**를 자동 검사한다.

## 전제 조건

| 항목 | 내용 | 확인 방법 |
|------|------|----------|
| LibreOffice | 7.4 이상 (`--one-page`용). 무료 | `soffice --version` |
| pypdf | 검증용. 없으면 변환만 하고 경고 | `python -m pip install pypdf` |
| 한글 폰트 | Windows는 맑은 고딕 기본 탑재 | — |

soffice를 못 찾으면 환경변수 `SOFFICE_PATH`에 전체 경로 지정
(예: `C:\Program Files\LibreOffice\program\soffice.exe`).

## 실행

스크립트는 **이 SKILL.md와 같은 폴더**의 `xlsx_to_pdf.py`. 그 절대경로로 실행한다
(Windows에서는 `python3` 대신 `python`).

```
python "<이 SKILL.md 폴더>/xlsx_to_pdf.py" "<입력.xlsx>" --outdir "./결과물" --one-page
```

| 옵션 | 설명 |
|------|------|
| `--outdir` | PDF 저장 폴더. 기본은 입력 파일 폴더. KOSTAT 규칙상 `./결과물/` 사용 |
| `--one-page` | 시트마다 1페이지. 인보이스는 **항상 사용** (열이 다음 장으로 밀리는 문제 방지) |
| `--overwrite` | 같은 이름 PDF 덮어쓰기. 없으면 기존 파일 보호 |

- 파일명: 입력 xlsx 이름 그대로 `.pdf` (예: `20261120_커미션인보이스_REV01.pdf`)
- 모든 시트가 출력된다 (커미션 시트 + SUMMARY 시트)
- 엑셀/리브레오피스가 열려 있어도 임시 프로필을 써서 충돌 없음

## 결과 판정 (종료 코드)

| 코드 | status | 의미 | 조치 |
|------|--------|------|------|
| 0 | `ok` | 변환 + 검증 통과 | 사용자에게 PDF 경로 보고 |
| 3 | `ok_with_warnings` | 변환 OK, 경고 있음 | 경고 내용 그대로 보고. 한글 폰트 경고면 PDF 1페이지를 열어 눈으로 확인 후 보고 |
| 2 | `verify_failed` | **수식 오류 발견** | PDF 사용 금지. 원본 xlsx의 해당 수식 확인 → 수정 → 재변환. 사용자에게 오류 셀 보고 |
| 1 | `fail` | 변환 실패 | reason 보고 (soffice 미설치, 파일 없음, 덮어쓰기 필요 등) |

## 검증 항목

1. **수식 오류**: `Err:xxx`, `#REF!`, `#VALUE!`, `#DIV/0!`, `#NAME?`, `#N/A`, `#NUM!`, `#NULL!`
2. **한글 폰트**: 한글 텍스트가 있는데 맑은 고딕/나눔/Noto KR 등 한글 폰트가 임베드되지 않았으면 경고
3. 페이지 수: 시트 수와 비교해 이상하면 보고 (`--one-page` 기준 페이지 수 = 시트 수)

## 하지 말 것

- **CLI-Anything(`cli-anything-libreoffice`) 사용 금지**: 2026-11-20 테스트에서 xlsx를 자체 JSON으로
  변환하는 과정에 수식이 전부 `Err:510`이 되고 테두리, 열 너비, 글꼴이 사라짐
- openpyxl로 xlsx를 다시 저장한 뒤 변환 금지: 로고 이미지, 인쇄 설정이 손실될 수 있음. 원본 그대로 변환
- `verify_failed` PDF를 고객/상사에게 전달 금지

## 연동

- `kostat-commission-invoice` Phase 3 (최종 저장)에서 인보이스 xlsx 저장 직후 호출
- 결과 보고 형식 예:
  ```
  PDF 출력 완료: ./결과물/20261120_커미션인보이스_REV01.pdf (2페이지, 검증 통과)
  ```
