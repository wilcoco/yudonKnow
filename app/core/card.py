"""판단 카드 — 이 도구의 원자 단위. **의존성 0** (프레임워크도 DB 도 모른다).

문서도 Q&A 도 아니고 **하나의 상황 판단**이 하나의 카드다. 절차서에 절대 안 적히는
두 칸 — ``cues``(무엇을 보고 아는가) 와 ``exceptions``(언제 안 통하는가) — 가
이 카드가 존재하는 이유다.

정본: ``docs/design.md`` §3.1 · 자기 발굴 연장은 ``docs/self-excavation.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class CardStatus(str, Enum):
    """카드 생애. **삭제는 없다 — 잠복(dormant)뿐이다** (CAMS-KnowledgeNet tree.py)."""

    DRAFT = "draft"           # 초안. 전문가가 아직 승인 안 함 → 분신이 인용 못 함
    CONFIRMED = "confirmed"   # 전문가 승인. 분신이 인용한다
    ANCHORED = "anchored"     # 후배의 적용 보고로 현장 검증됨 → ✔ 배지
    CONTESTED = "contested"   # "안 맞았다" 보고가 있음. 숨기지 않고 표시한 채 노출
    DORMANT = "dormant"       # 잠복. 조건이 바뀌면 부활 가능


class Tacitness(str, Enum):
    """암묵지 온도계 — **전문가 본인이** 매긴다 (self-excavation §2.12)."""

    SPEAKABLE = "speakable"   # 🟢 읽으면 따라 할 수 있다
    PARTIAL = "partial"       # 🟡 읽고 몇 번 해봐야 한다
    HANDS = "hands"           # 🔴 손끝이다 — 자동으로 도제 항목이 된다

    @property
    def emoji(self) -> str:
        return {"speakable": "🟢", "partial": "🟡", "hands": "🔴"}[self.value]


class Visibility(str, Enum):
    """통제권 — 자발성의 전제조건 (self-excavation §1). 처분권은 전문가에게."""

    PUBLIC = "public"       # 사내 공개
    TARGETED = "targeted"   # 지목한 사람에게만
    SEALED = "sealed"       # 내가 정한 날에 열린다 (퇴직일 등)
    PRIVATE = "private"     # 영원히 나만. 언제든 공개로 전환 가능


class NodeType(str, Enum):
    """H2A2H2 / coral 포맷 호환 (docs/reuse-map.md)."""

    PREMISE = "premise"
    INFERENCE = "inference"
    CONCLUSION = "conclusion"
    CONCEPT = "concept"
    CLAIM = "claim"
    EVIDENCE = "evidence"


class EdgeType(str, Enum):
    INFERS = "infers"
    SUPPORTS = "supports"
    REFUTES = "refutes"
    RELATES_TO = "relates_to"
    CITES = "cites"


#: 완성도를 세는 7칸. 순서가 곧 인터뷰가 채워가는 순서다.
SLOTS = ("situation", "cues", "judgment", "action", "rationale", "exceptions", "failure")


@dataclass
class Card:
    id: str
    expert: str
    title: str
    domain: str = ""

    situation: str = ""                              # 언제/어디서 (트리거)
    cues: list[str] = field(default_factory=list)    # ★ 무엇을 보고 아는가
    judgment: str = ""                               # 그래서 무슨 판단
    action: list[str] = field(default_factory=list)  # 무엇을 하는가 (순서)
    rationale: str = ""                              # 왜 (원리)
    exceptions: list[str] = field(default_factory=list)  # ★ 안 통하는 경우
    failure: str = ""                                # 실제로 틀렸던 사례

    #: 말로 담기지 않은 것. **지우지 않고 남긴다** — 도제 항목으로 이관된다.
    unspeakable: list[str] = field(default_factory=list)

    status: CardStatus = CardStatus.DRAFT
    tacitness: Tacitness = Tacitness.PARTIAL
    visibility: Visibility = Visibility.PUBLIC
    #: TARGETED 일 때 수신인, SEALED 일 때 개봉일
    for_whom: str = ""
    open_at: date | None = None

    risk: str = "mid"           # high | mid | low — 이 지식이 없을 때의 손실
    instrument: str = ""        # 어느 연장으로 팠는가 (self-excavation)
    source_turn: str = ""       # 원본 발화 (절대 삭제 안 함)
    citations: int = 0          # 분신이 인용한 횟수
    helped: int = 0             # "도움됐다" 보고
    missed: int = 0             # "안 맞았다" 보고

    # ------------------------------------------------------------------ 판정

    @property
    def filled(self) -> tuple[str, ...]:
        values = {
            "situation": self.situation,
            "cues": self.cues,
            "judgment": self.judgment,
            "action": self.action,
            "rationale": self.rationale,
            "exceptions": self.exceptions,
            "failure": self.failure,
        }
        return tuple(s for s in SLOTS if values[s])

    @property
    def missing(self) -> tuple[str, ...]:
        return tuple(s for s in SLOTS if s not in self.filled)

    @property
    def completeness(self) -> float:
        return len(self.filled) / len(SLOTS)

    def citable(self, *, floor: float = 0.6) -> bool:
        """분신이 이 카드로 답해도 되는가.

        두 개의 하드 게이트가 있다:

        1. **``cues`` 가 비면 완성도와 무관하게 인용 불가.** 신호 없는 카드는
           "그때그때 다르다" 와 같은 말이라 후배가 적용할 수 없다.
        2. 초안(draft)·잠복(dormant)은 인용하지 않는다. 논쟁 중(contested)인
           카드는 **인용하되 논쟁 표시와 함께** 나간다 — 숨기는 게 더 위험하다.
        """
        if self.status in (CardStatus.DRAFT, CardStatus.DORMANT):
            return False
        if not self.cues:
            return False
        # 판단이 없는 카드는 답이 될 수 없다 — 신호만으로는 "그래서?" 가 없다.
        if not self.judgment:
            return False
        # 수치 완성도 문턱은 두지 않는다. 전문가 승인이 품질 권위인데
        # (설계 원칙: 전문가가 고친 것이 기계보다 우선) 완성도 0.6 문턱이
        # 그 위에 앉아, 일찍 승인한 카드를 분신이 영영 못 쓰게 만들었다
        # (프로덕션 스팟 워크 실측 — 4턴 승인 카드 0.57 → 조용히 비인용).
        return True

    def visible_to(self, viewer: str, *, today: date | None = None) -> bool:
        """통제권의 구현. 전문가 본인은 언제나 자기 카드를 본다."""
        if viewer and viewer == self.expert:
            return True
        if self.visibility is Visibility.PUBLIC:
            return True
        if self.visibility is Visibility.PRIVATE:
            return False
        if self.visibility is Visibility.TARGETED:
            return bool(viewer) and viewer == self.for_whom
        # SEALED — 지정일이 오면 열린다
        if self.open_at is None:
            return False
        return (today or date.today()) >= self.open_at

    def anchor_verdict(self, *, min_reports: int) -> CardStatus:
        """적용 보고(닻)만으로 상태를 정한다 — 조회수·좋아요 같은 대리변수 금지.

        ✔ 배지의 출처는 전문가의 권위가 아니라 **후배의 실측**이다.
        """
        if self.missed:
            return CardStatus.CONTESTED
        if self.helped >= min_reports:
            return CardStatus.ANCHORED
        return CardStatus.CONFIRMED if self.status is not CardStatus.DRAFT else CardStatus.DRAFT

    # ------------------------------------------------------------- 포맷 호환

    def to_pic(self) -> dict:
        """P→I→C 그래프로 투영 — H2A2H2 / coral 온톨로지에 그대로 부을 수 있게.

        대응표는 ``docs/reuse-map.md``. 이 레포는 승계 도구(입구)이고
        온톨로지 쪽이 저수지라, 포맷을 맞춰두는 것이 전략이다.
        """
        nodes: list[dict] = []
        edges: list[dict] = []

        def node(ref: str, type: NodeType, title: str, content: str = "") -> str:
            nodes.append(
                {
                    "id": f"{self.id}:{ref}",
                    "type": type.value,
                    "title": title[:200],
                    "content": content,
                    "author": self.expert,
                }
            )
            return f"{self.id}:{ref}"

        def edge(src: str, dst: str, type: EdgeType) -> None:
            edges.append({"source": src, "target": dst, "type": type.value})

        premises: list[str] = []
        if self.situation:
            premises.append(node("sit", NodeType.PREMISE, self.situation))
        for i, cue in enumerate(self.cues):
            premises.append(node(f"cue{i}", NodeType.PREMISE, cue))

        inference = node(
            "judg", NodeType.INFERENCE, self.judgment or self.title, self.rationale
        )
        for p in premises:
            edge(p, inference, EdgeType.INFERS)

        conclusion = node(
            "act", NodeType.CONCLUSION, self.title, "\n".join(self.action)
        )
        edge(inference, conclusion, EdgeType.INFERS)

        # 예외는 판단을 반박하는 전제, 실패담은 결론을 반박하는 증거.
        for i, exc in enumerate(self.exceptions):
            edge(node(f"exc{i}", NodeType.PREMISE, exc), inference, EdgeType.REFUTES)
        if self.failure:
            edge(
                node("fail", NodeType.EVIDENCE, self.failure[:200], self.failure),
                conclusion,
                EdgeType.REFUTES,
            )
        if self.domain:
            edge(node("dom", NodeType.CONCEPT, self.domain), conclusion, EdgeType.RELATES_TO)

        return {"nodes": nodes, "edges": edges}


def next_slot(card: Card) -> str | None:
    """다음에 채워야 할 칸. 인터뷰어가 다음 질문을 고르는 근거."""
    for slot in SLOTS:
        if slot not in card.filled:
            return slot
    return None
