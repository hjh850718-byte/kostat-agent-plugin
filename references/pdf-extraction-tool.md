# PO PDF 추출 도구 — opendataloader-pdf

> `kostat-po-update`, `kostat-hk-po-update` 공통 참조 자료
> PO PDF의 "PDF 읽기" 단계에서 표가 깨지거나 레이아웃이 복잡한 문서를 처리할 때 사용한다.

---

## 언제 쓰나

| 상황 | 방식 |
|------|------|
| 텍스트 기반 단순 PO (표 구조 단순) | 기존 방식(Read 도구 직접 읽기)으로 충분 → 그대로 진행 |
| 표가 다단/병합 셀이라 컬럼이 밀려 읽히는 PO | opendataloader-pdf **hybrid 모드**로 재추출 |
| 스캔본(이미지) PO라 텍스트 추출이 안 되는 경우 | opendataloader-pdf **OCR 모드**(`--force-ocr --ocr-lang "ko,en"`) |
| 추출 결과를 근거로 원본 PDF 위치를 요약본에 인용해야 할 때 | JSON 출력의 `bounding box`/`page number`로 인용 좌표 확보 |

기본 원칙: **먼저 일반 방식으로 PO PDF를 읽고**, 필드가 누락되거나(Cust PN, Need By Date, Ship To 등) 표가 깨진 것으로 판단되면 opendataloader-pdf로 재추출한다. 모든 PO마다 무조건 실행할 필요는 없음(속도/토큰 절약).

---

## 설치

```bash
pip install -U opendataloader-pdf
# 복잡한 표/스캔본 처리가 필요하면 hybrid 확장 포함 설치
pip install -U "opendataloader-pdf[hybrid]"
```

Windows 환경 규칙(CLAUDE.md 준수): 실행 시 항상 `python -m opendataloader_pdf ...` 또는 CLI 진입점 `opendataloader-pdf`를 사용하고, `python3` 표기는 사용하지 않는다.

---

## CLI 사용법

**기본 추출 (JSON + Markdown 동시 출력)**
```bash
opendataloader-pdf "PO-8934_KOSTAT.pdf" --format json,markdown --output ./pdf-extract/
```

**표가 깨진 복잡한 레이아웃 → hybrid 모드**
```bash
# 터미널 1: 백엔드 기동
opendataloader-pdf-hybrid --port 5002

# 터미널 2: 변환 실행
opendataloader-pdf --hybrid docling-fast "PO-8934_KOSTAT.pdf" --format json --output ./pdf-extract/
```

**스캔본(이미지) PO → OCR 모드**
```bash
opendataloader-pdf-hybrid --port 5002 --force-ocr --ocr-lang "ko,en"
opendataloader-pdf --hybrid docling-fast "scanned_po.pdf" --format json --output ./pdf-extract/
```

---

## 출력(JSON) 구조 → PO 필드 매핑

각 요소는 다음 키를 가진다.

| 키 | 설명 |
|----|------|
| `type` | heading / paragraph / table / list / image 등 |
| `page number` | 1-index 페이지 번호 |
| `bounding box` | `[left, bottom, right, top]` (PDF point 좌표) |
| `content` | 추출된 텍스트 (표는 셀 구조 포함) |

**적용 방법**:
1. `type: "table"` 요소에서 PO#, Cust PN, Need By Date, Ship To, Remarks, TEMP(또는 HK PO의 품목/수량/단가/납기/Invoice#) 컬럼을 파싱한다.
2. 필드 매핑 규칙은 기존과 동일 — [field-mapping.md](field-mapping.md)(미국오더), [xview-mapping.md](xview-mapping.md)(HK/Amkor)를 그대로 따른다.
3. `page number` + `bounding box`는 po-summaries 마크다운의 인용 각주(예: `(p.1, PDF 좌표 참조)`)로만 보조 활용 — Excel 컬럼에는 넣지 않는다.

---

## 주의사항

- 로컬 실행 도구이므로 사내 PO 데이터가 외부 서버로 전송되지 않음 — 보안 요건 충족.
- hybrid 모드는 별도 백엔드 프로세스(`opendataloader-pdf-hybrid`)가 떠 있어야 동작 — 1회성 PO 처리에는 배보다 배꼽이 클 수 있으니, 표가 실제로 깨졌을 때만 사용.
- 추출 결과가 기존 방식과 다르면 **Excel 반영 전 필드 값을 상호 대조**하고, 불일치 시 사용자 확인 후 진행(기존 중복 PO# 처리 규칙과 동일한 원칙).
