"""커버리지와 승계 리스크 — **의존성 0**.

주의 (docs/roadmap.md 성공지표): 커버리지 % 를 단독으로 쓰지 않는다.
언제나 **🔴 손끝(도제) 비율**과 함께 보고한다. 담지 *못한* 양을 감추면
"다 캤다"는 착각만 남는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.card import Card, CardStatus, Tacitness

#: 한 영역이 "채워졌다" 고 볼 만한 카드 수. 이 이상은 수확체감으로 계산한다.
SATURATION = 12


@dataclass
class DomainCoverage:
    domain: str
    cards: int = 0
    citable: int = 0
    anchored: int = 0
    hands: int = 0          # 🔴 손끝 — 도제로 넘겨야 하는 것
    flagged: bool = False   # 전문가가 직접 꽂은 🚩 미개척 깃발

    #: 커버리지 상한. **1.0 을 주지 않는 것은 의도다** — 어떤 영역도 "다 캤다"
    #: 고 말하지 않는다. 남은 5% 는 아직 아무도 묻지 않은 질문의 자리다.
    CEILING = 0.95

    @property
    def coverage(self) -> float:
        """수확체감. 12장이면 ~0.87, 그 뒤로는 천장(0.95)에 붙기만 한다."""
        if not self.citable:
            return 0.0
        base = min(1.0 - 0.5 ** (self.citable / SATURATION * 3), self.CEILING)
        # 전문가 본인이 "아직 남았다" 고 깃발을 꽂았으면 기계 계산을 신뢰하지 않는다.
        return base * 0.6 if self.flagged else base

    @property
    def verified_ratio(self) -> float:
        return self.anchored / self.citable if self.citable else 0.0


@dataclass
class SuccessionRisk:
    expert: str
    days_left: int | None
    coverage: float
    hands_ratio: float
    domains: list[DomainCoverage] = field(default_factory=list)

    @property
    def score(self) -> float:
        """리스크 = 미커버리지 × 임박도. 0.0 ~ 1.0.

        정렬 기준이 곧 개입 순서다 (docs/user-flows.md §M1).
        """
        uncovered = 1.0 - self.coverage
        if self.days_left is None:
            urgency = 0.35
        elif self.days_left <= 0:
            urgency = 1.0
        else:
            urgency = min(180.0 / max(self.days_left, 1), 1.0)
        return round(min(uncovered * urgency, 1.0), 3)

    @property
    def level(self) -> str:
        s = self.score
        return "심각" if s >= 0.6 else "중" if s >= 0.3 else "저"


def by_domain(cards: list[Card], flags: set[str] | None = None) -> list[DomainCoverage]:
    flags = flags or set()
    out: dict[str, DomainCoverage] = {}
    for card in cards:
        if card.status is CardStatus.DORMANT:
            continue
        key = card.domain or "미분류"
        d = out.setdefault(key, DomainCoverage(domain=key))
        d.cards += 1
        if card.citable():
            d.citable += 1
        if card.status is CardStatus.ANCHORED:
            d.anchored += 1
        if card.tacitness is Tacitness.HANDS:
            d.hands += 1
    for name in flags:
        out.setdefault(name, DomainCoverage(domain=name)).flagged = True
    for name, d in out.items():
        d.flagged = d.flagged or name in flags
    return sorted(out.values(), key=lambda d: d.coverage)


def succession_risk(
    expert: str,
    cards: list[Card],
    *,
    days_left: int | None,
    flags: set[str] | None = None,
) -> SuccessionRisk:
    domains = by_domain(cards, flags)
    live = [c for c in cards if c.status is not CardStatus.DORMANT]
    coverage = sum(d.coverage for d in domains) / len(domains) if domains else 0.0
    hands = sum(1 for c in live if c.tacitness is Tacitness.HANDS)
    return SuccessionRisk(
        expert=expert,
        days_left=days_left,
        coverage=round(coverage, 3),
        hands_ratio=round(hands / len(live), 3) if live else 0.0,
        domains=domains,
    )
