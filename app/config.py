"""환경 설정 — 전부 환경변수, 전부 기본값 있음.

원칙 (alter-ai/coral 에서 이식): **키 없이도 뜬다.** ANTHROPIC_API_KEY 가 없으면
인터뷰어·분신이 규칙 기반으로 떨어지고, DATABASE_URL 이 없으면 SQLite 파일로
떨어진다. 배포가 설정에 인질로 잡히지 않게 하려는 것 — 발굴→카드→분신→공백→닻
동선은 stub 에서도 그대로 돈다.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _f(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def _i(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


def _normalize_db_url(url: str) -> str:
    """Railway/Heroku 의 ``postgres://`` 를 SQLAlchemy 2.x 드라이버 URL 로."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


@dataclass(frozen=True)
class Settings:
    # -- LLM (교체 가능 부품: 텍스트 in/out 경계에서만 접합) -----------------
    anthropic_api_key: str | None
    model: str
    max_tokens: int

    # -- 저장소 ------------------------------------------------------------
    database_url: str

    # -- 발굴 정책 ---------------------------------------------------------
    #: 한 세션의 목표 질문 수 (20분 기준). 넘기면 마무리를 권한다.
    interview_turns: int
    #: 카드가 인용 가능해지는 최소 완성도 (채워진 칸 / 7)
    citable_completeness: float

    # -- 분신 정책 ---------------------------------------------------------
    #: 한 답에 끌어올 카드 수
    retrieval_top_k: int
    #: 검색 결과 중 신규·저인용 카드에 강제 배정할 비율 (마태 효과 보정)
    explore_quota: float
    #: 이 확신도 아래면 **LLM 을 호출하지 않고** 공백(gap)으로 넘긴다.
    confidence_floor: float
    #: ✔ 현장 검증 배지에 필요한 최소 긍정 적용 보고 수
    anchor_min_reports: int

    # -- 도구함 ------------------------------------------------------------
    #: 이 개수만큼 카드가 쌓이면 잠긴 연장이 열린다 (선택지 과부하 방지)
    unlock_after_cards: int

    @property
    def llm_enabled(self) -> bool:
        return bool(self.anthropic_api_key)


def load_settings() -> Settings:
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if db_url:
        db_url = _normalize_db_url(db_url)
    else:
        data_dir = Path(os.environ.get("YDK_DATA_DIR", "./data")).resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite:///{data_dir / 'yudonknow.db'}"

    return Settings(
        anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        model=os.environ.get("YDK_MODEL", "claude-opus-5"),
        max_tokens=_i("YDK_MAX_TOKENS", 8000),
        database_url=db_url,
        interview_turns=_i("YDK_INTERVIEW_TURNS", 7),
        citable_completeness=_f("YDK_CITABLE_COMPLETENESS", 0.6),
        retrieval_top_k=_i("YDK_RETRIEVAL_TOP_K", 6),
        explore_quota=_f("YDK_EXPLORE_QUOTA", 0.25),
        confidence_floor=_f("YDK_CONFIDENCE_FLOOR", 0.35),
        anchor_min_reports=_i("YDK_ANCHOR_MIN_REPORTS", 2),
        unlock_after_cards=_i("YDK_UNLOCK_AFTER_CARDS", 3),
    )


settings = load_settings()
