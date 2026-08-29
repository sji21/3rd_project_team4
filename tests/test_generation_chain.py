"""PATCH-021 생성 체인 테스트.

임베딩 모델(2.3GB)도 Ollama 도 쓰지 않는다. 검색은 실제 `RetrievalService` 를
메모리 청크로 만들어(dense=None → 어휘 검색만) 그대로 쓰고, LLM 만 가짜로 바꾼다.
확인하려는 것은 답변 품질이 아니라 **흐름이 세 갈래로 정확히 갈리는지**, 그리고
근거·출처·면책 문구가 규칙대로 붙는지다.
"""

from __future__ import annotations

import unittest

from src.generation import chain as chain_module
from src.generation import prompt as prompt_module
from src.generation.chain import answer_question, build_qa_chain
from src.generation.llm import get_llm
from src.retrieval.service import RetrievalService


def law_chunk(chunk_id: str, text: str, no: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": "law-주택임대차보호법",
        "text": text,
        "metadata": {
            "title": "주택임대차보호법",
            "doc_type": "law",
            "article_id": f"주택임대차보호법-{no}",
            "article_no": no,
            "article_title": "대항력 등",
            "source_url": "https://law.go.kr/x",
            "status": "current",
        },
    }


def case_chunk(chunk_id: str, text: str, number: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": f"case-{chunk_id}",
        "text": text,
        "metadata": {
            "title": "건물인도",
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
    law_chunk(
        "law1",
        "[주택임대차보호법 제3조(대항력 등)] 임차인이 주택의 인도와 주민등록을 마친 때에는 "
        "그 다음 날부터 제3자에 대하여 효력이 생긴다",
        "제3조",
    ),
    law_chunk(
        "law2",
        "[주택임대차보호법 제3조의2(보증금의 회수)] 확정일자를 갖춘 임차인은 후순위권리자보다 "
        "우선하여 보증금을 변제받을 권리가 있다",
        "제3조의2",
    ),
    case_chunk("case1", "임차주택이 양도되면 양수인이 임대인의 지위를 승계한다", "2011다49523"),
]

QUESTION = "대항력은 언제부터 생기나요?"


def build_service() -> RetrievalService:
    """어휘 검색만 쓰는 진짜 서비스. 모델을 내려받지 않는다."""
    return RetrievalService(CHUNKS, dense=None)


class SpyService:
    """검색이 실제로 불렸는지 세는 대역."""

    def __init__(self) -> None:
        self.calls = 0
        self._inner = build_service()

    def search(self, question, k_law=5, k_case=5, k_guide=2):
        self.calls += 1
        return self._inner.search(question, k_law=k_law, k_case=k_case, k_guide=k_guide)


class AnswerQuestionTests(unittest.TestCase):
    def test_answerable_question_uses_evidence_and_appends_disclaimer(self) -> None:
        answer = answer_question(
            QUESTION,
            service=build_service(),
            llm=get_llm(fake_responses=["주택임대차보호법 제3조에 따라 다음 날부터 생깁니다."]),
        )

        self.assertEqual("answered", answer.status)
        self.assertIn(prompt_module.DISCLAIMER, answer.text)
        self.assertGreater(len(answer.laws), 0)

    def test_raw_text_excludes_code_added_disclaimer(self) -> None:
        """인용 검증은 모델이 실제로 쓴 문장만 봐야 한다.

        면책 문구를 raw_text 에 섞으면, 거기 든 표현을 모델의 인용으로 세게 된다.
        """
        answer = answer_question(
            QUESTION, service=build_service(), llm=get_llm(fake_responses=["답변 본문"])
        )

        self.assertEqual("답변 본문", answer.raw_text)
        self.assertNotIn(prompt_module.DISCLAIMER, answer.raw_text)

    def test_think_block_is_removed_from_answer(self) -> None:
        # Qwen3 의 사고 과정이 화면에 새면 안 된다. 사고 과정에만 등장한 조문
        # 번호(제99조)가 답변에 남으면 인용 검증도 무력해진다.
        answer = answer_question(
            QUESTION,
            service=build_service(),
            llm=get_llm(fake_responses=["<think>제99조를 쓸까 고민</think>제3조에 따릅니다."]),
        )

        self.assertNotIn("<think>", answer.text)
        self.assertNotIn("제99조", answer.text)
        self.assertIn("제3조에 따릅니다.", answer.text)

    def test_empty_question_abstains_without_calling_llm(self) -> None:
        # 검색 쪽이 빈 질문에 빈 결과를 주기로 되어 있다. llm 을 주지 않았으므로
        # 여기서 LLM 을 부르면 Ollama 접속 시도로 이어져 테스트가 느려지거나 깨진다.
        answer = answer_question("   ", service=build_service(), llm=None)

        self.assertEqual("abstained", answer.status)
        self.assertIn(prompt_module.NO_EVIDENCE_TEXT, answer.text)
        self.assertEqual((), answer.evidences)

    def test_refuse_check_skips_retrieval_and_llm(self) -> None:
        """범위 밖 질문은 검색조차 하지 않는다.

        답하면 안 되는 질문에 근거를 모아 주는 일 자체를 막는 것이 목적이다.
        """
        spy = SpyService()

        answer = answer_question(
            "이 집 계약해도 안전할까요?",
            service=spy,
            llm=None,
            refuse_check=lambda q: "안전할까요" in q,
        )

        self.assertEqual("refused", answer.status)
        self.assertEqual(0, spy.calls)
        self.assertIn(prompt_module.NON_VERDICT_NOTICE, answer.text)

    def test_default_refuse_check_is_off(self) -> None:
        # 범위 판정은 abstention.py 담당이다. 여기서 임시 규칙을 만들어 두면
        # 나중에 진짜 정책과 어긋난 채로 굳는다.
        answer = answer_question(
            "이 집 계약해도 안전할까요?",
            service=build_service(),
            llm=get_llm(fake_responses=["설명"]),
        )

        self.assertNotEqual("refused", answer.status)


    def test_empty_model_output_does_not_become_a_blank_answer(self) -> None:
        """사고 과정이 토큰 예산을 다 쓰면 걷어낸 뒤 빈 문자열만 남는다.

        실제로 8문항 중 3문항이 이렇게 빈 답변으로 나왔다. 화면에 빈 칸을
        보여주는 대신 상황을 알려야 한다.
        """
        answer = answer_question(
            QUESTION, service=build_service(), llm=get_llm(fake_responses=["   "])
        )

        self.assertEqual("abstained", answer.status)
        self.assertIn(prompt_module.GENERATION_FAILED_TEXT, answer.text)
        # 근거는 찾았으므로 출처는 남긴다 — 근거 부족과 구별된다.
        self.assertGreater(len(answer.laws), 0)


class EvidenceBudgetTests(unittest.TestCase):
    """근거를 몇 건 넘기느냐가 답변 정확도를 좌우했다.

    법령5·판례5 로 넘겼을 때 8B 모델이 초점을 잃고 오답을 냈고, 3·2 로 줄이자
    같은 질문 세 건이 전부 정답으로 바뀌었다. 누가 "검색이 5건 주니까 5건 쓰자"
    며 되돌리지 않도록 값 자체를 잠근다.
    """

    def test_defaults_are_smaller_than_what_retrieval_offers(self) -> None:
        from src.generation import chain as chain_module

        self.assertEqual(3, chain_module.DEFAULT_K_LAW)
        self.assertEqual(2, chain_module.DEFAULT_K_CASE)
        self.assertEqual(2, chain_module.DEFAULT_K_GUIDE)

    def test_defaults_reach_the_retrieval_service(self) -> None:
        class Spy:
            def __init__(self) -> None:
                self.kwargs: dict = {}
                self._inner = build_service()

            # 기본값을 실제와 다른 센티넬로 둔다. chain 이 값을 넘기지 않으면
            # 이 값이 그대로 보여 누락이 드러난다.
            def search(self, question, k_law=99, k_case=99, k_guide=99):
                self.kwargs = {"k_law": k_law, "k_case": k_case, "k_guide": k_guide}
                return self._inner.search(
                    question, k_law=k_law, k_case=k_case, k_guide=k_guide
                )

        spy = Spy()
        answer_question(QUESTION, service=spy, llm=get_llm(fake_responses=["답변"]))

        self.assertEqual({"k_law": 3, "k_case": 2, "k_guide": 2}, spy.kwargs)


class SourceDedupTests(unittest.TestCase):
    def test_blank_citations_are_not_merged(self) -> None:
        """citation 이 빈 근거들이 한 줄로 뭉개지면 안 된다."""
        from src.generation.models import Answer
        from src.retrieval.service import Evidence

        def ev(i):
            return Evidence(rank=i, chunk_id=f"c{i}", doc_type="law", citation="",
                            text="본문", score=1.0, source_url=f"http://x/{i}")

        answer = Answer("q", "answered", "t", laws=(ev(1), ev(2)), cases=(ev(3),))

        self.assertEqual(3, len(answer.sources()))


class ContextHandoffTests(unittest.TestCase):
    def test_law_and_case_are_passed_separately(self) -> None:
        """법령과 판례를 섞어 넘기면 모델이 판례 문장을 법조문처럼 인용한다."""
        service = build_service()
        result = service.search("집주인이 바뀌면 보증금은 어떻게 되나요?")
        context = prompt_module.format_context(result)

        self.assertIn("## 관련 법령", context)
        self.assertIn("## 관련 판례", context)

    def test_sources_are_deduplicated_and_carry_urls(self) -> None:
        answer = answer_question(
            QUESTION, service=build_service(), llm=get_llm(fake_responses=["답변"])
        )
        sources = answer.sources()

        self.assertEqual(len(sources), len({s["label"] for s in sources}))
        for source in sources:
            self.assertTrue(source["label"])
            self.assertTrue(source["url"])


class BuildQaChainTests(unittest.TestCase):
    def test_chain_returns_clean_string(self) -> None:
        chain = build_qa_chain(get_llm(fake_responses=["<think>혼잣말</think>본문"]))

        output = chain.invoke({"context": "[1] 근거", "question": "질문"})

        self.assertEqual("본문", output)




def boom_llm():
    """호출하면 터지는 LLM 대역. Ollama 가 꺼져 있는 상황을 흉내낸다."""
    from langchain_core.runnables import RunnableLambda

    def explode(_):
        raise ConnectionError("Ollama 에 연결할 수 없습니다")

    return RunnableLambda(explode)


class LlmFailureTests(unittest.TestCase):
    """LLM 호출이 실패해도 세 갈래 안에서 끝나는가.

    예외를 그대로 흘리면 answered·abstained·refused 로만 끝난다는 약속이 깨지고,
    부르는 쪽마다 try/except 를 따로 달아야 한다.
    """

    def test_connection_error_becomes_abstained(self) -> None:
        answer = answer_question(QUESTION, service=build_service(), llm=boom_llm())

        self.assertEqual("abstained", answer.status)
        self.assertIn(prompt_module.GENERATION_FAILED_TEXT, answer.text)
        self.assertIn(prompt_module.DISCLAIMER, answer.text)
        # 근거는 이미 찾았으므로 화면에 남긴다.
        self.assertGreater(len(answer.laws), 0)


class DefaultServiceCacheTests(unittest.TestCase):
    """검색 서비스 캐시가 재사용되고, 리셋으로 풀리는가.

    인덱스를 못 열면 어휘 검색만 하는 서비스가 캐시에 굳는다. 인덱스를 만든
    뒤 그 상태를 푸는 방법이 reset_default_service() 하나뿐이다.
    """

    def setUp(self) -> None:
        chain_module.reset_default_service()
        self.addCleanup(chain_module.reset_default_service)

    def test_service_is_built_once_and_reset_clears_it(self) -> None:
        built = []

        def fake_build():
            built.append(1)
            return build_service()

        original = chain_module._build_service
        chain_module._build_service = fake_build
        try:
            first = chain_module.get_default_service()
            second = chain_module.get_default_service()
            self.assertIs(first, second)
            self.assertEqual(1, len(built))

            chain_module.reset_default_service()
            third = chain_module.get_default_service()
            self.assertIsNot(first, third)
            self.assertEqual(2, len(built))
        finally:
            chain_module._build_service = original


# ★ article_id 는 검색의 GUIDE_TOPICS 가 쓰는 guide_id 와 같아야 한다.
#   다르면 주제 필터에 걸려 어떤 k_guide 값에도 0건이 나오고, 테스트가 아무것도
#   검증하지 못한 채 통과한다.
HUG_GUIDE_ID = "guide-HUG-전세보증금반환보증"


def guide_chunk(chunk_id: str, text: str, agency: str, topic: str,
                guide_id: str = HUG_GUIDE_ID) -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": guide_id,
        "text": text,
        "metadata": {
            "title": agency,
            "doc_type": "guide",
            "article_id": guide_id,
            "topic": topic,
            "source_url": "https://example.kr/guide",
            "status": "current",
        },
    }


