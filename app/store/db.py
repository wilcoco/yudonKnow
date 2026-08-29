"""영속 스키마 — SQLite(기본) / Postgres(DATABASE_URL 주입 시).

도메인 코어(``app/core``)는 저장소를 모른다. 이 모듈과 ``service.py`` 가
행(row)을 코어 객체로 조립하고 다시 해체해 넣는다. 느리지만 MVP 규모에서
정확하고, 코어의 의존성 0 규약을 지킨다 (alter-ai 에서 검증된 배치).

**원본 발화(``turns.answer``)는 어떤 경로로도 삭제하지 않는다.**
카드는 해석이고 해석은 틀릴 수 있다. 원본이 있어야 재해석이 가능하다.
"""

from __future__ import annotations

import logging

from datetime import date, datetime, timezone

from sqlalchemy import (
    text,
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
    #: 이 전문가가 파는 언어. 카드는 파낸 언어로 살고, 검색도 그 안에서 돈다
    #: (docs/design.md §7). 번역하면 지식이 아니라 요약이 된다.
    lang: Mapped[str] = mapped_column(String(8), default="ko", index=True)
    #: 분신 어투의 재료 (온보딩에서 본인이 채운다)
    sayings: Mapped[str] = mapped_column(Text, default="")     # 줄바꿈 구분
    taboos: Mapped[str] = mapped_column(Text, default="")      # 줄바꿈 구분
    #: 후배에게 남기는 말. 카드가 아니라 **사람의 말**이다 — 분신에게 말을 걸기
    #: 전에 한 번은 읽히는 자리이고, 이 도구에서 가장 사람다운 한 조각이다.
    farewell: Mapped[str] = mapped_column(Text, default="")
    #: 통제권 — 본인이 자기 분신을 끌 수 있다
    alter_active: Mapped[bool] = mapped_column(Boolean, default=True)
    leaving_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Flag(Base):
    """과업 단계이자 깃발 — 발굴 캠페인의 지도 조각.

    전문 지식공학의 1단계(Task Diagram)는 일의 단계를 그리고 **어느 단계가
    인지적으로 어려운지** 표시하는 것이다. 그 표시가 발굴 우선순위가 된다.
    """
    """🚩 머릿속 지도 — **전문가 본인이** "여기 아직 남았다" 고 꽂은 깃발.

    기계가 계산한 커버리지보다 이 깃발을 먼저 본다. 기계가 "다 됐다"고 해도
    본인이 아니라면 아닌 것이다 (docs/self-excavation.md §2.11).
    """

    __tablename__ = "flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    domain: Mapped[str] = mapped_column(String(128))
    #: 인지 난이도 — hard(감이 필요) / mid / easy. 캠페인이 hard 부터 판다.
    difficulty: Mapped[str] = mapped_column(String(8), default="")
    #: 어디서 왔나 — expert(온보딩·직접) / taskmap(과업 지도 인터뷰)
    origin: Mapped[str] = mapped_column(String(16), default="expert")
    #: 마지막 영역 검증(member checking) 때의 카드 수. 그 뒤로 3장 쌓이면
    #: 다시 검증이 익는다(ripe) — 검증은 한 번이 아니라 주기다.
    reviewed_cards: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class Session(Base):
    """발굴 세션 — 어느 연장으로 팠는지가 여기 남는다."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    instrument: Mapped[str] = mapped_column(String(32), default="ladder")
    #: 이 세션이 겨냥한 영역 — 이관 업무(깃발)에서 시작했으면 그 깃발.
    #: 카드의 domain 이 비면 이것을 물려받아 커버리지가 제 영역으로 오른다.
    domain: Mapped[str] = mapped_column(String(128), default="")
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
    #: 이 질문이 겨냥한 카드 칸. 기저가 없을 때 답을 어느 칸에 넣을지는
    #: 이것으로 정한다 — 내용을 지어내지 않고 **분류만** 한다.
    targets: Mapped[str] = mapped_column(String(32), default="")
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class CardRow(Base):
    """판단 카드. 리스트 칸은 줄바꿈 구분 문자열로 저장한다 (스키마 단순 유지)."""

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(128), default="", index=True)
    #: 이 카드가 파여 나온 언어. 검색은 같은 언어 안에서만 돈다 —
    #: 찾아 줘도 못 읽는 카드는 답이 아니다 (docs/design.md §7).
    lang: Mapped[str] = mapped_column(String(8), default="ko", index=True)

    situation: Mapped[str] = mapped_column(Text, default="")
    cues: Mapped[str] = mapped_column(Text, default="")
    judgment: Mapped[str] = mapped_column(Text, default="")
    action: Mapped[str] = mapped_column(Text, default="")
    rationale: Mapped[str] = mapped_column(Text, default="")
    exceptions: Mapped[str] = mapped_column(Text, default="")
    failure: Mapped[str] = mapped_column(Text, default="")
    unspeakable: Mapped[str] = mapped_column(Text, default="")
    #: 검색어 별칭 — "후배가 이걸 뭐라고 물을까". 승인 시점에 생성되는
    #: 숨은 검색 보조 토큰(화면·인용에 안 나감). 판정은 여전히 키워드
    #: 겹침의 결정적 문턱이고, 필드만 넓어진다.
    aliases: Mapped[str] = mapped_column(Text, default="")

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


class Document(Base):
    """문서함 — 보관함이 아니라 **발굴 지도**다.

    문서는 내용으로 정리되지 않는다. 문서가 **말하지 않는 것**(심문으로 나온
    질문들)과 그중 몇 개가 카드로 채워졌는지로 정리된다. 후배에게는 절대
    노출되지 않는다 — 후배에게 남는 것은 카드뿐이다.
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    expert: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    domain: Mapped[str] = mapped_column(String(128), default="")
    text: Mapped[str] = mapped_column(Text, default="")
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
    #: 이 질문을 만든 문서 (📄 심문 산출일 때). 문서함의 진행도가 여기서 나온다.
    source_doc: Mapped[str] = mapped_column(String(64), default="", index=True)
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
    #: 판 내용이 바뀌면 이전 판에 대한 보고는 배지 계산에서 빠진다 — 새 내용이
    #: 옛 증거로 재검증되는 것을 막는다. 원장은 append-only 라 역사는 남는다.
    stale: Mapped[bool] = mapped_column(Boolean, default=False)
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
    # timeout: 로컬 동시 부하에서 쓰기 락 대기(운영은 Postgres 라 무관)
    {"check_same_thread": False, "timeout": 30}
    if settings.database_url.startswith("sqlite") else {}
)
engine = create_engine(
    settings.database_url, connect_args=_connect_args, pool_pre_ping=True, future=True
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


log = logging.getLogger(__name__)


def init_db() -> None:
    """스키마 준비. **여러 인스턴스가 동시에 기동해도 죽지 않아야 한다.**

    create_all 의 존재 확인과 생성 사이에는 프로세스 간 경쟁이 있다 —
    Cloud Run 이 콜드 스타트에서 인스턴스 둘을 같이 올리면 한쪽이
    "already exists" 로 죽는다 (멀티 워커 부하 준비 중 실측). 지는 쪽은
    이미 이긴 쪽이 만든 스키마를 쓰면 되므로, 그 오류만 삼키고 진행한다.
    """
    try:
        Base.metadata.create_all(engine)
    except Exception as exc:
        if "already exists" not in str(exc).lower() \
                and "duplicate" not in str(exc).lower():
            raise
        log.warning("스키마 생성 경쟁에서 짐 — 이긴 쪽 스키마를 쓴다: %s", exc)
    _add_missing_columns()


def _add_missing_columns() -> None:
    """모델에는 있는데 테이블에 없는 칸을 **더하기만** 한다.

    ``create_all`` 은 이미 있는 테이블을 바꾸지 않는다. 그래서 칸을 하나 추가한
    배포가 기존 DB 에서 곧장 500 으로 죽는다 (`experts.farewell` 이 그랬다).
    Alembic 을 들이기엔 이 레포가 작고, 지우거나 바꾸는 마이그레이션은 어차피
    사람이 봐야 한다. 여기서는 **추가만** 처리한다 — 되돌릴 일이 없는 연산이라
    자동으로 돌려도 안전하다.
    """
    from sqlalchemy import inspect as sa_inspect

    inspector = sa_inspect(engine)
    with engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            have = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in have:
                    continue
                ddl = column.type.compile(engine.dialect)
                default = column.default.arg if column.default is not None else None
                clause = f'ALTER TABLE {table.name} ADD COLUMN "{column.name}" {ddl}'
                if isinstance(default, (str, int, float, bool)):
                    literal = f"'{default}'" if isinstance(default, str) else str(default)
                    clause += f" DEFAULT {literal}"
                log.warning("칸 추가: %s.%s", table.name, column.name)
                conn.execute(text(clause))
