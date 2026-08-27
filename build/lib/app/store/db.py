"""영속 스키마 — SQLite(기본) / Postgres(DATABASE_URL 주입 시).

도메인 코어(``app/core``)는 저장소를 모른다. 이 모듈과 ``service.py`` 가
행(row)을 코어 객체로 조립하고 다시 해체해 넣는다. 느리지만 MVP 규모에서
정확하고, 코어의 의존성 0 규약을 지킨다 (alter-ai 에서 검증된 배치).

**원본 발화(``turns.answer``)는 어떤 경로로도 삭제하지 않는다.**
카드는 해석이고 해석은 틀릴 수 있다. 원본이 있어야 재해석이 가능하다.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Expert(Base):
    """전문가 — 그리고 그의 분신 프로필."""

    __tablename__ = "experts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(128), default="")
    #: 분신 어투의 재료 (온보딩에서 본인이 채운다)
    sayings: Mapped[str] = mapped_column(Text, default="")     # 줄바꿈 구분
    taboos: Mapped[str] = mapped_column(Text, default="")      # 줄바꿈 구분
    #: 통제권 — 본인이 자기 분신을 끌 수 있다
    alter_active: Mapped[bool] = mapped_column(Boolean, default=True)
    leaving_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Flag(Base):
    """🚩 머릿속 지도 — **전문가 본인이** "여기 아직 남았다" 고 꽂은 깃발.

    기계가 계산한 커버리지보다 이 깃발을 먼저 본다. 기계가 "다 됐다"고 해도
    본인이 아니라면 아닌 것이다 (docs/self-excavation.md §2.11).
    """

    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    domain: Mapped[str] = mapped_column(String(128))
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Session(Base):
    """발굴 세션 — 어느 연장으로 팠는지가 여기 남는다."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    instrument: Mapped[str] = mapped_column(String(32), default="ladder")
    card_id: Mapped[str] = mapped_column(String(64), default="")
    closed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Turn(Base):
    """문답 한 번. **원본 발화는 절대 삭제하지 않는다.**"""

    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("sessions.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text, default="")
    rung: Mapped[str] = mapped_column(String(32), default="")
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CardRow(Base):
    """판단 카드. 리스트 칸은 줄바꿈 구분 문자열로 저장한다 (스키마 단순 유지)."""

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(128), default="", index=True)

    situation: Mapped[str] = mapped_column(Text, default="")
    cues: Mapped[str] = mapped_column(Text, default="")
    judgment: Mapped[str] = mapped_column(Text, default="")
    action: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    exceptions: Mapped[str] = mapped_column(Text, default="")
    failure: Mapped[str] = mapped_column(Text, default="")
    unspeakable: Mapped[str] = mapped_column(Text, default="")

    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    tacitness: Mapped[str] = mapped_column(String(16), default="partial")
    visibility: Mapped[str] = mapped_column(String(16), default="public")
    for_whom: Mapped[str] = mapped_column(String(64), default="")
    open_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    risk: Mapped[str] = mapped_column(String(8), default="mid")
    instrument: Mapped[str] = mapped_column(String(32), default="")
    source_turn: Mapped[str] = mapped_column(String(64), default="")
    citations: Mapped[int] = mapped_column(Integer, default=0)
    helped: Mapped[int] = mapped_column(Integer, default=0)
    missed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Ask(Base):
    """후배가 분신에게 물은 것. 답했든 못 답했든 남는다."""

    __tablename__ = "asks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    asker: Mapped[str] = mapped_column(String(64), index=True, default="")
    question: Mapped[str] = mapped_column(Text)
    answered: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Citation(Base):
    """분신이 어느 카드로 답했는가 — 유산 원장의 원천."""

    __tablename__ = "citations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ask_id: Mapped[str] = mapped_column(String(64), ForeignKey("asks.id"), index=True)
    card_id: Mapped[str] = mapped_column(String(64), ForeignKey("cards.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Gap(Base):
    """분신이 못 답한 것 → 전문가의 큐. **인터뷰 주제를 현장 수요가 정한다.**"""

    __tablename__ = "gaps"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    question: Mapped[str] = mapped_column(Text)
    asked_count: Mapped[int] = mapped_column(Integer, default=1)
    askers: Mapped[str] = mapped_column(Text, default="")   # 줄바꿈 구분
    filled_card: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_asked: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Anchor(Base):
    """적용 보고 = 외부 현실 닻 (CAMS-KnowledgeNet verification.py 이식).

    ✔ 현장 검증 배지의 **유일한** 출처. 조회수·좋아요는 세지 않는다.
    """

    __tablename__ = "anchors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    card_id: Mapped[str] = mapped_column(String(64), ForeignKey("cards.id"), index=True)
    reporter: Mapped[str] = mapped_column(String(64), default="")
    verdict: Mapped[str] = mapped_column(String(16))      # helped | missed | pending
    detail: Mapped[str] = mapped_column(Text, default="")
    metric: Mapped[str] = mapped_column(String(128), default="")
    baseline: Mapped[float] = mapped_column(Float, default=0.0)
    observed: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class LedgerRow(Base):
    """유산 원장 — append-only. 지워지지 않는다."""

    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    event: Mapped[str] = mapped_column(String(32))
    card_id: Mapped[str] = mapped_column(String(64), default="")
    actor: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(
    settings.database_url, connect_args=_connect_args, pool_pre_ping=True, future=True
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)
