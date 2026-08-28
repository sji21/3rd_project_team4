"""질문 하나를 받아 LLM 에 넘길 근거를 뽑는 진입점.

생성 쪽이 검색 내부를 몰라도 되게 하는 것이 목적이다. 돌려주는 것은 청크
딕셔너리가 아니라 본문과 출처가 붙은 `Evidence` 다.

**법령과 판례를 따로 뽑는다.** 한 통에 넣고 뽑으면 서로를 밀어낸다. 두 종류를
섞어 측정했을 때 법령 Hit@5 가 17.4%p 떨어졌다. 질문 하나에 필요한 것은 "근거
조문 몇 개"와 "그 쟁점을 다룬 판례 몇 개"이지 둘을 섞은 상위 5개가 아니다.

나누는 방식이 검색기마다 다르다. 어휘 검색(BM25)은 **코퍼스를 쪼개서** 만든다.
IDF 가 코퍼스 전체 기준이라 "대항력"의 희소성이 법령 133 조문 안에서와 판례
26 건 안에서 다르기 때문이다. 임베딩 쪽은 Chroma 컬렉션 하나를 공유하고
`doc_type` 필터로 가른다. 벡터는 문서마다 독립적이라 쪼갤 이유가 없고, 쪼개면
컬렉션이 늘어 적재만 번거로워진다.

파라미터는 지금 양쪽이 같다. **나눠 둔 것은 구조이지 값이 아니다.** 측정 결과
법령은 b=0.25, 판례는 b=0.75 가 좋았는데(긴 조문이 알맹이인 법령과 달리 판례는
길이를 눌러야 한다) 그 튜닝은 실데이터가 들어온 뒤로 미룬다. 그때 아래 `LAW`/
`CASE` 설정값만 바꾸면 된다.
"""

from __future__ import annotations

import re

from dataclasses import dataclass, field, replace
from pathlib import Path

from src.retrieval.dense import (
    DenseRetriever,
    EmbeddingBackend,
    SentenceTransformerEmbedding,
)
from src.retrieval.hybrid import HybridRetriever, Member
from src.retrieval.retriever import BM25Retriever, Retriever, load_chunks

DEFAULT_MODEL = "nlpai-lab/KURE-v1"
DEFAULT_INDEX = Path("data/index/chroma_kurev1_1024")
LAW_CHUNKS = Path("data/chunks/chunks.jsonl")
CASE_CHUNKS = Path("data/chunks/cases.jsonl")

# 어느 doc_type 이 어느 묶음인지. 시행령·시행규칙은 법령과 함께 다뤄야 한다.
LAW_TYPES = ("law", "decree", "rule")
CASE_TYPES = ("case",)

# 청크 규격의 출처 헤더. docs/chunk-schema.md 와 validate_chunks 가 쓰는 것과 같다.
_HEADER = re.compile(r"^\[.+?\]")


@dataclass(frozen=True)
class Corpus:
    """한 묶음의 검색 설정.

    두 묶음의 값이 지금 같은 것은 의도한 상태다. 튜닝 전까지 기본값을 쓴다.
    """

    name: str
    doc_types: tuple[str, ...]
    bm25_b: float = 0.75
    expand_weight: float = 1.0
    bm25_weight: float = 1.0
    dense_weight: float = 1.0
    exclude_titles: tuple[str, ...] = ()

    def where(self) -> dict:
        """이 묶음만 남기는 메타데이터 필터.

        조건이 둘이면 $and 로 묶는다. Chroma 가 키를 나란히 두는 것을 거부하고,
        메모리 필터도 같은 문법을 받도록 맞춰 두었다.
        """
        conditions: list[dict] = [{"doc_type": {"$in": list(self.doc_types)}}]
        if self.exclude_titles:
            conditions.append({"title": {"$nin": list(self.exclude_titles)}})
        return conditions[0] if len(conditions) == 1 else {"$and": conditions}


LAW = Corpus("법령", LAW_TYPES)
CASE = Corpus("판례", CASE_TYPES)

# 코퍼스에 들어 있는 상가 법령. 주택 질문에서는 빼야 한다.
COMMERCIAL_LAWS = ("상가건물 임대차보호법", "상가건물 임대차보호법 시행령")

# 상가 임대차에서만 쓰는 말들. 주택 질문에는 거의 나오지 않는다.
# "영업" 같은 넓은 말은 넣지 않았다. 오탐이 나면 주택 질문에 상가 조문이 섞인다.
COMMERCIAL_SIGNS = ("상가", "점포", "가게", "사무실", "권리금", "환산보증금")


