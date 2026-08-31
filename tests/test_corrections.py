"""정정은 신호가 되지 않는다 (심사 QA P0).

"그런 감각 신호는 없었다. 기록하지 마라" 는 발화가
① 신호 칸에 저장되지 않고 ② 같은 감각 질문의 재등장을 만들지 않아야 한다.
"""

from __future__ import annotations

from app.capture import interview
from app.store import service


def test_qa_sentences_never_become_cues():
    for line in (
        "There was no sound, smell, or visual clue before I saw the bumper.",
        "Do not record one.",
        "None of those sensory channels was reliable here.",
        "그런 감각 신호는 없었습니다. 기록하지 마세요.",
    ):
        assert interview.not_cue_material(line), line
    # 진짜 신호는 통과한다
    assert not interview.not_cue_material(
        "warranty claims cluster on one supplier's lot numbers")


def test_sense_negation_pivots_instead_of_reasking(session):
    service.ensure_expert(session, "qa-fix", display_name="qa-fix")
    started = service.start_session(session, "qa-fix", lang="en")
    r1 = service.answer_turn(
        session, started["turn_id"],
        "I catch a bad supplier lot from the relational data, not the part itself.",
        lang="en")
    # 신호 칸을 겨냥한 턴에서 감각 부재를 선언한다
    r = r1
    for _ in range(6):
        if r.get("targets") == "cues" or r.get("rung") in ("sense", "probe"):
            break
        r = service.answer_turn(
            session, r["turn_id"],
            "The warranty claim rate doubled for one lot code.", lang="en")
        if not r.get("turn_id"):
            break
    r2 = service.answer_turn(
        session, r["turn_id"],
        "There was no sound, smell, or visual clue. Do not record one. "
        "It was a relational data signal.", lang="en")
    # ① 재질문 금지 — 감각 채널 분해 질문이 다시 나오면 안 된다
    assert r2["rung"] != "sense"
    for token in ("eye, ear, hand", "눈·귀·손"):
        assert token not in r2["question"]
    # ② 카드 신호 칸에 정정문이 없다
    cues = (r2.get("card") or {}).get("cues") or []
    joined = " ".join(cues).lower()
    assert "do not record" not in joined
    assert "no sound" not in joined


def test_confirm_scrubs_correction_lines(session):
    service.ensure_expert(session, "qa-fix2", display_name="qa-fix2")
    started = service.start_session(session, "qa-fix2", lang="en")
    service.answer_turn(
        session, started["turn_id"],
        "One supplier lot doubled the warranty claims.", lang="en")
    from app.store import db as _db
    card_id = session.get(_db.Session, started["session_id"]).card_id
    result = service.confirm_card(
        session, card_id, lang="en",
        edits={"title": "Lot-clustered warranty claims mean a supplier defect",
               "cues": ["warranty claims cluster on one lot code",
                        "Do not record one.",
                        "There was no sound, smell, or visual clue"],
               "judgment": "quarantine the lot"})
    cues = result["card"]["cues"]
    assert cues == ["warranty claims cluster on one lot code"]


def test_identity_seeking_questions_are_demoted():
    """이름·신원·사번을 묻는 생성 질문은 규칙 기반으로 강등된다 (심사 QA #1).

    화면이 "실명은 필요 없습니다" 라고 약속하는데 질문이 이름을 물으면 모순이다.
    """
    from app.capture.interview import asks_identity
    assert asks_identity(
        "Who was the shipping clerk you worked with during that outage?")
    assert asks_identity("그 담당자 이름이 무엇입니까?")
    assert asks_identity("What is his name and employee number?")
    # 역할·절차 질문은 통과
    assert not asks_identity(
        "What role did the shipping clerk play in verifying the count?")
    assert not asks_identity("Who signs off the final release checklist?")
