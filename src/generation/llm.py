"""로컬 양자화 LLM 연결 — Qwen3-8B (Q4_K_M) on Ollama.

OpenAI API 대신 로컬 Ollama 로 돌린다. Ollama 는 `http://localhost:11434/v1` 에
OpenAI 호환 엔드포인트를 그대로 열어 주므로, 이미 requirements.txt 에 있는
`langchain-openai` 의 ChatOpenAI 에 base_url 만 바꿔 끼우면 된다.
`langchain-ollama` 같은 새 의존성을 추가하지 않는 이유다.

api_key 는 Ollama 가 검사하지 않지만 OpenAI 클라이언트가 값이 없으면 예외를
내므로 아무 문자열이나 넣는다.

## Qwen3 의 사고 과정(<think>) 처리

Qwen3 는 추론 과정을 `<think> ... </think>` 로 먼저 뱉는 하이브리드 모델이다.
그대로 두면 두 가지 문제가 생긴다.

1. 사용자 화면에 모델의 혼잣말이 그대로 보인다.
2. 인용 검증(citation.py)이 **사고 과정 안에 등장한 조문 번호**까지 답변에서
   인용한 것으로 세어, 실제로는 인용하지 않은 조문이 검증을 통과한다.

그래서 두 겹으로 막는다. 프롬프트에 Qwen3 의 소프트 스위치 `/no_think` 를 넣어
애초에 만들지 않게 하고(prompt.py), 그래도 나오면 `strip_reasoning()` 이 잘라낸다.
소프트 스위치는 모델·버전에 따라 무시될 수 있으므로 잘라내는 쪽이 최종 보루다.
"""

from __future__ import annotations

import logging
import os
import re

from langchain_core.language_models.fake_chat_models import FakeListChatModel

# ── 설정값 (환경 변수로 덮어쓸 수 있다) ──────────────────────────

logger = logging.getLogger(__name__)


def _env_number(name: str, default: str, cast):
    """숫자 환경 변수를 읽는다. 비어 있거나 숫자가 아니면 기본값으로 돌아간다.

    `.env` 에 키만 적고 값을 비워 두면 int() 가 터져 src.generation 전체가
    import 불가가 된다. 스택트레이스만으로는 원인을 알기 어려워 방어한다.
    """
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        raw = default
    try:
        return cast(raw)
    except (TypeError, ValueError):
        logger.warning("%s 값이 숫자가 아니어서 기본값 %s 를 씁니다: %r", name, default, raw)
        return cast(default)


