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

import re

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
    #: 이 사람이 판 언어. 카드는 파낸 언어로 산다 (docs/design.md §7).
    lang: str = "ko"
    #: 남긴 카드 수 — 언어 경계에서 "없다" 와 "못 읽는다" 를 가르는 데 쓴다.
    card_count: int = 0

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
    #: 탐색 쿼터로 밀어올려진 카드 — "새 판단이라 아직 검증이 얇다" 를 후배가
    #: 알아야 한다. 표시 없이 밀어올리면 검증 안 된 카드가 검증된 것처럼 읽힌다.
    explored: list[str] = field(default_factory=list)
    #: 🔴 손끝 지식이 걸리면 "읽어서 안 됩니다" 를 함께 말한다
    apprentice_notice: str = ""
    stubbed: bool = False

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": round(self.confidence, 3),
            "is_gap": self.is_gap,
            "contested": self.contested,
            "explored": self.explored,
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


#: 인용 토큰 — 카드 블록이 쓰는 형식 그대로 ``[#카드id]``. id 형식을 가정하지
#: 않는다 — 형식이 바뀌면 검증이 조용히 무력화되는 것보다, 토큰 규약 하나에
#: 묶이는 편이 안전하다.
_CITE = re.compile(r"\[#([^\[\]\s]+)\]")


def _grounded(text: str, chosen: list[Card]) -> bool:
    """생성된 답이 근거 위에 서 있는가 — 결정적 검사, LLM 없음.

    ① 인용이 하나도 없으면 탈락 — 근거 없는 문장은 검증할 방법이 없다.
    ② 선택되지 않은 카드를 인용하면 탈락 — 지어낸 출처다.
    ③ 문단(빈 줄 구분) 각각에 인용이 있어야 한다 — 인용 하나 달고 그 뒤로
       자유 발화하는 패턴을 막는다. 짧은 연결 문단(한 줄, 80자 미만)은 봐준다.
    """
    cited = set(_CITE.findall(text))
    if not cited:
        return False
    allowed = {c.id for c in chosen}
    if not cited <= allowed:
        return False
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    for para in paragraphs:
        if _CITE.search(para):
            continue
        if len(para) < 80 and "\n" not in para:
            continue   # 인사말·연결 문장 정도는 허용
        return False
    return True


#: 자책·실패 어휘 — 서술 문장에 이 말이 나오면, 그 **어간이 카드 원문에
#: 실제로 있는지** 를 기계가 확인한다. 회고체를 자연스럽게 만들려고 LLM 이
#: "그 신호를 놓친 것은 나의 실패였다" 를 지어낸 실측이 이 검열의 이유다 —
#: 판단 답변의 환각보다 회고록의 허위 자책이 명예에 더 깊이 닿는다.
_BLAME = {
    "실패": ("실패",), "후회": ("후회",), "놓쳤": ("놓치", "놓쳤", "놓친"),
    "놓친": ("놓치", "놓쳤", "놓친"), "잘못": ("잘못",), "부끄": ("부끄",),
    "뼈아": ("뼈아",), "아쉬": ("아쉬",), "자책": ("자책",), "탓": ("탓",),
    "fail": ("fail",), "regret": ("regret",), "mistake": ("mistake",),
    "missed": ("miss",), "ashamed": ("ashamed", "shame"), "blame": ("blame",),
}


def _honest_prose(text: str, cards: list[Card]) -> str:
    """카드에 없는 실패·자책 문장을 **통째로 떨군다** — 문장 단위, 결정적.

    회고록 서술은 표지고 카드가 진실이다. 표지가 진실에 없는 자책을 더하면
    그 문장만 빠진다 — 나머지 서술은 산다. 전부 떨어지면 빈 문자열
    (화면은 카드 원문만 남는다 — 지어낸 회고보다 낫다).
    """
    corpus = " ".join(
        " ".join([c.title, c.situation, c.judgment, c.rationale, c.failure,
                  " ".join(c.cues), " ".join(c.action), " ".join(c.exceptions)])
        for c in cards
    ).lower()
    kept: list[str] = []
    for sent in re.split(r"(?<=[.!?다])\s+", text.strip()):
        if not sent.strip():
            continue
        low = sent.lower()
        fabricated = False
        for word, stems in _BLAME.items():
            if word in low and not any(st in corpus for st in stems):
                log.warning("회고록 서술에서 카드에 없는 자책 문장 제거: %s", sent[:60])
                fabricated = True
                break
        if not fabricated:
            kept.append(sent.strip())
    return " ".join(kept)


