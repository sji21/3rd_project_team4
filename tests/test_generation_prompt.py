"""PATCH-019 프롬프트 테스트.

프롬프트 문구를 통째로 비교하지 않는다. 그렇게 하면 표현을 다듬을 때마다
테스트가 깨져서 결국 지워진다. 대신 **깨지면 안 되는 안전 규칙이 프롬프트에
남아 있는지**만 확인한다.
"""

from __future__ import annotations

import unittest

from src.generation import prompt as prompt_module
from src.retrieval.service import Evidence, RetrievalResult


def evidence(rank: int, citation: str, text: str, doc_type: str = "law") -> Evidence:
    return Evidence(
        rank=rank,
        chunk_id=f"{doc_type}-{rank}",
        doc_type=doc_type,
        citation=citation,
        text=text,
        score=1.0,
        source_url="https://law.go.kr/x",
    )


class SystemPromptTests(unittest.TestCase):
    def test_forbids_answering_outside_evidence(self) -> None:
        text = prompt_module.SYSTEM_QA

        self.assertIn("지어내지", text)
        self.assertIn("확인할 수 없습니다", text)

    def test_requires_named_citations_not_numbers(self) -> None:
        """번호 인용을 시키면 안 된다.

        검색 결과의 `[1]` 은 묶음 안 순번이라 법령에도 판례에도 1번이 있다.
        번호로 인용하게 하면 그 인용이 어느 쪽을 가리키는지 알 수 없다.
        """
        text = prompt_module.SYSTEM_QA

        self.assertIn("번호가 아니라 이름으로", text)
        self.assertIn("법원과 사건번호", text)

    def test_requires_verbatim_dates_and_amounts(self) -> None:
        """기간을 요약하면 하루 차이로 권리 순위가 바뀐다.

        실제로 Qwen3 가 "그 다음 날부터"를 "날부터"로 줄여 결론을 틀리게 쓴
        일이 있었다. 그 사례를 프롬프트에 예시로 박아 두었고, 이 테스트는
        그 예시가 지워지지 않았는지 지킨다.
        """
        text = prompt_module.SYSTEM_QA

        self.assertIn("글자 그대로", text)
        self.assertIn("첫 문장", text)

        # ★ "그 다음 날부터" 만 확인하면 안 된다. 그 문자열은 참고 자료 예시 줄에도
        #   있어서, 정작 지켜야 할 ✓/✗ 대조 예시를 지워도 테스트가 통과한다.
        #   (변이 검사에서 실제로 통과해 버리는 것을 확인하고 고쳤다.)
        #   작은 모델은 추상적 지시보다 이 대조 예시에 훨씬 잘 반응하므로
        #   두 줄이 함께 살아 있어야 한다.
        self.assertIn('✓ "마친 그 다음 날부터 효력이 생깁니다"', text)
        self.assertIn('✗ "마친 날부터 효력이 생깁니다"', text)

    def test_conclusion_must_not_paraphrase_periods(self) -> None:
        """'결론을 먼저 요약하라'와 '그대로 옮기라'가 부딪히면 안 된다.

        형식 지침이 뒤에 있어 더 강하게 먹히므로, 형식 쪽에서도 같은 규칙을
        다시 못 박아 둔다.
        """
        self.assertIn("결론 문장에서도", prompt_module.SYSTEM_QA)

    def test_forbids_self_contradiction(self) -> None:
        self.assertIn("표현이 달라지면 안 됩니다", prompt_module.SYSTEM_QA)

    def test_forbids_fabricated_direct_quotes(self) -> None:
        """조문 번호는 맞는데 따옴표 안 내용이 딴 조문인 경우가 실제로 있었다.

        (Qwen3 가 제3조의3 제8항이라며 전혀 다른 문장을 따옴표로 인용했다.)
        조문 번호만 대조하는 citation.py 로는 잡히지 않는 종류라 프롬프트가
        1차 방어선이다.
        """
        text = prompt_module.SYSTEM_QA

        self.assertIn("따옴표로 인용할 때는", text)
        self.assertIn("그대로 적혀 있는 문장만", text)

    def test_forbids_merging_amount_brackets(self) -> None:
        # 서울(5,500만원)을 과밀억제권역(4,800만원) 구간에 합쳐 넣은 사례가 있었다.
        self.assertIn("과밀억제권역", prompt_module.SYSTEM_QA)
        self.assertIn("항목을 합치거나", prompt_module.SYSTEM_QA)

    def test_forbids_writing_urls(self) -> None:
        """출처 링크는 코드가 붙인다.

        모델이 URL을 쓰다가 토큰 상한에 걸려 주소 한가운데서 끊긴 적이 있다.
        """
        self.assertIn("URL이나 링크를 쓰지 마십시오", prompt_module.SYSTEM_QA)

    def test_caps_length_and_forbids_repetition(self) -> None:
        # 400자 목표인데 2,300자까지 나왔고, 같은 문장을 여섯 번 반복했다.
        text = prompt_module.SYSTEM_QA

        self.assertIn("400자를 넘기지 마십시오", text)
        self.assertIn("다시 말하지 마십시오", text)
        self.assertIn("줄글", text)

    def test_separates_law_and_case_weight(self) -> None:
        self.assertIn("같은 무게로 쓰지 마십시오", prompt_module.SYSTEM_QA)

    def test_forbids_verdict_on_user_contract(self) -> None:
        # 전세ON 의 기본 원칙. 이 줄이 사라지면 서비스 성격 자체가 바뀐다.
        self.assertIn("판정하지 마십시오", prompt_module.SYSTEM_QA)
        self.assertIn("판정하지 않습니다", prompt_module.NON_VERDICT_NOTICE)

    def test_no_think_switch_goes_in_the_user_turn(self) -> None:
        """시스템 프롬프트에 두면 무시된다.

        실제로 시스템 쪽에 두었을 때 Qwen3 가 사고 과정에 토큰을 다 써서
        답변이 통째로 비는 일이 있었다. Qwen3 문서가 정한 자리는 사용자 턴이다.
        """
        self.assertNotIn("/no_think", prompt_module.system_prompt())
        self.assertTrue(prompt_module.human_prompt().endswith("/no_think"))


