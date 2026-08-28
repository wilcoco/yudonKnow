"""LLM 어댑터 — **산출물 층위 접합만.** 텍스트 in / 텍스트 out.

alter-ai(coral) 의 규약을 그대로 이식했다 (docs/reuse-map.md):

    기저 LLM 은 산출물 층위로만 접합한다. 내부 표현에 개입하지 않는다.
    기저 교체 가능성이 전략 자산이다.

그 규약이 실제로 값을 했다. 기저를 Anthropic 에서 **Gemini 로 갈아끼우는 데
이 파일 하나만** 바뀌었다 — 인터뷰(`capture/interview.py`)도 분신
(`alter/persona.py`)도 손대지 않았다. 접합면이 ``answer`` / ``extract`` 두
개뿐이기 때문이다.

접합 순서: **Gemini(기본) → Anthropic(대체) → stub.**
키가 하나도 없으면 :class:`StubLLM` 로 떨어진다 — 발굴→카드→분신→공백→닻
동선은 stub 에서도 그대로 돈다.
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

    def transcribe(self, audio: bytes, mime: str, *, lang: str = "en") -> str: ...


class StubLLM:
    """키 없이 뜨는 모드. **답을 지어내는 대신 stub 임을 밝힌다.**

    그럴듯한 가짜를 만들면 카드가 쓰레기로 차고, 후배가 분신을 믿을 근거가
    사라진다. 이 도구에서 신뢰는 기능이다.
    """

    name = "stub"

    def answer(self, system: str, prompt: str) -> str:
        return (
            "⚠ LLM 미연결 (stub 모드). GOOGLE_API_KEY 를 설정하면 실제 응답이 "
            "들어옵니다. 아래는 검색된 근거 카드 원문입니다.\n\n" + prompt
        )

    def extract(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        return {}

    def transcribe(self, audio: bytes, mime: str, *, lang: str = "en") -> str:
        return ""   # 가짜 전사를 만들지 않는다 — 화면은 이 경우 마이크를 숨긴다


# ------------------------------------------------------------------ Gemini

#: Gemini ``response_schema`` 가 받는 키만 남긴다. JSON Schema 를 그대로 넘기면
#: ``additionalProperties`` 같은 키에서 400 이 난다. 스키마 원본
#: (`capture/interview.py`) 은 공급자 중립으로 두고 여기서만 깎는다 —
#: 접합면 바깥으로 공급자 사정을 새게 하지 않으려는 것.
_GEMINI_SCHEMA_KEYS = frozenset(
    {"type", "format", "description", "nullable", "enum", "items",
     "properties", "required", "minItems", "maxItems", "propertyOrdering"}
)


def _gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """JSON Schema → Gemini 가 받는 부분집합 (재귀)."""
    out: dict[str, Any] = {}
    for key, value in schema.items():
        if key not in _GEMINI_SCHEMA_KEYS:
            continue
        if key == "properties" and isinstance(value, dict):
            out[key] = {k: _gemini_schema(v) for k, v in value.items()}
        elif key == "items" and isinstance(value, dict):
            out[key] = _gemini_schema(value)
        else:
            out[key] = value
    return out


class GeminiLLM:
    """Gemini 접합 — Google GenAI SDK. 호출은 텍스트 경계에서만 일어난다.

    Gemini API 키(``GOOGLE_API_KEY``) 와 Vertex AI(``YDK_VERTEX_PROJECT``) 를
    모두 받는다. 어느 쪽이든 같은 SDK 한 장으로 붙고, 위쪽 코드는 차이를
    모른다.
    """

    def __init__(
        self,
        *,
        model: str,
        max_tokens: int,
        api_key: str | None = None,
        vertex_project: str | None = None,
        vertex_location: str = "us-central1",
    ) -> None:
        from google import genai
        from google.genai import types

        self._types = types
        if vertex_project:
            self._client = genai.Client(
                vertexai=True, project=vertex_project, location=vertex_location
            )
            origin = f"vertex/{vertex_location}"
        else:
            self._client = genai.Client(api_key=api_key)
            origin = "gemini-api"
        self._model = model
        self._max_tokens = max_tokens
        self.name = f"{model} ({origin})"

    def _gen(self, **kw):
        """생성 호출 + 지수 백오프. 429(쿼터)·일시장애는 심사 당일 몰림에서
        실제로 난다 — 조용히 stub 으로 떨어지느니 잠깐 기다렸다 다시 친다."""
        import time as _t

        delay = 1.0
        for attempt in range(4):
            try:
                return self._client.models.generate_content(**kw)
            except Exception as exc:
                msg = str(exc)
                transient = ("429" in msg or "RESOURCE_EXHAUSTED" in msg
                             or "503" in msg or "UNAVAILABLE" in msg
                             or "500" in msg)
                if not transient or attempt == 3:
                    raise
                _t.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable")

    def answer(self, system: str, prompt: str) -> str:
        response = self._gen(
            model=self._model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                system_instruction=system,
                max_output_tokens=self._max_tokens,
            ),
        )
        return (response.text or "").strip()

    def transcribe(self, audio: bytes, mime: str, *, lang: str = "en") -> str:
        """현장 발화 → 텍스트. **정리하지 않는다** — 원본 발화가 자료다.

        요약·문어체 교정을 시키지 않는 것이 중요하다. 흐트러진 말 그대로가
        "messy unstructured stream" 의 실물이고, 정리는 카드 구조화가 한다.
        """
        instruction = (
            "다음 음성을 받아 적어라. 요약하지 말고, 문어체로 고치지 말고, "
            "말한 그대로 적어라. 전사문만 출력하라."
            if lang == "ko" else
            "Transcribe this audio. Do not summarise, do not clean it up — "
            "write exactly what was said. Output the transcript only."
        )
        response = self._gen(
            model=self._model,
            contents=[
                self._types.Part.from_bytes(data=audio, mime_type=mime),
                instruction,
            ],
            config=self._types.GenerateContentConfig(max_output_tokens=self._max_tokens),
        )
        return (response.text or "").strip()

    def extract(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """스키마 강제 구조화 추출 (카드 포획·오답 생성이 쓴다)."""
        response = self._gen(
            model=self._model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                max_output_tokens=self._max_tokens,
                response_mime_type="application/json",
                response_schema=_gemini_schema(schema),
            ),
        )
        text = (response.text or "").strip()
        return json.loads(text) if text else {}


# --------------------------------------------------------------- Anthropic


class AnthropicLLM:
    """Anthropic Messages API 접합. 대체 기저 — 교체 가능성의 실물 증거다.

    오디오 전사는 지원하지 않는다 — 이 기저로 바꾸면 화면이 마이크를 숨긴다.
    기저 교체가 기능 강등으로 이어질 수 있음을 감추지 않는 것도 계약의 일부다.
    """

    def transcribe(self, audio: bytes, mime: str, *, lang: str = "en") -> str:
        return ""

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
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            thinking={"type": "adaptive"},
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return json.loads(text) if text else {}


# ------------------------------------------------------------------ 선택


_cached: BaseLLM | None = None


def _build() -> BaseLLM:
    """설정이 고른 기저를 세운다. 실패하면 **서비스를 죽이지 않고** 다음으로."""
    provider = settings.provider

    if provider in ("auto", "gemini") and settings.gemini_enabled:
        try:
            llm = GeminiLLM(
                model=settings.gemini_model,
                max_tokens=settings.max_tokens,
                api_key=settings.google_api_key,
                vertex_project=settings.vertex_project,
                vertex_location=settings.vertex_location,
            )
            log.info("LLM: %s", llm.name)
            return llm
        except Exception as exc:  # SDK 미설치·키 불량 — 서비스는 계속 뜬다
            log.warning("Gemini 초기화 실패: %s", exc)
            if provider == "gemini":
                return StubLLM()

    if provider in ("auto", "anthropic") and settings.anthropic_api_key:
        try:
            llm = AnthropicLLM(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
                max_tokens=settings.max_tokens,
            )
            log.info("LLM: %s", llm.name)
            return llm
        except Exception as exc:
            log.warning("Anthropic 초기화 실패: %s", exc)

    log.info("LLM 키 없음 — stub 으로 기동")
    return StubLLM()


def get_llm() -> BaseLLM:
    global _cached
    if _cached is None:
        _cached = _build()
    return _cached


def reset_llm_cache() -> None:
    """테스트용."""
    global _cached
    _cached = None
