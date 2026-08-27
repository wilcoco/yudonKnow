"""LLM 어댑터 — **산출물 층위 접합만.** 텍스트 in / 텍스트 out.

alter-ai(coral) 의 규약을 그대로 이식했다 (docs/reuse-map.md):

    기저 LLM 은 산출물 층위로만 접합한다. 내부 표현에 개입하지 않는다.
    기저 교체 가능성이 전략 자산이다.

그래서 이 파일이 얇다. 인터페이스는 ``answer`` 와 ``extract`` 두 개뿐이고,
``ANTHROPIC_API_KEY`` 가 없으면 :class:`StubLLM` 로 떨어진다 — 발굴→카드→분신→
공백→닻 동선은 stub 에서도 그대로 돈다.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.config import settings

log = logging.getLogger(__name__)


class BaseLLM(Protocol):
    """교체 가능 부품의 계약."""

    name: str

    def answer(self, system: str, prompt: str) -> str: ...

    def extract(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]: ...


class StubLLM:
    """키 없이 뜨는 모드. **답을 지어내는 대신 stub 임을 밝힌다.**

    그럴듯한 가짜를 만들면 카드가 쓰레기로 차고, 후배가 분신을 믿을 근거가
    사라진다. 이 도구에서 신뢰는 기능이다.
    """

    name = "stub"

    def answer(self, system: str, prompt: str) -> str:
        return (
            "⚠ LLM 미연결 (stub 모드). ANTHROPIC_API_KEY 를 설정하면 실제 응답이 "
            "들어옵니다. 아래는 검색된 근거 카드 원문입니다.\n\n" + prompt
        )

    def extract(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {}


class AnthropicLLM:
    """Anthropic Messages API 접합. 호출은 텍스트 경계에서만 일어난다."""

    def __init__(self, api_key: str, model: str, max_tokens: int) -> None:
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens
        self.name = model

    def answer(self, system: str, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(b.text for b in response.content if b.type == "text").strip()

    def extract(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """스키마 강제 구조화 추출 (카드 포획·질문 생성이 쓴다)."""
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return json.loads(text) if text else {}


_cached: BaseLLM | None = None


def get_llm() -> BaseLLM:
    global _cached
    if _cached is not None:
        return _cached
    if settings.llm_enabled:
        try:
            _cached = AnthropicLLM(
                api_key=settings.anthropic_api_key or "",
                model=settings.model,
                max_tokens=settings.max_tokens,
            )
            log.info("LLM: %s", settings.model)
        except Exception as exc:  # SDK 미설치·키 불량 — 서비스는 계속 뜬다
            log.warning("LLM 초기화 실패, stub 로 대체: %s", exc)
            _cached = StubLLM()
    else:
        log.info("ANTHROPIC_API_KEY 없음 — stub 으로 기동")
        _cached = StubLLM()
    return _cached


def reset_llm_cache() -> None:
    """테스트용."""
    global _cached
    _cached = None
