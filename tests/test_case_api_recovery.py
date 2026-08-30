"""판례 공개 API 복구 도구의 네트워크 없는 계약 테스트."""

from __future__ import annotations

import json
from pathlib import Path

from src.ingestion.build_verified_case_source import build_verified_source, unique_candidate_ids
from src.ingestion.refetch_case_details import oc_from_environment, refetch_records
from src.ingestion.resolve_case_ids import Candidate, exact_matches, resolve_candidates


def detail_service(**overrides: object) -> dict[str, object]:
    service = {
        "사건번호": "2024다12345",
        "법원명": "대법원",
        "선고일자": "20240102",
        "사건명": "임대차보증금반환",
        "판결요지": "공식 판결요지",
        "판례내용": "공식 판례 전문",
    }
    service.update(overrides)
    return service


def test_oc_reads_repository_variable_from_env_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("LAW_OPEN_API_OC", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=unused\nLAW_OPEN_API_OC=team-oc\n", encoding="utf-8")

    assert oc_from_environment(env_file) == "team-oc"


def test_refetch_only_replaces_completely_missing_detail(monkeypatch) -> None:
    requested: list[str] = []

    def fake_fetch(case_id: str, oc: str):
        requested.append(case_id)
        return detail_service(), ""

    monkeypatch.setattr("src.ingestion.refetch_case_details.fetch_detail", fake_fetch)
    records, summary = refetch_records(
        [
            {"case_id": "missing", "source_url": "https://example.test/missing", "service": {}},
            {"case_id": "partial", "source_url": "https://example.test/partial", "service": {"사건번호": "2024다9"}},
        ],
        oc="team-oc",
        delay=0,
    )

    assert requested == ["missing"]
    assert summary.attempted == summary.recovered == 1
    assert records[0]["service"] == detail_service()
    assert records[1]["service"] == {"사건번호": "2024다9"}


def test_verified_source_deduplicates_candidate_ids_and_reports_unavailable(tmp_path: Path, monkeypatch) -> None:
    candidate_file = tmp_path / "candidates.jsonl"
    candidate_file.write_text(
        "\n".join(json.dumps(item) for item in ({"case_id": "1"}, {"case_id": "1"}, {"case_id": "2"})) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "src.ingestion.build_verified_case_source.fetch_detail",
        lambda case_id, oc: (detail_service(**{"판례정보일련번호": "official-1"}), "") if case_id == "1" else (None, "필수 필드 누락"),
    )

    assert unique_candidate_ids([candidate_file]) == ["1", "2"]
    records, summary = build_verified_source(["1", "2"], oc="team-oc", delay=0)
    assert [record["case_id"] for record in records] == ["official-1"]
    assert summary.candidates == 2 and summary.accepted == 1
    assert summary.unavailable[0]["case_id"] == "2"


def test_resolver_requires_unique_exact_match(monkeypatch) -> None:
    candidate = Candidate("old-1", "2024다12345", "대법원", "2024-01-02")
    result = {"사건번호": "2024다12345", "법원명": "대법원", "선고일자": "20240102", "판례일련번호": "new-1"}
    assert exact_matches(candidate, [result]) == [result]
    monkeypatch.setattr("src.ingestion.resolve_case_ids.search_by_case_number", lambda number, oc: [result])

    summary = resolve_candidates([candidate], oc="team-oc")
    assert summary.resolved == {"old-1": "new-1"}

    monkeypatch.setattr(
        "src.ingestion.resolve_case_ids.search_by_case_number",
        lambda number, oc: [result, {**result, "판례일련번호": "new-2"}],
    )
    summary = resolve_candidates([candidate], oc="team-oc")
    assert summary.resolved == {}
    assert summary.unresolved[0]["reason"] == "정확 일치 판례가 여러 건"