def mentions_commercial(question: str) -> bool:
    return any(sign in question for sign in COMMERCIAL_SIGNS)


def route_law_corpus(question: str, base: Corpus = LAW) -> Corpus:
    """질문에 맞는 법령 범위를 고른다.

    **기본은 주택이다.** 전세ON 은 주택임대차 서비스이고, 코퍼스의 법령 133청크 중
    57청크(43%)가 상가 법령이라 그대로 두면 주택 질문에서 상가 조문이 상위를
    차지한다. 실제로 "집주인이 바뀌면" 질문에 상가건물 임대차보호법 제5조가
    1위로 올라왔다.

    상가 신호가 있으면 빼지 않는다. **상가로 바꾸는 것이 아니라 제외를 푸는 것**이다.
    "상가주택"처럼 둘 다 걸린 질문에서 주택 조문이 사라지면 안 된다.

    한계: 낱말 표에 없는 표현은 잡지 못한다. 평가셋 27문항에 상가 질문이 하나도
    없어 이 분기는 검색 성능으로 검증하지 못했다. 판정 자체는 테스트로 잠갔다.
    """
    if mentions_commercial(question):
        return replace(base, exclude_titles=())
    return replace(base, exclude_titles=COMMERCIAL_LAWS)


@dataclass(frozen=True)
class Evidence:
    """LLM 에 넘길 근거 한 조각.

    citation 을 따로 두는 이유는 답변에 출처를 적게 하기 위해서다. 본문만 넘기면
    모델이 "관련 법에 따르면" 같은 문장을 쓰고, 사용자는 확인할 방법이 없다.
    """

    rank: int
    chunk_id: str
    doc_type: str
    citation: str
    text: str
    score: float
    source_url: str = ""

    def as_prompt_block(self) -> str:
        """프롬프트에 그대로 넣을 수 있는 한 덩어리.

        청크는 규격상 `[법령명 제N조(제목)]` 헤더로 시작한다 — 현재 코퍼스
        159건 전부가 그렇다. 그 앞에 citation 을 또 붙이면 같은 문장이 두 번
        들어간다. 헤더가 있으면 본문을 그대로 쓴다.

        citation 필드 자체는 남긴다. 화면에 출처만 따로 보여주거나 링크를 걸 때
        본문에서 헤더를 다시 떼어내지 않아도 되기 때문이다.
        """
        if _HEADER.match(self.text):
            return f"[{self.rank}] {self.text}"
        return f"[{self.rank}] {self.citation}\n{self.text}"


@dataclass
class RetrievalResult:
    question: str
    laws: list[Evidence] = field(default_factory=list)
    cases: list[Evidence] = field(default_factory=list)

    def as_prompt_context(self) -> str:
        """법령과 판례를 구분해 붙인 근거 묶음.

        구분을 유지하는 이유가 있다. 판례는 그 사건의 사실관계 위에서 나온 판단이라
        조문과 같은 무게로 읽으면 안 된다. 섞어서 넘기면 모델이 판례의 문장을
        법조문처럼 인용한다.
        """
        parts: list[str] = []
        if self.laws:
            parts.append(
                "## 관련 법령\n" + "\n\n".join(e.as_prompt_block() for e in self.laws)
            )
        if self.cases:
            parts.append(
                "## 관련 판례\n" + "\n\n".join(e.as_prompt_block() for e in self.cases)
            )
        return "\n\n".join(parts)

    def is_empty(self) -> bool:
        return not self.laws and not self.cases


def citation_of(metadata: dict) -> str:
    """청크만 떼어 봐도 어디서 왔는지 알 수 있는 한 줄.

    판례는 사건명만으로 무의미하다 — "추심금", "배당이의"는 여럿이다. 법원과
    사건번호가 있어야 답변에서 인용할 수 있다.
    """
    if metadata.get("doc_type") in CASE_TYPES:
        head = " ".join(
            x for x in (metadata.get("court_name", ""), metadata.get("case_number", "")) if x
        )
        decided = metadata.get("decision_date", "")
        name = metadata.get("title", "")
        tail = f" ({decided} 선고)" if decided else ""
        return f"{head} {name}{tail}".strip()

    label = f"{metadata.get('title', '')} {metadata.get('article_no', '')}".strip()
    article_title = metadata.get("article_title", "")
    return f"{label}({article_title})" if article_title else label


def _to_evidence(rank: int, chunk: dict, score: float) -> Evidence:
    metadata = chunk["metadata"]
    return Evidence(
        rank=rank,
        chunk_id=chunk["chunk_id"],
        doc_type=str(metadata.get("doc_type", "")),
        citation=citation_of(metadata),
        text=chunk["text"],
        score=round(float(score), 4),
        source_url=str(metadata.get("source_url", "")),
    )


