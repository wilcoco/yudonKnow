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
    gap_id: str = ""
    step: str = ""


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


class TranscribeIn(BaseModel):
    audio_b64: str          # 브라우저 MediaRecorder 산출물 (webm/ogg/mp4)
    mime: str = "audio/webm"


class DocumentIn(BaseModel):
    expert: str
    text: str
    title: str = ""
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
    service._guard_demo(body.id, lang)   # 전시 전문가 프로필은 덮어쓰기 금지
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


@router.get("/experts/{expert}/next")
def peek_next(
    expert: str,
    skip: int = 0,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """오늘의 질문 미리보기 — 홈의 주인공. 세션은 만들지 않는다."""
    return service.peek_next_question(session, expert, skip=skip, lang=lang)


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
    service._guard_demo(expert)          # 단, 전시 전문가는 심사 기간 보호
    row = service.get_expert(session, expert)
    row.alter_active = body.active
    session.commit()
    return {"expert": expert, "active": row.alter_active}


@router.get("/experts/{expert}/statement")
def statement(
    expert: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """내 지식 사용 명세서 — 전문가 본인이 뽑아 인사팀에 내미는 정산 근거."""
    return service.usage_statement(session, expert, lang=lang)


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
        session, body.expert, instrument=body.instrument,
        gap_id=body.gap_id, step=body.step, lang=lang,
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


class UnansweredIn(BaseModel):
    question: str
    asker: str = ""


@router.post("/alter/{expert}/unanswered")
def unanswered(
    expert: str,
    body: UnansweredIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """"이건 답이 아니었어요" — 후배의 판정으로 질문을 공백 큐에 되돌린다."""
    return service.mark_unanswered(
        session, expert, body.question, asker=body.asker, lang=lang
    )


@router.get("/alter/{expert}/followup")
def followup(
    expert: str,
    asker: str = "",
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """재방문 고리 — 지난번 인용받고 아직 보고 안 한 카드 하나를 되물어본다."""
    return service.followup(session, expert, asker, lang=lang)


class RouteIn(BaseModel):
    question: str
    asker: str = ""


@router.post("/route")
def route(
    body: RouteIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """통합 질문창 — 질문에 판단을 남긴 전문가를 찾아 연결한다(답은 안 한다)."""
    return service.route_question(
        session, body.question, asker=body.asker, lang=lang
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


@router.post("/transcribe")
def transcribe(body: TranscribeIn, lang: str = Depends(get_lang)) -> dict:
    """음성 → 텍스트. 결과는 **답 칸에 채워질 뿐, 바로 제출되지 않는다** —
    전문가가 고친 것이 기계 전사보다 우선한다."""
    import base64

    try:
        audio = base64.b64decode(body.audio_b64, validate=True)
    except Exception:
        raise service.ServiceError("잘못된 오디오 데이터입니다")
    if len(audio) > 15_000_000:   # ~15MB ≈ 수 분 분량이면 충분하다
        raise service.ServiceError("녹음이 너무 깁니다 — 3분 안쪽으로 잘라주세요")
    text = get_llm().transcribe(audio, body.mime, lang=lang)
    return {"text": text, "supported": bool(text) or settings.llm_enabled}


class MonologueIn(BaseModel):
    expert: str
    text: str
    domain: str = ""


@router.post("/monologue")
def mine_monologue(
    body: MonologueIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """혼잣말 → 질문 → 공백 큐. 문서와 같은 불변식 — 카드로 변환하지 않는다."""
    return service.mine_monologue(
        session, body.expert, body.text, domain=body.domain, lang=lang
    )


@router.get("/experts/{expert}/documents")
def my_documents(
    expert: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """문서함 — 발굴 지도. 후배 화면에는 절대 노출되지 않는다."""
    return service.my_documents(session, expert, lang=lang)


@router.get("/documents/{doc_id}")
def document_detail(
    doc_id: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.document_detail(session, doc_id, lang=lang)


@router.get("/experts/{expert}/cards")
def my_cards(
    expert: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.my_cards(session, expert, lang=lang)


@router.get("/cards/{card_id}")
def card_detail(
    card_id: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    return service.card_detail(session, card_id, lang=lang)


@router.post("/cards/{card_id}/preview")
def alter_preview(
    card_id: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """방금 남긴 카드로 분신이 답하는 시연 — 원장에 기록되지 않는다."""
    return service.alter_preview(session, card_id, lang=lang)


@router.post("/cards/{card_id}/resume")
def resume_card(
    card_id: str,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """파다 만 초안을 인터뷰로 이어간다."""
    return service.resume_session(session, card_id, lang=lang)


@router.post("/documents")
def interrogate_document(
    body: DocumentIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    """문서 → 질문 → 공백 큐. **카드로 변환하지 않는다.**"""
    return service.interrogate_document(
        session, body.expert, body.text, title=body.title,
        domain=body.domain, lang=lang,
    )


@router.post("/flags")
def flag(
    body: FlagIn,
    session: Session = Depends(get_session),
    lang: str = Depends(get_lang),
) -> dict:
    service._guard_demo(body.expert, lang)
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


@router.post("/admin/backfill-aliases")
def backfill_aliases(
    session: Session = Depends(get_session), lang: str = Depends(get_lang)
) -> dict:
    """검색어 별칭 뒤채움 — 별칭 도입 이전에 승인된 카드들.

    빈 별칭 카드만 건드리는 멱등 연산이라 반복 호출은 무해하다(비용 상한).
    """
    return service.backfill_aliases(session, lang=lang)


@router.get("/admin/board")
def board(
    session: Session = Depends(get_session), lang: str = Depends(get_lang)
) -> dict:
    return service.admin_board(session, lang=lang)
