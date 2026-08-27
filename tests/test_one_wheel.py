"""한 바퀴가 닫히는가 — 이 레포가 증명해야 하는 단 하나.

    전문가가 승인한 판단이 **실제로 후배의 답에 인용되는가.**

인용되지 않으면 이 시스템은 예쁜 인터뷰 녹취록일 뿐이다.
``test_the_wheel_closes`` 가 그 화살표를 직접 검사한다.
"""

from __future__ import annotations

import pytest

from app.core.card import CardStatus
from app.store import service


def _leave_a_judgment(session, expert="hong", lang="ko", **confirm):
    """전문가가 판단 하나를 남기는 최소 경로 (연장: 사다리)."""
    service.ensure_expert(session, expert, display_name="홍길동 수석")
    started = service.start_session(session, expert, lang=lang)
    service.answer_turn(
        session,
        started["turn_id"],
        "신규 금형 초도 양산에서 플로우마크가 게이트 반대편에만 나왔다. "
        "압력 그래프 초기 피크가 느슨한 걸 보고 온도가 아니라 초기 사출 속도 문제로 봤다.",
        lang=lang,
    )
    card_id = session.get(__import__("app.store.db", fromlist=["db"]).Session,
                          started["session_id"]).card_id

    # stub 모드에서는 구조화가 규칙 기반으로 떨어지므로, 전문가가 직접 채운다 —
    # 실제 화면에서도 전문가의 교정이 기계 추출보다 우선한다.
    result = service.confirm_card(
        session,
        card_id,
        edits={
            "title": "플로우마크가 게이트 반대편에만 생기면",
            "domain": "사출 성형",
            "cues": ["게이트 반대편에만 물결무늬", "사출 압력 그래프 초기 피크가 느슨"],
            "judgment": "금형 온도가 아니라 초기 사출 속도 부족",
            "action": ["1단 속도 +8%", "30샷 관찰"],
            "rationale": "온도가 원인이면 전면에 고르게 나온다",
            "exceptions": ["재생재 30% 초과 시 안 통한다"],
        },
        lang=lang,
        **confirm,
    )
    return card_id, result


def test_the_wheel_closes(session):
    """승인된 판단이 후배의 답에 **실제로 인용된다.** 이 화살표가 전부다."""
    card_id, _ = _leave_a_judgment(session)

    reply = service.ask_alter(
        session, "hong", "플로우마크가 한쪽만 나오는데요", asker="kim", lang="ko"
    )

    assert reply["is_gap"] is False
    assert card_id in [c["id"] for c in reply["cards"]], "승인한 판단이 인용되지 않았다"
    assert reply["persona"] == "홍길동 수석의 분신"

    # 같은 카드가 영어 화면에서도 그대로 인용된다 — 영어 지원은 규정 6조의
    # 통과 조건이고, 바퀴는 언어를 타지 않아야 한다.
    english = service.ask_alter(
        session, "hong", "flow marks on one side only", asker="lee", lang="en"
    )
    assert english["persona"] == "홍길동 수석's alter"


def test_unknown_question_becomes_a_gap_in_the_experts_queue(session):
    """분신이 못 답한 것은 버려지지 않고 **전문가의 큐로 돌아간다.**"""
    _leave_a_judgment(session)

    reply = service.ask_alter(session, "hong", "연차 정산은 어떻게 하나요", asker="kim")
    assert reply["is_gap"] is True
    assert reply["cards"] == []

    home = service.expert_home(session, "hong")
    assert home["gaps"], "공백이 전문가 큐에 쌓이지 않았다"
    assert "연차" in home["gaps"][0]["question"]


def test_repeated_gap_raises_its_priority(session):
    """같은 질문이 반복되면 우선순위가 오른다 — 빈도가 곧 수요다."""
    _leave_a_judgment(session)
    for asker in ("kim", "park", "lee"):
        service.ask_alter(session, "hong", "연차 정산은 어떻게 하나요", asker=asker)

    home = service.expert_home(session, "hong")
    assert home["gaps"][0]["count"] == 3
    assert set(home["gaps"][0]["askers"]) == {"kim", "park", "lee"}