def memoir_prose(
    llm: BaseLLM, *, name: str, sayings: list[str], domain: str,
    cards: list[Card], lang: str = "en",
) -> str:
    """회고록 장(章) 서두의 1인칭 서술 — **삶을 지어내지 않는다.**

    자서전 형태를 위해 흐르는 문장을 엮되, 재료는 카드에 적힌 사실뿐이다.
    태어난 곳·가족·감정사 같은 전기적 사실을 발명하는 순간 이것은 그 사람의
    책이 아니라 기계의 소설이 된다. 화면에는 "카드에서 엮음" 표시가 붙고,
    판단 기록 원문이 본문으로 함께 남는다 — 서술은 표지이고 카드가 진실이다.
    """
    if not cards:
        return ""
    block = _cards_block(cards, lang)
    voice = " / ".join(sayings[:2]) if sayings else ""
    if lang == "ko":
        prompt = (
            f"{name} 의 회고록에서 '{domain}' 장을 여는 서술을 써라.\n"
            "규칙:\n"
            "· 1인칭('나는'). 3~5문장. 담담한 회고체.\n"
            "· 아래 판단 카드에 적힌 사실만 쓴다. 카드에 없는 사건·장소·인물·"
            "감정사를 지어내지 마라.\n"
            "· 실패담은 카드의 '실패' 칸에 **적혀 있을 때만** 한 문장으로 "
            "품어라. 카드에 없는 실패·후회·자책을 만들어 넣지 마라 — "
            "이것은 그 사람의 공식 기록이다.\n"
            f"{'· 이 사람의 말투: ' + voice if voice else ''}\n"
            f"\n[판단 카드]\n{block}\n\n서술만 출력하라."
        )
    else:
        prompt = (
            f"Write the opening passage of the '{domain}' chapter of {name}'s "
            "memoir.\n"
            "Rules:\n"
            "- First person. 3-5 sentences. Quiet, reflective tone.\n"
            "- Use only facts present in the cards below. Invent no events, "
            "places, people, or feelings that are not there.\n"
            "- Include a failure only if the cards' failure field actually "
            "records one. Never invent failure, regret or self-blame that is "
            "not on the cards — this is the person's official record.\n"
            f"{'- Their turns of phrase: ' + voice if voice else ''}\n"
            f"\n[Judgment cards]\n{block}\n\nOutput the passage only."
        )
    try:
        text = llm.answer("", prompt).strip()
    except Exception:
        return ""
    if not text or text.startswith("⚠"):
        return ""
    # 프롬프트는 부탁이고 검열은 집행이다 — 카드에 없는 자책 문장은 여기서
    # 기계적으로 떨어진다.
    return _honest_prose(text, cards)


