"""유산 원장 — **의존성 0**. 보람의 회계.

이 도구가 죽는 이유는 기술이 아니라 **전문가가 3회차에 그만두기 때문**이다.
그래서 원장은 부가 기능이 아니라 엔진이다 (docs/design.md §3.5).

두 가지 금지 (CAMS-KnowledgeNet 의 "대리변수 금지" 이식):

1. **조회수·좋아요를 세지 않는다.** 인용과 후배의 명시적 적용 보고만 센다.
2. **인사 평가 지표로 쓰지 않는다.** 감시로 쓰이는 순간 발굴이 멈춘다
   (docs/roadmap.md 거버넌스). 원장은 본인과 본인이 지정한 사람만 본다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class LedgerEvent(str, Enum):
    CARD_CONFIRMED = "card_confirmed"   # 내가 카드를 승인했다
    CITED = "cited"                     # 내 분신이 내 카드로 답했다
    HELPED = "helped"                   # 후배가 "도움됐다" 고 보고했다
    MISSED = "missed"                   # "안 맞았다" — 교정 신호. 숨기지 않는다
    ANCHORED = "anchored"               # 현장 검증됨 (✔)
    GAP_FILLED = "gap_filled"           # 후배가 물었는데 못 답했던 것을 내가 채웠다
    THANKS = "thanks"                   # 후배가 남긴 감사 메시지


@dataclass
class Entry:
    event: LedgerEvent
    expert: str
    card_id: str = ""
    actor: str = ""        # 후배 등 상대방
    detail: str = ""
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def sentence(self, phrase: str) -> str:
        """원장 한 줄. **문장은 코어가 만들지 않는다** — 표현 층이 언어에 맞는
        ``phrase`` 를 넘겨주고, 코어는 누가·무엇을 붙일지만 안다.
        판정 로직에 언어가 섞이면 둘 다 망가진다 (``app/i18n.py`` 참고)."""
        who = f"{self.actor}: " if self.actor else ""
        tail = f" — {self.detail}" if self.detail else ""
        return f"{who}{phrase}{tail}"


@dataclass
class LegacySummary:
    """전문가 홈 최상단에 항상 뜨는 블록."""

    expert: str
    cards_alive: int = 0
    cards_verified: int = 0
    citations: int = 0       # 카드가 인용된 총 횟수 (한 답이 여러 장을 쓸 수 있다)
    answers: int = 0         # 분신이 당신의 카드로 답한 횟수
    askers: int = 0          # 당신에게 물어본 사람 수 (중복 제거)
    helped: int = 0
    missed: int = 0
    gaps_open: int = 0
    hands_items: int = 0     # 🔴 도제로 넘겨야 하는 것
    recent: list[Entry] = field(default_factory=list)

    @property
    def help_rate(self) -> float:
        total = self.helped + self.missed
        return round(self.helped / total, 3) if total else 0.0

    @property
    def headline_key(self) -> str:
        """어느 문장을 쓸지만 고른다. 문장 자체는 표현 층이 만든다.

        이 한 줄 때문에 전문가가 다시 온다 — 그래서 *무엇을 말할지* 는 코어가
        정하고, *어떤 말로* 는 화면이 정한다.
        """
        if self.askers and self.answers:
            return "ledger.headline.both"
        if self.cards_alive:
            return "ledger.headline.alive"
        return "ledger.headline.empty"


def summarize(expert: str, entries: list[Entry], **counts: int) -> LegacySummary:
    summary = LegacySummary(expert=expert, **counts)
    summary.recent = sorted(entries, key=lambda e: e.at, reverse=True)[:8]
    return summary