def split_by_type(chunks: list[dict], doc_types: tuple[str, ...]) -> list[dict]:
    return [c for c in chunks if c["metadata"].get("doc_type") in doc_types]


class RetrievalService:
    """질문 하나에 법령 TOP-k 와 판례 TOP-k 를 돌려준다.

    임베딩 모델은 한 번만 올린다. KURE-v1 은 2.3GB 라 질의마다 올리면 쓸 수 없다.
    Streamlit 에서는 이 객체를 `@st.cache_resource` 로 감싸면 된다.
    """

    def __init__(
        self,
        chunks: list[dict],
        dense: Retriever | None = None,
        law: Corpus = LAW,
        case: Corpus = CASE,
    ) -> None:
        """chunks 는 법령·판례가 섞여 있어도 된다. doc_type 으로 갈라 쓴다.

        dense 가 None 이면 어휘 검색만으로 동작한다. 임베딩 없이도 결과가 나와야
        인덱스가 아직 없는 환경에서 앱을 띄울 수 있다.
        """
        self.dense = dense
        self.corpora = (law, case)
        self._chunks = {c["chunk_id"]: c for c in chunks}
        self._retrievers = {
            corpus.name: self._build(corpus, split_by_type(chunks, corpus.doc_types))
            for corpus in self.corpora
        }

    def _build(self, corpus: Corpus, chunks: list[dict]) -> HybridRetriever | None:
        """묶음 하나에 대한 검색기. 청크가 없으면 만들지 않는다."""
        if not chunks:
            return None
        members = [
            Member(
                BM25Retriever(chunks, b=corpus.bm25_b),
                f"{corpus.name}-bm25",
                corpus.bm25_weight,
                corpus.expand_weight,
            )
        ]
        if self.dense is not None:
            members.append(
                Member(self.dense, f"{corpus.name}-dense", corpus.dense_weight, 0.0)
            )
        return HybridRetriever(members)

    @classmethod
    def from_index(
        cls,
        chunk_paths: tuple[Path | str, ...] = (LAW_CHUNKS, CASE_CHUNKS),
        index_path: Path | str = DEFAULT_INDEX,
        model: str = DEFAULT_MODEL,
    ) -> "RetrievalService":
        """앱에서 쓰는 방식. 벡터는 Chroma 에서 읽으므로 재임베딩이 없다."""
        from src.retrieval.dense import ChromaRetriever

        chunks = _load_all(chunk_paths)
        backend = SentenceTransformerEmbedding(model)
        return cls(chunks, ChromaRetriever(backend, index_path))

    @classmethod
    def from_files(
        cls,
        chunk_paths: tuple[Path | str, ...] = (LAW_CHUNKS, CASE_CHUNKS),
        backend: EmbeddingBackend | None = None,
    ) -> "RetrievalService":
        """Chroma 없이 메모리에서 임베딩한다. 평가·실험용."""
        chunks = _load_all(chunk_paths)
        backend = backend or SentenceTransformerEmbedding(DEFAULT_MODEL)
        return cls(chunks, DenseRetriever(chunks, backend))

    def _search_one(self, corpus: Corpus, question: str, k: int) -> list[Evidence]:
        # 라우팅으로 만든 사본도 이름은 같다. 검색기는 이름으로 찾는다.
        retriever = self._retrievers.get(corpus.name)
        if retriever is None or k <= 0:
            return []
        # 필터를 함께 넘긴다. BM25 는 이미 쪼갠 코퍼스를 보지만, 공유 Chroma 는
        # 이 필터가 없으면 다른 묶음의 문서까지 끌어온다.
        hits = retriever.search(question, k, corpus.where())
        return [
            _to_evidence(rank, self._chunks[chunk_id], score)
            for rank, (chunk_id, score) in enumerate(hits, start=1)
            if chunk_id in self._chunks
        ]

    def search(self, question: str, k_law: int = 5, k_case: int = 5) -> RetrievalResult:
        """법령 k_law 건, 판례 k_case 건을 각각 뽑는다."""
        law, case = self.corpora
        return RetrievalResult(
            question=question,
            laws=self._search_one(route_law_corpus(question, law), question, k_law),
            cases=self._search_one(case, question, k_case),
        )


def _load_all(paths: tuple[Path | str, ...]) -> list[dict]:
    """있는 파일만 읽어 합친다. 한쪽이 없어도 나머지로 동작해야 한다."""
    chunks: list[dict] = []
    for path in paths:
        path = Path(path)
        if path.exists():
            chunks.extend(load_chunks(path))
    return chunks
