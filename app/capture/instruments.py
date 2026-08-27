"""자기 발굴 도구함 — 연장 12개. **의존성 0** (LLM 도 DB 도 모른다).

이 모듈이 이 제품을 기존 지식관리 도구와 가르는 지점이다.

    사용자는 설득해야 할 사람이 아니라 **이미 남기고 싶어 하는 사람**이다.
    부족한 것은 의지가 아니라 **꺼내는 연장**이다.

정본: ``docs/self-excavation.md``. §4 의 "연장 → 카드 칸" 대응표가
:data:`INSTRUMENTS` 의 ``fills`` 필드 그 자체다 — 문서와 코드가 같은 표를 본다.

운영 원칙 (여기 코드로 박아둔다):
  · 오늘 뭘 할지는 **본인이 고른다.** :func:`recommend` 는 추천만 한다.
  · 모든 연장은 3분 안에 한 조각이 끝나야 한다.
  · 첫 2주는 2개만 노출한다 — 선택지가 많으면 아무것도 고르지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.card import Card, SLOTS


@dataclass(frozen=True)
class Instrument:
    key: str
    emoji: str
    name: str
    #: 전문가에게 보이는 한 줄. 기계 어휘 금지.
    pitch: str
    #: 이 연장이 주로 채우는 카드 칸 (self-excavation §4 의 ● )
    fills: tuple[str, ...]
    #: 부수적으로 채워지는 칸 (○)
    also: tuple[str, ...] = ()
    minutes: int = 3
    #: 처음부터 열려 있는가. False 면 카드가 쌓여야 열린다 (선택지 과부하 방지)
    unlocked: bool = False
    #: 첫 질문 — 연장의 성격이 여기서 드러난다
    opener: str = ""


INSTRUMENTS: tuple[Instrument, ...] = (
    Instrument(
        key="moment", emoji="🔨", name="순간 포착",
        pitch="방금 판단한 게 있나요? 30초, 세 줄이면 됩니다.",
        fills=("situation", "cues"), also=("judgment",),
        minutes=1, unlocked=True,
        opener="방금 무슨 상황이었나요? 한 줄로만.",
    ),
    Instrument(
        key="wrong", emoji="⚖️", name="오답 채점기",
        pitch="제가 틀린 답을 냅니다. 빨간펜만 들어주세요.",
        fills=("judgment", "rationale"), also=("cues", "action", "exceptions"),
        minutes=3, unlocked=True,
        opener="제가 낸 답이 맞습니까? 틀렸다면 어디가 틀렸는지만 짚어주세요.",
    ),
    Instrument(
        key="contrast", emoji="🔍", name="대조 짝",
        pitch="비슷한 두 상황. 무엇이 다른지만 말해주세요.",
        fills=("cues", "judgment"), also=("situation", "rationale"),
        minutes=4,
        opener="이 두 경우를 가르는 건 뭔가요?",
    ),
    Instrument(
        key="sensory", emoji="👂", name="감각 사다리",
        pitch="'그냥 감으로'를 눈·귀·손·냄새·타이밍·리듬으로 쪼갭니다.",
        fills=("cues",), minutes=5,
        opener="그 '감'을 채널별로 나눠봅니다. 눈에 무엇이 보였나요?",
    ),
    Instrument(
        key="point", emoji="📷", name="가리키기",
        pitch="말로 안 되면 사진에 동그라미 치고 한 줄만.",
        fills=("cues",), also=("action",), minutes=2,
        opener="사진이나 화면을 올리고, 중요한 데에 표시해 주세요.",
    ),
    Instrument(
        key="aloud", emoji="🗣", name="소리내어 하기",
        pitch="일하면서 그냥 중얼거리세요. 자르는 건 제가 합니다.",
        fills=("situation", "cues", "judgment", "action"), also=("rationale",),
        minutes=10,
        opener="지금 하시는 일을 하면서, 머릿속에 떠오르는 걸 그대로 말해주세요.",
    ),
    Instrument(
        key="debate", emoji="🥊", name="분신과 논쟁",
        pitch="당신의 분신에게 물어보고, 틀리면 반박하세요.",
        fills=("exceptions", "rationale"), also=("judgment",), minutes=5,
        opener="분신에게 물어보세요. 답이 어설프면 그 자리에서 반박하시면 됩니다.",
    ),
    Instrument(
        key="letter", emoji="✉️", name="후계자에게",
        pitch="'김대리에게 남기는 말'로 쓰면 훨씬 많이 나옵니다.",
        fills=SLOTS, minutes=15,
        opener="누구에게 남기시겠습니까? 그 사람이 3개월 뒤 겪을 일부터 쓰시면 됩니다.",
    ),
    Instrument(
        key="regret", emoji="📉", name="회한 채굴",
        pitch="그때로 돌아가면 무엇을 다르게 하시겠습니까?",
        fills=("failure", "exceptions", "rationale"), also=("situation",), minutes=5,
        opener="크게 틀렸던 적이 있나요? 그때 무슨 일이 있었나요?",
    ),
    Instrument(
        key="boundary", emoji="🎚", name="경계 슬라이더",
        pitch="'적당히 높으면'을 숫자로 바꿉니다.",
        fills=("cues", "exceptions"), minutes=2,
        opener="몇 부터가 위험한가요? 슬라이더로 짚어주세요.",
    ),
    Instrument(
        key="map", emoji="🗺", name="머릿속 지도",
        pitch="아직 안 판 곳에 당신이 직접 깃발을 꽂습니다.",
        fills=(), minutes=2,
        opener="어느 영역이 아직 크게 남아 있나요?",
    ),
    Instrument(
        key="gauge", emoji="🌡", name="암묵지 온도계",
        pitch="이건 읽어서 되나요, 옆에서 봐야 하나요?",
        fills=(), minutes=1,
        opener="이 판단, 글로 읽고 따라 할 수 있는 종류입니까?",
    ),
)

BY_KEY = {i.key: i for i in INSTRUMENTS}

#: 사다리 모드 (AI 가 운전) 는 연장이 아니라 기본값이다.
LADDER = "ladder"

#: 빈 칸 → 그 칸을 채우는 연장 (self-excavation §4 표의 세로 읽기)
_SLOT_TO_INSTRUMENTS: dict[str, tuple[str, ...]] = {
    "situation": ("moment", "regret", "aloud"),
    "cues": ("contrast", "sensory", "point", "boundary"),
    "judgment": ("wrong", "contrast", "aloud"),
    "action": ("aloud", "letter"),
    "rationale": ("wrong", "debate", "regret"),
    "exceptions": ("debate", "regret", "boundary"),
    "failure": ("regret", "letter"),
}


def unlocked(card_count: int, *, threshold: int = 3) -> list[Instrument]:
    """열려 있는 연장. 첫 2주엔 2개만 — 선택지 과부하는 이탈의 원인이다."""
    if card_count >= threshold:
        return list(INSTRUMENTS)
    return [i for i in INSTRUMENTS if i.unlocked]


@dataclass
class Suggestion:
    instrument: Instrument
    #: 왜 이걸 추천하는지 전문가에게 보여줄 한 줄. 근거 없는 추천은 하지 않는다.
    because: str
    card_id: str = ""


def recommend(
    cards: list[Card],
    *,
    flags: set[str] | None = None,
    open_gaps: int = 0,
    card_count: int | None = None,
    threshold: int = 3,
    limit: int = 3,
) -> list[Suggestion]:
    """오늘 무엇으로 팔지 **제안만** 한다. 고르는 것은 전문가다.

    추천 순서는 곧 이 도구의 가치관이다:
    ① 후배가 막힌 곳(공백) → ② 전문가 본인이 꽂은 깃발 → ③ 카드의 빈 칸.
    기계가 계산한 커버리지보다 **사람의 신호를 먼저 본다.**
    """
    count = card_count if card_count is not None else len(cards)
    available = {i.key for i in unlocked(count, threshold=threshold)}
    out: list[Suggestion] = []

    def push(key: str, because: str, card_id: str = "") -> None:
        if key in available and not any(s.instrument.key == key for s in out):
            out.append(Suggestion(BY_KEY[key], because, card_id))

    # ① 후배의 공백이 최우선. 인터뷰 주제는 현장 수요가 정한다.
    if open_gaps:
        push("wrong", f"후배가 막힌 곳 {open_gaps}건이 기다립니다. 3분이면 됩니다.")

    # ② 전문가 본인이 "아직 남았다" 고 표시한 곳.
    for name in sorted(flags or ()):
        push("aloud", f"'{name}'에 깃발을 꽂아두셨습니다.")
        break

    # ③ 카드의 빈 칸 — 신호(cues)와 예외(exceptions)가 비면 가장 위험하다.
    for slot in ("cues", "exceptions", "failure", "rationale"):
        target = next(
            (c for c in cards if slot in c.missing and c.status.value != "dormant"),
            None,
        )
        if target is None:
            continue
        for key in _SLOT_TO_INSTRUMENTS[slot]:
            if key in available:
                push(key, f"'{target.title}'에 {_KO[slot]}가 비어 있습니다.", target.id)
                break

    if not out:
        push("moment", "오늘 내린 판단 하나만 남겨두세요.")
    return out[:limit]


_KO = {
    "situation": "상황",
    "cues": "신호",
    "judgment": "판단",
    "action": "조치",
    "rationale": "근거",
    "exceptions": "예외",
    "failure": "실패담",
}


def slot_ko(slot: str) -> str:
    return _KO.get(slot, slot)
