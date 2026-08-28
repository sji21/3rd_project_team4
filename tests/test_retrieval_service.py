"""PATCH-018 검색 진입점 테스트.

임베딩 모델(2.3GB)을 내려받지 않도록 가짜 Dense 검색기를 쓴다. 확인하려는 것은
검색 품질이 아니라 **법령과 판례가 섞이지 않고 따로 나오는지**, 그리고 생성 쪽이
쓸 출처가 제대로 붙는지다.
"""

from __future__ import annotations

import unittest

from src.retrieval.retriever import matches
from src.retrieval.service import (
    CASE,
    COMMERCIAL_LAWS,
    LAW,
    Corpus,
    Evidence,
    RetrievalService,
    citation_of,
    route_law_corpus,
    split_by_type,
)


def law_chunk(chunk_id: str, text: str, no: str, title: str = "주택임대차보호법",
              doc_type: str = "law") -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": f"law-{title}",
        "text": text,
        "metadata": {
            "title": title,
            "doc_type": doc_type,
            "article_id": f"{title}-{no}",
            "article_no": no,
            "article_title": "대항력 등",
            "source_url": "https://law.go.kr/x",
            "status": "current",
        },
    }


def case_chunk(chunk_id: str, text: str, number: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": f"case-document:{chunk_id}",
        "text": text,
        "metadata": {
            "title": "추심금",
            "doc_type": "case",
            "article_id": chunk_id,
            "court_name": "대법원",
            "case_number": number,
            "decision_date": "2013-01-17",
            "source_url": "https://law.go.kr/y",
            "status": "current",
        },
    }


CHUNKS = [
    law_chunk("law1", "임차인이 주택의 인도와 주민등록을 마친 때에는 대항력이 생긴다", "제3조"),
    law_chunk("law2", "보증금은 후순위권리자보다 우선하여 변제받을 권리가 있다", "제3조의2"),
    law_chunk("dec1", "우선변제를 받을 임차인의 범위는 다음과 같다", "제10조",
              title="주택임대차보호법 시행령", doc_type="decree"),
    case_chunk("case1", "임차주택이 양도되면 양수인이 임대인의 지위를 승계한다", "2011다49523"),
    case_chunk("case2", "공동임차인 중 1명의 대항력은 임대차 전체에 미친다", "2021다238650"),
]


class FakeDense:
    """모든 청크를 고정 순서로 돌려주는 Dense 대역.

    프로토콜이 요구하는 `search(query, k, where)` 만 구현한다. where 를 실제로
    적용해야 공유 컬렉션에서 묶음이 갈리는지 확인할 수 있다.
    """

    def __init__(self, chunks: list[dict]) -> None:
        self.chunks = chunks
        self.calls: list[tuple[str, int, dict | None]] = []

    def search(self, query, k, where=None):
        self.calls.append((query, k, where))
        # 실제 Chroma 와 같은 필터 의미를 쓴다. 직접 해석하면 $and 를 놓친다.
        hits = [
            (c["chunk_id"], 1.0 - i * 0.01)
            for i, c in enumerate(self.chunks)
            if matches(c["metadata"], where)
        ]
        return hits[:k]


def build(dense: bool = True) -> RetrievalService:
    return RetrievalService(CHUNKS, FakeDense(CHUNKS) if dense else None)


class SeparationTests(unittest.TestCase):
    """법령과 판례가 섞이면 안 된다."""

    def test_laws_and_cases_come_back_separately(self):
        result = build().search("집주인이 바뀌면 보증금은?", k_law=3, k_case=2)
        self.assertTrue(all(e.doc_type in LAW.doc_types for e in result.laws))
        self.assertTrue(all(e.doc_type in CASE.doc_types for e in result.cases))

    def test_decrees_are_grouped_with_laws(self):
        """시행령은 법령과 함께 다뤄야 한다. 따로 빠지면 근거가 반쪽이 된다."""
        result = build().search("우선변제를 받을 임차인의 범위", k_law=5, k_case=5)
        self.assertIn("dec1", [e.chunk_id for e in result.laws])

    def test_each_side_respects_its_own_k(self):
        result = build().search("대항력", k_law=2, k_case=1)
        self.assertEqual(len(result.laws), 2)
        self.assertEqual(len(result.cases), 1)

    def test_zero_k_skips_that_side(self):
        result = build().search("대항력", k_law=3, k_case=0)
        self.assertEqual(result.cases, [])
        self.assertTrue(result.laws)

    def test_shared_dense_index_is_filtered_per_corpus(self):
        """Chroma 는 컬렉션 하나를 공유한다. 필터가 빠지면 판례가 법령 쪽에 섞인다."""
        dense = FakeDense(CHUNKS)
        RetrievalService(CHUNKS, dense).search("대항력", k_law=3, k_case=3)
        filters = [call[2] for call in dense.calls]
        self.assertIn({"doc_type": {"$in": list(CASE.doc_types)}}, filters)
        # 법령 쪽은 라우팅이 상가 제외를 더해 $and 로 나간다
        law_filter = next(f for f in filters if f != filters[-1])
        self.assertTrue(
            any(c.get("doc_type") == {"$in": list(LAW.doc_types)}
                for c in law_filter["$and"])
        )

    def test_bm25_is_built_per_corpus_not_shared(self):
        """IDF 가 코퍼스 전체 기준이라 쪼개지 않으면 서로의 점수를 왜곡한다."""
        service = build(dense=False)
        law_bm25 = service._retrievers["법령"].members[0].retriever
        case_bm25 = service._retrievers["판례"].members[0].retriever
        self.assertEqual(len(law_bm25.chunks), 3)
        self.assertEqual(len(case_bm25.chunks), 2)


