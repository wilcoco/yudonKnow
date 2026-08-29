"""분신의 검색 — **의존성 0**. 확신도를 여기서 정한다.

가장 중요한 설계 결정이 이 파일에 있다:

    **공백(모른다) 판정은 LLM 이 하지 않는다.**

LLM 에게 "모르면 모른다고 해" 라고 부탁하는 설계는 실패한다. 여기서 계산한
확신도가 기준 미달이면 **LLM 을 호출조차 하지 않고** 공백으로 넘긴다.
coral 의 "관문은 LLM 을 호출하지 않는다" 규약을 대상만 바꿔 이식한 것이다
(docs/reuse-map.md). ``tests/test_core.py`` 가 이 구조를 강제한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.card import Card

_TOKEN = re.compile(r"[0-9A-Za-z가-힣]+")

#: 조사를 떼는 최소 규칙. 형태소 분석기(konlpy 등)를 붙이지 않는 이유는 배포
#: 단순성이다 — Railway 에 JVM 을 올릴 이유가 없다. 정확도가 부족해지는 지점은
#: 카드 수천 장 규모이고, 그때는 임베딩으로 간다 (docs/roadmap.md P1).
_JOSA = (
    "에서는", "으로는", "에게는", "이라고", "라고는", "에서", "에게", "한테", "으로",
    "부터", "까지", "라도", "이나", "이며", "처럼", "보다", "만큼", "밖에",
    "가", "이", "은", "는", "을", "를", "에", "의", "도", "만", "로", "과", "와", "나",
)

#: 한국어 불용어 최소 집합. 형태소 분석기를 붙이지 않는 이유는 배포 단순성이다
#: (카드 수백 장 규모에서 이득 < 복잡도 — docs/design.md §7).
_STOP_KO = {
    "그리고", "그런데", "하지만", "어떻게", "무엇", "뭐", "언제", "왜", "제가",
    "저는", "이거", "그거", "저거", "합니다", "하나요", "인가요", "있나요", "때",
    "경우", "관련", "문제", "상황", "해야", "하면", "되나요", "어떤",
}

#: 영어 불용어. 이게 없으면 "how do I …" 의 기능어가 카드 본문에 걸려 **답하지
#: 말아야 할 질문에 확신도가 붙는다.** 공백 판정이 이 목록에 직접 달려 있다.
_STOP_EN = {
    "the", "a", "an", "and", "or", "but", "if", "of", "on", "in", "at", "to",
    "for", "with", "from", "by", "as", "is", "are", "was", "were", "be", "been",
    "do", "does", "did", "have", "has", "had", "can", "could", "should", "would",
    "will", "shall", "may", "might", "must", "how", "what", "when", "where",
    "why", "who", "which", "this", "that", "these", "those", "there", "here",
    "it", "its", "my", "your", "our", "their", "his", "her", "we", "you", "they",
    "me", "him", "them", "us", "about", "into", "over", "under", "than", "then",
    "so", "not", "no", "any", "some", "all", "just", "only", "get", "got",
    "new", "old", "one", "two", "please", "thanks", "hi", "hello",
}

_STOP = _STOP_KO | _STOP_EN


def _is_hangul(token: str) -> bool:
    return any("\uac00" <= ch <= "\ud7a3" for ch in token)


def _stem(token: str) -> str:
    """한국어는 조사를 떼고, 영어는 복수형 -s 만 뗀다.

    영어 어간 추출기를 붙이지 않는 이유는 정확도가 아니라 **예측 가능성**이다.
    이 점수가 공백 판정의 임계값이 되므로, 틀렸을 때 왜 틀렸는지 사람이 즉시
    설명할 수 있어야 한다.
    """
    if _is_hangul(token):
        for josa in _JOSA:
            if token.endswith(josa) and len(token) - len(josa) >= 2:
                return token[: -len(josa)]
        return token
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        if len(raw) < 2 or raw in _STOP:
            continue
        stem = _stem(raw)
        if stem not in _STOP:
            out.append(stem)
    return out


def _overlap(query: set[str], field: set[str]) -> float:
    """겹침 비율. 한국어 복합명사에만 **부분 일치**로 부분 점수를 준다.

    "사출압력" 과 "압력" 은 부분 일치가 필요하다 — 한국어는 띄어쓰기 없이 붙는다.
    **영어에는 이 규칙을 적용하지 않는다.** 적용하면 "rate" 가 "calibrate" 에,
    "the" 가 "then" 에 걸려서 *답하지 말아야 할 질문에 확신도가 붙는다.*
    실제로 그렇게 새는 것을 데모 시드에서 잡았고,
    ``test_unrelated_english_question_is_always_a_gap`` 가 재발을 막는다.
    """
    if not query:
        return 0.0
    hit = 0.0
    # 질문 토큰의 30% 는 잡음("나와요", "이상해요" 같은 서술어)이라고 보고 봐준다.
    # 형태소 분석 없이 서술어를 거르는 대신 분모를 깎는 쪽을 택했다 — 규칙이
    # 하나뿐이라 틀려도 예측 가능하다.
    denom = max(len(query) * 0.7, 1.0)
    for token in query:
        if token in field:
            hit += 1.0
            continue
        if not _is_hangul(token):
            continue  # 라틴 문자는 정확 일치만 — 부분 일치는 오답을 만든다
        if len(token) >= 3 and any(
            token in f or (len(f) >= 3 and f in token)
            for f in field
            if _is_hangul(f)
        ):
            hit += 0.6
    return min(hit / denom, 1.0)


@dataclass
class Hit:
    card: Card
    score: float
    #: 탐색 쿼터로 밀어 올려진 결과인가 (마태 효과 보정 — CAMS-KnowledgeNet 이식)
    explored: bool = False


@dataclass
class Retrieval:
    hits: list[Hit]
    confidence: float
    #: 확신도가 바닥 미만이라 **LLM 을 호출하지 않고** 공백으로 넘겼는가
    is_gap: bool

    @property
    def cards(self) -> list[Card]:
        return [h.card for h in self.hits]


#: 카드의 어느 칸이 질문과 겹쳤는가에 따른 가중치.
#: ``cues`` 가 가장 높다 — 후배의 질문은 대개 "이런 게 보이는데" 로 온다.
_FIELD_WEIGHT = {
    "title": 3.0,
    "cues": 3.0,
    # 별칭은 cues 와 같은 급 — "후배의 표현"이니까. 화면엔 안 나가고
    # 검색만 본다. 승인 시점에 LLM 이 생성, 실패하면 그냥 빈 칸.
    "aliases": 3.0,
    "situation": 2.0,
    "judgment": 1.5,
    "domain": 1.5,
    "action": 1.0,
    "rationale": 0.7,
    "exceptions": 0.7,
}


def _card_fields(card: Card) -> dict[str, str]:
    return {
        "title": card.title,
        "cues": " ".join(card.cues),
        "aliases": " ".join(card.aliases),
        "situation": card.situation,
        "judgment": card.judgment,
        "domain": card.domain,
        "action": " ".join(card.action),
        "rationale": card.rationale,
        "exceptions": " ".join(card.exceptions),
    }


def score_card(card: Card, query_tokens: list[str]) -> float:
    """질문 토큰이 카드의 어느 칸에 얼마나 걸리는가. 0.0 ~ 1.0 로 정규화."""
    if not query_tokens:
        return 0.0
    unique = set(query_tokens)
    raw = 0.0
    for name, text in _card_fields(card).items():
        field_tokens = set(tokenize(text))
        if not field_tokens:
            continue
        raw += _FIELD_WEIGHT[name] * _overlap(unique, field_tokens)
    # 현장 검증된 카드에 소폭 가산. **인기가 아니라 실측이 근거다.**
    # 인용 횟수는 곱하지 않는다 — 많이 쓰인 카드가 더 맞는 카드는 아니다.
    if card.status.value == "anchored":
        raw *= 1.15
    if card.status.value == "contested":
        raw *= 0.85
    # 포화 정규화: 여러 칸에 두루 걸릴수록 1.0 에 수렴하되 닿지는 않는다.
    return raw / (raw + 2.0)


def retrieve(
    cards: list[Card],
    question: str,
    *,
    viewer: str = "",
    top_k: int = 6,
    explore_quota: float = 0.25,
    confidence_floor: float = 0.35,
    citable_floor: float = 0.6,
) -> Retrieval:
    """질문 → 근거 카드 + 확신도 + 공백 여부.

    통제권(``visible_to``)과 인용 자격(``citable``)을 **검색 단계에서** 건다.
    비공개·봉인 카드가 점수만 올리고 답에 안 쓰이는 상황을 만들지 않기 위해서다.
    """
    tokens = tokenize(question)
    eligible = [
        c for c in cards if c.visible_to(viewer) and c.citable(floor=citable_floor)
    ]
    scored = [Hit(c, score_card(c, tokens)) for c in eligible]
    scored = [h for h in scored if h.score > 0.0]
    scored.sort(key=lambda h: (-h.score, h.card.id))

    confidence = scored[0].score if scored else 0.0
    if confidence < confidence_floor:
        # 여기서 끝. LLM 은 호출되지 않는다.
        return Retrieval(hits=[], confidence=confidence, is_gap=True)

    chosen = scored[:top_k]

    # 탐색 쿼터 — 인용 많은 카드만 계속 나오는 마태 효과를 끊는다.
    n_explore = int(top_k * explore_quota)
    if n_explore:
        fresh = [
            h for h in scored[top_k:] if h.card.citations == 0 and h.score > 0.15
        ]
        for hit in fresh[:n_explore]:
            hit.explored = True
            chosen = chosen[: top_k - 1] + [hit]

    return Retrieval(hits=chosen, confidence=confidence, is_gap=False)
