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


def sign_key(line: str) -> tuple[str, str]:
    """규칙 줄 → (canonical ID, 표시 문구).

    같은 임상 신호가 카드마다 다른 문장으로 적히면 문진에 두 번 서고,
    한쪽 '예' / 한쪽 '아니오' 라는 모순 입력이 가능해진다 (QA P0 실측:
    같은 헛구역질이 문구에 따라 상향/판정없음으로 갈렸다). 전문가가 규칙
    줄에 `dry_heaving :: 반복적으로 토하려 하지만 아무것도 안 나옴` 처럼
    ID 를 달면, **같은 ID 는 하나의 질문이고 답 하나가 그 ID 를 쓰는
    모든 카드에 동시에 적용된다.** 태그 없는 줄은 문장 자체가 ID 다
    (하위 호환). ID 부여도 전문가 승인 화면의 몫 — 기계가 문장 유사도로
    동치를 추측하지 않는다.
    """
    if "::" in line:
        left, right = line.split("::", 1)
        key, label = left.strip(), right.strip()
        return (key or label), (label or key)
    t = line.strip()
    return t, t


def _answer(answers: dict[str, str], sign: str) -> str:
    key, _ = sign_key(sign)
    return answers.get(key, UNKNOWN)


def _labels(lines: list[str], answers: dict[str, str], want: str) -> list[str]:
    return [sign_key(s)[1] for s in lines if _answer(answers, s) == want]


def evaluate_card(card: Card, answers: dict[str, str]) -> Verdict:
    """카드 하나의 판정 — 순수 함수, LLM 없음."""
    ruled = bool(card.rule_all or card.rule_none or card.rule_priority)
    if not ruled:
        return Verdict(card.id, card.title, "untriaged")

    # 트리거는 두 갈래다: ① 신호(cues) 중 하나 '예' (any_of — 위급 카드의
    # 관례), ② **rule_all 전부 '예'** — 전문가가 성립 조건을 all_of 로
    # 정의했으면 그 충족이 곧 트리거다. ②가 없던 것이 QA P0 실측이다:
    # RED 조건 3개를 all_of 에 넣고 전부 '예' 로 답했는데 옛 신호가
    # 미답이라 "해당 신호 없음" 이 나왔다.
    cue_hit = any(_answer(answers, c) == YES for c in card.cues)
    # rule_all 은 성립의 문이지 입장의 문이 아니다 — 조건 **하나라도**
    # '예' 면 카드는 무대에 오른다. 안 그러면 위급 신호 하나를 본 심사자가
    # "성립하는 판단이 없습니다" 를 받는다 (QA P0 실측: 무산성 헛구역질
    # 하나 '예' → 판정 없음). 하나 '예' + 나머지 모름은 applies 가 아니라
    # **escalate** 로 나간다 — 성립의 문(전부 '예')은 그대로 닫혀 있다.
    any_hit = any(_answer(answers, s) == YES for s in card.rule_all)
    triggered = cue_hit or any_hit or (not card.cues and not card.rule_all)

    refuted_by = _labels(card.rule_all, answers, NO)
    refuted_by += _labels(card.rule_none, answers, YES)
    if refuted_by:
        return Verdict(card.id, card.title, "refuted",
                       priority=card.rule_priority, refuted_by=refuted_by)

    unknowns = _labels(card.rule_all, answers, UNKNOWN)
    unknowns += _labels(card.rule_none, answers, UNKNOWN)

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