def test_field_report_is_the_only_source_of_the_verified_badge(session):
    """✔ 배지는 전문가의 권위가 아니라 후배의 실측에서 나온다."""
    card_id, _ = _leave_a_judgment(session)
    service.ask_alter(session, "hong", "플로우마크가 한쪽만 나와요", asker="kim")

    first = service.report_anchor(session, card_id, "helped", reporter="kim")
    assert first["status"] == CardStatus.CONFIRMED.value      # 1건으로는 아직

    second = service.report_anchor(
        session, card_id, "helped", reporter="park", detail="야간 라인 정지를 막았다"
    )
    assert second["status"] == CardStatus.ANCHORED.value


def test_a_negative_report_contests_the_card_and_reaches_the_expert(session):
    """'안 맞았다' 는 숨기지 않는다. 카드는 논쟁 상태가 되고 전문가 큐에 오른다."""
    card_id, _ = _leave_a_judgment(session)
    service.report_anchor(
        session, card_id, "missed", reporter="kim", detail="재생재 비율이 높은 라인이었다"
    )

    home = service.expert_home(session, "hong")
    assert [c["id"] for c in home["contested"]] == [card_id]


def test_the_ledger_gives_the_expert_something_back(session):
    """보람이 부가 기능이 아니라 엔진이다 — 이게 없으면 3회차에 그만둔다."""
    card_id, _ = _leave_a_judgment(session)
    service.ask_alter(session, "hong", "플로우마크가 한쪽만 나와요", asker="kim")
    service.report_anchor(
        session, card_id, "helped", reporter="kim", detail="야간 라인 정지를 막았다"
    )

    ko = service.expert_home(session, "hong", lang="ko")
    assert ko["legacy"]["citations"] >= 1
    assert ko["legacy"]["askers"] == 1
    assert ko["legacy"]["helped"] == 1
    assert any("도움" in e["sentence"] for e in ko["legacy"]["recent"])

    en = service.expert_home(session, "hong", lang="en")
    assert any("helped" in e["sentence"] for e in en["legacy"]["recent"])
    assert "juniors asked" in en["legacy"]["headline"]


def test_confirm_refuses_a_card_without_cues(session):
    """신호 없는 판단은 남길 수 없다 — 후배가 쓸 수 없기 때문이다."""
    service.ensure_expert(session, "hong", display_name="홍길동 수석")
    started = service.start_session(session, "hong", lang="ko")
    service.answer_turn(
        session, started["turn_id"], "그때그때 상황 봐서 판단한다.", lang="ko"
    )
    from app.store import db

    card_id = session.get(db.Session, started["session_id"]).card_id
    with pytest.raises(service.ServiceError) as exc:
        service.confirm_card(session, card_id, lang="ko")
    assert "신호" in str(exc.value)

    with pytest.raises(service.ServiceError) as exc_en:
        service.confirm_card(session, card_id, lang="en")
    assert "Cues are empty" in str(exc_en.value)


def test_sealed_card_stays_shut_until_the_day_the_expert_chose(session):
    """통제권 — 봉인한 판단은 후배에게 안 나간다. 그래야 깊은 것을 남긴다."""
    from datetime import date, timedelta

    _leave_a_judgment(
        session, visibility="sealed", open_at=date.today() + timedelta(days=30)
    )
    reply = service.ask_alter(session, "hong", "플로우마크가 한쪽만 나와요", asker="kim")
    assert reply["is_gap"] is True


def test_expert_can_stop_their_own_alter(session):
    _leave_a_judgment(session)
    row = service.get_expert(session, "hong")
    row.alter_active = False
    session.commit()

    reply = service.ask_alter(
        session, "hong", "플로우마크가 한쪽만 나와요", asker="kim", lang="ko"
    )
    assert reply["is_gap"] is True
    assert "멈춰" in reply["text"]


def test_export_carries_the_cards_and_the_pic_graph(session):
    """내 카드는 내가 가져간다. 그리고 coral/H2A2H2 로 부을 수 있는 형태로."""
    _leave_a_judgment(session)
    dump = service.export_cards(session, "hong")
    assert dump["cards"]
    assert dump["pic_graph"][0]["nodes"]


def test_filling_a_gap_is_recorded_as_legacy(session):
    """후배가 막혔던 곳을 뚫어준 것 — 전문가가 가장 보람을 느끼는 사건."""
    service.ensure_expert(session, "hong", display_name="홍길동 수석")
    service.ask_alter(
        session, "hong", "플로우마크가 한쪽만 나오는데요", asker="kim", lang="ko"
    )

    _, result = _leave_a_judgment(session)
    assert result["filled_gap"]

    home = service.expert_home(session, "hong", lang="ko")
    assert any("뚫어" in e["sentence"] for e in home["legacy"]["recent"])
