"""국가법령정보센터 판례 상세 원천 JSONL을 표준 ``CaseRecord`` JSONL로 변환한다.

원천 파일은 수집 시점의 API 응답을 보존하고, 이 모듈은 검색에 필요한 필드만
``data/parsed/case_records.jsonl`` 규격으로 평평하게 만든다. 현재 프로젝트의
판례 청크 규칙은 한 판례의 공식 판결요지 하나를 청크 하나로 쓰는 것이다.

입력 한 줄 예시::

    {"case_id": "233877", "source_url": "...", "service": {
      "사건번호": "2022다255126", "법원명": "대법원", "선고일자": "20230202",
      "판결요지": "..."
    }}

실행::

    python -m src.ingestion.parse_cases \
      --input data/raw/case_details.jsonl \
      --output data/parsed/case_records.jsonl \
      --collected-at 2026-08-30T00:00:00Z
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from src.ingestion.load_cases import CaseRecord, write_case_records


_HTML = re.compile(r"<[^>]*>")
_SPACE = re.compile(r"\s+")
_DATE = re.compile(r"\d{8}")
# 전세ON의 1차 범위. 넓은 민사 판례 목록에서 주택임대차와 무관한 사건을
# 표준 코퍼스에 섞지 않기 위한 선별 기준이다.
HOUSING_SCOPE = re.compile(
    r"주택|임대차|임차인|임대인|보증금|대항력|우선변제|소액임차|"
    r"확정일자|전입|주민등록|임차권"
)
# 1차 수동 범위 검토에서 제외한 명시적 상가임대차 사건이다. "임대차"나 "상가"라는
# 낱말만으로 자동 제외하면 주택 사건의 비교·사실관계 설명까지 빠지므로, 검토 결과를
# 식별자로 고정한다. 범위를 넓힌 별도 코퍼스에는 --include-all을 쓴다.
DEFAULT_EXCLUDED_CASE_IDS = frozenset({"216659", "240969", "619451"})


def clean(value: object) -> str:
    """API의 HTML·줄바꿈을 검색용 평문으로 정리한다."""

    text = _HTML.sub(" ", str(value or "")).replace("&nbsp;", " ")
    return _SPACE.sub(" ", text).strip()


def date_of(value: object) -> str:
    """``YYYYMMDD`` 또는 날짜 문자열을 ``YYYY-MM-DD``로 정규화한다."""

    matched = _DATE.search(str(value or ""))
    if not matched:
        return ""
    digits = matched.group(0)
    return f"{digits[:4]}-{digits[4:6]}-{digits[6:]}"


@dataclass
class ParseSummary:
    records: int = 0
    skipped: list[str] = field(default_factory=list)


def record_from_raw(
    raw: dict[str, object], *, collected_at: str, source_label: str
) -> CaseRecord | None:
    """공식 판례 상세 응답 하나를 서비스 표준 레코드로 바꾼다.

    원천 응답에는 ``service`` 아래에 국가법령정보센터의 한글 키가 들어 있다.
    판결 전문이 있더라도 현재 청크 정책에 따라 ``판결요지``만 ``full_text``에
    넣는다. 전문을 검색하려면 별도 청킹 정책과 평가를 먼저 정해야 한다.
    """

    service = raw.get("service")
    if not isinstance(service, dict):
        return None

    case_id = clean(raw.get("case_id"))
    case_number = clean(service.get("사건번호"))
    court_name = clean(service.get("법원명"))
    decision_date = date_of(service.get("선고일자"))
    case_type = clean(service.get("사건종류명")) or "민사"
    case_name = clean(service.get("사건명"))
    holding = clean(service.get("판결요지"))
    source_url = clean(raw.get("source_url"))
    if not source_url and case_id:
        source_url = f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={case_id}"

    record = CaseRecord(
        case_id=case_id,
        case_number=case_number,
        court_name=court_name,
        decision_date=decision_date,
        case_type=case_type,
        case_name=case_name,
        holding=holding,
        summary=holding,
        full_text=holding,
        source_url=source_url,
        collected_at=collected_at,
        status="current",
        file_path=source_label,
        summary_type="official",
        summary_model=None,
    )
    return record


def is_housing_case(raw: dict[str, object]) -> bool:
    """판결요지·판시사항·사건명 중 하나가 주택임대차 범위인지 확인한다."""

    service = raw.get("service")
    if not isinstance(service, dict):
        return False
    scope_text = " ".join(
        clean(service.get(key)) for key in ("판결요지", "판시사항", "사건명")
    )
    return bool(HOUSING_SCOPE.search(scope_text))


def has_full_official_text(raw: dict[str, object]) -> bool:
    """요지 외에 공식 상세 응답 본문도 받은 건만 신뢰 가능한 입력으로 쓴다."""

    service = raw.get("service")
    return isinstance(service, dict) and bool(clean(service.get("판례내용")))


def parse_raw_lines(
    lines: list[str], *, collected_at: str, source_label: str, min_holding_length: int = 30,
    include_all: bool = False,
) -> tuple[list[CaseRecord], ParseSummary]:
    """원천 줄을 검사하고 중복 없는 표준 레코드를 돌려준다."""

    summary = ParseSummary()
    candidates: list[CaseRecord] = []
    seen_ids: set[str] = set()

    for lineno, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            summary.skipped.append(f"{lineno}번째 줄: JSON 파싱 실패 — {error}")
            continue
        if not isinstance(raw, dict):
            summary.skipped.append(f"{lineno}번째 줄: 객체가 아님")
            continue

        record = record_from_raw(raw, collected_at=collected_at, source_label=source_label)
        if record is None:
            summary.skipped.append(f"{lineno}번째 줄: service 객체가 없음")
            continue
        if not has_full_official_text(raw):
            summary.skipped.append(f"{lineno}번째 줄 {record.case_id}: 공식 판례내용이 없음")
            continue
        if not include_all and record.case_id in DEFAULT_EXCLUDED_CASE_IDS:
            summary.skipped.append(f"{lineno}번째 줄 {record.case_id}: 1차 수동 범위에서 제외한 상가 사건")
            continue
        if not include_all and not is_housing_case(raw):
            summary.skipped.append(f"{lineno}번째 줄 {record.case_id}: 주택임대차 범위 밖")
            continue
        if len(record.holding) < min_holding_length:
            summary.skipped.append(f"{lineno}번째 줄 {record.case_id}: 판결요지가 너무 짧음")
            continue
        problems = record.validate()
        if problems:
            summary.skipped.extend(
                f"{lineno}번째 줄 {record.case_id}: {problem}" for problem in problems
            )
            continue
        if record.case_id in seen_ids:
            summary.skipped.append(f"{lineno}번째 줄 {record.case_id}: case_id 중복")
            continue
        seen_ids.add(record.case_id)
        candidates.append(record)

    # 국가법령정보센터에는 같은 사건번호가 다른 precSeq로 중복 노출되는 경우가 있다.
    # SQLite의 cases.case_number는 고유해야 하므로 하나만 남긴다. 동일 사건이면 더 큰
    # 숫자 precSeq를 표준 식별자로 택한다. 수집 순서와 무관하게 재현되며, 기존 207건
    # 스테이징에서 사용한 공개 식별자와도 일치한다.
    by_number: dict[str, list[CaseRecord]] = {}
    for record in candidates:
        by_number.setdefault(record.case_number, []).append(record)

    records: list[CaseRecord] = []
    for case_number, group in by_number.items():
        def case_id_key(record: CaseRecord) -> tuple[int, str]:
            return (int(record.case_id), record.case_id) if record.case_id.isdecimal() else (-1, record.case_id)

        selected = max(group, key=case_id_key)
        records.append(selected)
        for record in group:
            if record is not selected:
                summary.skipped.append(
                    f"사건번호 {case_number}: {selected.case_id}을 남기고 중복 case_id {record.case_id} 제외"
                )

    # API 수집 순서가 바뀌어도 같은 JSONL 순서가 나오게 한다.
    records.sort(key=lambda record: (record.decision_date, record.case_number, record.case_id))
    summary.records = len(records)
    return records, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="공식 판례 상세 원천을 CaseRecord JSONL로 변환")
    parser.add_argument("--input", required=True, help="공식 판례 상세 원천 JSONL")
    parser.add_argument("--output", default="data/parsed/case_records.jsonl", help="표준 CaseRecord JSONL")
    parser.add_argument(
        "--collected-at", required=True,
        help="원천 수집 시각(예: 2026-08-30T00:00:00Z). 실행 시각으로 바꾸지 않는다.",
    )
    parser.add_argument("--source-label", default=None, help="레코드 file_path에 남길 원천 경로")
    parser.add_argument("--min-holding-length", type=int, default=30)
    parser.add_argument(
        "--include-all", action="store_true",
        help="전세ON 기본 주택임대차 범위와 수동 제외 목록을 적용하지 않는다.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"원천 파일이 없습니다: {input_path}")
        return 1
    if args.min_holding_length < 1:
        print("--min-holding-length는 1 이상이어야 합니다.")
        return 1

    source_label = args.source_label or input_path.as_posix()
    records, summary = parse_raw_lines(
        input_path.read_text(encoding="utf-8").splitlines(),
        collected_at=args.collected_at,
        source_label=source_label,
        min_holding_length=args.min_holding_length,
        include_all=args.include_all,
    )
    write_case_records(records, Path(args.output))

    print(f"  표준 판례 레코드: {args.output} ({summary.records}건)")
    if summary.skipped:
        print(f"  제외: {len(summary.skipped)}건")
        for reason in summary.skipped[:10]:
            print(f"    - {reason}")
        if len(summary.skipped) > 10:
            print(f"    ... 외 {len(summary.skipped) - 10}건")
    return 0


if __name__ == "__main__":
    sys.exit(main())
