"""공식 안내(가이드) 원문을 수집해 적재용 레코드로 만든다.

법령·판례만으로는 답할 수 없는 질문이 있다. "전세보증금반환보증이 뭔가요?"는
HUG 상품 안내이지 조문이 아니고, "집주인이 세금을 안 냈는지 어떻게 확인하나요?"는
주택임대차보호법 제3조의7 이 열람 권리를 정할 뿐 **어떻게** 열람하는지는 국세청
안내에 있다. 이런 문서가 없으면 검색기가 엉뚱한 조문을 자신 있게 내놓는다.

**원문을 그대로 가져온다.** 요약해서 넣지 않는다. 평가 질문을 보고 쓴 요약문을
코퍼스에 넣으면 그 질문에만 맞는 문서가 되고 측정이 부풀려진다. 이 프로젝트에서
이미 두 번 겪었다(청크 보강 실험, 판례 요약본).

실행:
    python -m src.ingestion.fetch_guides --records data/parsed/guide_records.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass, field
from html import unescape
from pathlib import Path

import requests

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t]+")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class GuideSource:
    """수집할 안내 문서 하나.

    warmup_url 이 있는 페이지가 있다. 국세청은 목록 페이지를 먼저 열어 세션을
    만들지 않으면 본문 없이 빈 껍데기를 돌려준다.
    """

    guide_id: str
    title: str
    agency: str
    guide_type: str
    topic: str
    url: str
    start_marker: str          # 본문이 시작되는 줄에 들어 있는 말
    end_marker: str = ""       # 이 말이 나오면 본문 끝 (없으면 max_lines 까지)
    warmup_url: str = ""
    max_lines: int = 60


SOURCES: tuple[GuideSource, ...] = (
    GuideSource(
        guide_id="guide-HUG-전세보증금반환보증",
        title="HUG 전세보증금반환보증 상품안내",
        agency="주택도시보증공사",
        guide_type="상품안내",
        topic="전세보증금 반환보증",
        url="https://www.khug.or.kr/hug/web/ig/dr/igdr000001.jsp",
        # 상단 메뉴가 600줄 넘게 이어진다. 표 요약문이 본문 시작 지점이다.
        start_marker="전세보증금반환보증 상품 개요",
        end_marker="위탁금융기관",
        max_lines=80,
    ),
    GuideSource(
        guide_id="guide-국세청-미납국세열람",
        title="국세청 미납국세 등 열람신청 안내",
        agency="국세청",
        guide_type="민원안내",
        topic="임대인 미납국세 열람",
        url="https://www.nts.go.kr/nts/na/ntt/selectNttInfo.do?nttSn=1325154&mi=2207",
        # "개요"만 찾으면 좌측 메뉴의 "세무조사 개요"가 먼저 걸린다.
        start_marker="열람신청(주택임차",
        end_marker="첨부파일",
        warmup_url="https://www.nts.go.kr/nts/na/ntt/selectNttList.do?mi=2207",
    ),
)


@dataclass
class GuideRecord:
    """적재용 원천 레코드. load_guides 가 이 형식을 읽는다."""

    guide_id: str
    title: str
    agency: str
    guide_type: str
    topic: str
    source_url: str
    published_at: str
    content: str
    collected_at: str
    status: str = "current"

    def validate(self) -> list[str]:
        problems: list[str] = []
        for name in ("guide_id", "title", "agency", "guide_type", "topic",
                     "source_url", "content", "collected_at"):
            if not str(getattr(self, name)).strip():
                problems.append(f"{name} 이 비어 있음")
        if len(self.content) < 100:
            # 페이지 구조가 바뀌어 본문을 못 잡으면 짧은 조각만 남는다.
            problems.append(f"본문이 {len(self.content)}자뿐이다 (100자 미만)")
        return problems


def html_to_lines(raw: str) -> list[str]:
    """본문 HTML 을 줄 단위 평문으로 만든다.

    `fetch_law_mock.html_to_text` 와 같은 방식이다. 이 저장소에는 bs4·lxml 이
    없으므로 표준 라이브러리만 쓴다.
    """
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|td|tr|li|h\d)>", "\n", text)
    text = unescape(_TAG.sub(" ", text))
    return [ln for ln in (_WS.sub(" ", l).strip() for l in text.split("\n")) if ln]


def extract_body(lines: list[str], source: GuideSource) -> str:
    """머리말·메뉴를 걷어내고 안내 본문만 남긴다.

    공공기관 페이지는 상단 메뉴가 수백 줄이라 통째로 넣으면 청크가 메뉴로 채워진다.
    시작 표시를 찾아 그 지점부터 자른다.
    """
    start = next((i for i, l in enumerate(lines) if source.start_marker in l), -1)
    if start < 0:
        return ""
    body = lines[start : start + source.max_lines]
    if source.end_marker:
        # 첫 줄부터 찾으면 안 된다. 시작 줄이 목차 성격이라 끝 표시를 함께 담고
        # 있는 경우가 있고(HUG 가 그렇다), 그러면 본문이 통째로 잘려 나간다.
        end = next(
            (i for i, l in enumerate(body) if i > 0 and source.end_marker in l),
            len(body),
        )
        body = body[:end]
    # 메뉴 잔재로 남는 한두 글자 줄은 버린다.
    return "\n".join(l for l in body if len(l) > 3)


def fetch(source: GuideSource, session: requests.Session) -> str:
    if source.warmup_url:
        session.get(source.warmup_url, timeout=20)
        time.sleep(0.5)
    response = session.get(source.url, timeout=20)
    response.raise_for_status()
    if not response.encoding or response.encoding.lower() == "iso-8859-1":
        response.encoding = response.apparent_encoding
    return response.text


def collect(sources: tuple[GuideSource, ...] = SOURCES,
            collected_at: str = "") -> tuple[list[GuideRecord], list[str]]:
    collected_at = collected_at or time.strftime("%Y-%m-%d")
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Referer": "https://www.google.com/"})

    records: list[GuideRecord] = []
    problems: list[str] = []
    for source in sources:
        try:
            body = extract_body(html_to_lines(fetch(source, session)), source)
        except Exception as error:                      # 네트워크·파싱 모두
            problems.append(f"{source.guide_id}: {type(error).__name__} {error}")
            continue

        record = GuideRecord(
            guide_id=source.guide_id,
            title=source.title,
            agency=source.agency,
            guide_type=source.guide_type,
            topic=source.topic,
            source_url=source.url,
            published_at=collected_at,   # 안내 페이지에 발행일이 없다. 수집일을 쓴다.
            content=body,
            collected_at=collected_at,
        )
        found = record.validate()
        if found:
            problems.extend(f"{source.guide_id}: {p}" for p in found)
            continue
        records.append(record)
    return records, problems


def main() -> int:
    parser = argparse.ArgumentParser(description="공식 안내 원문을 수집한다")
    parser.add_argument("--records", default="data/parsed/guide_records.jsonl")
    args = parser.parse_args()

    records, problems = collect()
    print(f"\n  수집 {len(records)}/{len(SOURCES)}건")
    for record in records:
        print(f"    {record.guide_id:<34}{len(record.content):>6}자  {record.title}")

    if problems:
        # 페이지 구조가 바뀌면 조용히 빈 문서가 들어간다. 반드시 보이게 한다.
        print(f"\n  실패 {len(problems)}건:")
        for problem in problems:
            print(f"    {problem}")

    if not records:
        print("\n  수집된 문서가 없어 파일을 쓰지 않았습니다.\n")
        return 1

    out = Path(args.records)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
    print(f"\n  원천 레코드 -> {out}\n")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
