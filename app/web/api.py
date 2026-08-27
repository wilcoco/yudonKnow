"""JSON API. 화면은 이 위에 얇게 얹힌다."""

from __future__ import annotations

from datetime import date
from typing import Any, Generator

from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.capture.instruments import INSTRUMENTS, LADDER
from app.capture.llm import get_llm
from app.config import settings
from app.i18n import pick
from app.store import db, service

router = APIRouter(prefix="/api")


def get_session() -> Generator[Session, None, None]:
    session = db.SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_lang(
    lang: str | None = Query(default=None),
    accept_language: str | None = Header(default=None),
) -> str:
    """``?lang=`` 우선, 없으면 브라우저가 보낸 ``Accept-Language``, 없으면 영어.

    대회 규정 6조가 영어 지원을 통과 조건으로 두므로 기본값은 영어다. 유돈의
    브라우저는 한국어를 먼저 보내니 한국어로 뜬다 (``app/i18n.py``).
    """
    return pick(accept_language, lang)


# ----------------------------------------------------------------- 요청 모델

class ExpertIn(BaseModel):
    id: str
    display_name: str = ""
    farewell: str = ""
    sayings: list[str] = Field(default_factory=list)
    taboos: list[str] = Field(default_factory=list)
    leaving_on: date | None = None


class SessionIn(BaseModel):
    expert: str
    instrument: str = LADDER


class AnswerIn(BaseModel):
    answer: str = ""
    skip: bool = False


class ConfirmIn(BaseModel):
    edits: dict[str, Any] = Field(default_factory=dict)
    tacitness: str = ""
    visibility: str = ""
    for_whom: str = ""
    open_at: date | None = None


class AskIn(BaseModel):
    question: str
    asker: str = ""


class AnchorIn(BaseModel):
    verdict: str
    reporter: str = ""
    detail: str = ""
    metric: str = ""
    baseline: float = 0.0
    observed: float = 0.0


class FlagIn(BaseModel):
    expert: str
    domain: str
    note: str = ""


class GradeIn(BaseModel):
    expert: str
    topic: str


class DocumentIn(BaseModel):
    expert: str
    text: str
    domain: str = ""


class ThanksIn(BaseModel):
    expert: str
    message: str
    actor: str = ""


class AlterToggleIn(BaseModel):
    active: bool


# --------------------------------------------------------------------- 라우트

@router.get("/health")
def health(session: Session = Depends(get_session)) -> dict:
    """앱만 뜨고 DB 가 죽은 상태를 잡으려고 왕복까지 한다."""
    session.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "version": __version__,
        "llm": get_llm().name,
        "llm_enabled": settings.llm_enabled,
        "store": settings.database_url.split("://")[0],
    }


@router.get("/instruments")
def instruments(cards: int = 0, lang: str = Depends(get_lang)) -> dict:
    """도구함. **AI 가 고르지 않는다** — 무엇이 열려 있는지만 알려준다."""
    from app.capture.instruments import unlocked

    open_keys = {i.key for i in unlocked(cards, threshold=settings.unlock_after_cards)}
    return {
        "instruments": [
            {
                "key": i.key, "emoji": i.emoji, "minutes": i.minutes,
                "fills": list(i.fills), "unlocked": i.key in open_keys,
                **i.localized(lang),
            }
            for i in INSTRUMENTS
        ],
        "unlock_after_cards": settings.unlock_after_cards,
    }


@router.post("/experts")
def upsert_expert(
    body: ExpertIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    row = service.ensure_expert(
        session,
        body.id,
        display_name=body.display_name or body.id,
        sayings="\n".join(body.sayings),
        taboos="\n".join(body.taboos),
        leaving_on=body.leaving_on,
        farewell=body.farewell or None,   # 빈 값으로 기존 글을 지우지 않는다
        # 온보딩 화면의 언어가 이 사람이 파는 언어다. 카드도 분신도 여기서 산다.
        lang=lang,
    )
    return {"expert": row.id, "alter": service.persona_of(row).label(lang)}


@router.get("/experts")
def list_experts(
    session: Session = Depends(get_session), lang: str = Depends(get_lang)
) -> dict:
    from sqlalchemy import select

    rows = session.scalars(select(db.Expert)).all()
    return {
        "experts": [
            {
                "id": r.id,
                "name": r.display_name or r.id,
                "alter": service.persona_of(r).label(lang),
                "farewell": r.farewell,
                "active": r.alter_active,
                "days_left": service.days_left(r),
            }
            for r in rows
        ]
    }


@router.get("/experts/{expert}/home")
def home(
    expert: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.expert_home(session, expert, lang=lang)


@router.post("/experts/{expert}/alter")
def toggle_alter(
    expert: str, body: AlterToggleIn, session: Session = Depends(get_session)
) -> dict:
    """통제권 — 본인이 자기 분신을 끈다. 남의 결재가 필요 없다."""
    row = service.get_expert(session, expert)
    row.alter_active = body.active
    session.commit()
    return {"expert": expert, "active": row.alter_active}


@router.get("/experts/{expert}/export")
def export(expert: str, session: Session = Depends(get_session)) -> dict:
    """내 카드는 내가 가져간다."""
    return service.export_cards(session, expert)


@router.post("/sessions")
def start_session(
    body: SessionIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.start_session(
        session, body.expert, instrument=body.instrument, lang=lang
    )


@router.post("/turns/{turn_id}")
def answer(
    turn_id: str,
    body: AnswerIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.answer_turn(
        session, turn_id, body.answer, skip=body.skip, lang=lang
    )


@router.post("/cards/{card_id}/confirm")
def confirm(
    card_id: str,
    body: ConfirmIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.confirm_card(
        session, card_id, edits=body.edits, tacitness=body.tacitness,
        visibility=body.visibility, for_whom=body.for_whom, open_at=body.open_at,
        lang=lang,
    )


@router.post("/cards/{card_id}/dormant")
def dormant(
    card_id: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.dormant_card(session, card_id, lang=lang)


@router.post("/cards/{card_id}/report")
def report(
    card_id: str,
    body: AnchorIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.report_anchor(
        session, card_id, body.verdict, reporter=body.reporter, detail=body.detail,
        metric=body.metric, baseline=body.baseline, observed=body.observed, lang=lang,
    )


@router.post("/alter/{expert}/ask")
def ask(
    expert: str,
    body: AskIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.ask_alter(
        session, expert, body.question, asker=body.asker, lang=lang
    )


@router.post("/documents")
def interrogate_document(
    body: DocumentIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """문서 → 질문 → 공백 큐. **카드로 변환하지 않는다.**"""
    return service.interrogate_document(
        session, body.expert, body.text, domain=body.domain, lang=lang
    )


@router.post("/flags")
def flag(
    body: FlagIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.flag_domain(
        session, body.expert, body.domain, body.note, lang=lang
    )


@router.post("/grade")
def grade(
    body: GradeIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.grade_prompt(session, body.expert, body.topic, lang=lang)


@router.post("/thanks")
def thanks(
    body: ThanksIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.thank(
        session, body.expert, body.message, actor=body.actor, lang=lang
    )


@router.get("/admin/board")
def board(
    session: Session = Depends(get_session), lang: str = Depends(get_lang)
) -> dict:
    return service.admin_board(session, lang=lang)