class CitationTests(unittest.TestCase):
    """출처가 없으면 모델이 "관련 법에 따르면" 이라고 쓴다."""

    def test_case_citation_carries_court_and_number(self):
        text = citation_of(CHUNKS[3]["metadata"])
        self.assertIn("대법원", text)
        self.assertIn("2011다49523", text)
        self.assertIn("2013-01-17", text)

    def test_law_citation_carries_article_number(self):
        text = citation_of(CHUNKS[0]["metadata"])
        self.assertIn("주택임대차보호법", text)
        self.assertIn("제3조", text)

    def test_evidence_keeps_text_and_source_url(self):
        result = build().search("대항력", k_law=1, k_case=0)
        evidence = result.laws[0]
        self.assertTrue(evidence.text)
        self.assertTrue(evidence.source_url)
        self.assertEqual(evidence.rank, 1)


class PromptContextTests(unittest.TestCase):
    def test_context_labels_the_two_kinds(self):
        """판례를 조문과 같은 무게로 읽으면 안 되므로 구분을 유지한다."""
        context = build().search("집주인이 바뀌면", k_law=2, k_case=2).as_prompt_context()
        self.assertIn("## 관련 법령", context)
        self.assertIn("## 관련 판례", context)
        self.assertLess(context.index("## 관련 법령"), context.index("## 관련 판례"))

    def test_context_omits_an_empty_section(self):
        context = build().search("대항력", k_law=2, k_case=0).as_prompt_context()
        self.assertNotIn("## 관련 판례", context)

    def test_blocks_carry_the_citation(self):
        context = build().search("집주인이 바뀌면", k_law=0, k_case=1).as_prompt_context()
        self.assertIn("2011다49523", context)


class DegradedInputTests(unittest.TestCase):
    """데이터가 덜 갖춰진 상태에서도 나머지로 돌아가야 한다."""

    def test_works_without_a_dense_retriever(self):
        """인덱스가 아직 없어도 어휘 검색만으로 앱을 띄울 수 있어야 한다."""
        result = build(dense=False).search("대항력", k_law=3, k_case=3)
        self.assertTrue(result.laws)
        self.assertTrue(result.cases)

    def test_missing_case_corpus_still_returns_laws(self):
        laws_only = split_by_type(CHUNKS, LAW.doc_types)
        result = RetrievalService(laws_only, FakeDense(laws_only)).search("대항력")
        self.assertTrue(result.laws)
        self.assertEqual(result.cases, [])
        self.assertFalse(result.is_empty())

    def test_empty_corpus_returns_empty_result(self):
        result = RetrievalService([], None).search("대항력")
        self.assertTrue(result.is_empty())
        self.assertEqual(result.as_prompt_context(), "")


class ConfigTests(unittest.TestCase):
    def test_corpus_parameters_are_currently_identical(self):
        """지금 값이 같은 것은 의도한 상태다. 나눈 것은 구조이지 값이 아니다.

        튜닝할 때 이 테스트가 깨지면 그때 기대값을 바꾸면 된다.
        """
        self.assertEqual(LAW.bm25_b, CASE.bm25_b)
        self.assertEqual(LAW.expand_weight, CASE.expand_weight)

    def test_tuning_one_corpus_does_not_touch_the_other(self):
        tuned = Corpus("법령", LAW.doc_types, bm25_b=0.25)
        service = RetrievalService(CHUNKS, None, law=tuned)
        self.assertEqual(service._retrievers["법령"].members[0].retriever.b, 0.25)
        self.assertEqual(service._retrievers["판례"].members[0].retriever.b, CASE.bm25_b)


if __name__ == "__main__":
    unittest.main()


