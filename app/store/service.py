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

from app.alter.persona import AlterReply, Persona, memoir_prose, respond
from app.capture import campaign, interview
from app.capture.instruments import LADDER, recommend, unlocked
from app.capture.llm import get_llm
from app.config import settings
from app.core import coverage as cov
from app.core import legacy
from app.core.card import Card, CardStatus, Tacitness, Visibility
from app.i18n import DEFAULT as LANG_DEFAULT
from app.i18n import t
from app.store import db, notify


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
        aliases=_lines(row.aliases),
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
    row.aliases = _join(card.aliases)
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


def _guard_demo(expert_id: str, lang: str = LANG_DEFAULT) -> None:
    """전시 전문가(featured)는 **읽기 전용**이다.

    데모에는 로그인이 없어 이름이 곧 신원이다 — 그대로 두면 심사자가 "나" 칸에
    yudon 을 치고 분신을 꺼 버릴 수 있다(전 심사자의 데모가 부서진다).
    전시 전문가로는 구경(서가·회고록·명세서)과 후배 행동(질문·보고·감사)만
    되고, 본인 행세(발굴·수정·정지·문서 투입)는 여기서 막는다.
    본인 몫 체험은 트랙 B — 자기 전문가를 만들면 전부 열린다.
    """
    if expert_id in settings.featured:
        raise ServiceError(t("err.demo_readonly", lang))


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

