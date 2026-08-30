"""결정론 판정 엔진 — 외부 QA 가 잡은 구멍이 회귀하지 않는 것을 강제한다.

핵심 시나리오 (veTriage 재현 실험 실측): GREEN(완화) 카드에서 신호 하나
("구토 1회")만 '예' 여도 GREEN 이 나오면 안 된다 — 물 유지·정상 반응이
확인되기 전에는. 그리고 모름은 절대 하향의 근거가 되지 않는다.
"""

from app.core.card import Card, CardStatus
from app.core.protocol import NO, UNKNOWN, YES, evaluate, evaluate_card


def green_card(**over):
    base = dict(
        id="g1", expert="vet", title="한 번 토했고 그 외 전부 정상이면 일반 예약",
        domain="문진", situation="전화",
        cues=["구토 1회"],
        judgment="일반 sick 예약",
        rule_all=["물을 마시고 유지한다", "밝고 걷고 정상 반응"],
        rule_none=["무산성 헛구역질", "복부 팽창"],
        rule_priority=1,
        status=CardStatus.CONFIRMED,
    )
    base.update(over)
    return Card(**base)


def red_card(**over):
    base = dict(
        id="r1", expert="vet", title="무산성 헛구역질 + 팽만이면 즉시",
        domain="문진", situation="전화",
        cues=["무산성 헛구역질", "복부 팽창"],
        judgment="의사 즉시 호출 또는 ER",
        rule_all=[], rule_none=[], rule_priority=3,
        status=CardStatus.CONFIRMED,
    )
    base.update(over)
    return Card(**base)


def test_a_single_sign_never_yields_a_reassuring_verdict():
    """QA 실측 구멍: '구토 1회' 하나로 GREEN 이 나왔다 — 이제는 안 된다."""
    v = evaluate_card(green_card(), {"구토 1회": YES})
    assert v.state != "applies", "미확인 조건이 남았는데 완화 판단이 성립했다"
    assert "물을 마시고 유지한다" in v.unknowns


def test_reassuring_verdict_needs_the_whole_gate():
    v = evaluate_card(green_card(), {
        "구토 1회": YES, "물을 마시고 유지한다": YES, "밝고 걷고 정상 반응": YES,
        "무산성 헛구역질": NO, "복부 팽창": NO,
    })
    assert v.state == "applies"


def test_unknown_never_downgrades_it_escalates():
    """트리거 + 반박 없음 + 미확인 → 상향. 모름이 안심의 근거가 될 수 없다."""
    v = evaluate_card(green_card(), {
        "구토 1회": YES, "물을 마시고 유지한다": YES, "밝고 걷고 정상 반응": YES,
        "무산성 헛구역질": UNKNOWN, "복부 팽창": NO,
    })
    assert v.state == "escalate"
    assert "무산성 헛구역질" in v.unknowns


def test_red_beats_green_on_conflict():
    """충돌 사례: 구토 1회 + 헛구역질 + 팽창 — 온화한 카드가 지우지 못한다."""
    answers = {
        "구토 1회": YES, "물을 마시고 유지한다": YES, "밝고 걷고 정상 반응": YES,
        "무산성 헛구역질": YES, "복부 팽창": YES,
    }
    out = evaluate([green_card(), red_card()], answers)
    assert out["top"].card_id == "r1", "RED 가 우선하지 않았다"
    g = next(v for v in out["verdicts"] if v.card_id == "g1")
    assert g.state == "refuted" and "무산성 헛구역질" in g.refuted_by


def test_urgent_card_triggers_on_any_sign():
    v = evaluate_card(red_card(), {"무산성 헛구역질": YES})
    assert v.state == "applies" and v.priority == 3


def test_unruled_card_is_reading_material_not_a_verdict():
    """규칙 없는 카드는 판정 대상이 아니다 — 열람으로만 선다."""
    bare = green_card(rule_all=[], rule_none=[], rule_priority=0)
    assert evaluate_card(bare, {"구토 1회": YES}).state == "untriaged"


def test_no_standing_verdict_leaves_the_gap_open():
    """아무 판정도 못 서면 공백 경로(분신→전문가 큐)가 정답이다."""
    out = evaluate([green_card(), red_card()], {"구토 1회": UNKNOWN})
    assert out["open"] is True


def test_engine_is_deterministic():
    answers = {"구토 1회": YES, "무산성 헛구역질": UNKNOWN}
    a = evaluate([green_card(), red_card()], answers)
    b = evaluate([green_card(), red_card()], answers)
    assert [v.state for v in a["verdicts"]] == [v.state for v in b["verdicts"]]


def test_conflict_check_ignores_domain_walls(session=None):
    """QA 실측 구멍: GREEN 과 RED 가 다른 업무명으로 컴파일되면 충돌 검사가
    무력화됐다. 판정은 업무명과 무관하게 전 카드가 무대다."""
    g = green_card(domain="동물병원 접수 및 트리아지")
    r = red_card(domain="반려동물 응급 접수")
    out = evaluate([g, r], {
        "구토 1회": YES, "물을 마시고 유지한다": YES, "밝고 걷고 정상 반응": YES,
        "무산성 헛구역질": YES, "복부 팽창": YES,
    })
    assert out["top"].card_id == "r1", "업무명이 갈렸다고 RED 가 무대에서 빠졌다"


def test_declining_an_incident_pivots_to_conditions():
    """사례 사양 가드 — 프롬프트 부탁으로 안 됐던 것(QA 2회 실측)을
    결정적으로: '그런 사례는 없다' 다음 질문은 사건 요구가 아니라 조건이다."""
    from app.capture.interview import declined_incident, next_question
    from app.capture.llm import StubLLM

    assert declined_incident("그런 사례는 없습니다")
    assert declined_incident("기억이 없네요, 넘어가죠")
    assert declined_incident("No such case comes to mind, let's move on")
    assert not declined_incident("문제 없이 잘 끝났습니다. 그날은 압력을 먼저 봤고 …"
                                  "그 뒤로 30분을 지켜봤습니다")

    q = next_question(
        StubLLM(), history=[("구체적으로 언제였나요?", "그런 사례는 없습니다")],
        lang="ko",
    )
    assert q.rung == "condition", f"사양 후에도 사건을 요구했다: {q.text[:60]}"
    assert "전부" in q.text and "하나라도" in q.text
