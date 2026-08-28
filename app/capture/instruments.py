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
    #: 영문 병기 — 대회 규정 6조(영어 지원)는 통과 조건이다 (``docs/hackathon.md``).
    name_en: str = ""
    pitch_en: str = ""
    opener_en: str = ""

    def localized(self, lang: str = "en") -> dict[str, str]:
        """화면에 나갈 한 벌. 문안을 카탈로그로 빼지 않고 여기 둔 이유는 연장
        정의와 문안이 같이 움직여야 하기 때문이다 — 떼어두면 반드시 어긋난다."""
        if lang == "ko" or not self.name_en:
            return {"name": self.name, "pitch": self.pitch, "opener": self.opener}
        return {
            "name": self.name_en,
            "pitch": self.pitch_en or self.pitch,
            "opener": self.opener_en or self.opener,
        }


INSTRUMENTS: tuple[Instrument, ...] = (
    Instrument(
        key="moment", emoji="🔨", name="순간 포착",
        name_en="Moment Capture",
        pitch_en="Just made a call? Thirty seconds, three lines.",
        opener_en="What was the situation, just now? One line only.",
        pitch="방금 판단한 게 있나요? 30초, 세 줄이면 됩니다.",
        fills=("situation", "cues"), also=("judgment",),
        minutes=1, unlocked=True,
        opener="방금 무슨 상황이었나요? 한 줄로만.",
    ),
    Instrument(
        key="wrong", emoji="⚖️", name="오답 채점기",
        name_en="Wrong-Answer Grader",
        pitch_en="I'll give a wrong answer. You just hold the red pen.",
        opener_en="Is my answer right? If it's wrong, point only at the part that's wrong.",
        pitch="제가 틀린 답을 냅니다. 빨간펜만 들어주세요.",
        fills=("judgment", "rationale"), also=("cues", "action", "exceptions"),
        minutes=3, unlocked=True,
        opener="제가 낸 답이 맞습니까? 틀렸다면 어디가 틀렸는지만 짚어주세요.",
    ),
    Instrument(
        key="contrast", emoji="🔍", name="대조 짝",
        name_en="Contrast Pairs",
        pitch_en="Two near-identical situations. Only tell me what differs.",
        opener_en="What separates these two cases?",
        pitch="비슷한 두 상황. 무엇이 다른지만 말해주세요.",
        fills=("cues", "judgment"), also=("situation", "rationale"),
        minutes=4,
        opener="이 두 경우를 가르는 건 뭔가요?",
    ),
    Instrument(
        key="sensory", emoji="👂", name="감각 사다리",
        name_en="Sensory Ladder",
        pitch_en="Splits a gut feeling into eye, ear, hand, smell, timing, rhythm.",
        opener_en="Let's split that feel by channel. What did you see?",
        pitch="'그냥 감으로'를 눈·귀·손·냄새·타이밍·리듬으로 쪼갭니다.",
        fills=("cues",), minutes=5,
        opener="그 '감'을 채널별로 나눠봅니다. 눈에 무엇이 보였나요?",
    ),
    Instrument(
        key="point", emoji="📷", name="가리키기",
        name_en="Point & Annotate",
        pitch_en="If words fail, circle it on a photo and write one line.",
        opener_en="Upload a photo or screen, and mark what matters.",
        pitch="말로 안 되면 사진에 동그라미 치고 한 줄만.",
        fills=("cues",), also=("action",), minutes=2,
        opener="사진이나 화면을 올리고, 중요한 데에 표시해 주세요.",
    ),
    Instrument(
        key="aloud", emoji="🗣", name="소리내어 하기",
        name_en="Think Aloud",
        pitch_en="Just mutter while you work. I'll do the cutting.",
        opener_en="While you do what you are doing, say what comes to mind.",
        pitch="일하면서 그냥 중얼거리세요. 자르는 건 제가 합니다.",
        fills=("situation", "cues", "judgment", "action"), also=("rationale",),
        minutes=10,
        opener="지금 하시는 일을 하면서, 머릿속에 떠오르는 걸 그대로 말해주세요.",
    ),
    Instrument(
        key="debate", emoji="🥊", name="분신과 논쟁",
        name_en="Argue With Your Alter",
        pitch_en="Ask your own alter, then push back when it's weak.",
        opener_en="Ask your alter. If the answer is thin, argue with it right there.",
        pitch="당신의 분신에게 물어보고, 틀리면 반박하세요.",
        fills=("exceptions", "rationale"), also=("judgment",), minutes=5,
        opener="분신에게 물어보세요. 답이 어설프면 그 자리에서 반박하시면 됩니다.",
    ),
    Instrument(
        key="letter", emoji="✉️", name="후계자에게",
        name_en="Letter To A Successor",
        pitch_en="Address it to one named person and far more comes out.",
        opener_en="Who are you leaving this for? Start with what they'll hit in three months.",
        pitch="'김대리에게 남기는 말'로 쓰면 훨씬 많이 나옵니다.",
        fills=SLOTS, minutes=15,
        opener="누구에게 남기시겠습니까? 그 사람이 3개월 뒤 겪을 일부터 쓰시면 됩니다.",
    ),
    Instrument(
        key="regret", emoji="📉", name="회한 채굴",
        name_en="Regret Mining",
        pitch_en="If you could go back, what would you do differently?",
        opener_en="Was there a time this went badly wrong? What happened?",
        pitch="그때로 돌아가면 무엇을 다르게 하시겠습니까?",
        fills=("failure", "exceptions", "rationale"), also=("situation",), minutes=5,
        opener="크게 틀렸던 적이 있나요? 그때 무슨 일이 있었나요?",
    ),
    Instrument(
        key="boundary", emoji="🎚", name="경계 슬라이더",
        name_en="Boundary Slider",
        pitch_en="Turns \"reasonably high\" into a number.",
        opener_en="From what value does it get dangerous? Point with the slider.",
        pitch="'적당히 높으면'을 숫자로 바꿉니다.",
        fills=("cues", "exceptions"), minutes=2,
        opener="몇 부터가 위험한가요? 슬라이더로 짚어주세요.",
    ),
    Instrument(
        key="map", emoji="🗺", name="머릿속 지도",
        name_en="Mind Map",
        pitch_en="You plant the flags on ground you haven't dug yet.",
        opener_en="Which area still has something big left in it?",
        pitch="아직 안 판 곳에 당신이 직접 깃발을 꽂습니다.",
        fills=(), minutes=2,
        opener="어느 영역이 아직 크게 남아 있나요?",
    ),
    Instrument(
        key="gauge", emoji="🌡", name="암묵지 온도계",
        name_en="Tacitness Gauge",
        pitch_en="Is this readable, or do you have to be watching?",
        opener_en="This judgment — is it the kind you can read and follow?",
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
    """쓸 수 있는 연장 — **처음부터 전부.**

    v0.1 은 첫 2주에 2개만 열었다. 선택지 과부하가 이탈 원인 1번이라는 근거는
    지금도 맞지만, 감추는 방식에는 대가가 두 개 있었다: ① 이 도구의 차별점이
    연장 12개인데 쓰는 사람이 그 사실을 모른다, ② 오늘 필요한 연장이 잠긴
    2개 밖에 있으면 할 수 있는 게 없다.

    과부하는 이제 **추천**이 막는다 — ``recommend()`` 가 근거와 함께 3개까지만
    앞에 세우고, 나머지는 보이되 읽지 않아도 된다. 고르는 것은 여전히
    전문가다 (docs/self-excavation.md §5).
    """
    return list(INSTRUMENTS)


@dataclass
class Suggestion:
    instrument: Instrument
    #: 왜 이걸 추천하는지 전문가에게 보여줄 한 줄. 근거 없는 추천은 하지 않는다.
    because: str
    card_id: str = ""


def recommend(
    cards: list[Card],
    *,
    lang: str = "en",
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
        push("wrong", _because_gap(open_gaps, lang))

    # ② 전문가 본인이 "아직 남았다" 고 표시한 곳.
    for name in sorted(flags or ()):
        push("aloud", _because_flag(name, lang))
        break

    # ②.5 같은 영역에서 신호가 겹치는 두 카드 — 무엇이 갈랐는지가 판별
    # 지식이다. 겹침 판정은 토큰(결정적)으로 한다.
    pair = _overlapping_pair(cards)
    if pair:
        push("contrast", _because_pair(pair[0].title, pair[1].title, lang))

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
                push(key, _because_empty(target.title, slot, lang), target.id)
                break

    if not out:
        push("moment", _because_default(lang))
    return out[:limit]


def slot_label(slot: str, lang: str = "en") -> str:
    """카드 칸 이름. 문안은 ``app/i18n.py`` 가 갖는다."""
    from app.i18n import t

    return t(f"slot.{slot}", lang)


# ── 추천 사유 문장 (근거 없는 추천은 하지 않는다) ──────────────────────

def _overlapping_pair(cards: list[Card]) -> tuple[Card, Card] | None:
    """같은 영역에서 신호 토큰이 겹치는 살아있는 카드 한 쌍."""
    from app.core.retrieval import tokenize

    live = [c for c in cards if c.status.value not in ("dormant", "draft") and c.cues]
    by_domain: dict[str, list[Card]] = {}
    for c in live:
        by_domain.setdefault(c.domain or "-", []).append(c)
    for group in by_domain.values():
        for i, a in enumerate(group):
            ta = set(tokenize(" ".join(a.cues)))
            for b in group[i + 1:]:
                if ta & set(tokenize(" ".join(b.cues))):
                    return (a, b)
    return None


def _because_pair(a: str, b: str, lang: str) -> str:
    if lang == "ko":
        return f"「{a[:18]}」와 「{b[:18]}」의 신호가 겹칩니다 — 무엇이 갈랐는지가 판별 지식입니다."
    return f"'{a[:22]}' and '{b[:22]}' share cues — what told them apart is the knowledge."


def _because_gap(count: int, lang: str) -> str:
    if lang == "ko":
        return f"후배가 막힌 곳 {count}건이 기다립니다. 3분이면 됩니다."
    noun = "place" if count == 1 else "places"
    verb = "is" if count == 1 else "are"
    return f"{count} {noun} where a junior got stuck {verb} waiting. Three minutes."


def _because_flag(name: str, lang: str) -> str:
    if lang == "ko":
        return f"'{name}'에 깃발을 꽂아두셨습니다."
    return f"You planted a flag on '{name}'."


def _because_empty(title: str, slot: str, lang: str) -> str:
    label = slot_label(slot, lang)
    if lang == "ko":
        return f"'{title}'에 {label}가 비어 있습니다."
    return f"'{title}' has no {label.lower()} yet."


def _because_default(lang: str) -> str:
    if lang == "ko":
        return "오늘 내린 판단 하나만 남겨두세요."
    return "Leave behind just one call you made today."