LLM_BASE_URL = os.getenv("JEONSEON_LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("JEONSEON_LLM_MODEL", "qwen3:8b-q4_K_M")
LLM_API_KEY = os.getenv("JEONSEON_LLM_API_KEY", "ollama")  # Ollama 는 검사하지 않음

# 법령 근거를 그대로 옮기는 작업이라 창작이 필요 없다. 낮게 둔다.
LLM_TEMPERATURE = _env_number("JEONSEON_LLM_TEMPERATURE", "0.2", float)

# 8B 양자화 모델을 CPU 로 돌리면 첫 응답까지 수십 초가 걸릴 수 있다.
LLM_TIMEOUT = _env_number("JEONSEON_LLM_TIMEOUT", "180", float)

# ★ 길이 상한. 프롬프트의 "400자 안팎" 지시만으로는 막히지 않는다.
# 근거를 다 쓰고 나면 지어내기 시작해, 실제로 1,700~2,300자 답변에 오류가 몰렸다.
# 1200 토큰(한국어 900자쯤)이면 정상 답변은 그대로 두고 폭주만 끊는다.
# 700 으로 줄였다가 사고 과정이 예산을 다 써서 답변이 통째로 빈 적이 있다.
LLM_MAX_TOKENS = _env_number("JEONSEON_LLM_MAX_TOKENS", "1200", int)

def _env_flag(name: str, default: str = "1") -> bool:
    """환경 변수를 참/거짓으로 읽는다. 대소문자와 흔한 표기를 모두 받는다."""
    return os.getenv(name, default).strip().lower() not in ("0", "false", "no", "off", "")


# 서버 쪽 사고 과정 스위치. 프롬프트의 `/no_think` 가 무시될 때를 대비해 함께 쓴다.
# 지원하지 않는 서버는 모르는 필드를 무시하므로 켜 두어도 해가 없다.
THINK_OFF = _env_flag("JEONSEON_LLM_NO_THINK")


# ── 사고 과정 제거 ────────────────────────────────────────────

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

# 길이 제한 등으로 닫는 태그 없이 잘린 경우. 여는 태그부터 끝까지 버린다.
_THINK_OPEN = re.compile(r"<think>.*\Z", re.DOTALL | re.IGNORECASE)


def strip_reasoning(text: str) -> str:
    """Qwen3 의 `<think>...</think>` 구간을 잘라낸다.

    사고 과정이 없으면 원문을 그대로 돌려준다. 즉 다른 모델로 바꿔도 안전하다.
    """
    if not text:
        return ""
    cleaned = _THINK_BLOCK.sub("", text)
    cleaned = _THINK_OPEN.sub("", cleaned)
    return cleaned.strip()


_SENTENCE_END = (".", "!", "?", "\u201d", '"')

# 한글이 들어 있는가. 표식이 붙은 줄이 제목인지 문장인지 가르는 데 쓴다.
_HANGUL = re.compile(r"[가-힣]")


# 잘라낼 자리를 찾을 때 쓰는 종결 부호. 곧은 따옴표는 여는 것일 수 있어 뺀다.
_CUT_ENDS = (".", "!", "?", "\u201d")


def _ends_completely(text: str) -> bool:
    """문장이 제대로 끝났는가. 곧은 따옴표는 짝이 맞을 때만 끝으로 본다.

    인용을 열자마자 상한에 걸린 답변이 완결된 것으로 통과하던 문제가 있었다.
    """
    if not text.endswith(_SENTENCE_END):
        return False
    if text.endswith('"') and text.count('"') % 2 == 1:
        return False
    return True


# 마크다운 기호·번호·공백만 걷어낸 알맹이를 보기 위한 것.
_MARKDOWN_NOISE = re.compile(r"[#*>\-\s\d.)(]+")


# 소제목 표식으로 시작하는 줄인가. "### 4." "**결론**" "3)" 같은 것들.
_HEADING_MARKER = re.compile(r"^\s*(?:#{1,6}|\*\*|\d+[.)])")


def _is_stub_line(line: str) -> bool:
    """제목만 쓰고 내용이 시작되기 전에 끊긴 줄인가.

    상한에 걸린 답변은 "### 4." 처럼 소제목만 남기고 끝나는 일이 잦고,
    마침표로 끝나므로 문장 검사로는 안 걸러진다.

    ★ 지우는 조건이 두 겹인 이유가 있다. 길이만 보면 "월세는 아닙니다." 같은
      짧은 정상 문장이 지워지고, 표식만 보면 "2026. 3. 1.부터 시행됩니다."
      "**결론**: 됩니다." 처럼 날짜·금액이 든 문장이 지워진다. 후자는 프롬프트
      2번 규칙(원문 그대로 옮기기)이 지키라고 한 표현을 정확히 되돌리는 일이다.
    """
    stripped = line.strip()
    if not stripped:
        return True
    if not _HEADING_MARKER.match(stripped):
        return False
    # 표식이 붙어 있어도 완결된 한국어 문장이면 내용이다.
    if len(_HANGUL.findall(stripped)) >= 2 and stripped.endswith(_SENTENCE_END):
        return False
    return len(_MARKDOWN_NOISE.sub("", stripped)) < 8


# [보이는 글자](주소) 형태의 마크다운 링크.
_MARKDOWN_LINK = re.compile(r"\[([^\]\n]+)\]\([^)\n]*\)")


def unlink(text: str) -> str:
    """마크다운 링크에서 주소를 벗겨내고 글자만 남긴다.

    출처 링크는 `Answer.sources()` 가 따로 붙인다. 프롬프트로 금지했는데도
    모델이 계속 써서 후처리로도 막는다. 문장 자체는 멀쩡하므로 통째로 버리지
    않고 주소만 벗긴다. 잘려서 닫히지 않은 링크는 _drop_unclosed_bracket 담당.
    """
    return _MARKDOWN_LINK.sub(r"\1", text)


def _drop_unclosed_bracket(text: str) -> str:
    """닫히지 않은 괄호부터 뒤를 버린다. 단, 잘라낼 양이 절반을 넘으면 두고 본다.

    링크를 쓰다 끊기면 주소 안의 마침표 때문에 문장 검사도 소제목 검사도 통과한다.

    ★ 비율 가드가 핵심이다. 없으면 앞쪽에 괄호를 하나 열어 둔 멀쩡한 답변이 통째로
      날아간다. 실제로 "판례 [대법원 2011다49523 참조. …받으세요." 가 "판례" 두
      글자로 잘린 적이 있다. 잘린 꼬리는 전체의 10~20% 라, 앞쪽에서 잘라야 한다면
      그건 모델이 괄호를 그렇게 쓴 것이다.
    """
    for opener, closer in (("(", ")"), ("[", "]")):
        depth = 0
        unclosed = -1
        for i, ch in enumerate(text):
            if ch == opener:
                if depth == 0:
                    unclosed = i
                depth += 1
            elif ch == closer and depth:
                depth -= 1
        if depth and unclosed > len(text) * 0.5:
            text = text[:unclosed].rstrip()
    return text


def trim_to_last_sentence(text: str) -> str:
    """토큰 상한에 걸려 중간에서 끊긴 답변을 마지막 완성 지점까지 되돌린다.

    내용 없는 소제목 꼬리 줄과, 마지막 마침표 뒤의 미완성 문장을 걷어낸다.
    잘라낼 양이 절반을 넘으면 손대지 않는다 — 마침표 없이 끝나는 짧은 답변까지
    지우는 것이 잘린 문장보다 나쁘다.
    """
    if not text:
        return ""
    text = text.rstrip()

    lines = text.split("\n")
    while len(lines) > 1 and _is_stub_line(lines[-1]):
        lines.pop()
    text = "\n".join(lines).rstrip()

    text = _drop_unclosed_bracket(text)

    if _ends_completely(text):
        return text

    cut = max(text.rfind(end) for end in _CUT_ENDS)
    if cut > len(text) * 0.5:
        return text[: cut + 1]
    return text


def clean_output(text: str) -> str:
    """모델 출력을 화면에 내보낼 수 있는 상태로 만든다. 체인 마지막 단계.

    사고 과정 제거 → 링크 주소 벗기기 → 잘린 꼬리 다듬기 순서다. 링크를 먼저
    벗겨야, 완성된 링크가 든 문장이 "닫히지 않은 괄호"로 오인돼 잘리지 않는다.
    """
    return trim_to_last_sentence(unlink(strip_reasoning(text)))


# ── LLM 만들기 ────────────────────────────────────────────────

def _extra_body() -> dict:
    """요청 본문에 그대로 실려 갈 값들."""
    body: dict = {"max_tokens": LLM_MAX_TOKENS}
    if THINK_OFF:
        body["think"] = False
    return body


def get_llm(fake_responses: list[str] | None = None, **overrides):
    """LLM 하나를 만들어 돌려준다.

    fake_responses 를 주면 실제 모델을 부르지 않는 가짜 채팅 모델을 쓴다.
    테스트는 이것만 쓰므로 Ollama 없이도 전부 통과한다.

    overrides 로 model·temperature 등을 일회성으로 바꿀 수 있다.
    """
    if fake_responses is not None:
        if not fake_responses:
            # 빈 리스트로 만들면 첫 호출에서 IndexError 로 터진다. 만든 시점에 막는다.
            raise ValueError("fake_responses 가 비어 있습니다. 응답을 하나 이상 주세요.")
        return FakeListChatModel(responses=fake_responses)

    # 임포트를 함수 안에 두어, 가짜 모델만 쓰는 테스트가 openai 패키지에
    # 의존하지 않게 한다.
    from langchain_openai import ChatOpenAI

    body = _extra_body()
    # 호출자가 준 값도 extra_body 로 옮겨야 서버에 닿는다(아래 ★ 참고).
    if "max_tokens" in overrides:
        body["max_tokens"] = overrides.pop("max_tokens")
    # 통째로 덮어쓰면 상한과 think 스위치가 사라지므로 합친다.
    if "extra_body" in overrides:
        body.update(overrides.pop("extra_body") or {})

    settings = {
        "base_url": LLM_BASE_URL,
        "api_key": LLM_API_KEY,
        "model": LLM_MODEL,
        "temperature": LLM_TEMPERATURE,
        "timeout": LLM_TIMEOUT,
        # ★ max_tokens=... 로 주면 안 된다. langchain-openai 1.x 가 이름을
        # max_completion_tokens 로 바꿔 보내는데 Ollama 는 옛 이름만 알아들어,
        # 상한이 에러도 경고도 없이 무시된다. extra_body 는 요청 본문에 그대로
        # 합쳐지므로 이름이 바뀌지 않는다. 실제 전송 내용을 잡아 확인했다.
        "extra_body": body,
    }
    settings.update(overrides)
    return ChatOpenAI(**settings)


def probe(timeout: float = 5.0) -> tuple[bool, str]:
    """Ollama 가 떠 있고 모델이 받아져 있는지 확인한다.

    앱 기동 화면이나 데모 스크립트에서 "왜 답이 안 나오는지" 를 바로 알려주기
    위한 것이다. 실패해도 예외를 던지지 않고 사유 문자열을 돌려준다.
    """
    import json
    import urllib.error
    import urllib.request

    tags_url = LLM_BASE_URL.rstrip("/").removesuffix("/v1") + "/api/tags"
    try:
        with urllib.request.urlopen(tags_url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except OSError as error:  # URLError 포함
        return False, (
            f"Ollama 에 연결하지 못했습니다 ({LLM_BASE_URL}). "
            f"`ollama serve` 가 떠 있는지 확인하세요. 원인: {error}"
        )
    except ValueError as error:  # JSONDecodeError 포함. pragma: no cover
        return False, f"Ollama 응답을 해석하지 못했습니다: {error}"

    names = [model.get("name", "") for model in payload.get("models", [])]
    if not any(name == LLM_MODEL or name.startswith(LLM_MODEL) for name in names):
        return False, (
            f"모델 '{LLM_MODEL}' 이(가) 없습니다. `ollama pull {LLM_MODEL}` 로 먼저 받으세요. "
            f"현재 받아진 모델: {', '.join(names) or '없음'}"
        )
    return True, f"준비됨 — {LLM_MODEL} @ {LLM_BASE_URL}"
