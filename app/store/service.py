"""오케스트레이션 — 한 바퀴가 여기서 돈다.

    발굴(연장) → 카드 초안 → 전문가 승인 → 분신이 인용 → 적용 보고(닻)
              ↑                                              │
              └────────── 공백 큐 ◀───────────────────────────┘
                              │
                        유산 원장 (보람)

규칙 위반은 :class:`ServiceError` 로 던지고 웹 층이 400 으로 바꾼다 (500 아님).
사용자에게 그대로 보여줄 문장으로 쓴다.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session as OrmSession

from app.alter.persona import AlterReply, Persona, respond
from app.capture import interview
from app.capture.instruments import LADDER, recommend, unlocked
from app.capture.llm import get_llm
from app.config import settings
from app.core import coverage as cov
from app.core import legacy
from app.core.card import Card, CardStatus, Tacitness, Visibility
from app.i18n import DEFAULT as LANG_DEFAULT
from app.i18n import t
from app.store import db


class ServiceError(Exception):
    """규칙 위반. 500 이 아니라 400 으로 나간다."""


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _lines(text: str) -> list[str]:
    return [line.strip() for line in (text or "").split("\n") if line.strip()]


def _join(items: list[str]) -> str:
    return "\n".join(i.strip() for i in items if i and i.strip())


# ------------------------------------------------------------------ 조립/해체

def row_to_card(row: db.CardRow) -> Card:
    return Card(
        id=row.id,
        expert=row.expert,
        title=row.title,
        domain=row.domain,
        situation=row.situation,
        cues=_lines(row.cues),
        judgment=row.judgment,
        action=_lines(row.action),
        rationale=row.rationale,
        exceptions=_lines(row.exceptions),
        failure=row.failure,
        unspeakable=_lines(row.unspeakable),
        status=CardStatus(row.status),
        tacitness=Tacitness(row.tacitness),
        visibility=Visibility(row.visibility),
        for_whom=row.for_whom,
        open_at=row.open_at,
        risk=row.risk,
        instrument=row.instrument,
        source_turn=row.source_turn,
        citations=row.citations,
        helped=row.helped,
        missed=row.missed,
    )


def write_card(row: db.CardRow, card: Card) -> None:
    row.title = card.title
    row.domain = card.domain
    row.situation = card.situation
    row.cues = _join(card.cues)
    row.judgment = card.judgment
    row.action = _join(card.action)
    row.rationale = card.rationale
    row.exceptions = _join(card.exceptions)
    row.failure = card.failure
    row.unspeakable = _join(card.unspeakable)
    row.status = card.status.value
    row.tacitness = card.tacitness.value
    row.visibility = card.visibility.value
    row.for_whom = card.for_whom
    row.open_at = card.open_at
    row.risk = card.risk


def cards_of(session: OrmSession, expert: str) -> list[Card]:
    rows = session.scalars(
        select(db.CardRow).where(db.CardRow.expert == expert)
    ).all()
    return [row_to_card(r) for r in rows]


def get_expert(
    session: OrmSession, expert_id: str, *, lang: str = LANG_DEFAULT
) -> db.Expert:
    row = session.get(db.Expert, expert_id)
    if row is None:
        raise ServiceError(t("err.no_expert", lang, expert_id))
    return row


def ensure_expert(session: OrmSession, expert_id: str, **fields: Any) -> db.Expert:
    row = session.get(db.Expert, expert_id)
    if row is None:
        row = db.Expert(id=expert_id, display_name=fields.get("display_name", expert_id))
        session.add(row)
    for key, value in fields.items():
        if value is not None:
            setattr(row, key, value)
    session.commit()
    return row


def persona_of(row: db.Expert, *, card_count: int = 0) -> Persona:
    return Persona(
        expert=row.id,
        display_name=row.display_name,
        sayings=_lines(row.sayings),
        taboos=_lines(row.taboos),
        active=row.alter_active,
        lang=row.lang,
        card_count=card_count,
    )


def _confirmed_count(session: OrmSession, expert: str) -> int:
    """이 사람이 실제로 남긴 카드 수. 언어 경계 문안이 이 숫자에 달려 있다 —
    0 이면 정말 안 남긴 것이고, 0 이 아니면 못 읽는 것뿐이다."""
    dead = (CardStatus.DRAFT.value, CardStatus.DORMANT.value)
    return session.scalar(
        select(func.count()).select_from(db.CardRow).where(
            db.CardRow.expert == expert,
            db.CardRow.status.notin_(dead),
        )
    ) or 0


def days_left(row: db.Expert) -> int | None:
    if row.leaving_on is None:
        return None
    return (row.leaving_on - date.today()).days


def _log(
    session: OrmSession,
    expert: str,
    event: legacy.LedgerEvent,
    *,
    card_id: str = "",
    actor: str = "",
    detail: str = "",
) -> None:
    session.add(
        db.LedgerRow(
            expert=expert, event=event.value, card_id=card_id, actor=actor, detail=detail
        )
    )


# --------------------------------------------------------------------- 발굴

def start_session(
    session: OrmSession, expert: str, *, instrument: str = LADDER,
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """발굴 세션 시작. **연장은 전문가가 고른다** — 기본값은 사다리."""
    get_expert(session, expert, lang=lang)
    row = db.Session(id=_uid("s"), expert=expert, instrument=instrument)
    session.add(row)

    gap = _top_gap(session, expert)
    question = interview.next_question(
        get_llm(),
        instrument=instrument,
        gap_question=gap.question if gap else "",
        lang=lang,
    )
    turn = db.Turn(
        id=_uid("t"), session_id=row.id, question=question.text, rung=question.rung,
        targets=question.targets,
    )
    session.add(turn)
    session.commit()
    return {
        "session_id": row.id,
        "instrument": instrument,
        "turn_id": turn.id,
        "question": question.text,
        "rung": question.rung,
        "from_gap": bool(gap),
        "target": settings.interview_turns,
        "index": 1,
    }


def answer_turn(
    session: OrmSession, turn_id: str, answer: str, *, skip: bool = False,
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """전문가의 답 하나 → 카드 갱신 → 다음 질문.

    **"넘길게요" 는 항상 허용한다.** 못 답할 질문을 강요하면 다음에 안 온다
    (docs/elicitation-protocol.md §2).
    """
    turn = session.get(db.Turn, turn_id)
    if turn is None:
        raise ServiceError(t("err.no_turn", lang))
    if turn.answer:
        raise ServiceError(t("err.already_answered", lang))

    turn.answer = answer.strip()
    turn.skipped = skip or not turn.answer
    sess = session.get(db.Session, turn.session_id)
    if sess is None:
        raise ServiceError(t("err.no_session", lang))

    history = _history(session, sess.id)
    card_row = _upsert_card(session, sess, history, lang=lang)
    card = row_to_card(card_row)

    question = interview.next_question(
        get_llm(), instrument=sess.instrument, card=card, history=history, lang=lang
    )
    next_turn = db.Turn(
        id=_uid("t"), session_id=sess.id, question=question.text, rung=question.rung,
        targets=question.targets,
    )
    session.add(next_turn)
    session.commit()

    answered = sum(1 for _, a in history if a)
    filled_slot = turn.targets or interview.RUNG_SLOT.get(turn.rung, "")
    return {
        "card": card_view(card),
        "report": interview.slot_report(card, lang),
        # 되읽어주기 — 오해는 그 자리에서 잡는다 (elicitation-protocol §2).
        "reflection": (
            "" if turn.skipped else interview.reflect(card, filled_slot, lang)
        ),
        "turn_id": next_turn.id,
        "question": question.text,
        "rung": question.rung,
        "fallback": question.fallback,
        "index": answered + 1,
        "target": settings.interview_turns,
        "wrap_up": answered >= settings.interview_turns,
    }


def _history(session: OrmSession, session_id: str) -> list[tuple[str, str]]:
    turns = session.scalars(
        select(db.Turn).where(db.Turn.session_id == session_id).order_by(db.Turn.created_at)
    ).all()
    return [(t.question, t.answer) for t in turns if t.answer and not t.skipped]


def _slot_history(session: OrmSession, session_id: str) -> list[tuple[str, str]]:
    """(겨냥한 칸, 답) 쌍. 기저가 없을 때 카드를 채우는 유일한 근거다.

    ``targets`` 가 비면 그 단(rung)이 무엇을 물었는지로 떨어진다. 둘 다 없으면
    넣지 않는다 — 어느 칸인지 모르는 답을 아무 데나 넣지 않기 위해서다.
    """
    turns = session.scalars(
        select(db.Turn).where(db.Turn.session_id == session_id).order_by(db.Turn.created_at)
    ).all()
    pairs: list[tuple[str, str]] = []
    for turn in turns:
        if not turn.answer or turn.skipped:
            continue
        slot = turn.targets or interview.RUNG_SLOT.get(turn.rung, "")
        if slot:
            pairs.append((slot, turn.answer))
    return pairs


def _upsert_card(
    session: OrmSession, sess: db.Session, history: list[tuple[str, str]],
    *, lang: str = LANG_DEFAULT,
) -> db.CardRow:
    """대화가 쌓일 때마다 카드를 다시 뽑는다. 초안은 계속 덮어써도 안전하다 —
    승인 후에는 덮어쓰지 않는다 (전문가가 고친 것이 기계 추출보다 우선)."""
    draft = interview.capture(
        get_llm(), history, lang=lang, slots=_slot_history(session, sess.id)
    )
    if sess.card_id:
        row = session.get(db.CardRow, sess.card_id)
        if row is not None and row.status != CardStatus.DRAFT.value:
            return row
    else:
        row = None

    card = draft.to_card(
        id=sess.card_id or _uid("c"),
        expert=sess.expert,
        instrument=sess.instrument,
        source_turn=sess.id,
    )
    if row is None:
        row = db.CardRow(id=card.id, expert=sess.expert, title=card.title)
        session.add(row)
        sess.card_id = card.id
    write_card(row, card)
    row.instrument = sess.instrument
    row.source_turn = sess.id
    #: 카드는 파낸 언어로 산다. 검색이 언어를 넘지 않는 근거가 이 한 줄이다
    #: (docs/design.md §7) — 찾아 줘도 못 읽는 카드는 답이 아니기 때문이다.
    row.lang = lang
    return row


def confirm_card(
    session: OrmSession,
    card_id: str,
    *,
    edits: dict[str, Any] | None = None,
    tacitness: str = "",
    visibility: str = "",
    for_whom: str = "",
    open_at: date | None = None,
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """전문가 승인 — 이때부터 분신이 인용한다.

    승인 시 **통제권**(공개 범위)과 **암묵지 온도**를 본인이 정한다.
    """
    row = session.get(db.CardRow, card_id)
    if row is None:
        raise ServiceError(t("err.no_card", lang))
    card = row_to_card(row)

    for key, value in (edits or {}).items():
        if not hasattr(card, key):
            continue
        current = getattr(card, key)
        setattr(card, key, list(value) if isinstance(current, list) else value)
    if tacitness:
        card.tacitness = Tacitness(tacitness)
    if visibility:
        card.visibility = Visibility(visibility)
    if for_whom:
        card.for_whom = for_whom
    if open_at:
        card.open_at = open_at

    if not card.cues:
        raise ServiceError(t("err.no_cues", lang))
    card.status = CardStatus.CONFIRMED
    write_card(row, card)
    _log(session, card.expert, legacy.LedgerEvent.CARD_CONFIRMED, card_id=card.id)

    # 이 카드가 후배의 공백을 메웠는가 — 메웠으면 질문자에게 알릴 대상이 된다.
    filled = _match_gap(session, card)
    session.commit()
    return {
        "card": card_view(card),
        "warning": t("warn.no_exceptions", lang) if not card.exceptions else "",
        "filled_gap": filled,
    }


def dormant_card(
    session: OrmSession, card_id: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """폐기가 아니라 **잠복.** 조건이 바뀌면 되살아난다."""
    row = session.get(db.CardRow, card_id)
    if row is None:
        raise ServiceError(t("err.no_card", lang))
    row.status = CardStatus.DORMANT.value
    session.commit()
    return {"card_id": card_id, "status": row.status}


# ------------------------------------------------------------------- 오답 채점

def grade_prompt(
    session: OrmSession, expert: str, topic: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """⚖️ 오답 채점기 — 그럴듯한 오답을 내고 전문가에게 빨간펜을 준다."""
    get_expert(session, expert, lang=lang)
    cards = cards_of(session, expert)
    domain = cards[0].domain if cards else ""
    out = interview.wrong_answer(get_llm(), topic, domain, lang=lang)
    return {"topic": topic, **out}


# --------------------------------------------------------------------- 분신

def ask_alter(
    session: OrmSession, expert: str, question: str, *, asker: str = "",
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """후배의 질문 한 번. 답했으면 인용을, 못 답했으면 공백을 남긴다."""
    expert_row = get_expert(session, expert, lang=lang)
    persona = persona_of(expert_row, card_count=_confirmed_count(session, expert))
    cards = cards_of(session, expert)

    reply: AlterReply = respond(
        get_llm(),
        persona,
        cards,
        question,
        viewer=asker,
        top_k=settings.retrieval_top_k,
        explore_quota=settings.explore_quota,
        confidence_floor=settings.confidence_floor,
        days_left=days_left(expert_row),
        alternatives=_other_experts(session, expert, lang=lang),
        lang=lang,
    )

    ask = db.Ask(
        id=_uid("a"),
        expert=expert,
        asker=asker,
        question=question,
        answered=not reply.is_gap,
        confidence=reply.confidence,
    )
    session.add(ask)

    if reply.is_gap:
        _record_gap(session, expert, question, asker)
    else:
        for card in reply.cards:
            session.add(db.Citation(ask_id=ask.id, card_id=card.id))
            row = session.get(db.CardRow, card.id)
            if row is not None:
                row.citations += 1
        _log(
            session,
            expert,
            legacy.LedgerEvent.CITED,
            card_id=reply.cards[0].id,
            actor=asker,
            detail=question[:120],
        )
    session.commit()
    return {"ask_id": ask.id, "persona": persona.label(lang), **reply.as_dict()}


def _other_experts(
    session: OrmSession, expert: str, *, lang: str = ""
) -> list[str]:
    """다른 전문가. 물어본 언어로 판 사람만 세운다 — 못 읽을 사람을 권하면
    막다른 길을 하나 더 놓는 것이다."""
    rows = session.scalars(
        select(db.Expert).where(db.Expert.id != expert)
    ).all()
    if lang:
        rows = [r for r in rows if r.lang == lang]
    return [r.display_name or r.id for r in rows][:3]


def _record_gap(session: OrmSession, expert: str, question: str, asker: str) -> None:
    """같은 질문이 반복되면 카운트를 올린다 — 빈도가 곧 우선순위다."""
    existing = session.scalars(
        select(db.Gap).where(db.Gap.expert == expert, db.Gap.filled_card == "")
    ).all()
    key = set(_norm(question))
    for gap in existing:
        if key and len(key & set(_norm(gap.question))) / len(key) >= 0.6:
            gap.asked_count += 1
            gap.last_asked = datetime.now(timezone.utc)
            if asker and asker not in _lines(gap.askers):
                gap.askers = _join(_lines(gap.askers) + [asker])
            return
    session.add(
        db.Gap(id=_uid("g"), expert=expert, question=question, askers=asker or "")
    )


def _norm(text: str) -> list[str]:
    from app.core.retrieval import tokenize

    return tokenize(text)


def _top_gap(session: OrmSession, expert: str) -> db.Gap | None:
    gaps = open_gaps(session, expert)
    return gaps[0] if gaps else None


def open_gaps(session: OrmSession, expert: str) -> list[db.Gap]:
    """우선순위 = 질문 빈도 × 최근성. 현장 수요가 인터뷰 주제를 정한다."""
    rows = session.scalars(
        select(db.Gap).where(db.Gap.expert == expert, db.Gap.filled_card == "")
    ).all()
    return sorted(rows, key=lambda g: (-g.asked_count, g.last_asked), reverse=False)


def _match_gap(session: OrmSession, card: Card) -> str:
    """새 카드가 열린 공백을 메웠는지 확인한다."""
    for gap in open_gaps(session, card.expert):
        from app.core.retrieval import retrieve

        result = retrieve(
            [card], gap.question, viewer=card.expert,
            confidence_floor=settings.confidence_floor,
        )
        if not result.is_gap:
            gap.filled_card = card.id
            _log(
                session,
                card.expert,
                legacy.LedgerEvent.GAP_FILLED,
                card_id=card.id,
                detail=gap.question[:120],
            )
            return gap.question
    return ""


# ----------------------------------------------------------------------- 닻

def report_anchor(
    session: OrmSession,
    card_id: str,
    verdict: str,
    *,
    reporter: str = "",
    detail: str = "",
    metric: str = "",
    baseline: float = 0.0,
    observed: float = 0.0,
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """적용 보고 — ✔ 현장 검증 배지의 유일한 출처.

    "안 맞았다" 는 숨기지 않는다. 카드를 ``contested`` 로 바꾸고 전문가 큐에 올린다.
    """
    if verdict not in ("helped", "missed", "pending"):
        raise ServiceError(t("err.bad_verdict", lang))
    row = session.get(db.CardRow, card_id)
    if row is None:
        raise ServiceError(t("err.no_card", lang))

    session.add(
        db.Anchor(
            card_id=card_id, reporter=reporter, verdict=verdict, detail=detail,
            metric=metric, baseline=baseline, observed=observed,
        )
    )
    if verdict == "helped":
        row.helped += 1
        _log(session, row.expert, legacy.LedgerEvent.HELPED,
             card_id=card_id, actor=reporter, detail=detail[:120])
    elif verdict == "missed":
        row.missed += 1
        _log(session, row.expert, legacy.LedgerEvent.MISSED,
             card_id=card_id, actor=reporter, detail=detail[:120])

    card = row_to_card(row)
    new_status = card.anchor_verdict(min_reports=settings.anchor_min_reports)
    if new_status is not card.status:
        row.status = new_status.value
        if new_status is CardStatus.ANCHORED:
            _log(session, row.expert, legacy.LedgerEvent.ANCHORED, card_id=card_id)
    session.commit()
    return {"card_id": card_id, "status": row.status, "helped": row.helped, "missed": row.missed}


def thank(
    session: OrmSession, expert: str, message: str, *, actor: str = "",
    lang: str = LANG_DEFAULT,
) -> dict:
    """후배가 남기는 감사 — 퇴직일 리포트에 그대로 실린다."""
    get_expert(session, expert, lang=lang)
    _log(session, expert, legacy.LedgerEvent.THANKS, actor=actor, detail=message[:300])
    session.commit()
    return {"ok": True}


# ------------------------------------------------------------------ 화면 조립

def card_view(card: Card) -> dict[str, Any]:
    return {
        "id": card.id,
        "expert": card.expert,
        "title": card.title,
        "domain": card.domain,
        "situation": card.situation,
        "cues": card.cues,
        "judgment": card.judgment,
        "action": card.action,
        "rationale": card.rationale,
        "exceptions": card.exceptions,
        "failure": card.failure,
        "unspeakable": card.unspeakable,
        "status": card.status.value,
        "tacitness": card.tacitness.value,
        "tacitness_emoji": card.tacitness.emoji,
        "visibility": card.visibility.value,
        "for_whom": card.for_whom,
        "risk": card.risk,
        "completeness": round(card.completeness, 2),
        "citable": card.citable(),
        "citations": card.citations,
        "helped": card.helped,
        "missed": card.missed,
    }


def expert_home(
    session: OrmSession, expert: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """전문가 홈. **순서가 곧 우선순위다** — 보람 → 공백 → 교정 → 지도 → 도구함."""
    row = get_expert(session, expert, lang=lang)
    cards = cards_of(session, expert)
    live = [c for c in cards if c.status is not CardStatus.DORMANT]
    gaps = open_gaps(session, expert)
    flags = {
        f.domain
        for f in session.scalars(select(db.Flag).where(db.Flag.expert == expert)).all()
    }

    entries = [
        legacy.Entry(
            event=legacy.LedgerEvent(r.event), expert=r.expert, card_id=r.card_id,
            actor=r.actor, detail=r.detail, at=r.created_at.replace(tzinfo=timezone.utc)
            if r.created_at.tzinfo is None else r.created_at,
        )
        for r in session.scalars(
            select(db.LedgerRow).where(db.LedgerRow.expert == expert)
            .order_by(db.LedgerRow.created_at.desc()).limit(40)
        ).all()
    ]
    askers = session.scalar(
        select(func.count(func.distinct(db.Ask.asker)))
        .where(db.Ask.expert == expert, db.Ask.asker != "")
    ) or 0
    # 한 답이 카드 여러 장을 인용할 수 있으므로 인용 횟수와 답한 횟수는 다르다.
    answers = session.scalar(
        select(func.count()).select_from(db.Ask)
        .where(db.Ask.expert == expert, db.Ask.answered.is_(True))
    ) or 0

    summary = legacy.summarize(
        expert,
        entries,
        cards_alive=len(live),
        cards_verified=sum(1 for c in live if c.status is CardStatus.ANCHORED),
        citations=sum(c.citations for c in live),
        answers=int(answers),
        askers=int(askers),
        helped=sum(c.helped for c in live),
        missed=sum(c.missed for c in live),
        gaps_open=len(gaps),
        hands_items=sum(1 for c in live if c.tacitness is Tacitness.HANDS),
    )
    risk = cov.succession_risk(expert, cards, days_left=days_left(row), flags=flags)
    suggestions = recommend(
        live, lang=lang, flags=flags, open_gaps=len(gaps),
        card_count=len(live), threshold=settings.unlock_after_cards,
    )

    return {
        "expert": {
            "id": row.id,
            "name": row.display_name or row.id,
            "alter_label": persona_of(row).label(lang),
            "alter_active": row.alter_active,
            "days_left": days_left(row),
        },
        "legacy": {
            "headline": t(
                summary.headline_key, lang,
                askers=summary.askers, cited=summary.answers,
                alive=summary.cards_alive,
            ),
            "cards_alive": summary.cards_alive,
            "cards_verified": summary.cards_verified,
            "citations": summary.citations,
            "answers": summary.answers,
            "askers": summary.askers,
            "helped": summary.helped,
            "missed": summary.missed,
            "help_rate": summary.help_rate,
            "hands_items": summary.hands_items,
            "recent": [
                {
                    "sentence": e.sentence(t(f"ledger.{e.event.value}", lang)),
                    "event": e.event.value,
                    "card_id": e.card_id,
                }
                for e in summary.recent
            ],
        },
        "gaps": [
            {
                "id": g.id, "question": g.question, "count": g.asked_count,
                "askers": _lines(g.askers),
            }
            for g in gaps[:5]
        ],
        "contested": [
            card_view(c) for c in live if c.status is CardStatus.CONTESTED
        ],
        "map": {
            "coverage": risk.coverage,
            "hands_ratio": risk.hands_ratio,
            "risk": risk.score,
            "level": t(
                {"심각": "risk.high", "중": "risk.mid", "저": "risk.low"}[risk.level],
                lang,
            ),
            "domains": [
                {
                    "domain": d.domain, "coverage": round(d.coverage, 2),
                    "cards": d.cards, "anchored": d.anchored, "hands": d.hands,
                    "flagged": d.flagged,
                }
                for d in risk.domains
            ],
        },
        # 오늘의 입구 질문 (ACTA 지식 감사). 화면은 이걸 그대로 띄운다.
        "entry_probe": dict(
            zip(("kind", "question"), interview.entry_probe(len(live), lang))
        ),
        "toolbox": [
            {"key": i.key, "emoji": i.emoji, "minutes": i.minutes, **i.localized(lang)}
            for i in unlocked(len(live), threshold=settings.unlock_after_cards)
        ],
        "locked": 0,          # 잠기는 연장은 없다 — 화면 하위호환용으로 남긴다
        "tool_total": len(unlocked(999)),
        "suggestions": [
            {
                "key": s.instrument.key, "emoji": s.instrument.emoji,
                "name": s.instrument.localized(lang)["name"],
                "because": s.because, "card_id": s.card_id,
            }
            for s in suggestions
        ],
        "cards": [card_view(c) for c in live],
    }


def flag_domain(
    session: OrmSession, expert: str, domain: str, note: str = "",
    *, lang: str = LANG_DEFAULT,
) -> dict:
    """🚩 전문가가 직접 깃발을 꽂는다. 기계 계산보다 이걸 먼저 본다."""
    get_expert(session, expert, lang=lang)
    session.add(db.Flag(expert=expert, domain=domain, note=note))
    session.commit()
    return {"ok": True, "domain": domain}


def admin_board(session: OrmSession, *, lang: str = LANG_DEFAULT) -> dict[str, Any]:
    """승계 리스크 보드. **정렬 순서가 곧 개입 순서다.**"""
    rows = session.scalars(select(db.Expert)).all()
    board = []
    for row in rows:
        cards = cards_of(session, row.id)
        flags = {
            f.domain
            for f in session.scalars(select(db.Flag).where(db.Flag.expert == row.id)).all()
        }
        risk = cov.succession_risk(row.id, cards, days_left=days_left(row), flags=flags)
        level_key = {"심각": "risk.high", "중": "risk.mid", "저": "risk.low"}[risk.level]
        board.append(
            {
                "expert": row.id,
                "name": row.display_name or row.id,
                "days_left": days_left(row),
                "coverage": risk.coverage,
                "hands_ratio": risk.hands_ratio,
                "risk": risk.score,
                "level": t(level_key, lang),
                "cards": len(cards),
                "gaps": len(open_gaps(session, row.id)),
                "weakest": risk.domains[0].domain if risk.domains else "",
            }
        )
    board.sort(key=lambda b: -b["risk"])
    return {"board": board}


def export_cards(session: OrmSession, expert: str) -> dict[str, Any]:
    """내보내기 — **회사가 아니라 본인이 저자다** (통제권, self-excavation §1).

    P→I→C 그래프도 함께 낸다. coral/H2A2H2 온톨로지에 그대로 부을 수 있다.
    """
    cards = cards_of(session, expert)
    return {
        "expert": expert,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "cards": [card_view(c) for c in cards],
        "pic_graph": [c.to_pic() for c in cards],
    }