class BuildQaPromptTests(unittest.TestCase):
    def test_takes_context_and_question(self) -> None:
        template = prompt_module.build_qa_prompt()

        self.assertEqual({"context", "question"}, set(template.input_variables))

    def test_renders_both_values(self) -> None:
        rendered = prompt_module.build_qa_prompt().format(
            context="[1] 근거 본문", question="대항력은 언제 생기나요?"
        )

        self.assertIn("[1] 근거 본문", rendered)
        self.assertIn("대항력은 언제 생기나요?", rendered)


class FormatContextTests(unittest.TestCase):
    def test_empty_result_says_no_data(self) -> None:
        result = RetrievalResult(question="아무 질문")

        self.assertIn("검색된 자료가 없습니다", prompt_module.format_context(result))

    def test_keeps_law_and_case_sections_apart(self) -> None:
        result = RetrievalResult(
            question="집주인이 바뀌면?",
            laws=[evidence(1, "주택임대차보호법 제3조", "[주택임대차보호법 제3조(대항력 등)] 본문")],
            cases=[evidence(1, "대법원 2011다49523", "양수인이 지위를 승계한다", "case")],
        )

        context = prompt_module.format_context(result)

        self.assertIn("## 관련 법령", context)
        self.assertIn("## 관련 판례", context)
        self.assertLess(context.index("## 관련 법령"), context.index("## 관련 판례"))

    def test_does_not_duplicate_source_header(self) -> None:
        # 본문이 이미 `[법령명 제N조(제목)]` 로 시작하면 출처를 또 붙이지 않는다.
        result = RetrievalResult(
            question="q",
            laws=[evidence(1, "주택임대차보호법 제3조(대항력 등)", "[주택임대차보호법 제3조(대항력 등)] 본문")],
        )

        context = prompt_module.format_context(result)

        self.assertEqual(1, context.count("주택임대차보호법 제3조(대항력 등)"))


if __name__ == "__main__":
    unittest.main()


class ThinkSwitchLiveReadTests(unittest.TestCase):
    """사고 과정 스위치가 프롬프트와 서버 요청에서 같이 움직이는가.

    import 시점에 값을 복사해 두면, llm.THINK_OFF 가 나중에 바뀌었을 때
    서버에는 think:false 가 가는데 프롬프트에는 /no_think 가 안 붙는다.
    두 겹으로 막으려던 것이 한 겹만 남는다.
    """

    def test_human_prompt_follows_llm_module_at_call_time(self) -> None:
        from src.generation import llm as llm_module

        original = llm_module.THINK_OFF
        try:
            llm_module.THINK_OFF = True
            self.assertTrue(prompt_module.human_prompt().endswith("/no_think"))
            self.assertIs(False, llm_module._extra_body()["think"])

            llm_module.THINK_OFF = False
            self.assertFalse(prompt_module.human_prompt().endswith("/no_think"))
            self.assertNotIn("think", llm_module._extra_body())
        finally:
            llm_module.THINK_OFF = original
