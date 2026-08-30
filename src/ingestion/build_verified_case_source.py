"""공개 API에서 검증된 판례 상세 응답만 새 변환 원천으로 만든다."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.ingestion.parse_cases import clean
from src.ingestion.refetch_case_details import fetch_detail, oc_from_environment, write_jsonl_atomically


@dataclass
class VerifiedSourceSummary:
    candidates: int = 0
    accepted: int = 0
    unavailable: list[dict[str, str]] = field(default_factory=list)


def unique_candidate_ids(paths: list[Path]) -> list[str]:
    identifiers: list[str] = []
    seen: set[str] = set()
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            raw = json.loads(line)
            case_id = clean(raw.get("case_id"))
            if case_id and case_id not in seen:
                identifiers.append(case_id)
                seen.add(case_id)
    return identifiers


def build_verified_source(case_ids: list[str], *, oc: str, delay: float) -> tuple[list[dict[str, object]], VerifiedSourceSummary]:
    summary = VerifiedSourceSummary(candidates=len(case_ids))
    records: list[dict[str, object]] = []
    for case_id in case_ids:
        try:
            service, reason = fetch_detail(case_id, oc)
        except Exception as error:
            service, reason = None, f"API 요청 실패: {error}"
        if service is None:
            summary.unavailable.append({
                "case_id": case_id,
                "source_url": f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={case_id}",
                "reason": reason,
            })
        else:
            official_id = clean(service.get("판례정보일련번호")) or case_id
            records.append({
                "case_id": official_id,
                "source_url": f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={official_id}",
                "service": service,
            })
            summary.accepted += 1
        if delay:
            time.sleep(delay)
    return records, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="공개 API 검증 판례 상세 원천 생성")
    parser.add_argument("--candidates", required=True, nargs="+", help="후보 JSONL(복수 가능)")
    parser.add_argument("--output", required=True, help="검증된 공식 상세 원천 JSONL")
    parser.add_argument("--report", required=True, help="수집 불가 사유 보고서 JSON")
    parser.add_argument("--oc-env-file", default=None)
    parser.add_argument("--delay", type=float, default=0.1)
    args = parser.parse_args()
    candidate_paths = [Path(path) for path in args.candidates]
    case_ids = unique_candidate_ids(candidate_paths)
    records, summary = build_verified_source(
        case_ids,
        oc=oc_from_environment(Path(args.oc_env_file) if args.oc_env_file else None),
        delay=args.delay,
    )
    output_path, report_path = Path(args.output), Path(args.report)
    write_jsonl_atomically(records, output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(asdict(summary), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"공식 검증 후보 {summary.candidates}건 -> 사용 가능 {summary.accepted}건 · 수집 불가 {len(summary.unavailable)}건")
    print(f"원천: {output_path}\n보고서: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