class GuideEvidenceTests(unittest.TestCase):
    """검색이 낸 안내가 Answer 와 출처 목록까지 실제로 따라오는가.

    검색이 안내를 프롬프트에 실어 보내므로 모델이 그것을 인용한다. Answer 가
    안내를 버리면 인용 검증(citation.py)이 근거에 없는 출처로 보고 환각으로 잡는다.
    """

    QUESTION_GUIDE = "전세보증금반환보증은 어떤 제도인가요?"

    def setUp(self) -> None:
        guide = guide_chunk(
            "guide1",
            "[주택도시보증공사(전세보증금반환보증)] 보증기관이 임차인에게 보증금을 대신 지급합니다.",
            "주택도시보증공사",
            "전세보증금반환보증",
        )
        self.service = RetrievalService(CHUNKS + [guide], dense=None)

    def test_retrieved_guide_reaches_answer_and_sources(self) -> None:
        answer = answer_question(
            self.QUESTION_GUIDE,
            service=self.service,
            llm=get_llm(fake_responses=["주택도시보증공사 안내에 따르면 보증기관이 대신 지급합니다."]),
        )

        self.assertEqual(1, len(answer.guides), "검색이 낸 안내가 Answer 까지 오지 않았습니다")
        self.assertIn(answer.guides[0], answer.evidences)
        self.assertIn(
            "주택도시보증공사(전세보증금반환보증)",
            [source["label"] for source in answer.sources()],
        )

    def test_k_guide_zero_turns_guides_off(self) -> None:
        answer = answer_question(
            self.QUESTION_GUIDE,
            service=self.service,
            llm=get_llm(fake_responses=["확인할 수 없습니다."]),
            k_guide=0,
        )
        self.assertEqual((), answer.guides)


