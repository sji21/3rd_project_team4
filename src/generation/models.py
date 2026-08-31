"""생성 파트가 주고받는 공용 데이터 모델.

검색 쪽 산출물(`src.retrieval.service.Evidence`)을 그대로 재사용한다. 생성
전용으로 새 근거 타입을 만들면 같은 것을 두 번 정의하게 되고, 검색 쪽이 필드를
늘릴 때마다 옮겨 담는 코드가 따라 늘어난다.

여기 있는 것은 **답변 한 건의 결과**뿐이다. 프롬프트 문구는 prompt.py,
LLM 접속은 llm.py, 흐름은 chain.py 가 맡는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.retrieval.service import Evidence

# answered  : 근거를 찾아 LLM 이 답을 만든 경우
# abstained : 근거가 부족해 답을 만들지 않은 경우 (검색은 했다)
# refused   : 서비스 범위 밖이라 검색 전에 돌려보낸 경우
AnswerStatus = Literal["answered", "abstained", "refused"]


@dataclass(frozen=True)
class Answer:
    """사용자에게 돌려줄 답변 한 건.

    `text` 는 화면에 그대로 띄울 최종 문구(면책 문구 포함)이고, `raw_text` 는
    LLM 본문에 근거로 확정할 수 있는 한정적 시점 교정만 적용한 검증 대상이다.
    둘을 나눠 두는 이유는 인용 검증(citation.py)·근거 밖
    주장 검증(validation.py)이 **코드가 덧붙인 문구가 아니라 모델이 실제로 쓴
    문장만** 봐야 하기 때문이다. 면책 문구에 들어 있는 조문 번호를 모델이 인용한
    것으로 세면 검증이 무의미해진다.
    """

    question: str
    status: AnswerStatus
    text: str
    raw_text: str = ""
    laws: tuple[Evidence, ...] = ()
    cases: tuple[Evidence, ...] = ()
    # 공식 안내(HUG·국세청 등). 법적 근거가 아니라 실무 절차 자료이고,
    # 검색이 질문 주제일 때만 0~2건 준다.
    guides: tuple[Evidence, ...] = ()

    @property
    def evidences(self) -> tuple[Evidence, ...]:
        """법령 · 판례 · 안내 순. 화면 표시 순서와 같다.

        ★ 안내를 빠뜨리면 안 된다. 검색이 안내를 프롬프트에 실어 보내므로 모델이
          그것을 인용하는데, 여기에 없으면 인용 검증(citation.py)이 근거에 없는
          출처로 보고 환각으로 잡는다.
        """
        return self.laws + self.cases + self.guides

    def sources(self) -> list[dict]:
        """화면·JSON 출력용 출처 목록.

        같은 조문이 여러 청크로 쪼개져 있으면 출처 줄이 중복되므로 citation
        기준으로 한 번만 남긴다. 순서는 검색 순위를 그대로 따른다.
        """
        # citation 이 빌 수 있다(title·article_no 가 없는 청크). 그때 citation
        # 만으로 묶으면 서로 다른 근거가 한 줄로 뭉개져 chunk_id 를 보조 키로 쓴다.
        seen: set[str] = set()
        out: list[dict] = []
        for evidence in self.evidences:
            key = evidence.citation or f"#{evidence.chunk_id}"
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "label": evidence.citation or f"#{evidence.chunk_id}",
                    "url": evidence.source_url,
                    "doc_type": evidence.doc_type,
                    "chunk_id": evidence.chunk_id,
                }
            )
        return out
