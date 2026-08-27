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


#: 화면에 그대로 쓰는 문장. 기계 어휘를 전문가에게 보이지 않는다.
PHRASE = {
    LedgerEvent.CARD_CONFIRMED: "판단 하나를 남기셨습니다",
    LedgerEvent.CITED: "당신의 판단으로 답했습니다",
    LedgerEvent.HELPED: "도움이 됐다고 합니다",
    LedgerEvent.MISSED: "이 경우엔 안 맞았다고 합니다 — 한번 봐주세요",
    LedgerEvent.ANCHORED: "현장에서 검증됐습니다",
    LedgerEvent.GAP_FILLED: "후배가 막혔던 곳을 뚫어주셨습니다",
    LedgerEvent.THANKS: "후배가 감사를 남겼습니다",
}


@dataclass
class Entry:
    event: LedgerEvent
    expert: str
    card_id: str = ""
    actor: str = ""        # 후배 등 상대방
    detail: str = ""
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def sentence(self) -> str:
        who = f"{self.actor}: " if self.actor else ""
        tail = f" — {self.detail}" if self.detail else ""
        return f"{who}{PHRASE[self.event]}{tail}"


@dataclass
class LegacySummary:
    """전문가 홈 최상단에 항상 뜨는 블록."""

    expert: str
    cards_alive: int = 0
    cards_verified: int = 0
    citations: int = 0
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

    def headline(self) -> str:
        """한 문장. 이 문장 하나 때문에 전문가가 다시 온다."""
        if self.askers and self.citations:
            return (
                f"후배 {self.askers}명이 물었고, 그중 {self.citations}번을 "
                f"당신의 판단으로 답했습니다."
            )
        if self.cards_alive:
            return (
                f"판단 {self.cards_alive}개가 살아 있습니다. "
                "아직 아무도 묻지 않았지만, 남아 있습니다."
            )
        return "아직 아무것도 남기지 않으셨습니다. 3분이면 첫 하나가 남습니다."


def summarize(expert: str, entries: list[Entry], **counts: int) -> LegacySummary:
    summary = LegacySummary(expert=expert, **counts)
    summary.recent = sorted(entries, key=lambda e: e.at, reverse=True)[:8]
    return summary
