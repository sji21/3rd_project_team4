import json
from pathlib import Path
import unittest

from src.generation.abstention import (
    SCOPE_JUDGE_SYSTEM,
    build_scope_judge_prompt,
    classify_scope,
    is_out_of_scope,
)


class AbstentionTests(unittest.TestCase):
    def test_refuses_direct_contract_safety_verdict(self):
        decision = classify_scope("이 집 계약해도 안전할까요?")

        self.assertTrue(decision.out_of_scope)
        self.assertEqual(decision.reason, "contract_safety_verdict")
        self.assertEqual(decision.source, "deterministic")

    def test_refuses_market_price_lookup(self):
        decision = classify_scope("이 아파트 현재 시세가 얼마인가요?")

        self.assertTrue(decision.out_of_scope)
        self.assertEqual(decision.reason, "market_price_lookup")

    def test_allows_informational_risk_question(self):
        self.assertFalse(
            is_out_of_scope("전세계약 전에 어떤 위험 요소를 확인해야 하나요?")
        )

    def test_allows_legal_question_containing_safe_word(self):
        self.assertFalse(
            is_out_of_scope("안전한 계약을 위해 확정일자는 언제 받아야 하나요?")
        )

    def test_ambiguous_property_verdict_is_not_keyword_refused_without_judge(self):
        decision = classify_scope("이 집 괜찮을까요?")

        self.assertFalse(decision.out_of_scope)
        self.assertTrue(decision.needs_semantic_review)
        self.assertEqual(decision.source, "default_allow")

    def test_semantic_judge_skips_clear_rental_question(self):
        calls = []

        def judge(question):
            calls.append(question)
            return False

        decision = classify_scope(
            "대항력은 언제부터 생기나요?",
            semantic_judge=judge,
        )

        self.assertFalse(decision.out_of_scope)
        self.assertEqual(decision.source, "deterministic")
        self.assertFalse(decision.needs_semantic_review)
        self.assertEqual(calls, [])

    def test_semantic_judge_can_refuse_unrelated_domain(self):
        decision = classify_scope(
            "내일 서울 날씨 알려줘",
            semantic_judge=lambda _: True,
        )

        self.assertTrue(decision.out_of_scope)
        self.assertEqual(decision.reason, "semantic_out_of_scope")
        self.assertEqual(decision.source, "semantic_judge")

    def test_hard_refusal_skips_semantic_judge(self):
        def must_not_run(_):
            raise AssertionError("semantic judge should not run")

        decision = classify_scope(
            "이 집 계약해도 안전할까요?",
            semantic_judge=must_not_run,
        )

        self.assertTrue(decision.out_of_scope)
        self.assertEqual(decision.source, "deterministic")

    def test_semantic_judge_failure_defaults_to_allow(self):
        def broken_judge(_):
            raise RuntimeError("judge unavailable")

        decision = classify_scope(
            "이 집 괜찮을까요?",
            semantic_judge=broken_judge,
        )

        self.assertFalse(decision.out_of_scope)
        self.assertTrue(decision.needs_semantic_review)
        self.assertEqual(decision.source, "default_allow")

    def test_scope_judge_prompt_keeps_typo_tolerant_policy(self):
        prompt = build_scope_judge_prompt("대항력언제생겨요?")

        self.assertIn("대항력언제생겨요?", prompt)
        self.assertIn("오탈자", SCOPE_JUDGE_SYSTEM)
        self.assertIn("ALLOW", SCOPE_JUDGE_SYSTEM)
        self.assertIn("REFUSE", SCOPE_JUDGE_SYSTEM)

    def test_dev_scope_regression(self):
        dev_path = Path("data/eval/dev.jsonl")
        if not dev_path.exists():
            self.skipTest("data/eval/dev.jsonl is not available")

        false_refusals = []
        missed_refusals = []

        with dev_path.open(encoding="utf-8") as file:
            for line in file:
                row = json.loads(line)
                actual = is_out_of_scope(row["question"])
                expected = row["answer_type"] == "out_of_scope"

                if actual and not expected:
                    false_refusals.append(row["qid"])
                if expected and not actual:
                    missed_refusals.append(row["qid"])

        self.assertEqual(false_refusals, [])
        self.assertEqual(missed_refusals, [])


if __name__ == "__main__":
    unittest.main()
