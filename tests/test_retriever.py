import json
import tempfile
import unittest
from pathlib import Path

from src.retrieval.retriever import (
    BM25Retriever,
    TfidfRetriever,
    chunk_to_article,
    load_chunks,
    tokenize,
)


def _chunk(chunk_id: str, article_id: str, text: str) -> dict:
    return {
        "chunk_id": chunk_id,
        "text": text,
        "metadata": {"article_id": article_id},
    }


class TokenizeTests(unittest.TestCase):
    def test_preserves_article_reference_and_adds_bigrams(self) -> None:
        tokens = tokenize("제3조의2 확정일자")

        self.assertIn("§제3조의2", tokens)
        self.assertIn("확정", tokens)
        self.assertIn("정일", tokens)


class BM25RetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks = [
            _chunk("chunk-b", "article-b", "월차임 전환 산정률"),
            _chunk("chunk-a", "article-a", "임차권등기명령 신청"),
        ]

    def test_returns_most_relevant_chunk_first(self) -> None:
        retriever = BM25Retriever(self.chunks, b=0.25)

        results = retriever.search("임차권등기명령", k=2)

        self.assertEqual("chunk-a", results[0][0])
        self.assertGreater(results[0][1], 0)

    def test_respects_k_and_is_deterministic_for_ties(self) -> None:
        chunks = [
            _chunk("chunk-b", "article-b", "같은 표현"),
            _chunk("chunk-a", "article-a", "같은 표현"),
        ]
        retriever = BM25Retriever(chunks)

        self.assertEqual(["chunk-a"], [x[0] for x in retriever.search("같은 표현", k=1)])

    def test_empty_corpus_returns_no_results(self) -> None:
        self.assertEqual([], BM25Retriever([]).search("질문", k=5))

    def test_chunk_to_article_maps_metadata(self) -> None:
        self.assertEqual(
            {"chunk-b": "article-b", "chunk-a": "article-a"},
            chunk_to_article(self.chunks),
        )

    def test_load_chunks_reads_non_empty_jsonl_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "chunks.jsonl"
            path.write_text(
                "\n".join(json.dumps(chunk, ensure_ascii=False) for chunk in self.chunks)
                + "\n\n",
                encoding="utf-8",
            )

            self.assertEqual(self.chunks, load_chunks(path))


class TfidfRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.chunks = [
            _chunk("chunk-b", "article-b", "월차임 전환 산정률"),
            _chunk("chunk-a", "article-a", "임차권등기명령 신청"),
        ]

    def test_returns_most_relevant_chunk_first(self) -> None:
        results = TfidfRetriever(self.chunks).search("월차임 전환", k=2)

        self.assertEqual("chunk-b", results[0][0])
        self.assertGreater(results[0][1], 0)

    def test_returns_no_results_for_unknown_or_empty_corpus(self) -> None:
        self.assertEqual([], TfidfRetriever(self.chunks).search("완전히없는영단어xyz", k=5))
        self.assertEqual([], TfidfRetriever([]).search("질문", k=5))

    def test_ties_are_sorted_by_chunk_id(self) -> None:
        chunks = [
            _chunk("chunk-b", "article-b", "같은 표현"),
            _chunk("chunk-a", "article-a", "같은 표현"),
        ]

        results = TfidfRetriever(chunks).search("같은 표현", k=2)

        self.assertEqual(["chunk-a", "chunk-b"], [item[0] for item in results])


if __name__ == "__main__":
    unittest.main()
