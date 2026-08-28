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

    # 화면은 영어로 뜬다 (규정 6조의 통과 조건). 그러나 **바퀴는 언어를 탄다** —
    # 한국어로 판 카드는 한국어 질문에만 걸린다. 이건 결함이 아니라 결정이다:
    # 찾아 줘도 못 읽는 카드는 답이 아니고, 번역하면 지식이 아니라 요약이 된다
    # (docs/design.md §7). 영어 심사자에게는 영어로 판 Dale 이 따로 있다.
    english = service.ask_alter(
        session, "hong", "flow marks on one side only", asker="lee", lang="en"
    )
    assert english["persona"] == "홍길동 수석's alter", "분신 표시는 화면 언어를 따른다"
    assert english["is_gap"] is True, (
        "한국어 카드가 영어 질문에 걸렸다 — 후배가 읽지 못할 답을 낸 것이다"
    )


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
    # 문안 자체가 아니라 **수치가 문장에 실려 나오는지** 를 본다. 문구는 다듬을
    # 수 있어야 하고, 다듬을 때마다 테스트가 깨지면 문구를 안 다듬게 된다.
    headline = en["legacy"]["headline"]
    assert "1" in headline and "judgment" in headline


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


def test_language_wall_is_not_reported_as_an_empty_area(session):
    """**"안 남겼다" 와 "다른 언어로 남겼다" 는 다른 말이다.**

    카드가 있는데도 언어가 달라 못 걸린 것을 "남기지 않은 영역" 이라고 하면,
    설계 결정(카드는 파낸 언어로 산다 — docs/design.md §7)이 제품 결함으로
    읽힌다. 영어 심사자가 한국어로 판 전문가를 눌렀을 때 정확히 이 화면을 본다.
    """
    _leave_a_judgment(session)                      # hong 은 한국어로 판다
    service.ensure_expert(session, "dale", display_name="Dale", lang="en")

    reply = service.ask_alter(
        session, "hong", "flow marks on one side only", asker="judge", lang="en"
    )

    assert reply["is_gap"] is True
    assert "did not" not in reply["text"], "카드가 있는데 '안 남겼다' 고 말했다"
    assert "Korean" in reply["text"], "어느 언어로 남겼는지 말해주지 않았다"
    assert "Dale" in reply["text"], "같은 언어로 판 사람을 안내하지 않았다"


def test_a_truly_empty_area_still_says_so(session):
    """언어가 같은데 정말 안 남긴 것은 그대로 "안 남겼다" 여야 한다.

    언어 경계 문안이 진짜 공백까지 삼켜버리면, 모른다고 말하는 기능이 죽는다.
    """
    _leave_a_judgment(session)

    reply = service.ask_alter(
        session, "hong", "연차 정산은 어떻게 하나요", asker="kim", lang="ko"
    )

    assert reply["is_gap"] is True
    assert "남기지 않은 영역" in reply["text"]
    assert "남기셨습니다" not in reply["text"], "진짜 공백을 언어 문제로 덮었다"


def test_the_alter_never_points_at_someone_you_cannot_read(session):
    """대안 전문가는 **묻는 사람의 언어로 판 사람**만 세운다.

    못 읽을 사람을 권하는 것은 막다른 길을 하나 더 놓는 것이다.
    """
    _leave_a_judgment(session)
    service.ensure_expert(session, "kimko", display_name="김책임", lang="ko")

    reply = service.ask_alter(
        session, "hong", "how do I file annual leave", asker="judge", lang="en"
    )

    assert "김책임" not in reply["text"], "영어 사용자에게 한국어로 판 사람을 권했다"


def test_a_targeted_card_answers_only_the_named_junior(session):
    """지목 공개 — "이건 김대리한테만" 이 화면에서도 지켜지는가.

    통제권은 첫 화면이 **약속**하는 것이고, 여기가 그 약속이 **지켜지는** 자리다.
    지켜지지 않으면 전문가는 가장 값진 판단을 남기지 않는다.
    """
    from app.core.card import Visibility

    card_id, _ = _leave_a_judgment(
        session, visibility=Visibility.TARGETED.value, for_whom="kim"
    )

    named = service.ask_alter(
        session, "hong", "플로우마크가 한쪽만 나와요", asker="kim", lang="ko"
    )
    assert card_id in [c["id"] for c in named["cards"]], "지목된 사람이 못 받았다"

    other = service.ask_alter(
        session, "hong", "플로우마크가 한쪽만 나와요", asker="park", lang="ko"
    )
    assert other["is_gap"] is True, "지목 안 된 사람에게 새어 나갔다"


