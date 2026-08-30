"""결정론 판정 엔진 — 승인된 규칙만 실행한다.

컴파일러의 실행 층이다 (docs/roadmap.md): LLM 은 프로토콜을 **발견**하고
(인터뷰→카드), 전문가가 규칙을 **승인**하고(rule_all·rule_none·priority·
unknown), 이 모듈이 그 규칙을 **실행**한다. LLM 은 여기서 호출되지 않는다 —
같은 답이면 언제나 같은 판정이고, 그래서 검사·감사가 가능하다.

의미론 (외부 QA 가 준 스펙 — veTriage 재현 실험 실측):
- 트리거: 신호(cues) 중 하나라도 '예' (any_of).
- 성립(applies): 트리거 + rule_all 전부 '예' + rule_none 전부 '아니오'
  + 관련 미확인 0개. **완화 판단은 이 문을 다 지나야만 나온다.**
- 상향(escalate): 트리거됐고 반박되지 않았는데 미확인이 남은 카드가
  rule_unknown="escalate" 면 — 모른다는 이유로 내려가지 않는다.
- 반박(refuted): rule_all 중 '아니오' 가 있거나 rule_none 중 '예' 가 있다.
- 충돌: 성립·상향 중 rule_priority 높은 쪽이 판정이다. 온화한 카드가
  위급한 카드를 지우지 못한다.
- 규칙이 빈 카드는 판정 대상이 아니다(untriaged) — 열람으로만 선다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.card import Card

#: 답의 3상 — 체크박스가 아니라 예/아니오/모름. '모름' 이 1급 시민인 것이
#: 이 엔진의 존재 이유다: 모름은 절대 하향의 근거가 되지 않는다.
YES, NO, UNKNOWN = "yes", "no", "unknown"


@dataclass
class Verdict:
    card_id: str
    title: str
    #: applies | escalate | refuted | insufficient | untriaged
    state: str
    priority: int = 0
    #: 성립을 막고 있는 미확인 항목 — 화면이 "이것부터 확인하라" 로 세운다
    unknowns: list[str] = field(default_factory=list)
    #: 반박 근거 — 어떤 답이 이 카드를 눕혔는가
    refuted_by: list[str] = field(default_factory=list)


def _answer(answers: dict[str, str], sign: str) -> str:
    return answers.get(sign, UNKNOWN)


def evaluate_card(card: Card, answers: dict[str, str]) -> Verdict:
    """카드 하나의 판정 — 순수 함수, LLM 없음."""
    ruled = bool(card.rule_all or card.rule_none or card.rule_priority)
    if not ruled:
        return Verdict(card.id, card.title, "untriaged")

    triggered = any(_answer(answers, c) == YES for c in card.cues) if card.cues else True

    refuted_by = [s for s in card.rule_all if _answer(answers, s) == NO]
    refuted_by += [s for s in card.rule_none if _answer(answers, s) == YES]
    if refuted_by:
        return Verdict(card.id, card.title, "refuted",
                       priority=card.rule_priority, refuted_by=refuted_by)

    unknowns = [s for s in card.rule_all if _answer(answers, s) == UNKNOWN]
    unknowns += [s for s in card.rule_none if _answer(answers, s) == UNKNOWN]

    if not triggered:
        # 신호가 하나도 '예' 가 아니면 이 카드는 아직 무대에 없다.
        return Verdict(card.id, card.title, "insufficient",
                       priority=card.rule_priority, unknowns=unknowns)
    if not unknowns:
        return Verdict(card.id, card.title, "applies", priority=card.rule_priority)
    if card.rule_unknown == "escalate":
        # 트리거됐고 반박도 안 됐는데 확인이 안 끝났다 — 위로 간다.
        return Verdict(card.id, card.title, "escalate",
                       priority=card.rule_priority, unknowns=unknowns)
    return Verdict(card.id, card.title, "insufficient",
                   priority=card.rule_priority, unknowns=unknowns)


def evaluate(cards: list[Card], answers: dict[str, str]) -> dict:
    """영역의 판정 — 성립·상향 가운데 우선순위 최상이 최종이다."""
    verdicts = [evaluate_card(c, answers) for c in cards]
    standing = [v for v in verdicts if v.state in ("applies", "escalate")]
    standing.sort(key=lambda v: (-v.priority, v.state != "escalate"))
    top = standing[0] if standing else None
    return {
        "top": top,
        "verdicts": verdicts,
        #: 판정이 하나도 못 서면 화면은 공백 경로(분신→전문가 큐)로 보낸다
        "open": top is None,
    }
