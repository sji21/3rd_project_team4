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
    D) 법령 홀드아웃 20문항  봉인 평가셋의 Recall@3/@5 및 TOP3 오염 확인
    E) 민법 직접 질문 5문항  최소 후보 5개 조문이 실제로 검색되는지 확인

실행:
    python scripts/compare_minbeop_corpus.py --out data/eval/runs/minbeop_compare.json
"""

from __future__ import annotations

import argparse
import hashlib
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
REVIEW_HOLDOUT = REPO / "data/eval/minbeop_review_holdout_20260901.jsonl"

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

MINBEOP_QUESTIONS: list[tuple[str, str, str]] = [
    ("civil-623", "보일러가 고장 났는데 집주인이 수리해야 하나요?", "민법-제623조"),
    ("civil-626", "제가 먼저 낸 수리비를 집주인에게 청구할 수 있나요?", "민법-제626조"),
    ("civil-627", "누수 때문에 방 일부를 쓰지 못하면 월세를 줄일 수 있나요?", "민법-제627조"),
    ("civil-634", "집에 수리가 필요하면 집주인에게 알려야 하나요?", "민법-제634조"),
    ("civil-640", "월세를 두 달치 밀리면 집주인이 계약을 끝낼 수 있나요?", "민법-제640조"),
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
        #
        # 분모는 **법령 정답만** 센다. dev 의 gold_articles 에는 공식 안내 정답
        # (guide-국세청-미납국세열람 등)이 섞여 있는데, 이 비교는 법령 묶음만
        # 검색하므로(k_guide=0) 안내 정답은 구조적으로 도달할 수 없다. 분모에
        # 남기면 천장이 씌워진 수치가 나와 민법 때문에 잃은 것인지 원래 못 찾는
        # 것인지 구분되지 않는다.
        law_gold = {
            metadata["article_id"]
            for metadata in chunkmaps["base"].values()
            if metadata.get("doc_type") in ("law", "decree", "rule")
        }

        print("\n[A] dev 법령 회귀", flush=True)
        report["dev"] = []
        unreachable: list[str] = []
        for item in read_jsonl(REPO / "data/eval/dev.jsonl"):
            gold = item.get("gold_articles") or []
            scored = [g for g in gold if g in law_gold]
            unreachable.extend(g for g in gold if g not in law_gold)
            row = {
                "qid": item["qid"],
                "question": item["question"],
                "gold": gold,
                "law_gold": scored,
            }
            for name in VARIANTS:
                ranked = article_ids(services[name], chunkmaps[name],
                                     item["question"], args.k)
                row[name] = ranked
                row[f"{name}_top3"] = sum(1 for g in scored if g in ranked[:3])
                row[f"{name}_top5"] = sum(1 for g in scored if g in ranked[:5])
            report["dev"].append(row)

        report["unscored_gold"] = unreachable
        if unreachable:
            print(f"  법령 검색으로 도달 불가라 분모에서 제외한 정답 "
                  f"{len(unreachable)}개: {unreachable}", flush=True)

        total_gold = sum(len(r["law_gold"]) for r in report["dev"])
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
        # 생성 파트는 법령 3건만 쓴다(DEFAULT_K_LAW=3). TOP3 에서 밀려난 조문은
        # 순위가 한 칸 내려간 것이 아니라 **생성 근거에서 사라진 것**이므로 따로 센다.
        for name in VARIANTS:
            moved = [r["no"] for r in report["new_questions"]
                     if r["base"][:3] != r[name][:3]]
            entered = [r["no"] for r in report["new_questions"]
                       if any(a.startswith("민법") for a in r[name][:3])]
            dropped = {
                r["no"]: [a for a in r["base"][:3] if a not in r[name][:3]]
                for r in report["new_questions"]
                if [a for a in r["base"][:3] if a not in r[name][:3]]
            }
            report.setdefault("dropped_from_top3", {})[name] = dropped
            print(f"  {name:6s} TOP3 변동 {moved}  민법 TOP3 진입 {entered}", flush=True)
            for number, lost in dropped.items():
                print(f"         {number}번 생성 근거에서 빠짐: {lost}", flush=True)

        # D) 법령 홀드아웃 회귀. out_of_scope 문항은 검색 채점에서 제외한다.
        print("\n[D] 법령 홀드아웃 회귀", flush=True)
        report["law_holdout"] = []
        for item in read_jsonl(REPO / "data/eval/holdout.jsonl"):
            gold = item.get("gold_articles") or []
            if not gold:
                continue
            row = {
                "qid": item["qid"],
                "question": item["question"],
                "gold": gold,
            }
            for name in VARIANTS:
                ranked = article_ids(services[name], chunkmaps[name],
                                     item["question"], args.k)
                row[name] = ranked
                row[f"{name}_top3"] = sum(1 for g in gold if g in ranked[:3])
                row[f"{name}_top5"] = sum(1 for g in gold if g in ranked[:5])
            report["law_holdout"].append(row)

        holdout_gold = sum(len(r["gold"]) for r in report["law_holdout"])
        report["law_holdout_dropped_from_top3"] = {}
        for name in VARIANTS:
            top3 = sum(r[f"{name}_top3"] for r in report["law_holdout"])
            top5 = sum(r[f"{name}_top5"] for r in report["law_holdout"])
            moved = [r["qid"] for r in report["law_holdout"]
                     if r["base"][:3] != r[name][:3]]
            dropped = {
                r["qid"]: [a for a in r["base"][:3] if a not in r[name][:3]]
                for r in report["law_holdout"]
                if [a for a in r["base"][:3] if a not in r[name][:3]]
            }
            report["law_holdout_dropped_from_top3"][name] = dropped
            print(f"  {name:6s} Recall@3 {top3}/{holdout_gold} "
                  f"({top3 / holdout_gold:.1%})  Recall@5 {top5}/{holdout_gold}  "
                  f"TOP3 구성 변동 {moved}", flush=True)
            for qid, lost in dropped.items():
                print(f"         {qid} 생성 근거에서 빠짐: {lost}", flush=True)

        # E) 최소 후보 5개 조문별 직접 질문. 기존 평가셋에 없던 조문은 이 표를
        # 탐색적 확인으로만 사용하며, 채택 수치로 과장하지 않는다.
        print("\n[E] 민법 직접 질문(탐색)", flush=True)
        report["minbeop_questions"] = []
        for qid, question, gold in MINBEOP_QUESTIONS:
            row = {"qid": qid, "question": question, "gold": gold}
            for name in ("min5", "min6", "max11"):
                ranked = article_ids(services[name], chunkmaps[name], question, args.k)
                row[name] = ranked
                row[f"{name}_rank"] = next(
                    (rank for rank, article in enumerate(ranked, 1) if article == gold), 0
                )
            report["minbeop_questions"].append(row)
            print(f"  {qid}: min5 정답 순위 {row['min5_rank'] or '5위 밖'}", flush=True)

        # F) 외부 생성·사전 라벨링·해시 봉인한 민법 검토 전용 평가셋.
        # 이 결과로 민법 구성을 고르므로 독립 최종 holdout 수치로 재사용하지 않는다.
        if REVIEW_HOLDOUT.exists():
            review_hash = hashlib.sha256(REVIEW_HOLDOUT.read_bytes()).hexdigest()
            review_items = read_jsonl(REVIEW_HOLDOUT)
            scored_items = [item for item in review_items if item.get("gold_articles")]
            abstain_items = [item for item in review_items if not item.get("gold_articles")]
            report["review_holdout_sha256"] = review_hash
            report["review_holdout"] = []
            report["review_abstain"] = []

            print("\n[F] 봉인 민법 검토셋", flush=True)
            print(f"  SHA-256 {review_hash}", flush=True)
            for item in scored_items:
                row = {
                    "qid": item["qid"],
                    "question": item["question"],
                    "group": item["group"],
                    "difficulty": item["difficulty"],
                    "answer_type": item["answer_type"],
                    "gold": item["gold_articles"],
                }
                for name in VARIANTS:
                    ranked = article_ids(services[name], chunkmaps[name],
                                         item["question"], args.k)
                    row[name] = ranked
                report["review_holdout"].append(row)

            for item in abstain_items:
                row = {
                    "qid": item["qid"],
                    "question": item["question"],
                    "answer_type": item["answer_type"],
                    "abstain_reason": item["abstain_reason"],
                }
                for name in VARIANTS:
                    row[name] = article_ids(services[name], chunkmaps[name],
                                            item["question"], args.k)
                report["review_abstain"].append(row)

            n = len(report["review_holdout"])
            total_gold = sum(len(row["gold"]) for row in report["review_holdout"])
            report["review_metrics"] = {}
            for name in VARIANTS:
                ranks: list[int] = []
                recalled3 = 0
                recalled5 = 0
                for row in report["review_holdout"]:
                    gold = set(row["gold"])
                    ranked = row[name]
                    ranks.append(next(
                        (rank for rank, article in enumerate(ranked, 1)
                         if article in gold), 0
                    ))
                    recalled3 += sum(article in ranked[:3] for article in gold)
                    recalled5 += sum(article in ranked[:5] for article in gold)
                metrics = {
                    "n": n,
                    "gold_count": total_gold,
                    "hit_at_1": sum(rank == 1 for rank in ranks) / n,
                    "hit_at_3": sum(0 < rank <= 3 for rank in ranks) / n,
                    "hit_at_5": sum(0 < rank <= 5 for rank in ranks) / n,
                    "recall_at_3_micro": recalled3 / total_gold,
                    "recall_at_5_micro": recalled5 / total_gold,
                    "mrr": sum(1 / rank for rank in ranks if rank) / n,
                    "top3_changed_from_base": [
                        row["qid"] for row in report["review_holdout"]
                        if row["base"][:3] != row[name][:3]
                    ],
                    "dropped_from_base_top3": {
                        row["qid"]: [article for article in row["base"][:3]
                                     if article not in row[name][:3]]
                        for row in report["review_holdout"]
                        if [article for article in row["base"][:3]
                            if article not in row[name][:3]]
                    },
                }
                report["review_metrics"][name] = metrics
                print(
                    f"  {name:6s} Hit@1 {metrics['hit_at_1']:.1%}  "
                    f"Hit@3 {metrics['hit_at_3']:.1%}  "
                    f"Recall@3 {recalled3}/{total_gold} "
                    f"({metrics['recall_at_3_micro']:.1%})  "
                    f"MRR {metrics['mrr']:.3f}",
                    flush=True,
                )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    print(f"\n  결과: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