def gap_message(
    persona: Persona,
    *,
    days_left: int | None,
    alternatives: list[str],
    lang: str = "en",
) -> str:
    """모른다고 말하는 화면. **이걸 잘 말하는 것이 이 제품의 기능이다.**

    단, **"안 남겼다" 와 "다른 언어로 남겼다" 는 다른 말이다.** 카드가 있는데도
    언어가 달라서 못 걸린 것을 "남기지 않은 영역" 이라고 하면, 설계 결정이
    제품 결함으로 읽힌다. 언어 경계에서는 막다른 길이 아니라 이정표를 준다.
    """
    if persona.lang and persona.lang != lang and persona.card_count:
        lines = [
            t("alter.msg.lang_wall", lang,
              name=persona.display_name or persona.expert,
              count=(t("alter.msg.cards.one", lang) if persona.card_count == 1
                     else t("alter.msg.cards.many", lang, persona.card_count)),
              language=t(f"lang.name.{persona.lang}", lang)),
        ]
        if alternatives:
            lines += ["", t("alter.msg.lang_wall.alt", lang, ", ".join(alternatives))]
        return "\n".join(lines)

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
            "라고 말해라.\n"
            "인용 규약: 모든 문단 끝에 근거가 된 카드의 [#카드아이디] 를 붙여라. "
            "인용이 없거나 위 목록에 없는 카드를 인용한 답은 기계 검증에서 "
            "통째로 버려진다."
        )
    else:
        prompt = (
            f"[Judgment cards {who} left behind]\n{_cards_block(chosen, lang)}\n\n"
            f"[The junior's question]\n{question}\n\n"
            "Answer only from within these cards. For anything not on them, say "
            "\"they did not leave that behind\".\n"
            "Citation contract: end every paragraph with the [#card-id] it rests "
            "on. An answer with uncited paragraphs, or citing a card not listed "
            "above, is discarded whole by a mechanical check."
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
    elif not _grounded(text, chosen):
        # 인용 검증 — "카드 밖으로 나가지 않는다" 를 프롬프트에 부탁하지 않고
        # 코드가 확인한다. 답의 모든 문단에 실제 선택된 카드의 인용이 붙어
        # 있어야 하고, 없는 카드를 인용하면 탈락이다. 탈락하면 지어냈을지도
        # 모르는 문장 대신 **카드 원문**으로 강등한다 — 이 도구에서 생성은
        # 편의고, 원문은 진실이다.
        # 탈락 시 **한 번만** 교정 재생성한다 — 규약 위반은 대개 형식 실수라
        # (마지막 문단 인용 누락 등) 사유를 짚어 주면 고쳐 온다. 그래도
        # 탈락이면 카드 원문으로 강등 — 생성은 편의고, 원문은 진실이다.
        # (저장 직후 첫 성공 장면이 원문 덤프로 보인 QA 실측이 이 재시도의 이유.)
        log.warning("분신 답변이 인용 검증 탈락 — 1회 교정 재생성")
        redo = prompt + (
            "\n\n[기계 검증 탈락] 직전 답은 문단마다 [#카드아이디] 인용이 "
            "없거나 목록 밖 카드를 인용해 폐기됐다. 같은 내용을 규약대로 "
            "다시 써라." if lang == "ko" else
            "\n\n[Mechanical check failed] The previous answer was discarded: "
            "a paragraph lacked its [#card-id] citation or cited an unlisted "
            "card. Rewrite the same answer following the contract."
        )
        try:
            text = llm.answer(_system(persona, lang), redo).strip()
        except Exception as exc:
            log.warning("교정 재생성 실패: %s", exc)
            text = ""
        if not text or text.startswith("⚠") or not _grounded(text, chosen):
            log.warning("교정 재생성도 탈락 — 카드 원문으로 강등")
            stubbed = True
            text = t("alter.msg.ungrounded", lang) + "\n\n" + _cards_block(chosen, lang)

    # 근거는 **실제로 인용된 카드만**이다. 검색이 6장을 골랐어도(탐색
    # 쿼터가 밀어 올린 카드 포함) 답이 2장만 인용했으면 Evidence 는 2장 —
    # 무관한 카드의 ⚠ 경고가 이 답에 붙고 인용 수까지 부풀던 것이 QA
    # 실측이다. 원문 강등(stubbed)일 때만 보여준 원문 전체가 근거다.
    if not stubbed:
        cited_ids = set(_CITE.findall(text))
        evidence = [c for c in chosen if c.id in cited_ids] or chosen[:1]
    else:
        evidence = chosen
    contested = [c.id for c in evidence if c.status is CardStatus.CONTESTED]
    explored = [h.card.id for h in result.hits if h.explored]
    notice = ""
    if any(c.tacitness is Tacitness.HANDS for c in evidence):
        notice = t("alter.msg.apprentice", lang)
    return AlterReply(
        text=text,
        cards=evidence,
        confidence=result.confidence,
        is_gap=False,
        contested=contested,
        explored=explored,
        apprentice_notice=notice,
        stubbed=stubbed,
    )
