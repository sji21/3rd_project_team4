"""청크를 임베딩해 Chroma 컬렉션에 적재한다.

입력은 SQLite 조인 결과를 평평하게 뽑은 청크 JSONL 이다
(`src.ingestion.load_laws.export_chunks` 산출물). Chroma 에는 JOIN 이 없으므로
필터에 쓸 값이 이미 메타데이터에 들어 있어야 하고, 그 규격은
docs/chunk-schema.md 를 따른다.

임베딩은 여기서 직접 계산해 넘긴다. `embeddings=` 를 생략하면 Chroma 가 기본
모델(영어 중심)을 붙여 한국어 성능이 떨어진다.

실행:
    python -m src.retrieval.index --chunks data/chunks/chunks.jsonl
    python -m src.retrieval.index --chunks <파일> --model BAAI/bge-m3
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from src.database.config import resolve_database_paths
from src.retrieval.dense import EmbeddingBackend, SentenceTransformerEmbedding
from src.retrieval.retriever import load_chunks

DEFAULT_MODEL = "nlpai-lab/KURE-v1"
DEFAULT_COLLECTION = "knowledge_chunks"

# Chroma metadata 는 스칼라만 받는다. 값이 없으면 None 이 아니라 빈 문자열로 넣는다.
SCALARS = (str, int, float, bool)


@dataclass(frozen=True)
class IndexSummary:
    path: Path
    collection: str
    model: str
    dimension: int
    indexed: int
    seconds: float
    removed: int = 0


def index_dir_for(model_id: str, dimension: int, root: Path = Path("data/index")) -> Path:
    """모델과 차원을 디렉토리 이름에 남긴다.

    차원은 컬렉션마다 하나만 존재하므로, 모델을 바꾸면 컬렉션을 새로 만들어야 한다.
    이름으로 구분해 두면 두 모델을 나란히 두고 비교할 수 있다.
    """
    short = model_id.split("/")[-1].replace("-", "").lower()
    return root / f"chroma_{short}_{dimension}"


def clean_metadata(metadata: dict) -> dict:
    """Chroma 가 받을 수 있는 형태로 정리한다.

    None 과 리스트는 적재 시점에 예외를 일으킨다. 리스트는 "|" 로 이어 붙이고
    None 은 빈 문자열로 바꾼다. 조회 후 복원은 split("|").
    """
    out: dict = {}
    for key, value in metadata.items():
        if value is None:
            out[key] = ""
        elif isinstance(value, (list, tuple)):
            out[key] = "|".join(str(v) for v in value)
        elif isinstance(value, SCALARS):
            out[key] = value
        else:
            out[key] = str(value)
    return out


def build_index(
    chunks: Sequence[dict],
    backend: EmbeddingBackend,
    path: Path | None = None,
    collection_name: str = DEFAULT_COLLECTION,
    batch: int = 128,
) -> IndexSummary:
    import chromadb

    started = time.perf_counter()
    vectors = backend.embed([c["text"] for c in chunks])
    dimension = len(vectors[0]) if vectors else 0

    target = path or index_dir_for(backend.name, dimension)
    target.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(target))
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "hnsw:space": "cosine",
            "description": f"법령·판례 RAG 청크 ({backend.name}, {dimension}차원)",
        },
    )

    # upsert 라 같은 chunk_id 를 다시 넣어도 중복이 생기지 않는다.
    for i in range(0, len(chunks), batch):
        window = chunks[i : i + batch]
        collection.upsert(
            ids=[c["chunk_id"] for c in window],
            documents=[c["text"] for c in window],
            embeddings=vectors[i : i + batch],
            metadatas=[clean_metadata(c["metadata"]) for c in window],
        )

    # upsert 만으로는 이번 입력에서 빠진 청크가 컬렉션에 남는다. 조문이 삭제되거나
    # 코퍼스를 줄여 다시 색인하면 옛 문서가 계속 검색되므로 여기서 지운다.
    incoming = {c["chunk_id"] for c in chunks}
    existing = set(collection.get(include=[])["ids"])
    stale = sorted(existing - incoming)
    if stale:
        for i in range(0, len(stale), batch):
            collection.delete(ids=stale[i : i + batch])

    return IndexSummary(
        path=target,
        collection=collection.name,
        model=backend.name,
        dimension=dimension,
        indexed=collection.count(),
        seconds=round(time.perf_counter() - started, 2),
        removed=len(stale),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="청크를 Chroma 에 적재")
    ap.add_argument("--chunks", default="data/chunks/chunks.jsonl")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--collection", default=DEFAULT_COLLECTION)
    ap.add_argument("--path", default=None,
                    help="생략하면 JEONSEON_CHROMA_PATH, 없으면 모델·차원으로 결정")
    args = ap.parse_args()

    chunks_path = Path(args.chunks)
    if not chunks_path.exists():
        print(f"청크 파일이 없습니다: {chunks_path}")
        return 1

    chunks = load_chunks(chunks_path)
    print(f"\n  청크 {len(chunks)}건 · 모델 {args.model}")
    print("  임베딩 계산 중 …")

    # 경로 결정은 한 곳으로 모은다. 인덱서와 scripts/init_databases.py 가 서로 다른
    # 폴더를 쓰면 빈 컬렉션과 실제 색인이 갈라진다.
    target: Path | None = None
    if args.path:
        target = Path(args.path)
    elif os.getenv("JEONSEON_CHROMA_PATH", "").strip():
        target = resolve_database_paths().chroma

    backend = SentenceTransformerEmbedding(args.model)
    summary = build_index(
        chunks,
        backend,
        path=target,
        collection_name=args.collection,
    )

    print()
    print(f"  인덱스: {summary.path}")
    print(f"  컬렉션: {summary.collection}  ({summary.indexed}건, "
          f"{summary.dimension}차원)")
    print(f"  소요: {summary.seconds}초\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