def test_usage_statement_counts_only_what_the_ledger_counts(session):
    """명세서는 원장이 세는 것만 센다 — 인용·도움됨·검증, 그리고 안 맞음.

    조회수·좋아요 같은 대리변수가 어디에도 없어서 이 숫자가 그대로 정산
    근거가 된다 (roadmap 거버넌스 6항). "안 맞음" 을 숨기지 않는 것도 규약이다
    — 정직한 청구서가 협상에 더 세다.
    """
    card_id, _ = _leave_a_judgment(session)
    service.ask_alter(session, "hong", "플로우마크가 한쪽만 나와요", asker="kim")
    service.report_anchor(session, card_id, "helped", reporter="kim")
    service.report_anchor(session, card_id, "missed", reporter="lee",
                          detail="재생재 라인이었다")

    stmt = service.usage_statement(session, "hong", lang="ko")

    assert stmt["totals"]["cited"] >= 1
    assert stmt["totals"]["helped"] == 1
    assert stmt["totals"]["missed"] == 1, "'안 맞음' 이 청구서에서 사라졌다"
    row = next(c for c in stmt["cards"] if c["card_id"] == card_id)
    assert row["title"], "카드 제목 없이 숫자만 있으면 검증할 수 없는 청구서다"
    assert "rate" not in stmt and "amount" not in stmt, (
        "단가·금액이 제품에 들어왔다 — 그건 인사 정책이다"
    )


def test_the_preview_never_touches_the_ledger(session):
    """장면 2(분신 시연)는 원장에 기록되지 않는다.

    본인 확인용 시연이 인용·질문 수에 잡히면 보람의 회계도 사용 명세서도
    거짓이 된다 — 명세서를 정산 근거로 쓰겠다는 주장이 여기서 무너진다.
    """
    from sqlalchemy import func, select

    card_id, _ = _leave_a_judgment(session)
    before = session.scalar(select(func.count()).select_from(
        __import__("app.store.db", fromlist=["db"]).LedgerRow))

    preview = service.alter_preview(session, card_id, lang="ko")

    after = session.scalar(select(func.count()).select_from(
        __import__("app.store.db", fromlist=["db"]).LedgerRow))
    assert after == before, "시연이 원장에 기록됐다 — 명세서가 오염된다"
    assert preview["reply"]["is_gap"] is False, "방금 남긴 카드로 답하지 못했다"
    assert card_id in [c["id"] for c in preview["reply"]["cards"]]


def test_a_document_is_organized_by_what_it_does_not_say(session):
    """문서함의 정리 축은 내용이 아니라 **채움 진행도**다.

    문서에서 나온 질문이 카드로 채워지면 그 문서의 진행도가 오른다 —
    문서는 보관되는 게 아니라 발굴 지도로 산다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    result = service.interrogate_document(
        session, "hong", "사출 성형 초도 양산 절차서\n1. 예열 30분.", lang="ko"
    )
    doc_id = result["doc_id"]
    # stub 은 질문을 못 뽑으므로 문서발 질문을 직접 심는다 — 여기서 보는 것은
    # 추출 품질이 아니라 **질문→카드 연결이 진행도로 돌아오는가** 다.
    service._record_gap(session, "hong", "플로우마크가 한쪽만 나오면 어떻게 하나요?",
                        asker="📄", source_doc=doc_id)
    session.commit()

    shelf = service.my_documents(session, "hong", lang="ko")
    row = next(d for d in shelf["documents"] if d["id"] == doc_id)
    assert row["questions"] == 1 and row["filled"] == 0

    _leave_a_judgment(session)   # 그 질문에 맞는 판단을 남긴다

    shelf = service.my_documents(session, "hong", lang="ko")
    row = next(d for d in shelf["documents"] if d["id"] == doc_id)
    assert row["filled"] == 1, "카드가 채워졌는데 문서 진행도가 안 올랐다"

    detail = service.document_detail(session, doc_id, lang="ko")
    assert detail["questions"][0]["card_title"], "채운 카드로 연결이 없다"