def peek_next_question(
    session: OrmSession, expert: str, *, skip: int = 0, lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """오늘의 질문 미리보기 — **세션을 만들지 않는다.**

    홈의 주인공은 "오늘의 질문" 하나다 (MVP 척추: 묻는 대로 답하면, 당신
    없이도 일하는 판단이 남는다). 선택 순서는 start_session 과 같은 가치관:
    후배/문서/혼잣말 공백 → 카드 없는 이관 업무 → 입구 프로브 순환.
    ``skip`` 으로 넘길 수 있다 — 넘긴다고 사라지지 않고 뒤로 밀릴 뿐이다.
    """
    row = get_expert(session, expert, lang=lang)
    lang = row.lang or lang
    queue: list[dict[str, str]] = []

    for gap in open_gaps(session, expert):
        src = ("doc" if _lines(gap.askers) == ["📄"]
               else "voice" if _lines(gap.askers) == ["🎙"]
            else "review" if _lines(gap.askers) == ["🗺"] else "junior")
        queue.append({"question": gap.question, "source": src, "gap_id": gap.id})

    live = [c for c in cards_of(session, expert) if c.status is not CardStatus.DORMANT]
    covered = {c.domain for c in live if c.domain}
    flags = session.scalars(
        select(db.Flag).where(db.Flag.expert == expert).order_by(db.Flag.created_at)
    ).all()

    # 캠페인 지휘 — 사람 지식공학자의 절차: 지도 없으면 지도부터,
    # 있으면 🔴(감이 필요) 단계의 빈 곳부터 (app/capture/campaign.py).
    move = campaign.next_move(
        open_gaps=0,   # 공백은 위에서 이미 큐 앞에 앉았다
        steps=[{"domain": f.domain, "difficulty": f.difficulty,
                "cards": sum(1 for c in live if c.domain == f.domain
                             and c.status is not CardStatus.DRAFT),
                "reviewed": f.reviewed_cards}
               for f in flags],
        total_cards=len(live),
    )
    if move.phase == "review":
        queue.append({
            "question": t("review.invite", lang, step=move.step),
            "source": "review", "gap_id": "", "step": move.step,
        })
    if move.phase == "map":
        queue.append({
            "question": interview.TASKMAP_OPENER.get(lang, interview.TASKMAP_OPENER["en"]),
            "source": "map", "gap_id": "",
        })
    ordered = sorted(
        (f for f in flags if f.domain not in covered),
        key=lambda f: {"hard": 0, "mid": 1, "easy": 2, "": 1}.get(f.difficulty, 1),
    )
    for f in ordered:
        queue.append({
            "question": interview.flag_probe(f.domain, len(live), lang),
            "source": "flag", "gap_id": "",
        })

    probes = [interview.entry_probe(len(live) + i, lang) for i in range(4)]
    for kind, q in probes:
        queue.append({"question": q, "source": "probe", "gap_id": ""})

    picked = queue[skip % len(queue)]
    return picked | {"queued": len(queue), "readonly": expert in settings.featured}


def start_session(
    session: OrmSession, expert: str, *, instrument: str = LADDER,
    gap_id: str = "", step: str = "", lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """발굴 세션 시작. **연장은 전문가가 고른다** — 기본값은 사다리.

    ``gap_id`` 를 주면 그 공백부터 판다 — 문서함에서 빈 질문 하나를 짚어
    "지금 답하기" 를 눌렀을 때의 입구다.
    """
    _guard_demo(expert, lang)
    expert_row = get_expert(session, expert, lang=lang)
    # 발굴은 **전문가의 언어**로 산다. 화면 문구는 보는 사람 언어를 따르지만,
    # 질문과 카드가 요청 언어를 따르면 — 한국 전문가가 영어 브라우저로 팠을 때
    # 카드가 en 으로 저장돼 한국 후배 검색에서 영영 빠진다.
    lang = expert_row.lang or lang
    row = db.Session(id=_uid("s"), expert=expert, instrument=instrument)
    session.add(row)

    if instrument == "review":
        # 영역 검증(member checking) — 결정적 되읽기 + 한 가지 질문.
        # 즉석 카드 편집은 하지 않는다(음성 중 오해 위험) — 수정은 서가로.
        live = [c for c in cards_of(session, expert)
                if c.status is not CardStatus.DORMANT
                and c.status is not CardStatus.DRAFT
                and (c.domain or "—") == step]
        if not live:
            raise ServiceError(t("err.no_card", lang))
        listing = "\n".join(
            f"{i+1}. {c.title} — {c.judgment[:60]}" for i, c in enumerate(live)
        )
        row.domain = step
        text_q = t("review.opener", lang, step=step, n=len(live), listing=listing)
        turn = db.Turn(id=_uid("t"), session_id=row.id, question=text_q,
                       rung="review", targets="")
        session.add(turn)
        session.commit()
        return {
            "session_id": row.id, "instrument": instrument,
            "turn_id": turn.id, "question": text_q, "rung": "review",
            "from_gap": False, "domain": step,
            "target": 1, "index": 1,
        }

    gap = None
    if gap_id:
        picked = session.get(db.Gap, gap_id)
        if picked is not None and not picked.filled_card:
            gap = picked
    if gap is None:
        gap = _top_gap(session, expert)

    if gap is None and instrument == LADDER and step:
        # 드릴다운 — 전문가가 지도에서 단계를 직접 짚었다. 캠페인의 추천
        # 순서보다 본인의 선택이 먼저다 (운전대는 전문가에게).
        live_n = sum(
            1 for c in cards_of(session, expert)
            if c.status is not CardStatus.DORMANT
        )
        text_q = interview.flag_probe(step, live_n, lang)
        row.domain = step
        turn = db.Turn(id=_uid("t"), session_id=row.id, question=text_q,
                       rung="opener", targets="situation")
        session.add(turn)
        session.commit()
        return {
            "session_id": row.id, "instrument": instrument,
            "turn_id": turn.id, "question": text_q, "rung": "opener",
            "from_gap": False, "domain": step,
            "target": settings.interview_turns, "index": 1,
        }

    if gap is None and instrument == LADDER:
        # ② 카드 없는 이관 업무 — 전문가가 "남겨야 한다" 고 적은 영역인데
        # 아직 한 장도 없는 곳부터. 깃발은 본인이 그린 발굴 지도다.
        live = [c for c in cards_of(session, expert)
                if c.status is not CardStatus.DORMANT]
        covered = {c.domain for c in live if c.domain}
        flags = [
            f.domain for f in session.scalars(
                select(db.Flag).where(db.Flag.expert == expert)
                .order_by(db.Flag.created_at)
            ).all()
        ]
        bare = next((d for d in flags if d not in covered), "")
        if bare:
            text_q = interview.flag_probe(bare, len(live), lang)
            row.domain = bare
            turn = db.Turn(id=_uid("t"), session_id=row.id, question=text_q,
                           rung="opener", targets="situation")
            session.add(turn)
            session.commit()
            return {
                "session_id": row.id, "instrument": instrument,
                "turn_id": turn.id, "question": text_q, "rung": "opener",
                "from_gap": False, "domain": bare,
                "target": settings.interview_turns, "index": 1,
            }

    if gap is None and instrument == LADDER:
        # 문 ①("그냥 물어봐 주세요")의 첫 질문은 ACTA 입구 프로브 순환이다 —
        # 같은 질문(recall)만 반복하면 같은 종류의 지식만 나온다 (§3.2).
        live = [c for c in cards_of(session, expert)
                if c.status is not CardStatus.DORMANT]
        kind, text_q = interview.entry_probe(len(live), lang)
        turn = db.Turn(id=_uid("t"), session_id=row.id, question=text_q,
                       rung="opener", targets="situation")
        session.add(turn)
        session.commit()
        return {
            "session_id": row.id, "instrument": instrument,
            "turn_id": turn.id, "question": text_q, "rung": "opener",
            "from_gap": False, "probe": kind,
            "target": settings.interview_turns, "index": 1,
        }
    question = interview.next_question(
        get_llm(),
        instrument=instrument,
        gap_question=gap.question if gap else "",
        gap_source=(
            "doc" if bool(gap) and _lines(gap.askers) == ["📄"]
            else "voice" if bool(gap) and _lines(gap.askers) == ["🎙"]
            else "review" if bool(gap) and _lines(gap.askers) == ["🗺"]
            else "junior"
        ),
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
    expert_row = session.get(db.Expert, sess.expert)
    if expert_row is not None and expert_row.lang:
        lang = expert_row.lang   # 발굴은 전문가의 언어로 산다

    if sess.instrument == "review":
        # "됐다" → 검토 봉인. 빠진 것을 불렀다 → 즉시 다음 발굴 주제(공백 큐).
        flag = session.scalar(
            select(db.Flag).where(db.Flag.expert == sess.expert,
                                  db.Flag.domain == sess.domain)
        )
        live_n = sum(
            1 for c in cards_of(session, sess.expert)
            if c.status is not CardStatus.DORMANT
            and c.status is not CardStatus.DRAFT
            and (c.domain or "—") == sess.domain
        )
        # 완료 판정 — **짧은 답만** 완료다. "빠진 게 없다"(완료)와
        # "겨울철 얘기가 없네"(빠진 것!)가 같은 '없' 을 쓴다. 긴 문장은
        # 내용이지 승인이 아니다.
        done_words = ("됐", "없", "다 있", "충분", "맞아", "괜찮",
                      "done", "that's all", "nothing", "all there", "good", "fine")
        said = turn.answer.strip().lower()
        is_done = (turn.skipped
                   or (len(said) <= 14 and any(w in said for w in done_words)))
        sess.closed = True
        if flag is not None:
            flag.reviewed_cards = live_n
        if is_done:
            session.commit()
            return {
                "review_done": True, "question": t("review.sealed", lang, step=sess.domain),
                "reflection": "", "rung": "review", "targets": "", "turn_id": "",
                "card": None, "report": {"slots": []},
                "index": 1, "target": 1, "wrap_up": True, "fallback": False,
            }
        gap_q = (f"{turn.answer.strip()} ('{sess.domain}' 검토에서 짚으심)"
                 if lang == "ko" else
                 f"{turn.answer.strip()} (raised in the '{sess.domain}' review)")
        _record_gap(session, sess.expert, gap_q, asker="🗺")
        session.commit()
        return {
            "review_done": True,
            "question": t("review.queued", lang, what=turn.answer.strip()[:50]),
            "reflection": "", "rung": "review", "targets": "", "turn_id": "",
            "card": None, "report": {"slots": []},
            "index": 1, "target": 1, "wrap_up": True, "fallback": False,
        }

    if sess.instrument == "taskmap":
        # Phase 0 — 과업 지도. 카드를 만들지 않는다: 산출물은 단계 목록이고,
        # 그 목록이 이후 모든 발굴의 지도가 된다 (ACTA Task Diagram).
        steps = interview.extract_task_map(get_llm(), turn.answer, lang=lang)
        existing = {
            f.domain for f in session.scalars(
                select(db.Flag).where(db.Flag.expert == sess.expert)
            ).all()
        }
        for st in steps:
            if st["name"] not in existing:
                session.add(db.Flag(expert=sess.expert, domain=st["name"],
                                    difficulty=st["difficulty"], origin="taskmap"))
        sess.closed = True
        session.commit()
        summary = " / ".join(
            f"{'🔴' if st['difficulty']=='hard' else '🟡' if st['difficulty']=='mid' else '🟢'}"
            f"{st['name']}" for st in steps
        )
        return {
            "map_built": True, "steps": steps,
            "question": t("map.done", lang, summary=summary,
                          hard=sum(1 for x in steps if x["difficulty"] == "hard")),
            "reflection": "", "rung": "map", "targets": "",
            "turn_id": "", "card": None, "report": {"slots": []},
            "index": 1, "target": 1, "wrap_up": True, "fallback": False,
        }

    history = _history(session, sess.id)
    last_slot = turn.targets or interview.RUNG_SLOT.get(turn.rung, "")

    # 두 LLM 호출(카드 재추출 · 다음 질문)은 서로 독립이다 — 하나는 DB 를
    # 쓰고 하나는 순수하게 텍스트만 만든다. 직렬로 두면 한 턴이 두 왕복을
    # 기다린다(부하 실측 p50 8.4s). 다음 질문 생성은 세션을 건드리지 않으므로
    # 스레드로 띄우고, 카드 재추출은 이 스레드에서 DB 를 쓴다. 타겟 슬롯은
    # LLM 카드가 아니라 **결정적 슬롯 이력**으로 정하므로 카드 추출을 기다릴
    # 필요가 없다 (트리거 로직이 이미 last_slot 을 그렇게 쓴다).
    target_card = interview._fallback(
        history, _slot_history(session, sess.id)
    ).to_card(id="_probe", expert=sess.expert,
              instrument=sess.instrument, source_turn=sess.id)

    # **사용자는 다음 질문만 기다리면 된다.** 카드 재추출(스키마 강제 extract)은
    # 5초가 아니라 ~14초가 드는데(부하 실측), 이건 오른쪽 패널 갱신용일 뿐
    # 다음 질문 생성에 필요 없다. 그래서:
    #  · 다음 질문 = 결정적 슬롯 이력으로 타겟을 정하고 LLM 으로 한 문장 (~5s)
    #  · 카드 = 규칙 기반으로 즉시 채워 응답에 싣고, LLM 정련은 **다음 턴에**
    #    반영한다 (interview.capture 는 승인 직전 마지막 턴에서 완성).
    # 체감 지연이 ~14s→~5s 로 떨어진다. 카드의 최종 품질은 승인 시점에
    # confirm_card 로 전문가가 확정하므로 손상되지 않는다.
    card_row = _upsert_card(
        session, sess, history, lang=lang,
        refine=(answered_now := sum(1 for _, a in history if a)) >= settings.interview_turns - 1,
    )
    card = row_to_card(card_row)
    question = interview.next_question(
        get_llm(), instrument=sess.instrument, card=target_card,
        history=history, last_rung=turn.rung, last_slot=last_slot, lang=lang,
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
        "targets": question.targets,
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
    *, lang: str = LANG_DEFAULT, refine: bool = True,
) -> db.CardRow:
    """대화가 쌓일 때마다 카드를 다시 뽑는다. 초안은 계속 덮어써도 안전하다 —
    승인 후에는 덮어쓰지 않는다 (전문가가 고친 것이 기계 추출보다 우선)."""
    slots = _slot_history(session, sess.id)
    if refine:
        # LLM 정련 — 느리다(~14s). 마지막 턴(승인 직전)에만.
        draft = interview.capture(get_llm(), history, lang=lang, slots=slots)
    else:
        # 규칙 기반 즉시 — 답을 그 답을 끌어낸 칸에 넣는다. 패널이 바로 찬다.
        draft = interview._fallback(history, slots)
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
    if not card.domain and sess.domain:
        card.domain = sess.domain   # 깃발에서 시작한 세션 — 영역을 물려받는다
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
    _guard_demo(row.expert, lang)
    card = row_to_card(row)

    #: 판단의 실체가 담긴 칸. 이 칸이 바뀌면 **다른 판단**이 된 것이다.
    substance = (
        "title", "situation", "cues", "judgment", "action",
        "rationale", "exceptions", "failure",
    )
    before = {k: getattr(card, k) for k in substance}

    for key, value in (edits or {}).items():
        if not hasattr(card, key):
            continue
        current = getattr(card, key)
        setattr(card, key, list(value) if isinstance(current, list) else value)

    substantive = any(getattr(card, k) != before[k] for k in substance)
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

    # 판 내용이 바뀌면 실측은 처음부터 다시 센다. 옛 텍스트에 대한 적용 보고로
    # 새 텍스트가 ✔ 을 다는 것은 거짓 배지다. 기존 보고는 stale 로 빠지고
    # (원장은 append-only 라 보람·명세서의 역사는 그대로), 배지는 새 보고가
    # 다시 쌓여야 돌아온다.
    verification_reset = False
    had_reports = card.helped + card.missed > 0
    if substantive and had_reports:
        # 교정 회신 — "안 맞았다" 고 보고했던 후배들에게, 그 보고로 카드가
        # 고쳐졌음을 알린다. 보고가 허공에 가면 다음 보고는 없다.
        if card.missed:
            reporters = sorted({
                a.reporter for a in session.scalars(
                    select(db.Anchor).where(
                        db.Anchor.card_id == card.id,
                        db.Anchor.verdict == "missed",
                        db.Anchor.stale.is_(False),
                    )
                ).all() if a.reporter
            })
            expert_row2 = session.get(db.Expert, card.expert)
            notify.card_fixed(
                expert=card.expert,
                expert_name=(expert_row2.display_name or card.expert)
                            if expert_row2 else card.expert,
                card_title=card.title, reporters=reporters,
            )
        session.query(db.Anchor).filter(
            db.Anchor.card_id == card.id, db.Anchor.stale.is_(False)
        ).update({"stale": True})
        card.helped = 0
        card.missed = 0
        row.helped = 0
        row.missed = 0
        verification_reset = True

    card.status = CardStatus.CONFIRMED
    # 검색어 별칭 — 승인 순간이 "후배가 뭐라고 물을까" 를 뽑기 가장 좋은
    # 때다(내용 확정). 실질 수정 시에도 재생성. 실패는 무해(빈 목록).
    if substantive or not card.aliases:
        expert_row3 = session.get(db.Expert, card.expert)
        card.aliases = interview.search_aliases(
            get_llm(), title=card.title, situation=card.situation,
            cues=card.cues,
            lang=(expert_row3.lang if expert_row3 and expert_row3.lang else lang),
        )
    write_card(row, card)
    _log(session, card.expert, legacy.LedgerEvent.CARD_CONFIRMED, card_id=card.id)

    # 이 카드가 후배의 공백을 메웠는가 — 메웠으면 질문자에게 알릴 대상이 된다.
    filled = _match_gap(session, card)
    session.commit()
    return {
        "card": card_view(card),
        "warning": t("warn.no_exceptions", lang) if not card.exceptions else "",
        "filled_gap": filled,
        "verification_reset": verification_reset,
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
        # **접근 공백 ≠ 지식 공백.** 지목·봉인으로 잠긴 카드가 이 질문에
        # 답할 수 있는데 보는 사람이 자격이 없어 공백이 된 경우 —
        # ① 전문가에게 "다시 파라" 고 시키면 안 된다 (이미 답을 남겼고,
        #    일부러 잠갔다), ② 후배에게 "남기지 않은 영역" 이라고 하면
        #    거짓말이다. 소유자 시점(모든 카드가 보임)으로 한 번 더 검색해
        #    가려낸다 — 결정적 검색이라 LLM 호출 없음.
        from app.core.retrieval import retrieve as _retrieve

        owner_view = _retrieve(
            cards, question, viewer=expert,
            top_k=settings.retrieval_top_k, explore_quota=0.0,
            confidence_floor=settings.confidence_floor,
        ) if persona.active else None   # 정지된 분신의 안내문은 덮지 않는다
        if owner_view is not None and not owner_view.is_gap:
            reply.text = t("alter.msg.restricted", lang,
                           name=persona.display_name or expert)
            ask.answered = False
            session.commit()
            return {"ask_id": ask.id, "persona": persona.label(lang),
                    **reply.as_dict(), "restricted": True}
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


def followup(
    session: OrmSession, expert: str, asker: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """재방문 고리 — "지난번 그 판단, 써보셨어요?"

    바퀴에서 가장 약한 화살표가 적용 보고다: 답을 받아 현장에 간 후배가
    돌아와 눌러줄 계기가 없었다. 같은 후배가 다시 온 순간이 그 계기다 —
    지난번에 인용받았는데 아직 보고하지 않은 카드 하나를 되물어본다.
    ✔ 배지도, 교정 신호도, 명세서도 전부 이 화살표에서 태어난다.
    """
    if not asker:
        return {"card": None}
    cited = session.scalars(
        select(db.LedgerRow).where(
            db.LedgerRow.expert == expert,
            db.LedgerRow.event == legacy.LedgerEvent.CITED.value,
            db.LedgerRow.actor == asker,
        ).order_by(db.LedgerRow.created_at.desc()).limit(10)
    ).all()
    reported = {
        a.card_id for a in session.scalars(
            select(db.Anchor).where(db.Anchor.reporter == asker)
        ).all()
    }
    for entry in cited:
        if entry.card_id and entry.card_id not in reported:
            row = session.get(db.CardRow, entry.card_id)
            if row is None or row.status == CardStatus.DORMANT.value:
                continue
            return {"card": {
                "id": row.id, "title": row.title,
                "asked": entry.detail,      # 그때 무엇을 물었었는지
                "at": entry.created_at.date().isoformat() if entry.created_at else "",
            }}
    return {"card": None}


def route_question(
    session: OrmSession, question: str, *, asker: str = "",
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """통합 질문창 — 답하지 않고 **누가 판단을 남겼는지 연결만** 한다.

    후배가 선배를 골라 들어가는 대신, 질문부터 던진다: "이 문제는 도장은
    유돈, 폐수는 Dale 의 판단이 있습니다." 전 전문가의 카드에 같은 결정적
    검색을 돌린다 — LLM 호출 없음, 즉답, 원장·공백 기록 없음(미리보기와
    같은 원칙: 실제로 그 분신에게 물을 때만 흔적이 남는다).

    여러 선배의 답을 **합성하지 않는다** — 분신은 한 사람의 카드만 근거로
    자기 목소리로 말한다는 불변식이 이 서비스의 경계다. 여기서는 문만
    가리키고, 답은 각 분신의 방에서 듣는다.
    """
    from app.core.retrieval import retrieve

    question = (question or "").strip()
    if not question:
        return {"experts": []}
    featured = settings.featured
    found: list[dict[str, Any]] = []
    for r in session.scalars(select(db.Expert)).all():
        if not r.alter_active:
            continue
        if featured and r.id not in featured:
            continue   # 공개 명부와 같은 안전핀 — 손님 계정은 포털에 안 선다
        cards = cards_of(session, r.id)
        got = retrieve(
            cards, question, viewer=asker, top_k=3, explore_quota=0.0,
            confidence_floor=settings.confidence_floor,
        )
        if got.is_gap:
            continue
        persona = persona_of(r)
        # 사람 추천과 카드 나열은 기준이 다르다 — 사람은 최고 히트가 정하고,
        # 곁다리 카드(1등 점수의 절반 미만)는 목록에서 뺀다. "관련 카드" 에
        # 약한 카드가 섞이면 추천 전체가 못 미더워진다 (QA 실측).
        top = max(h.score for h in got.hits)
        strong = [h for h in got.hits if h.score >= top * 0.5]
        found.append({
            "expert": r.id,
            "alter": persona.label(lang),
            "lang": r.lang,
            "confidence": round(got.confidence, 2),
            # 제목만 보인다 — retrieve 가 이미 보는 사람의 자격(visible_to,
            # citable)으로 거른 카드들이라 잠긴 판단이 새지 않는다.
            "hits": [{"id": h.card.id, "title": h.card.title,
                      "domain": h.card.domain} for h in strong],
        })
    found.sort(key=lambda e: -e["confidence"])
    return {"experts": found}


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


def mark_unanswered(
    session: OrmSession, expert: str, question: str, *,
    asker: str = "", lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """후배가 "이건 답이 아니었어요" 를 눌렀다 — 공백으로 되돌린다.

    확신도 문턱은 약한 칸 겹침(근거·상황의 토큰)으로도 넘을 수 있고, 그때
    분신은 말로는 "남기지 않으셨습니다" 라면서 시스템상으로는 답변·인용으로
    집계된다 — 질문은 전문가에게 영영 닿지 않는다. 모델의 말투를 파싱해서
    고치는 것은 판정을 모델에 위임하는 것이라 하지 않는다. **판정은 사람이
    한다**: 답을 받은 후배가 가장 정확한 판정자다.
    (검색 정밀도 자체는 P1 하이브리드 — docs/roadmap.md)
    """
    get_expert(session, expert, lang=lang)
    _record_gap(session, expert, question, asker=asker)
    session.commit()
    return {"queued": True}


def _record_gap(
    session: OrmSession, expert: str, question: str, asker: str,
    source_doc: str = "",
) -> None:
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
        db.Gap(id=_uid("g"), expert=expert, question=question,
               askers=asker or "", source_doc=source_doc)
    )
    # 새 공백만 알린다 — 반복 질문(위 return 경로)은 쏘지 않는다.
    row = session.get(db.Expert, expert)
    notify.gap_opened(
        expert=expert,
        expert_name=(row.display_name or expert) if row else expert,
        question=question, asker=asker,
        days_left=days_left(row) if row else None,
        source=("doc" if asker == "📄" else "voice" if asker == "🎙" else "junior"),
    )


def interrogate_document(
    session: OrmSession, expert: str, text: str, *,
    title: str = "", domain: str = "", lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """📄 절차서 빨간펜 — 문서가 다루지 않는 판단 지점을 **공백 큐**에 넣는다.

    문서는 저장되지만 **보관함이 아니라 발굴 지도**로다: 문서함의 정리 축은
    내용이 아니라 "이 문서가 말하지 않는 질문 N개 중 M개가 채워졌다" 는
    진행도다. 후배에게는 절대 노출되지 않는다 — 후배에게 남는 것은 카드뿐이고,
    답이 나와야 카드가 된다. 문서는 질문이 되지, 카드가 되지 않는다.
    """
    _guard_demo(expert, lang)
    get_expert(session, expert, lang=lang)
    first_line = next((l.strip() for l in (text or "").splitlines() if l.strip()), "")
    doc = db.Document(
        id=_uid("d"), expert=expert, title=(title or first_line)[:200],
        domain=domain, text=(text or "")[:200_000],
    )
    session.add(doc)
    probes = interview.probe_document(
        get_llm(), text, domain=domain, lang=lang
    )
    for item in probes:
        question = item["question"]
        if item.get("anchor"):
            # 어느 구절에서 나온 질문인지 붙인다 — 전문가가 맥락을 바로 잡는다.
            if lang == "ko":
                question = f'{question} (문서: "{item["anchor"]}")'
            else:
                question = f'{question} (doc: "{item["anchor"]}")'
        _record_gap(session, expert, question, asker="📄", source_doc=doc.id)
    session.commit()
    return {"expert": expert, "doc_id": doc.id, "title": doc.title,
            "questions": probes, "queued": len(probes)}


def my_documents(
    session: OrmSession, expert: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """문서함 — 문서마다 "판단 지점 N · 채움 M" 진행도가 붙는다."""
    get_expert(session, expert, lang=lang)
    docs = session.scalars(
        select(db.Document).where(db.Document.expert == expert)
        .order_by(db.Document.created_at.desc())
    ).all()
    out = []
    for d in docs:
        gaps = session.scalars(
            select(db.Gap).where(db.Gap.source_doc == d.id)
        ).all()
        filled = sum(1 for g in gaps if g.filled_card)
        out.append({
            "id": d.id, "title": d.title, "domain": d.domain,
            "questions": len(gaps), "filled": filled,
            "open": len(gaps) - filled,
            "added": d.created_at.date().isoformat() if d.created_at else "",
        })
    return {"expert": expert, "documents": out}


def document_detail(
    session: OrmSession, doc_id: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """문서 하나의 지도 — 질문들과 각각의 채움 상태. 빈 질문은 인터뷰 입구다."""
    doc = session.get(db.Document, doc_id)
    if doc is None:
        raise ServiceError(t("err.no_card", lang))
    gaps = session.scalars(
        select(db.Gap).where(db.Gap.source_doc == doc_id)
        .order_by(db.Gap.created_at)
    ).all()
    items = []
    for g in gaps:
        card_title = ""
        if g.filled_card:
            card = session.get(db.CardRow, g.filled_card)
            card_title = card.title if card else ""
        items.append({
            "gap_id": g.id, "question": g.question,
            "filled_card": g.filled_card, "card_title": card_title,
        })
    return {
        "id": doc.id, "title": doc.title, "domain": doc.domain,
        "text": doc.text, "questions": items,
        "filled": sum(1 for i in items if i["filled_card"]),
    }


def mine_monologue(
    session: OrmSession, expert: str, text: str, *,
    domain: str = "", lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """🎙 혼잣말 채굴 — 전사에서 건진 판단의 흔적을 **공백 큐**에 넣는다.

    문서 심문과 같은 길이다: 재료는 질문이 되고, 카드는 전문가의 확인된
    답에서만 나온다. 전사 원문은 저장하지 않는다 — 남는 것은 질문뿐이다.
    """
    _guard_demo(expert, lang)
    get_expert(session, expert, lang=lang)
    probes = interview.probe_monologue(get_llm(), text, domain=domain, lang=lang)
    for item in probes:
        question = item["question"]
        if item.get("anchor"):
            question = (f'{question} (혼잣말: "{item["anchor"]}")' if lang == "ko"
                        else f'{question} (you said: "{item["anchor"]}")')
        _record_gap(session, expert, question, asker="🎙")
    session.commit()
    return {"expert": expert, "questions": probes, "queued": len(probes)}


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

def my_cards(
    session: OrmSession, expert: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """내 카드 목록 — 전문가의 **정리** 화면.

    꺼내는 흐름만 있고 돌아볼 흐름이 없으면 전문가는 쓰기 전용 사용자가 된다.
    손 가야 할 것(교정 요청·파다 만 초안)이 위로 온다.
    """
    get_expert(session, expert, lang=lang)
    rows = session.scalars(
        select(db.CardRow).where(db.CardRow.expert == expert)
        .order_by(db.CardRow.created_at.desc())
    ).all()

    def _bucket(row: db.CardRow) -> int:
        if row.status == CardStatus.CONTESTED.value:
            return 0          # 후배가 "안 맞았다" — 가장 먼저
        if row.status == CardStatus.DRAFT.value:
            return 1          # 파다 만 것
        return 2

    cards = [
        {
            "id": r.id, "title": r.title or t("card.untitled", lang),
            "domain": r.domain, "status": r.status,
            "tacitness_emoji": Tacitness(r.tacitness).emoji,
            "visibility": r.visibility,
            "helped": r.helped, "missed": r.missed,
            "draft": r.status == CardStatus.DRAFT.value,
            "contested": r.status == CardStatus.CONTESTED.value,
            "anchored": r.status == CardStatus.ANCHORED.value,
        }
        for r in sorted(rows, key=_bucket)
    ]
    return {"expert": expert, "cards": cards,
            "attention": sum(1 for c in cards if c["draft"] or c["contested"])}


def card_detail(
    session: OrmSession, card_id: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """카드 상세 — 수정 화면의 재료 세 가지를 함께 준다.

    ① 카드 현재 값, ② **후배의 보고 원문** (교정하려면 무엇이 안 맞았는지
    알아야 한다), ③ **원본 발화** (카드는 해석이고 원본은 보존된다 — 그
    원칙을 고치는 자리에서 눈으로 보게 한다).
    """
    row = session.get(db.CardRow, card_id)
    if row is None:
        raise ServiceError(t("err.no_card", lang))

    reports = [
        {
            "verdict": a.verdict, "reporter": a.reporter, "detail": a.detail,
            "stale": a.stale,
            "at": a.created_at.date().isoformat() if a.created_at else "",
        }
        for a in session.scalars(
            select(db.Anchor).where(db.Anchor.card_id == card_id)
            .order_by(db.Anchor.created_at.desc())
        ).all()
    ]

    utterances = []
    if row.source_turn:
        utterances = [
            {"question": turn.question, "answer": turn.answer}
            for turn in session.scalars(
                select(db.Turn).where(db.Turn.session_id == row.source_turn)
                .order_by(db.Turn.created_at)
            ).all()
            if turn.answer and not turn.skipped
        ]

    return {"card": card_view(row_to_card(row)), "reports": reports,
            "utterances": utterances}


def resume_session(
    session: OrmSession, card_id: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """파다 만 초안을 **인터뷰로** 이어간다.

    세션 도중 나간 전문가의 15분이 미아가 되지 않게 한다. 마지막으로 답하지
    않은 질문이 그대로 다시 나온다 — 원본 발화가 보존돼 있어서 가능한 일이다.
    """
    row = session.get(db.CardRow, card_id)
    if row is None or not row.source_turn:
        raise ServiceError(t("err.no_card", lang))
    _guard_demo(row.expert, lang)
    sess = session.get(db.Session, row.source_turn)
    if sess is None:
        raise ServiceError(t("err.no_session", lang))

    open_turn = session.scalars(
        select(db.Turn).where(db.Turn.session_id == sess.id, db.Turn.answer == "")
        .order_by(db.Turn.created_at.desc())
    ).first()
    if open_turn is None:
        # 열린 질문이 없으면 하나 만든다 — 카드의 빈 칸이 다음 질문을 정한다.
        card = row_to_card(row)
        history = _history(session, sess.id)
        question = interview.next_question(
            get_llm(), instrument=sess.instrument, card=card,
            history=history, lang=lang,
        )
        open_turn = db.Turn(
            id=_uid("t"), session_id=sess.id, question=question.text,
            rung=question.rung, targets=question.targets,
        )
        session.add(open_turn)
        session.commit()

    card = row_to_card(row)
    history = _history(session, sess.id)
    answered = sum(1 for _, a in history if a)
    return {
        "history": [{"question": q, "answer": a} for q, a in history],
        "session_id": sess.id,
        "instrument": sess.instrument,
        "turn_id": open_turn.id,
        "question": open_turn.question,
        "rung": open_turn.rung,
        "targets": open_turn.targets,
        "from_gap": False,
        "card": card_view(card),
        "report": interview.slot_report(card, lang),
        "target": settings.interview_turns,
        "index": answered + 1,
    }


def alter_preview(
    session: OrmSession, card_id: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """방금 남긴 카드로 분신이 답하는 것을 **본인에게** 보여준다.

    "아, 이게 남는 거구나" 가 일어나는 자리다 — 전문가는 뭘 물을지 고민할
    필요 없이, 시스템이 후배처럼 묻고 분신이 답하는 장면을 본다.

    **원장에 기록하지 않는다.** 본인 확인용 시연이 인용·질문 수에 잡히면
    보람의 회계도, 사용 명세서도 거짓이 된다 — ask_alter 를 쓰지 않고 응답
    엔진만 직접 부르는 이유다.
    """
    row = session.get(db.CardRow, card_id)
    if row is None:
        raise ServiceError(t("err.no_card", lang))
    expert_row = get_expert(session, row.expert, lang=lang)

    # 시연 질문은 제목이 아니라 **신호**에서 만든다. 후배는 "이런 게
    # 보이는데" 로 묻고, 검색도 신호 칸 가중이 최고다. (제목은 일찍 승인한
    # 카드에선 정련 전 원문 문장이라 검색이 빗나간다 — 스팟 워크 실측.)
    card0 = row_to_card(row)
    seed = card0.cues[0] if card0.cues else row.title
    # 검색에는 신호 원문만 — 붙임말("이럴 땐 어떻게 하죠")의 토큰이 분모를
    # 키워 겹침 점수를 죽인다. 화면 표시용 문장은 따로 꾸민다.
    shown = (
        f"{seed} — 이럴 땐 어떻게 하죠?" if lang == "ko"
        else f"{seed} — what do I do?"
    )
    reply = respond(
        get_llm(),
        persona_of(expert_row, card_count=_confirmed_count(session, row.expert)),
        cards_of(session, row.expert),
        seed,
        viewer=row.expert,          # 본인 — 봉인·지목 카드도 본인은 본다
        top_k=settings.retrieval_top_k,
        explore_quota=0.0,          # 시연에 탐색 쿼터는 무의미하다
        confidence_floor=settings.confidence_floor,
        days_left=days_left(expert_row),
        lang=lang,
    )
    return {"question": shown, "reply": reply.as_dict()}


def memoir(
    session: OrmSession, expert: str, *, viewer: str = "",
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """판단 회고록 — **자서전은 입력이 아니라 출력이다.**

    "40년을 정리해 주십시오" 라고 하면 도망간다. 판단을 파다 보면 회고록이
    조판되어 나온다 — 그리고 보통 자서전과 달리, 각 장에 "내 판단이 내가
    떠난 뒤에도 쓰였다" 는 증거(후배의 보고)가 여백 주석으로 붙는다.

    재료는 전부 이미 있다: 카드(상황·판단·실패담), 남기는 말(서문),
    적용 보고 원문(여백 주석), 말로 담지 못한 것(부록 — 감추지 않는다),
    원장 합계(에필로그). 퇴직식에서 인쇄본을 증정하는 그림까지가 이 함수다.
    """
    row = get_expert(session, expert, lang=lang)
    lang = row.lang or lang        # 회고록은 그 사람의 언어로 산다

    owner = bool(viewer) and viewer == expert
    # 통제권은 회고록에서도 산다 — 봉인·비공개·지목 카드는 본인 판에만
    # 실린다. URL 은 누구나 열 수 있으므로(데모 신원은 soft, SSO 는 P1)
    # 남의 판은 공개 카드로만 제본된다.
    cards = [
        c for c in cards_of(session, expert)
        if c.status is not CardStatus.DORMANT and c.status is not CardStatus.DRAFT
        and (owner or c.visible_to(viewer))
    ]
    # 영역별 장(章) — 같은 영역의 판단이 한 장으로 묶인다.
    chapters: dict[str, list[dict[str, Any]]] = {}
    for c in sorted(cards, key=lambda x: x.domain):
        notes = [
            {"who": a.reporter, "what": a.detail, "verdict": a.verdict,
             "at": a.created_at.date().isoformat() if a.created_at else ""}
            for a in session.scalars(
                select(db.Anchor).where(
                    db.Anchor.card_id == c.id, db.Anchor.detail != ""
                ).order_by(db.Anchor.created_at)
            ).all()
        ]
        chapters.setdefault(c.domain or "—", []).append(
            {"card": card_view(c), "notes": notes}
        )

    hands = [
        {"title": c.title, "items": c.unspeakable}
        for c in cards if c.unspeakable
    ]

    stmt = usage_statement(session, expert, lang=lang)
    # 장 서두의 1인칭 서술 — **여기서 생성하지 않는다.** 두 가지 이유:
    # ① 장마다 LLM 을 돌리면 첫 화면이 20초 백지가 된다 (QA 실측) —
    #    껍데기는 즉시 뜨고 서술은 화면이 비동기로 청한다.
    # ② 본인이 승인한 서술만 확정이다 — 승인분은 DB 에서 그대로 나오고,
    #    초안은 화면에서 '승인 전' 배지를 달고 온다.
    saved = {
        m.domain: m for m in session.scalars(
            select(db.MemoirChapter).where(db.MemoirChapter.expert == expert)
        ).all()
    }

    return {
        "expert": expert,
        "name": row.display_name or expert,
        "lang": lang,
        "farewell": row.farewell,
        "leaving_on": row.leaving_on.isoformat() if row.leaving_on else "",
        # 남의 판에는 **본인이 승인한 서술만** 실린다 — 초안(기계의 문장)이
        # 그 사람 소개로 나가는 일은 없다. 본인 판에서만 초안을 만들고 다듬는다.
        "chapters": [
            {
                "domain": d, "entries": entries,
                "prose": (saved[d].prose if d in saved and
                          (owner or saved[d].approved_at) else ""),
                "approved": bool(d in saved and saved[d].approved_at),
            }
            for d, entries in chapters.items()
        ],
        "llm": settings.llm_enabled and owner,
        "owner": owner,
        "hands": hands,          # 글로 담지 못한 것 — 부록으로, 감추지 않는다
        "totals": stmt["totals"],
        "date": date.today().isoformat(),
    }


def memoir_draft(
    session: OrmSession, expert: str, domain: str, *, viewer: str = "",
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """장 서두 서술의 초안 — 생성하고 **승인 없이** 저장한다(캐시).

    자책 검열(persona._honest_prose)을 통과한 문장만 온다. 이미 저장된
    초안·승인분이 있으면 재생성하지 않는다 — "다시 엮기" 는 refresh 로.
    """
    row = get_expert(session, expert, lang=lang)
    lang = row.lang or lang
    existing = session.scalar(
        select(db.MemoirChapter).where(
            db.MemoirChapter.expert == expert, db.MemoirChapter.domain == domain
        )
    )
    if existing and existing.prose:
        return {"prose": existing.prose,
                "approved": bool(existing.approved_at)}
    if not settings.llm_enabled:
        return {"prose": "", "approved": False}   # stub 은 지어내지 않는다
    owner = bool(viewer) and viewer == expert
    cards = [
        c for c in cards_of(session, expert)
        if (c.domain or "—") == domain
        and c.status not in (CardStatus.DORMANT, CardStatus.DRAFT)
        and (owner or c.visible_to(viewer))   # 잠긴 카드가 서술로 새지 않게
    ]
    text = memoir_prose(
        get_llm(), name=row.display_name or expert, sayings=_lines(row.sayings),
        domain=domain, cards=cards, lang=lang,
    )
    if text:
        if existing is None:
            existing = db.MemoirChapter(expert=expert, domain=domain)
            session.add(existing)
        existing.prose = text
        session.commit()
    return {"prose": text, "approved": False}


def memoir_approve(
    session: OrmSession, expert: str, domain: str, prose: str, *,
    lang: str = LANG_DEFAULT,
) -> dict[str, Any]:
    """본인이 고친 서술을 확정한다 — **이 승인이 있어야 기록이다.**

    저장되는 것은 기계의 초안이 아니라 본인이 다듬은 문장이다. 빈 문장으로
    승인하면 그 장은 서술 없이 카드만 남는다 — 그것도 본인의 선택이다.
    """
    get_expert(session, expert, lang=lang)
    _guard_demo(expert, lang)
    row = session.scalar(
        select(db.MemoirChapter).where(
            db.MemoirChapter.expert == expert, db.MemoirChapter.domain == domain
        )
    )
    if row is None:
        row = db.MemoirChapter(expert=expert, domain=domain)
        session.add(row)
    row.prose = prose.strip()
    row.approved_at = datetime.now(timezone.utc)
    session.commit()
    return {"approved": True, "domain": domain}


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


def usage_statement(
    session: OrmSession, expert: str, *, lang: str = LANG_DEFAULT
) -> dict[str, Any]:
    """내 지식 사용 명세서 — **전문가가 회사에 청구하는** 정산 근거.

    방향이 규약이다: 회사가 전문가를 조회하는 화면이 아니라, 전문가 본인이
    자기 화면에서 뽑아 인사팀에 내미는 문서다. 그래야 "원장은 성과 지표로
    쓰지 않는다"(roadmap 거버넌스 2항)와 충돌하지 않는다 — 평가는 회사가
    사람을 보는 것이고, 명세서는 사람이 남긴 것의 값을 받는 것이다.

    세는 것은 원장이 세는 것뿐이다: 인용·도움됨·현장 검증. 조회수·좋아요
    같은 대리변수가 없어서 이 숫자를 그대로 정산 근거로 쓸 수 있다.
    **단가와 지급은 여기 없다** — 그건 코드가 아니라 인사 정책이다
    (roadmap 거버넌스 6항). "안 맞았다" 도 숨기지 않고 함께 적는다:
    청구서가 정직해야 단가 협상이 산다.
    """
    row = get_expert(session, expert, lang=lang)
    entries = session.scalars(
        select(db.LedgerRow).where(db.LedgerRow.expert == expert)
        .order_by(db.LedgerRow.created_at)
    ).all()

    billable = {"cited", "helped", "anchored"}
    by_card: dict[str, dict[str, Any]] = {}
    totals = {"cited": 0, "helped": 0, "anchored": 0, "missed": 0}
    for e in entries:
        if e.event not in billable and e.event != "missed":
            continue
        totals[e.event] += 1
        card = by_card.setdefault(e.card_id or "-", {
            "card_id": e.card_id, "title": "",
            "cited": 0, "helped": 0, "anchored": 0, "missed": 0, "items": [],
        })
        card[e.event] += 1
        card["items"].append({
            "event": e.event, "actor": e.actor, "detail": e.detail,
            "at": e.created_at.date().isoformat() if e.created_at else "",
        })
    for cid, card in by_card.items():
        row_c = session.get(db.CardRow, cid)
        card["title"] = row_c.title if row_c else cid

    return {
        "expert": expert,
        "name": row.display_name or expert,
        "period_end": date.today().isoformat(),
        "totals": totals,
        "cards": sorted(
            by_card.values(), key=lambda c: c["helped"] + c["cited"], reverse=True
        ),
        # 단가·금액 칸은 의도적으로 없다 — 정책 제언과 경계는 거버넌스 6항.
        "note_key": "statement.note",
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
            "lang": row.lang,
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
            # 미응답 숫자 — 빠지면 화면이 "미응답 " 으로 끝난다 (QA 실측)
            "gaps_open": summary.gaps_open,
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
        # 전시 전문가는 구경 모드 — 화면이 본인-행세 버튼을 아예 숨긴다.
        "readonly": expert in settings.featured,
        # 캠페인 스트립 — 절차(지도→채집→검증)가 메인에서 보이게.
        "campaign_steps": [
            {
                "domain": f.domain, "difficulty": f.difficulty,
                "cards": (n := sum(
                    1 for c in live if c.domain == f.domain
                    and c.status is not CardStatus.DRAFT)),
                "ripe": n - f.reviewed_cards >= 3,
            }
            for f in session.scalars(
                select(db.Flag).where(db.Flag.expert == expert)
                .order_by(db.Flag.created_at)
            ).all()
        ],
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


def backfill_aliases(session: Session, *, lang: str = LANG_DEFAULT) -> dict[str, Any]:
    """별칭 도입 이전에 승인된 카드에 검색어 별칭을 채운다.

    빈 별칭 + 인용 가능 카드만, 한 번에 40장 상한(호출당 비용 상한).
    시연 전문가(read-only 가드)도 대상이다 — 내용 수정이 아니라 검색 보조라
    전문가의 말은 한 글자도 안 바뀐다.
    """
    rows = session.scalars(
        select(db.CardRow).where(
            db.CardRow.aliases == "",
            db.CardRow.status.in_(["confirmed", "anchored", "contested"]),
        ).limit(40)
    ).all()
    llm = get_llm()
    filled = 0
    for row in rows:
        expert_row = session.get(db.Expert, row.expert)
        terms = interview.search_aliases(
            llm, title=row.title, situation=row.situation,
            cues=_lines(row.cues),
            lang=(expert_row.lang if expert_row and expert_row.lang else lang),
        )
        if terms:
            row.aliases = _join(terms)
            filled += 1
    session.commit()
    return {"scanned": len(rows), "filled": filled}


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