class RoutingTests(unittest.TestCase):
    """전세ON 은 주택 서비스다. 기본 범위가 주택이어야 한다.

    코퍼스의 법령 133청크 중 57청크(43%)가 상가 법령이라, 빼지 않으면 주택
    질문에서 상가 조문이 상위를 차지한다. 실제로 "집주인이 바뀌면" 질문에
    상가건물 임대차보호법 제5조가 1위로 올라왔다.
    """

    HOUSING = [
        "전세 사는 중에 집주인이 바뀌면 보증금은 어떻게 되나요?",
        "대항력은 언제부터 생기나요?",
        "묵시적 갱신이면 기간이 얼마가 되나요?",
        "월세로 전환할 때 상한이 있나요?",
    ]
    COMMERCIAL = [
        "상가 임대차도 계약갱신요구권이 있나요?",
        "점포를 넘길 때 권리금은 어떻게 되나요?",
        "환산보증금을 넘으면 어떤 차이가 있나요?",
        "사무실 임대차도 같은 법이 적용되나요?",
    ]

    def test_housing_questions_exclude_commercial_laws(self):
        for question in self.HOUSING:
            with self.subTest(question=question):
                self.assertEqual(
                    route_law_corpus(question).exclude_titles, COMMERCIAL_LAWS
                )

    def test_commercial_questions_keep_commercial_laws(self):
        for question in self.COMMERCIAL:
            with self.subTest(question=question):
                self.assertEqual(route_law_corpus(question).exclude_titles, ())

    def test_commercial_signal_widens_instead_of_switching(self):
        """상가로 바꾸는 것이 아니라 제외를 푸는 것이다.

        "상가주택"처럼 둘 다 걸린 질문에서 주택 조문이 사라지면 안 된다.
        """
        corpus = route_law_corpus("상가주택인데 주택 부분만 전세로 살고 있어요")
        self.assertEqual(corpus.exclude_titles, ())
        self.assertEqual(corpus.doc_types, LAW.doc_types)

    def test_routing_keeps_the_tuned_parameters(self):
        """범위만 바꾸고 파라미터는 건드리지 않는다."""
        tuned = Corpus("법령", LAW.doc_types, bm25_b=0.25)
        self.assertEqual(route_law_corpus("대항력", tuned).bm25_b, 0.25)


class WhereClauseTests(unittest.TestCase):
    """Chroma 는 조건이 둘 이상이면 $and 를 요구한다."""

    def test_single_condition_stays_flat(self):
        self.assertEqual(CASE.where(), {"doc_type": {"$in": list(CASE.doc_types)}})

    def test_two_conditions_are_wrapped_in_and(self):
        where = route_law_corpus("대항력은 언제 생기나요?").where()
        self.assertIn("$and", where)
        self.assertEqual(len(where["$and"]), 2)

    def test_memory_filter_understands_the_same_clause(self):
        """같은 필터를 BM25 와 Chroma 에 그대로 넘길 수 있어야 한다."""
        where = route_law_corpus("대항력은 언제 생기나요?").where()
        housing = {"doc_type": "law", "title": "주택임대차보호법"}
        commercial = {"doc_type": "law", "title": COMMERCIAL_LAWS[0]}
        self.assertTrue(matches(housing, where))
        self.assertFalse(matches(commercial, where))

    def test_or_clause_is_supported_too(self):
        where = {"$or": [{"doc_type": "law"}, {"doc_type": "case"}]}
        self.assertTrue(matches({"doc_type": "case"}, where))
        self.assertFalse(matches({"doc_type": "guide"}, where))


class PromptBlockTests(unittest.TestCase):
    """청크 159건 전부가 출처 헤더로 시작한다. 앞에 또 붙이면 두 번 들어간다."""

    def test_header_is_not_repeated(self):
        evidence = Evidence(1, "c1", "law", "주택임대차보호법 제3조",
                            "[주택임대차보호법 제3조(대항력 등)]\n임차인이 인도와 주민등록을",
                            0.5)
        block = evidence.as_prompt_block()
        self.assertEqual(block.count("주택임대차보호법 제3조"), 1)
        self.assertTrue(block.startswith("[1] ["))

    def test_citation_is_added_when_the_text_has_no_header(self):
        evidence = Evidence(1, "c1", "law", "주택임대차보호법 제3조",
                            "임차인이 인도와 주민등록을 마친 때", 0.5)
        block = evidence.as_prompt_block()
        self.assertIn("주택임대차보호법 제3조", block)
        self.assertIn("임차인이 인도와", block)

    def test_citation_field_survives_for_the_ui(self):
        """본문에서 헤더를 다시 떼어내지 않아도 되도록 필드는 남긴다."""
        result = build().search("대항력", k_law=1, k_case=0)
        self.assertTrue(result.laws[0].citation)
