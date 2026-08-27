"""분신 (Alter) — 전문가가 남는 형태.

**3대 규약. 코드로 강제하며, 되돌리지 말 것** (docs/design.md §3.3):

1. **카드 밖으로 나가지 않는다.** 근거 카드 없이는 한 문장도 만들지 않는다.
   일반 LLM 상식으로 메우는 순간 이것은 사내 챗봇이 되고 신뢰를 잃는다.
2. **항상 근거를 편다.** 답 옆에 인용 카드가 뜨고, 검증 여부가 붙는다.
3. **사칭하지 않는다.** "홍길동 수석" 이 아니라 **"홍길동 수석의 분신"** 이다.

그리고 가장 중요한 구조:

    **모른다는 판정은 LLM 이 하지 않는다.**

:func:`respond` 는 확신도가 바닥 미만이면 **LLM 을 호출하지 않고** 공백을
반환한다. LLM 에게 "모르면 모른다고 해" 라고 부탁하는 설계는 실패한다.
``tests/test_core.py::test_gap_decision_never_calls_the_llm`` 이 이를 강제한다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.capture.llm import BaseLLM
from app.i18n import t
from app.core.card import Card, CardStatus, Tacitness
from app.core.retrieval import Retrieval, retrieve

log = logging.getLogger(__name__)


@dataclass
class Persona:
    """분신의 목소리. 전문가가 온보딩에서 직접 채운다 (user-flows S1)."""

    expert: str
    display_name: str = ""
    #: 자주 하는 말 — 어투가 여기서 나온다
    sayings: list[str] = field(default_factory=list)
    #: "절대 이러지 마라" 고 가르치는 것 — 안전 원칙
    taboos: list[str] = field(default_factory=list)
    active: bool = True   # 전문가가 자기 분신을 끌 수 있다 (통제권)

    def label(self, lang: str = "en") -> str:
        """화면에 뜨는 이름. **사칭 금지 규약의 구현.**

        어느 언어에서도 사람 이름 단독으로 뜨지 않는다 — 언제나 "…의 분신" /
        "…'s alter" 다. ``tests/test_core.py::test_alter_label_never_impersonates``
        가 이것을 강제한다.
        """
        return t("alter.of", lang, self.display_name or self.expert)


@dataclass
class AlterReply:
    text: str
    cards: list[Card]
    confidence: float
    is_gap: bool
    #: 인용 카드 중 논쟁 중인 것이 있으면 경고를 함께 낸다
    contested: list[str] = field(default_factory=list)
    #: 🔴 손끝 지식이 걸리면 "읽어서 안 됩니다" 를 함께 말한다
    apprentice_notice: str = ""
    stubbed: bool = False

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "is_gap": self.is_gap,
            "contested": self.contested,
            "apprentice_notice": self.apprentice_notice,
            "stubbed": self.stubbed,
            "cards": [
                {
                    "id": c.id,
                    "title": c.title,
                    "domain": c.domain,
                    "status": c.status.value,
                    "verified": c.status is CardStatus.ANCHORED,
                    "tacitness": c.tacitness.value,
                    "cues": c.cues,
                    "action": c.action,
                    "exceptions": c.exceptions,
                    "failure": c.failure,
                    "unspeakable": c.unspeakable,
                }
                for c in self.cards
            ],
        }


def _system_ko(persona: Persona) -> str:
    lines = [
        f"너는 '{persona.label('ko')}' 이다. {persona.display_name or persona.expert} 본인이 "
        "아니라 그가 남긴 판단 카드로만 말하는 분신이다.",
        "",
        "절대 규칙:",
        "1. 아래 제공된 카드에 있는 내용으로만 답해라. 카드에 없는 것은 "
        "일반 상식으로도 메우지 마라. 모르면 모른다고 해라.",
        "2. 답에 쓴 카드 번호를 문장 끝에 [#카드ID] 로 표시해라.",
        "3. 카드에 예외가 있으면 반드시 함께 말해라. 예외를 빠뜨린 답은 위험하다.",
        "4. 카드에 실패담이 있으면 접지 말고 그대로 알려줘라. 후배가 가장 필요로 한다.",
        "5. 본인인 척하지 마라. 너는 분신이다.",
        "6. 한국어로, 짧고 현장 말투로. 카드에 적힌 현장 용어를 그대로 써라.",
    ]
    if persona.sayings:
        lines.append("\n이 사람이 자주 하던 말 (어투 참고): " + " / ".join(persona.sayings))
    if persona.taboos:
        lines.append("이 사람이 절대 하지 말라고 가르친 것: " + " / ".join(persona.taboos))
    return "\n".join(lines)


def _system_en(persona: Persona) -> str:
    who = persona.display_name or persona.expert
    lines = [
        f"You are '{persona.label('en')}'. You are not {who} — you are an alter that "
        "speaks only from the judgment cards they left behind.",
        "",
        "Absolute rules:",
        "1. Answer only from the cards provided below. Do not fill gaps with general "
        "knowledge, not even common sense. If you do not know, say so.",
        "2. Mark the card you used at the end of the sentence as [#CARD_ID].",
        "3. If a card has exceptions, you must state them. An answer that drops the "
        "exception is dangerous.",
        "4. If a card has a war story, do not fold it away — a junior needs it most.",
        "5. Never pretend to be the person. You are an alter.",
        "6. Answer in English, short, in the voice of the shop floor. Keep the "
        "expert's own terms exactly as written on the card.",
    ]
    if persona.sayings:
        lines.append("\nThings this person said often (for voice): "
                     + " / ".join(persona.sayings))
    if persona.taboos:
        lines.append("What this person taught juniors never to do: "
                     + " / ".join(persona.taboos))
    return "\n".join(lines)


def _system(persona: Persona, lang: str = "en") -> str:
    return _system_ko(persona) if lang == "ko" else _system_en(persona)


def _cards_block(cards: list[Card], lang: str = "en") -> str:
    """카드 원문 블록. **카드 내용은 번역하지 않는다** — 전문가가 자기 현장
    용어로 쓴 원본이고, 번역하면 지식이 아니라 요약이 된다. 라벨만 언어를 탄다."""
    L = {
        "situation": t("slot.situation", lang),
        "cues": t("slot.cues", lang),
        "judgment": t("slot.judgment", lang),
        "action": t("slot.action", lang),
        "rationale": t("slot.rationale", lang),
        "exceptions": t("slot.exceptions", lang),
        "failure": t("slot.failure", lang),
    }
    verified = "(현장 검증됨)" if lang == "ko" else "(verified in the field)"
    contested = (
        "(최근 안 맞았다는 보고가 있음 — 그대로 알려줄 것)" if lang == "ko"
        else "(recently reported as not holding — say so plainly)"
    )
    out = []
    for c in cards:
        parts = [f"[#{c.id}] {c.title}"]
        if c.situation:
            parts.append(f"  {L['situation']}: {c.situation}")
        if c.cues:
            parts.append(f"  {L['cues']}: " + " / ".join(c.cues))
        if c.judgment:
            parts.append(f"  {L['judgment']}: {c.judgment}")
        if c.action:
            parts.append(f"  {L['action']}: " + " → ".join(c.action))
        if c.rationale:
            parts.append(f"  {L['rationale']}: {c.rationale}")
        if c.exceptions:
            parts.append(f"  {L['exceptions']}: " + " / ".join(c.exceptions))
        if c.failure:
            parts.append(f"  {L['failure']}: {c.failure}")
        if c.status is CardStatus.ANCHORED:
            parts.append(f"  {verified}")
        if c.status is CardStatus.CONTESTED:
            parts.append(f"  {contested}")
        out.append("\n".join(parts))
    return "\n\n".join(out)


def gap_message(
    persona: Persona,
    *,
    days_left: int | None,
    alternatives: list[str],
    lang: str = "en",
) -> str:
    """모른다고 말하는 화면. **이걸 잘 말하는 것이 이 제품의 기능이다.**"""
    sent = t("alter.msg.gap.sent", lang)
    if days_left is not None:
        sent += t("alter.msg.gap.dday", lang, days_left)
    lines = [
        t("alter.msg.gap", lang, name=persona.display_name or persona.expert),
        "",
        sent,
    ]
    if alternatives:
        lines.append(t("alter.msg.gap.alt", lang, ", ".join(alternatives)))
    return "\n".join(lines)


def respond(
    llm: BaseLLM,
    persona: Persona,
    cards: list[Card],
    question: str,
    *,
    viewer: str = "",
    top_k: int = 6,
    explore_quota: float = 0.25,
    confidence_floor: float = 0.35,
    days_left: int | None = None,
    alternatives: list[str] | None = None,
    lang: str = "en",
) -> AlterReply:
    """후배의 질문 → 분신의 답. 근거 없으면 답하지 않는다."""
    if not persona.active:
        return AlterReply(
            text=t("alter.msg.stopped", lang, label=persona.label(lang)),
            cards=[], confidence=0.0, is_gap=True,
        )

    result: Retrieval = retrieve(
        cards,
        question,
        viewer=viewer,
        top_k=top_k,
        explore_quota=explore_quota,
        confidence_floor=confidence_floor,
    )

    if result.is_gap:
        # LLM 은 여기서 호출되지 않는다. 이 줄이 이 파일의 존재 이유다.
        return AlterReply(
            text=gap_message(
                persona, days_left=days_left,
                alternatives=alternatives or [], lang=lang,
            ),
            cards=[],
            confidence=result.confidence,
            is_gap=True,
        )

    chosen = result.cards
    who = persona.display_name or persona.expert
    if lang == "ko":
        prompt = (
            f"[{who}님이 남긴 판단 카드]\n{_cards_block(chosen, lang)}\n\n"
            f"[후배의 질문]\n{question}\n\n"
            "위 카드 안에서만 답해라. 카드에 없는 부분은 '그건 남기지 않으셨습니다' "
            "라고 말해라."
        )
    else:
        prompt = (
            f"[Judgment cards {who} left behind]\n{_cards_block(chosen, lang)}\n\n"
            f"[The junior's question]\n{question}\n\n"
            "Answer only from within these cards. For anything not on them, say "
            "\"they did not leave that behind\"."
        )
    stubbed = False
    try:
        text = llm.answer(_system(persona, lang), prompt).strip()
    except Exception as exc:
        log.warning("분신 응답 실패, 카드 원문으로 대체: %s", exc)
        text = ""
    if not text or text.startswith("⚠"):
        # stub/실패 시에도 **카드 원문**을 보여준다. 지어내는 것보다 낫다.
        stubbed = True
        text = t("alter.msg.stub", lang) + "\n\n" + _cards_block(chosen, lang)

    contested = [c.id for c in chosen if c.status is CardStatus.CONTESTED]
    notice = ""
    if any(c.tacitness is Tacitness.HANDS for c in chosen):
        notice = t("alter.msg.apprentice", lang)
    return AlterReply(
        text=text,
        cards=chosen,
        confidence=result.confidence,
        is_gap=False,
        contested=contested,
        apprentice_notice=notice,
        stubbed=stubbed,
    )
