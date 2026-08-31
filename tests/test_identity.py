"""신원 해석 — 표기 변형이 사람을 가르지 않는다 (심사 QA P0).

'Judge PM Tacit 053' 으로 만든 계정에 'Judge-PM-Tacit-053' 으로 들어가면
**같은 사람**이어야 한다. 권한 판정은 언제나 해석된 정본 id 의 정확 비교이고,
정규화 문자열 자체를 권한 키로 쓰지 않는다: 두 전문가가 겹치면 해석을 포기한다.
"""

from __future__ import annotations

from app.store import service


def test_name_variants_resolve_to_one_actor(session):
    service.ensure_expert(session, "Judge PM Tacit 053",
                          display_name="Judge PM Tacit 053")
    for variant in ("Judge-PM-Tacit-053", "judge pm tacit 053",
                    "Judge_PM_Tacit_053", "Judge PM Tacit 053"):
        assert service.resolve_expert_id(session, variant) == "Judge PM Tacit 053"


def test_owner_sees_own_private_card_via_hyphen_variant(session):
    expert = "Judge PM Tacit 053"
    service.ensure_expert(session, expert, display_name=expert)
    started = service.start_session(session, expert, lang="en")
    service.answer_turn(
        session, started["turn_id"],
        "When the retry queue doubles I stop the rollout, because a doubled "
        "queue means the canary is masking timeouts.", lang="en",
    )
    from app.store import db as _db
    card_id = session.get(_db.Session, started["session_id"]).card_id
    service.confirm_card(
        session, card_id, visibility="private", lang="en",
        edits={"title": "Doubled retry queue means a masking canary",
               "cues": ["retry queue depth doubled"],
               "judgment": "stop the rollout"},
    )

    viewer = service.resolve_expert_id(session, "Judge-PM-Tacit-053")
    from app.store.service import cards_of
    cards = [c for c in cards_of(session, expert)
             if viewer == expert or c.visible_to(viewer)]
    assert cards, "하이픈 표기의 본인이 자기 비공개 카드를 못 보면 QA P0 재발"


def test_ambiguous_variants_are_not_merged(session):
    # 두 명이 정규화상 겹치면 해석하지 않는다 — 정규화는 권한 키가 아니다.
    service.ensure_expert(session, "john-doe", display_name="john-doe")
    service.ensure_expert(session, "John Doe", display_name="John Doe")
    assert service.resolve_expert_id(session, "john_doe") == "john_doe"
    # 정확 일치는 언제나 그 사람 자신이다.
    assert service.resolve_expert_id(session, "john-doe") == "john-doe"
    assert service.resolve_expert_id(session, "John Doe") == "John Doe"