class StubService:
    """정해진 결과를 그대로 돌려주는 검색 대역. 주제 판정을 우회한다."""

    def __init__(self, result) -> None:
        self.result = result

    def search(self, question, k_law=5, k_case=5, k_guide=2):
        return self.result


class GuideOnEveryExitTests(unittest.TestCase):
    """answered 뿐 아니라 실패 갈래에서도 안내가 실려 나오는가.

    답변을 못 만들어도 근거는 이미 찾았으므로 화면에 보여줘야 한다. 세 자리 중
    하나라도 빠뜨리면 "실패했을 때만 안내 출처가 사라지는" 재현 어려운 버그가 된다.
    """

    def setUp(self) -> None:
        from src.retrieval.service import Evidence, RetrievalResult

        guide = Evidence(
            rank=1,
            chunk_id="guide1",
            doc_type="guide",
            citation="주택도시보증공사(전세보증금반환보증)",
            text="보증기관이 임차인에게 보증금을 대신 지급합니다.",
            score=1.0,
            source_url="https://example.kr/guide",
        )
        law = Evidence(
            rank=1,
            chunk_id="law1",
            doc_type="law",
            citation="주택임대차보호법 제3조(대항력 등)",
            text="그 다음 날부터 제3자에 대하여 효력이 생긴다",
            score=1.0,
            source_url="https://law.go.kr/x",
        )
        self.service = StubService(
            RetrievalResult(question=QUESTION, laws=[law], guides=[guide])
        )

    def test_answered(self) -> None:
        answer = answer_question(
            QUESTION, service=self.service, llm=get_llm(fake_responses=["정상 답변입니다."])
        )
        self.assertEqual("answered", answer.status)
        self.assertEqual(1, len(answer.guides))

    def test_empty_answer(self) -> None:
        answer = answer_question(
            QUESTION, service=self.service, llm=get_llm(fake_responses=["   "])
        )
        self.assertEqual("abstained", answer.status)
        self.assertEqual(1, len(answer.guides))

    def test_llm_failure(self) -> None:
        answer = answer_question(QUESTION, service=self.service, llm=boom_llm())
        self.assertEqual("abstained", answer.status)
        self.assertEqual(1, len(answer.guides))


class FallbackCorpusTests(unittest.TestCase):
    """인덱스 없이 뜨는 폴백이 검색과 같은 청크 묶음을 읽는가.

    Chroma 를 못 열면 어휘 검색만으로 동작한다. 이때 읽는 청크 목록이 검색의
    `from_index` 기본값과 어긋나면 특정 묶음만 조용히 사라진 채 서비스가 뜨고,
    그 상태가 캐시에 굳는다. 안내(guide)가 추가됐을 때 실제로 그랬다.
    """

    def test_fallback_reads_the_same_paths_as_from_index(self) -> None:
        import inspect

        from src.retrieval.service import RetrievalService as Service

        expected = inspect.signature(Service.from_index).parameters["chunk_paths"].default
        self.assertEqual(tuple(expected), tuple(chain_module.fallback_chunk_paths()))

if __name__ == "__main__":
    unittest.main()
