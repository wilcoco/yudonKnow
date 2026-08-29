"""발굴 캠페인 — 사람 지식공학자의 **절차**를 지휘한다. 의존성 0.

한 세션 안의 기술(사다리·프로브·되읽기)은 interview.py 가 맡는다. 이 모듈이
맡는 것은 그 위의 층 — 전문 기관에서 지식공학자가 하던 **엔게이지먼트 계획**
이다: 과업 지도를 먼저 그리고, 어려운 단계부터 사건을 채집하고, 지도 대비
어디까지 팠는지로 다음 수를 정한다.

전 과정이 결정적이다. 무엇을 팔지 LLM 이 정하지 않는다 — 우선순위는
현장 수요(공백)와 전문가 본인의 난이도 표시가 정한다.

    Phase 0  과업 지도   단계가 하나도 없으면: 일 전체를 단계로 부르게 한다
    Phase 1  사건 수집   🔴(hard) 단계 중 카드 없는 곳 → 그 단계를 겨냥한 프로브
    Phase 2  타임라인    (세션 안 — interview 의 timeline 단이 수행)
    Phase 3  심화        (세션 안 — 사다리·트리거)
    공백 우선            후배·문서·혼잣말 공백은 언제나 지도보다 앞선다 —
                         인터뷰 주제는 현장 수요가 정한다 (design §3.4)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Move:
    """캠페인의 다음 수."""

    phase: str        # gap | map | step | probe
    step: str = ""    # phase == step 일 때 겨냥하는 단계
    difficulty: str = ""


def next_move(
    *,
    open_gaps: int,
    steps: list[dict],          # [{"domain", "difficulty", "cards": int}]
    total_cards: int,
) -> Move:
    """다음 수 하나. 우선순위가 곧 방법론이다.

    ① 공백 — 현장 수요가 항상 먼저다.
    ② 지도 없음 — 단계가 하나도 없으면 과업 지도부터. 지도 없이 파는 것은
       손전등 없이 갱도에 들어가는 것이다 (ACTA Task Diagram 이 1단계인 이유).
    ③ hard 단계의 빈 곳 — 전문가 본인이 "감이 필요하다" 고 표시한 단계.
    ④ 아무 단계의 빈 곳 → ⑤ 자유 프로브 순환.
    """
    if open_gaps > 0:
        return Move(phase="gap")
    if not steps:
        return Move(phase="map")
    ranked = sorted(
        (s for s in steps if s.get("cards", 0) == 0),
        key=lambda s: {"hard": 0, "mid": 1, "easy": 2, "": 1}.get(
            s.get("difficulty", ""), 1
        ),
    )
    if ranked:
        top = ranked[0]
        return Move(phase="step", step=top["domain"],
                    difficulty=top.get("difficulty", ""))
    return Move(phase="probe")
