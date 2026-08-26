"""검색기(Retriever).

검색 방식이 무엇이든 아래 인터페이스만 지키면 평가 하네스가 그대로 돌아간다.

    search(query, k) -> [(chunk_id, score), ...]   점수 내림차순

지금은 외부 API 없이 돌아가는 BM25(어휘 기반)만 구현되어 있다.
임베딩 기반 Dense 검색은 팀원의 인덱싱 파이프라인이 준비되면
같은 인터페이스로 DenseRetriever 를 추가하면 된다.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Iterable, Protocol

# 한글 음절 / 한자 / 영숫자 덩어리를 하나의 낱말로 끊는다.
_WORD_RE = re.compile(r"[가-힣]+|[一-龥]+|[A-Za-z]+|[0-9]+")
# "제3조의2", "제88조" 같은 조문 지시어. 법령 검색에서 가장 중요한 정확일치 신호.
_ARTICLE_RE = re.compile(r"제\d+조(?:의\d+)?(?:제\d+항)?")


def tokenize(text: str, char_ngram: int = 2) -> list[str]:
    """한국어 검색용 토큰화.

    형태소 분석기 없이도 쓸 만하게 만들기 위해 세 종류를 섞는다.
      1. 낱말 그대로        — "확정일자", "임차권등기명령"
      2. 낱말 내부 문자 n-gram — 조사가 붙어 표기가 흔들려도 매칭되게
      3. 조문 지시어         — "제3조의2" 를 통째로 한 토큰으로 보존

    3번이 없으면 "제3조"와 "제3조의2"가 문자 n-gram 상에서 거의 구분되지 않는다.
    """
    tokens: list[str] = []

    for article in _ARTICLE_RE.findall(text):
        tokens.append(f"§{article}")

    for word in _WORD_RE.findall(text):
        tokens.append(word)
        if len(word) > char_ngram:
            for i in range(len(word) - char_ngram + 1):
                tokens.append(word[i : i + char_ngram])

    return tokens


class Retriever(Protocol):
    """모든 검색기가 지켜야 할 최소 약속."""

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        ...


class BM25Retriever:
    """문서 안에 질의어가 얼마나 자주, 얼마나 드물게 등장하는지로 점수를 매기는 고전 검색기.

    k1: 같은 단어가 반복 등장할 때 점수가 얼마나 더 오를지 (클수록 반복을 더 인정)
    b : 긴 문서에 얼마나 불이익을 줄지 (0이면 길이 무시, 1이면 길이로 완전 정규화)
    """

    def __init__(
        self,
        chunks: list[dict],
        k1: float = 1.5,
        b: float = 0.75,
        char_ngram: int = 2,
    ) -> None:
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.char_ngram = char_ngram

        self.chunk_ids = [c["chunk_id"] for c in chunks]
        self.doc_tokens = [tokenize(c["text"], char_ngram) for c in chunks]
        self.doc_freqs = [Counter(toks) for toks in self.doc_tokens]
        self.doc_lens = [len(toks) for toks in self.doc_tokens]
        self.avg_len = sum(self.doc_lens) / len(self.doc_lens) if self.doc_lens else 0.0

        n_docs = len(chunks)
        df: Counter[str] = Counter()
        for freqs in self.doc_freqs:
            df.update(freqs.keys())
        # 표준 BM25 IDF. 흔한 토큰일수록 0에 가까워진다.
        self.idf = {
            term: math.log(1 + (n_docs - n + 0.5) / (n + 0.5)) for term, n in df.items()
        }

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        q_tokens = tokenize(query, self.char_ngram)
        scores: list[tuple[str, float]] = []

        for i, freqs in enumerate(self.doc_freqs):
            score = 0.0
            norm = self.k1 * (1 - self.b + self.b * self.doc_lens[i] / self.avg_len)
            for term in q_tokens:
                tf = freqs.get(term)
                if not tf:
                    continue
                score += self.idf.get(term, 0.0) * tf * (self.k1 + 1) / (tf + norm)
            if score > 0:
                scores.append((self.chunk_ids[i], score))

        # 동점일 때 순서가 흔들리면 같은 설정을 두 번 돌려도 점수가 달라진다.
        # chunk_id 를 2차 정렬 기준으로 두어 결정론적으로 만든다.
        scores.sort(key=lambda x: (-x[1], x[0]))
        return scores[:k]


def load_chunks(path: str | Path) -> list[dict]:
    """chunks jsonl 을 읽어 리스트로 돌려준다."""
    chunks = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


def chunk_to_article(chunks: Iterable[dict]) -> dict[str, str]:
    """chunk_id -> article_id 매핑.

    평가 정답은 조문 단위로 잡고, 검색 결과(청크)를 이 표로 조문으로 환산해서 채점한다.
    청킹 방식이 바뀌어 chunk_id 가 전부 달라져도 평가셋은 그대로 쓸 수 있다.
    """
    return {c["chunk_id"]: c["metadata"]["article_id"] for c in chunks}
