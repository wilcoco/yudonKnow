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


def test_declines_and_meta_refusals_never_become_card_material():
    """QA 실측: "실제 사례는 없습니다" 가 카드 제목으로, "없습니다,
    추론해서 만들지 마세요" 가 신호로 저장됐다. 사양·기계 지시는 카드
    어느 칸에도 들어가지 않는다."""
    from app.capture.interview import _fallback, not_card_material

    assert not_card_material("실제 사례는 없습니다")
    assert not_card_material("없습니다, 추론해서 만들지 마세요")
    assert not_card_material("없습니다")
    assert not not_card_material("압력에는 문제가 없었습니다. 그날은 속도를 먼저 봤습니다")

    draft = _fallback(
        [("구체적 사례가 있었나요?", "실제 사례는 없습니다"),
         ("무엇을 보십니까?", "게이트 반대편 물결무늬를 봅니다")],
        [("cues", "없습니다, 추론해서 만들지 마세요"),
         ("cues", "게이트 반대편 물결무늬")],
    )
    d = draft.data
    assert "없습니다" not in d["title"], f"사양이 제목이 됐다: {d['title']}"
    assert all("추론" not in c for c in d["cues"]), f"기계 지시가 신호가 됐다: {d['cues']}"
    assert any("물결무늬" in c for c in d["cues"]), "정상 신호까지 떨어졌다"


def test_skip_button_also_pivots_to_conditions():
    """스킵 버튼은 history 에 안 실린다 — 그래도 사양이다 (QA 실측:
    넘겨도 같은 단계에서 표현만 바꿔 재질문)."""
    from app.capture.interview import next_question
    from app.capture.llm import StubLLM

    q = next_question(
        StubLLM(), history=[("첫 질문", "정상적인 답변이었다")],
        last_rung="deepen", skipped_last=True, lang="ko",
    )
    assert q.rung == "condition", f"스킵 후에도 방향을 안 틀었다: {q.rung}"
    # 조건 질문마저 스킵하면 같은 질문을 반복하지 않는다
    q2 = next_question(
        StubLLM(), history=[("q", "a")], last_rung="condition",
        skipped_last=True, lang="ko",
    )
    assert q2.rung != "condition", "조건 질문 스킵 후 같은 질문을 반복했다"


def test_all_of_satisfaction_is_itself_a_trigger():
    """QA P0 실측: RED 조건 3개를 all_of 에 넣고 전부 '예' 로 답해도
    "해당 신호 없음" — 옛 신호(cues)만 트리거로 인정했기 때문이다.
    전문가가 all_of 로 정의한 성립 조건의 충족은 그 자체가 트리거다."""
    red = red_card(
        cues=["옛 신호 A", "옛 신호 B"],          # 문진에 안 나올 잡음
        rule_all=["무산성 헛구역질", "복부 팽창", "심한 통증"],
        rule_none=[], rule_priority=10,
    )
    v = evaluate_card(red, {
        "무산성 헛구역질": YES, "복부 팽창": YES, "심한 통증": YES,
    })
    assert v.state == "applies", f"all_of 전부 예인데 {v.state}"
    assert v.priority == 10

    # 충돌: GREEN 도 완전 성립시켜도 우선순위 10 이 이긴다
    out = evaluate([green_card(), red], {
        "구토 1회": YES, "물을 마시고 유지한다": YES, "밝고 걷고 정상 반응": YES,
        "무산성 헛구역질": YES, "복부 팽창": YES, "심한 통증": YES,
    })
    assert out["top"].card_id == "r1" and out["top"].priority == 10


def test_one_urgent_sign_escalates_never_silently_drops():
    """QA P0 실측: RED 의 all_of 조건 하나만 '예' 로 답하자 "성립하는 승인
    판단이 없습니다". 위급 신호 하나는 무대에 올라야 한다 — 전부 확인
    전에는 성립이 아니라 **상향**으로."""
    red = red_card(
        cues=[], rule_all=["무산성 헛구역질", "복부 팽창", "심한 통증"],
        rule_none=[], rule_priority=10,
    )
    out = evaluate([green_card(), red], {"무산성 헛구역질": YES})
    assert out["open"] is False, "위급 신호 하나가 판정 없음으로 사라졌다"
    assert out["top"].card_id == "r1"
    assert out["top"].state == "escalate", "전부 미확인인데 성립으로 나갔다"
    assert set(out["top"].unknowns) == {"복부 팽창", "심한 통증"}

    # 성립의 문은 그대로: 전부 '예' 여야 applies
    v = evaluate_card(red, {"무산성 헛구역질": YES, "복부 팽창": YES,
                            "심한 통증": YES})
    assert v.state == "applies"


def test_canonical_ids_merge_the_same_signal_across_cards():
    """QA P0 실측: 같은 헛구역질이 카드마다 다른 문장이라 별도 문항으로
    서고, 한쪽 '예'/한쪽 '아니오' 모순 입력이 가능했다. `id :: 문구`
    태그가 있으면 같은 ID 는 하나의 질문이고, 답 하나가 전 카드에 적용."""
    green = green_card(rule_none=[
        "dry_heaving :: 반복적으로 토하려 하지만 아무것도 나오지 않음",
        "복부 팽창"])
    red = red_card(cues=[], rule_priority=10, rule_none=[], rule_all=[
        "dry_heaving :: 10~20분 사이 여러 차례 토하려 하지만 아무것도 안 나옴",
        "tight_belly :: 배가 눈에 띄게 불렀거나 단단함"])

    # 답은 canonical ID 로 한 번 — 두 카드가 동시에 반응한다
    out = evaluate([green, red], {"dry_heaving": YES})
    assert out["top"].card_id == "r1" and out["top"].state == "escalate"
    g = next(v for v in out["verdicts"] if v.card_id == "g1")
    assert g.state == "refuted", "같은 신호 '예' 가 GREEN 의 none_of 에 안 닿았다"
    # 표시 라벨은 문구 (ID 노출 아님)
    assert "배가 눈에 띄게" in out["top"].unknowns[0]

    # 문진에는 같은 ID 가 한 번만 선다
    from app.store.service import _triage_signs
    signs = _triage_signs([green, red])
    keys = [x["key"] for x in signs]
    assert keys.count("dry_heaving") == 1


def test_uncovered_exceptions_block_triage_eligibility():
    """QA P0 실측: 카드에 "양조장 정기 세척일 수 있다" 예외가 있는데
    규칙(none_of)에 없으면, 문진이 그것을 못 물어 위급 오판이 된다.
    예외를 다 덮지 못한 카드는 판정 무대에 서지 못한다."""
    from app.core.protocol import triage_eligible, uncovered_exceptions

    leaky = red_card(
        rule_all=["ph_rising :: influent pH climbing past 8.5"],
        rule_none=[], rule_priority=3,
        exceptions=["It may be the brewery's permitted first-Monday caustic clean."],
    )
    assert uncovered_exceptions(leaky), "안 덮인 예외를 못 찾았다"
    assert not triage_eligible(leaky), "예외가 새는 카드가 판정 무대에 섰다"

    sealed = red_card(
        rule_all=["ph_rising :: influent pH climbing past 8.5"],
        rule_none=["brewery_clean :: it is the brewery's permitted first-Monday caustic clean"],
        rule_priority=3,
        exceptions=["It may be the brewery's permitted first-Monday caustic clean."],
    )
    assert triage_eligible(sealed), "예외를 덮었는데도 무대에서 뺐다"
