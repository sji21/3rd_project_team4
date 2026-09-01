"""민법 임대차 조문을 법령 코퍼스에 넣었을 때의 검색 영향을 잰다.

넣을지 말지를 정하기 전에 **회귀부터 확인**하려고 만들었다. 코퍼스에 문서를
더하면 기존 질문의 순위가 흔들릴 수 있는데, 흔들림이 정답을 잃는 수준인지
자리만 바뀌는 수준인지는 재보지 않으면 알 수 없다.

저장소의 DB·인덱스·청크 파일은 건드리지 않는다. 지식 DB를 임시 폴더로 복사해
거기에만 민법을 적재하고, Chroma 대신 메모리 임베딩(``DenseRetriever``)으로
변형끼리 같은 조건에서 비교한다.

변형
    base   현재 코퍼스 (법령 133)
    min5   + 민법 5조  제623·626·627·634·640조   (최소 적용 계획 1순위)
    min6   + 민법 6조  min5 + 제621조             (주임법이 본문에서 인용하는 조문)
    max11  + 민법 11조 1·2순위 전부 + 제621조

측정
    A) dev 27문항        법령 gold 조문의 Recall@3/@5 — 회귀 확인
    B) 판례 홀드아웃 20문항  판례 순위가 정말 안 움직이는지 — 구조상 안 움직여야 한다
    C) 신규 20문항        민법 추가 전후 법령 TOP5 변화

실행:
    python scripts/compare_minbeop_corpus.py --out data/eval/runs/minbeop_compare.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.relational import connect_database
from src.ingestion.fetch_law_mock import (
    fetch,
    html_to_text,
    parse_articles,
    parse_law_header,
)
from src.ingestion.load_laws import LawArticleRecord, export_chunks, load_records
from src.retrieval.dense import DenseRetriever, SentenceTransformerEmbedding
from src.retrieval.retriever import load_chunks
from src.retrieval.service import DEFAULT_MODEL, RetrievalService

REPO = Path(__file__).resolve().parents[1]

# 국가법령정보센터 민법. lsiSeq 와 시행일은 법령 페이지에서 확인한 값이다.
MINBEOP_SEQ = "284415"
MINBEOP_EFF = "20260317"

PLAN_TIER1 = ["제623조", "제626조", "제627조", "제634조", "제640조"]
PLAN_TIER2 = ["제624조", "제625조", "제628조", "제629조", "제630조"]
# 주임법 제3조의2·제3조의4 가 본문에서 「민법」 제621조를 인용하는데 코퍼스에
# 없다. 끊어진 참조라 생성 단계에서 환각으로 잡힌 적이 있어 후보로 함께 잰다.
DANGLING = ["제621조"]

VARIANTS: dict[str, list[str]] = {
    "base": [],
    "min5": PLAN_TIER1,
    "min6": PLAN_TIER1 + DANGLING,
    "max11": PLAN_TIER1 + PLAN_TIER2 + DANGLING,
}

# 발표 전 점검용으로 받은 주택임대차 질문. dev 셋과 겹치지 않는다.
NEW_QUESTIONS: list[tuple[int, str]] = [
    (1, "전입신고는 언제까지 해야 하나요?"),
    (2, "확정일자는 꼭 받아야 하나요?"),
    (3, "전입신고와 확정일자를 받으면 보증금을 보호받을 수 있나요?"),
    (4, "집주인이 바뀌어도 기존 계약대로 계속 살 수 있나요?"),
    (5, "계약기간이 끝나기 전에 집주인이 나가라고 할 수 있나요?"),
    (6, "계약이 끝났는데 보증금을 돌려받지 못하면 어떻게 해야 하나요?"),
    (7, "월세를 몇 번 밀리면 집주인이 계약을 끝낼 수 있나요?"),
    (8, "집주인이 갑자기 월세나 보증금을 올려달라고 하면 따라야 하나요?"),
    (9, "계약기간이 끝나면 자동으로 계약이 끝나는 건가요?"),
    (10, "계약을 다시 하고 싶으면 집주인에게 언제 말해야 하나요?"),
    (11, "계약기간이 끝났는데 아무 말 없이 계속 살고 있으면 계약은 어떻게 되나요?"),
    (12, "집주인이 직접 들어와 살겠다고 하면 계약 연장을 거절할 수 있나요?"),
    (13, "계약을 한 번 연장한 뒤에도 다시 계약 연장을 요구할 수 있나요?"),
    (14, "집이 경매로 넘어가면 제 보증금은 돌려받을 수 있나요?"),
    (15, "이사를 먼저 가야 하는데 보증금을 아직 못 받았다면 어떻게 해야 하나요?"),
    (16, "보증금 중에서 다른 사람보다 먼저 돌려받을 수 있는 금액이 따로 있나요?"),
    (17, "집주인이 바뀐 뒤 새 집주인이 계약 내용을 바꾸자고 하면 따라야 하나요?"),
    (18, "계약 연장을 요구했는데 집주인이 직접 산다고 해서 나왔습니다. "
         "그런데 다른 사람에게 다시 세를 놓으면 어떻게 하나요?"),
    (19, "경매가 시작된 집에서 보증금을 보호받으려면 전입신고와 확정일자 중 "
         "어떤 조건을 갖춰야 하나요?"),
    (20, "계약이 자동으로 연장된 상태에서 세입자가 이사를 가고 싶다면 언제 "
         "집주인에게 알려야 하나요?"),
]


def minbeop_records(articles: list[str]) -> list[LawArticleRecord]:
    """민법 원문을 받아 요청한 조문만 적재 레코드로 만든다.

    ``fetch_law_mock`` 의 파서를 그대로 쓴다. 민법은 1,100여 조라 전부 넣으면
    주택임대차 질문이 묻히므로, 여기서 조문을 골라내는 것이 핵심이다.
    """
    text = html_to_text(fetch(MINBEOP_SEQ, MINBEOP_EFF))
    header = parse_law_header(text)
    parsed = {no: (title, body) for no, title, body in parse_articles(text)}

    missing = [no for no in articles if no not in parsed]
    if missing:
        raise ValueError(f"민법 원문에서 찾지 못한 조문: {missing}")

    collected = time.strftime("%Y-%m-%d")
    return [
        LawArticleRecord(
            law_name="민법",
            law_type="법률",
            ministry=header["ministry"] or "법무부",
            law_code=MINBEOP_SEQ,
            proclamation_number=header["proclamation_number"],
            proclaimed_at=header["proclaimed_at"],
            effective_from=header["effective_from"],
            content=parsed[no][1],
            source_url=f"https://www.law.go.kr/법령/민법/{no}",
            collected_at=collected,
            article_number=no,
            article_title=parsed[no][0],
            document_type="law",
            file_path=f"data/raw/law/민법-{MINBEOP_EFF}.txt",
        )
        for no in articles
    ]


def build_law_chunks(articles: list[str], workdir: Path, name: str) -> Path:
    """지식 DB 사본에 민법을 적재하고 법령 청크를 뽑는다. 원본은 안 건드린다."""
    if not articles:
        return REPO / "data/chunks/chunks.jsonl"

    database = workdir / f"kb_{name}.sqlite3"
    shutil.copy2(REPO / "data/database/knowledge.sqlite3", database)
    out = workdir / f"chunks_{name}.jsonl"
    with closing(connect_database(database)) as connection:
        summary = load_records(minbeop_records(articles), connection)
        if summary.skipped:
            raise RuntimeError(f"{name}: 적재 건너뜀 {summary.skipped}")
        export_chunks(connection, out)
    return out


def article_ids(service, chunkmap, question: str, k: int) -> list[str]:
    result = service.search(question, k_law=k, k_case=0, k_guide=0)
    return [chunkmap[e.chunk_id]["article_id"] for e in result.laws]


def case_ids(service, chunkmap, question: str, k: int) -> list[str]:
    result = service.search(question, k_law=0, k_case=k, k_guide=0)
    return [chunkmap[e.chunk_id].get("case_id", "") for e in result.cases]


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="민법 추가가 검색에 주는 영향 측정")
    parser.add_argument("--out", type=Path,
                        default=REPO / "data/eval/runs/minbeop_compare.json")
    parser.add_argument("--k", type=int, default=5, help="법령·판례 상위 몇 건까지 볼지")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    case_path = REPO / "data/chunks/cases.jsonl"
    guide_path = REPO / "data/chunks/guides.jsonl"

    print(f"임베딩 모델 로드: {args.model}", flush=True)
    backend = SentenceTransformerEmbedding(args.model)

    with TemporaryDirectory() as temp:
        workdir = Path(temp)
        services: dict[str, RetrievalService] = {}
        chunkmaps: dict[str, dict] = {}

        for name, articles in VARIANTS.items():
            law_path = build_law_chunks(articles, workdir, name)
            chunks: list[dict] = []
            for path in (law_path, case_path, guide_path):
                chunks.extend(load_chunks(path))
            services[name] = RetrievalService(chunks, DenseRetriever(chunks, backend))
            chunkmaps[name] = {c["chunk_id"]: c["metadata"] for c in chunks}
            print(f"  {name}: 청크 {len(chunks)}건 (민법 {len(articles)}조)", flush=True)

        report: dict = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M"),
            "model": args.model,
            "k": args.k,
            "variants": {name: articles for name, articles in VARIANTS.items()},
        }

        # A) dev 회귀
        print("\n[A] dev 법령 회귀", flush=True)
        report["dev"] = []
        for item in read_jsonl(REPO / "data/eval/dev.jsonl"):
            gold = item.get("gold_articles") or []
            row = {"qid": item["qid"], "question": item["question"], "gold": gold}
            for name in VARIANTS:
                ranked = article_ids(services[name], chunkmaps[name],
                                     item["question"], args.k)
                row[name] = ranked
                row[f"{name}_top3"] = sum(1 for g in gold if g in ranked[:3])
                row[f"{name}_top5"] = sum(1 for g in gold if g in ranked[:5])
            report["dev"].append(row)

        total_gold = sum(len(r["gold"]) for r in report["dev"])
        for name in VARIANTS:
            top3 = sum(r[f"{name}_top3"] for r in report["dev"])
            top5 = sum(r[f"{name}_top5"] for r in report["dev"])
            moved = sum(1 for r in report["dev"] if r["base"][:3] != r[name][:3])
            print(f"  {name:6s} Recall@3 {top3}/{total_gold} "
                  f"({top3 / total_gold:.1%})  Recall@5 {top5}/{total_gold}  "
                  f"TOP3 구성 변동 {moved}문항", flush=True)

        # B) 판례 홀드아웃 — 법령에 뭘 넣든 순위가 움직이면 안 된다
        print("\n[B] 판례 홀드아웃", flush=True)
        report["case_holdout"] = []
        holdout_path = REPO / "data/eval/case_holdout_current_20.jsonl"
        if holdout_path.exists():
            for item in read_jsonl(holdout_path):
                row = {"qid": item["qid"], "gold": item["gold_case_ids"]}
                for name in VARIANTS:
                    row[name] = case_ids(services[name], chunkmaps[name],
                                         item["question"], args.k)
                report["case_holdout"].append(row)
            for name in VARIANTS:
                moved = sum(1 for r in report["case_holdout"] if r["base"] != r[name])
                print(f"  {name:6s} 순위 변동 {moved}건", flush=True)
        else:
            print("  홀드아웃 파일 없음, 건너뜀", flush=True)

        # C) 신규 질문
        print("\n[C] 신규 20문항", flush=True)
        report["new_questions"] = []
        for number, question in NEW_QUESTIONS:
            row = {"no": number, "question": question}
            for name in VARIANTS:
                row[name] = article_ids(services[name], chunkmaps[name],
                                        question, args.k)
            report["new_questions"].append(row)
        for name in VARIANTS:
            moved = [r["no"] for r in report["new_questions"]
                     if r["base"][:3] != r[name][:3]]
            entered = [r["no"] for r in report["new_questions"]
                       if any(a.startswith("민법") for a in r[name][:3])]
            print(f"  {name:6s} TOP3 변동 {moved}  민법 TOP3 진입 {entered}", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"\n  결과: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
