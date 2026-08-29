"""공식 판례 상세 원천 → 표준 CaseRecord 변환 테스트."""

from __future__ import annotations

import json

from src.ingestion.parse_cases import parse_raw_lines


def raw_case(**service_overrides: object) -> dict[str, object]:
    service = {
        "사건번호": "2024다12345",
        "법원명": "대법원",
        "선고일자": "20240102",
        "사건종류명": "민사",
        "사건명": "임대차보증금반환",
        "판결요지": "<p>공식 판결요지를 한 판례의 단일 검색 청크로 사용한다.</p>",
        "판례내용": "공식 판례 상세 응답 본문",
    }
    service.update(service_overrides)
    return {"case_id": "12345", "source_url": "https://example.test/case/12345", "service": service}


def test_parse_raw_lines_creates_standard_official_case_record():
    records, summary = parse_raw_lines(
        [json.dumps(raw_case(), ensure_ascii=False)],
        collected_at="2026-08-30T00:00:00Z",
        source_label="data/raw/case_details.jsonl",
    )

    assert summary.records == 1
    assert summary.skipped == []
    record = records[0]
    assert record.case_id == "12345"
    assert record.decision_date == "2024-01-02"
    assert record.holding == "공식 판결요지를 한 판례의 단일 검색 청크로 사용한다."
    assert record.full_text == record.holding
    assert record.summary_type == "official"


def test_parse_raw_lines_rejects_short_or_duplicate_holdings():
    first = raw_case()
    duplicate = raw_case()
    short = raw_case(**{"판결요지": "짧음", "사건번호": "2024다99999"})

    records, summary = parse_raw_lines(
        [
            json.dumps(first, ensure_ascii=False),
            json.dumps(duplicate, ensure_ascii=False),
            json.dumps(short, ensure_ascii=False),
        ],
        collected_at="2026-08-30T00:00:00Z",
        source_label="data/raw/case_details.jsonl",
    )

    assert len(records) == 1
    assert any("case_id 중복" in reason for reason in summary.skipped)
    assert any("판결요지가 너무 짧음" in reason for reason in summary.skipped)


def test_parse_raw_lines_keeps_largest_public_id_for_same_case_number():
    older = raw_case()
    newer = raw_case()
    newer["case_id"] = "67890"

    records, summary = parse_raw_lines(
        [json.dumps(older, ensure_ascii=False), json.dumps(newer, ensure_ascii=False)],
        collected_at="2026-08-30T00:00:00Z",
        source_label="data/raw/case_details.jsonl",
    )

    assert [record.case_id for record in records] == ["67890"]
    assert any("사건번호 2024다12345" in reason for reason in summary.skipped)
