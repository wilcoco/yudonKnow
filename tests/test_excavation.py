"""발굴만으로 카드가 채워지는가 — 기저 없이도.

이 파일이 막는 회귀는 실제로 있었던 것이다. ``_fallback`` 이 **첫 답만**
``situation`` 에 넣고 나머지 칸을 하드코딩으로 비워두던 시절, 발굴을 몇 턴을
돌리든 카드는 자라지 않았다. ``cues`` 가 영원히 비니 질문 생성기는 같은 질문을
반복했고, 신호 없는 카드는 인용 불가라 **한 바퀴가 시작점에서 끊겼다.**

테스트 전부가 통과하는데도 그랬다. ``test_one_wheel`` 의 헬퍼가 인터뷰를 한 턴만
돌리고 나머지 칸은 ``confirm_card(edits=...)`` 로 주입했기 때문이다. 화면에는
그 주입 경로가 없다. 그래서 여기서는 **주입 없이** 발굴만으로 판다.
"""

from __future__ import annotations

from app.store import db, service

#: (답, 그 답이 들어가야 할 칸). 질문 순서는 사다리가 정하므로 답만 넣는다.
_DIG = [
    "신규 금형 초도 양산인데 게이트 반대편에만 물결무늬가 떴다",
    "사출 압력 그래프 초기 피크가 느슨하다. 금형 온도계는 정상이라 다들 속는다",
    "온도 문제가 아니라 초기 사출 속도가 모자란 거다",
    "1단 속도 8퍼센트 올리고 30샷 관찰한다. 안 잡히면 게이트 단면 확인",
    "온도가 원인이면 전면에 고르게 나온다. 한쪽만이면 흐름 선단 문제다",
    "재생재 비율 30퍼센트 넘으면 안 통한다. 겨울철 첫 가동 2시간도 예외다",
    "2019년에 속도만 올리다 게이트 마모를 놓쳐 금형 수리 2주 걸렸다",
]


def _dig(session, expert="hong", lang="ko"):
    """전문가가 **연장만 써서** 판다. 칸을 손으로 채워 넣지 않는다."""
    service.ensure_expert(session, expert, display_name="홍길동 수석", lang=lang)
    started = service.start_session(session, expert, instrument="moment", lang=lang)
    turn_id = started["turn_id"]
    for answer in _DIG:
        result = service.answer_turn(session, turn_id, answer, lang=lang)
        turn_id = result["turn_id"]
    card_id = session.get(db.Session, started["session_id"]).card_id
    return card_id, result


def test_excavation_fills_the_card_without_a_base(session):
    """기저가 없어도 발굴이 카드를 채운다 — 답을 그 답을 끌어낸 칸에 넣어서.

    지어내는 게 아니다. 전문가가 실제로 한 말만 들어간다.
    """
    card_id, _ = _dig(session)
    card = service.row_to_card(session.get(db.CardRow, card_id))

    assert card.situation, "상황이 비었다"
    assert card.cues, "신호가 비었다 — 이러면 이 카드는 영원히 인용 불가다"
    assert card.judgment, "판단이 비었다"
    assert card.action, "조치가 비었다"

    # 넣은 것은 전문가가 한 말뿐이어야 한다.
    said = " ".join(_DIG)
    for cue in card.cues:
        assert cue.strip(" .") in said, f"전문가가 하지 않은 말이 신호에 들어갔다: {cue}"


def test_every_answer_moves_the_card(session):
    """턴을 돌릴 때마다 카드가 **자란다.**

    completeness 가 제자리면 그 턴의 답은 어디에도 안 들어간 것이다. 예전 버그가
    정확히 이 모양이었고, 화면에서는 같은 질문이 반복되는 것으로 보였다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    started = service.start_session(session, "hong", instrument="moment", lang="ko")
    turn_id, seen = started["turn_id"], -1.0

    for answer in _DIG[:4]:
        result = service.answer_turn(session, turn_id, answer, lang="ko")
        turn_id = result["turn_id"]
        now = result["card"]["completeness"]
        assert now > seen, f"답을 넣었는데 카드가 그대로다 ({now}) — 답이 버려졌다"
        seen = now


def test_the_question_moves_on_once_a_slot_is_filled(session):
    """채운 칸을 다시 묻지 않는다.

    같은 질문이 반복되면 전문가는 두 번째 세션에 오지 않는다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    started = service.start_session(session, "hong", instrument="moment", lang="ko")

    first = service.answer_turn(session, started["turn_id"], _DIG[0], lang="ko")
    second = service.answer_turn(session, first["turn_id"], _DIG[1], lang="ko")

    assert first["question"] != second["question"], "같은 질문을 두 번 물었다"


def test_a_dug_card_becomes_citable_without_hand_editing(session):
    """발굴 → 승인 → 인용. **중간에 손으로 칸을 채우지 않는다.**

    ``test_one_wheel`` 은 ``edits`` 로 칸을 주입해서 이 경로를 건너뛴다.
    화면에는 그 주입구가 없으므로, 여기서 실제 경로를 지킨다.
    """
    card_id, _ = _dig(session)
    service.confirm_card(session, card_id, lang="ko")

    reply = service.ask_alter(
        session, "hong", "플로우마크가 게이트 반대편에만 나오는데요",
        asker="kim", lang="ko",
    )

    assert reply["is_gap"] is False, "발굴로만 만든 카드가 인용되지 않았다"
    assert card_id in [c["id"] for c in reply["cards"]]


def test_a_document_becomes_questions_never_cards(session):
    """📄 절차서 빨간펜 — **문서는 질문이 되지, 카드가 되지 않는다.**

    문서를 카드로 자동 변환하면 신호가 빈 카드가 쏟아지고 제품이 사내 RAG
    챗봇으로 무너진다. 이 선이 무너지면 이 도구가 비판하는 바로 그 물건이 된다.
    stub 은 extract 를 빈 dict 로 떨어뜨리므로 질문 0개가 정상이다 — 여기서
    보는 것은 **개수가 아니라 어떤 경우에도 카드가 생기지 않는다**는 것이다.
    """
    from sqlalchemy import select

    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    before = len(session.scalars(select(db.CardRow)).all())

    result = service.interrogate_document(
        session, "hong", "1. 예열 30분. 2. 불량 시 적절히 조정한다.", lang="ko"
    )

    after = len(session.scalars(select(db.CardRow)).all())
    assert after == before, "문서에서 카드가 만들어졌다 — RAG 챗봇으로 가는 문이다"
    assert "questions" in result and "queued" in result


def test_doc_questions_join_the_same_gap_queue(session):
    """문서발 질문은 새 큐가 아니라 **공백 큐**로 들어간다.

    "다음에 팔 곳" 을 정하는 자리는 하나여야 한다. 큐가 둘이면 우선순위도 둘이다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    service._record_gap(session, "hong", "예열 30분의 근거가 무엇인가요?", asker="📄")
    session.commit()

    home = service.expert_home(session, "hong", lang="ko")
    assert any("예열" in g["question"] for g in home["gaps"]), "공백 큐에 없다"

    started = service.start_session(session, "hong", lang="ko")
    assert started["from_gap"] is True
    assert "절차서" in started["question"], "문서발 질문을 후배 질문처럼 말했다"


def test_a_hedge_is_never_accepted_as_a_cue(session):
    """**"그냥 감으로" 는 신호가 아니다.**

    얼버무림이 `신호` 칸에 들어가면 인용 게이트를 통과하는 쓰레기 카드가 된다.
    후배가 "그때그때 다르다" 를 판단 근거로 받는 것 — 이 도구가 존재하는 이유가
    정확히 그 실패를 막는 것이다. 얼버무림은 도제 항목(unspeakable)으로 간다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    started = service.start_session(session, "hong", instrument="moment", lang="ko")
    r = service.answer_turn(session, started["turn_id"], _DIG[0], lang="ko")
    r = service.answer_turn(
        session, r["turn_id"], "그때그때 다르죠, 그냥 감으로 합니다", lang="ko"
    )

    card = service.row_to_card(
        session.get(db.CardRow, session.get(db.Session, started["session_id"]).card_id)
    )
    assert card.cues == [], "얼버무림이 신호에 들어갔다"
    assert any("감으로" in u for u in card.unspeakable), "도제 항목으로 남지 않았다"


def test_first_hedge_gets_one_deepening_probe_not_the_next_topic(session):
    """얼버무림 1회차: 넘어가지 않고 같은 칸을 **사건 하나**로 다시 판다.

    사람 지식공학자가 절대 넘어가지 않는 자리다 — 일반론은 물려줄 수 없다
    (CDM: 사건 → 신호 → 규칙. docs/elicitation-protocol.md §0).
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    started = service.start_session(session, "hong", instrument="moment", lang="ko")
    r = service.answer_turn(session, started["turn_id"], _DIG[0], lang="ko")
    r = service.answer_turn(
        session, r["turn_id"], "그때그때 다르죠, 그냥 감으로 합니다", lang="ko"
    )

    assert r["rung"] == "deepen", "얼버무림인데 다음 주제로 넘어갔다"
    assert "그날" in r["question"], "사건 하나로 끌어내리는 질문이 아니다"
    assert r["targets"] == "cues", "같은 칸을 다시 파지 않았다"


def test_second_hedge_moves_on_instead_of_forcing_words(session):
    """얼버무림 2회차: 강요하지 않는다.

    억지 언어화는 지어낸 신호를 만든다. 두 번 물어서 안 나오면 그건 정말
    말로 안 되는 것이고, 도제 항목으로 남긴 채 다음 칸으로 간다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    started = service.start_session(session, "hong", instrument="moment", lang="ko")
    r = service.answer_turn(session, started["turn_id"], _DIG[0], lang="ko")
    r = service.answer_turn(session, r["turn_id"], "그냥 감으로 하는 거죠", lang="ko")
    assert r["rung"] == "deepen"
    r = service.answer_turn(session, r["turn_id"], "정말 말로는 못 해요, 보면 알아요", lang="ko")

    assert r["rung"] != "deepen", "말로 안 되는 것을 세 번째 강요했다"
    assert r["targets"] != "cues", "다음 칸으로 넘어가지 않았다"


def test_a_flag_becomes_the_next_question_and_the_card_inherits_its_domain(session):
    """이관 업무(깃발)는 장식이 아니라 **발굴 지도**다.

    "이걸 남겨야 한다" 고 적은 영역에 카드가 없으면, 다음 발굴이 그 영역을
    겨냥한 질문으로 시작하고, 거기서 나온 카드는 그 영역을 물려받는다 —
    그래야 커버리지가 제 영역으로 오른다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    session.add(db.Flag(expert="hong", domain="협력사 품질 사고 초기 대응"))
    session.commit()

    started = service.start_session(session, "hong", lang="ko")
    assert "협력사 품질 사고 초기 대응" in started["question"], "깃발이 질문이 되지 않았다"

    r = service.answer_turn(session, started["turn_id"],
                            "작년에 협력사 도금 불량으로 라인 세웠던 때가 있었다", lang="ko")
    assert r["card"]["domain"] == "협력사 품질 사고 초기 대응", "카드가 영역을 물려받지 않았다"


def test_excavation_lives_in_the_experts_language_not_the_browsers(session):
    """**발굴은 전문가의 언어로 산다.**

    한국 전문가가 영어 브라우저로 팠을 때 카드가 en 으로 저장되면, 그 카드는
    한국 후배의 검색에서 영영 빠진다 — 조용한 데이터 오염이다. 질문도 카드
    언어도 요청 언어가 아니라 전문가의 언어를 따라야 한다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")

    started = service.start_session(session, "hong", instrument="moment", lang="en")
    assert "상황" in started["question"] or "무슨" in started["question"], (
        "한국 전문가에게 영어로 물었다"
    )

    r = service.answer_turn(session, started["turn_id"],
                            "게이트 반대편에만 물결무늬가 떴다", lang="en")
    row = session.get(db.CardRow, r["card"]["id"])
    assert row.lang == "ko", f"카드가 {row.lang} 로 저장됐다 — 한국 후배 검색에서 빠진다"


def test_a_vague_quantity_is_pinned_to_a_number_once(session):
    """"적당히 높으면" 은 후배가 쓸 수 없다 — 경계 슬라이더가 그 자리에서 선다.

    숫자 없는 모호 수치어가 나오면 다음 질문이 "몇부터입니까" 로 짚는다.
    한 번만 — 짚었는데 또 짚으면 취조가 된다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    started = service.start_session(session, "hong", instrument="moment", lang="ko")
    r = service.answer_turn(session, started["turn_id"], _DIG[0], lang="ko")
    r = service.answer_turn(session, r["turn_id"],
                            "압력이 적당히 높으면 그때 세워", lang="ko")
    assert r["rung"] == "pin", "모호 수치어를 짚지 않았다"
    assert "몇부터" in r["question"]

    r = service.answer_turn(session, r["turn_id"], "그냥 적당히 보는 거지", lang="ko")
    assert r["rung"] != "pin", "같은 수를 두 번 뒀다 — 취조가 된다"


def test_a_sensory_answer_gets_the_channel_probe(session):
    """신호를 파는 중 감각이 언급되면 감각 사다리가 그 자리에서 선다."""
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    started = service.start_session(session, "hong", instrument="moment", lang="ko")
    r = service.answer_turn(session, started["turn_id"], _DIG[0], lang="ko")
    r = service.answer_turn(session, r["turn_id"],
                            "그건 소리가 달라. 울림으로 아는 거야", lang="ko")
    assert r["rung"] == "sense", "감각어인데 채널 분해가 서지 않았다"
    assert "채널" in r["question"] or "눈·귀" in r["question"]


def test_overlapping_cues_summon_the_contrast_pair(session):
    """같은 영역, 겹치는 신호의 두 카드 — 대조 짝이 추천 최상단 근처에 선다."""
    from app.capture.instruments import recommend
    from app.core.card import Card, CardStatus

    a = Card(id="ca", expert="h", title="게이트 반대편 플로우마크", domain="사출",
             cues=["게이트 반대편 물결무늬"], judgment="속도", status=CardStatus.CONFIRMED)
    b = Card(id="cb", expert="h", title="게이트 주변 플로우마크", domain="사출",
             cues=["게이트 주변 물결무늬"], judgment="온도", status=CardStatus.CONFIRMED)

    keys = [s.instrument.key for s in recommend([a, b], lang="ko", card_count=9)]
    assert "contrast" in keys, "신호 겹침인데 대조 짝이 서지 않았다"


class _CleanRefiner:
    """정련 LLM 흉내 — 깨끗한 카드를 내며 도제 항목을 빼먹는다."""

    name = "clean"

    def extract(self, prompt, schema):
        return {"title": "플로우마크 판단", "situation": "초도 양산",
                "cues": ["압력 피크 느슨"], "judgment": "속도 문제",
                "action": ["1단 +8%"], "rationale": "", "exceptions": [],
                "failure": "", "unspeakable": [], "risk": "mid"}

    def answer(self, *a, **k):
        return ""

    def transcribe(self, *a, **k):
        return ""


def test_refinement_may_polish_but_never_lose(session):
    """**정련은 다듬을 수 있어도 잃을 수는 없다.**

    얼버무림 규칙이 도제 항목으로 보낸 말("그냥 감으로")은 전문가가 실제로 한
    말이다. 마지막 턴의 LLM 정련이 그것을 빼먹으면 "말한 것은 지워지지
    않는다" 가 카드 층에서 깨진다 — 재현으로 확인된 실제 결함이었다.
    """
    from app.capture import interview

    hist = [("상황?", "게이트 반대편 물결무늬"),
            ("신호?", "그냥 감으로 아는 거야"),
            ("신호?", "압력 피크가 느슨해")]
    slots = [("situation", hist[0][1]), ("cues", hist[1][1]), ("cues", hist[2][1])]

    refined = interview.capture(_CleanRefiner(), hist, lang="ko", slots=slots)

    assert "그냥 감으로 아는 거야" in refined.data["unspeakable"], (
        "정련이 도제 항목을 지웠다"
    )
    assert any("느슨" in c for c in refined.data["cues"]), "규칙 기반 신호가 사라졌다"
    assert refined.data["judgment"] == "속도 문제", "정련의 다듬기는 유지되어야 한다"


def test_the_campaign_follows_the_knowledge_engineers_procedure(session):
    """캠페인 = 사람 지식공학자의 절차: 지도 없으면 지도부터, 있으면 🔴부터.

    ① 단계가 하나도 없으면 오늘의 질문이 과업 지도 인터뷰다 (ACTA 1단계 —
       지도 없이 파는 것은 손전등 없이 갱도에 들어가는 것).
    ② 지도가 그려지면 '감이 필요하다(hard)' 고 표시된 단계가 먼저 온다.
    ③ 공백은 언제나 지도보다 앞선다 — 주제는 현장 수요가 정한다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")

    first = service.peek_next_question(session, "hong", lang="ko")
    assert first["source"] == "map", "지도 없는 첫 손님에게 지도부터 묻지 않았다"
    assert "단계" in first["question"]

    started = service.start_session(session, "hong", instrument="taskmap", lang="ko")
    done = service.answer_turn(
        session, started["turn_id"],
        "입고 검사, 그다음 도장 준비, 도장은 감이 필요하지, 마지막 출하 검사는 "
        "체크리스트대로 하면 돼", lang="ko",
    )
    assert done["map_built"] and done["wrap_up"]
    flags = {f.domain: f.difficulty for f in session.scalars(
        __import__("sqlalchemy").select(db.Flag).where(db.Flag.expert == "hong")
    ).all()}
    assert flags, "지도가 저장되지 않았다"
    assert any(d == "hard" for d in flags.values()), "'감이 필요' 표시가 유실됐다"

    nxt = service.peek_next_question(session, "hong", lang="ko")
    assert nxt["source"] == "flag", "지도를 그렸는데 단계 발굴로 넘어가지 않았다"
    hard_names = [n for n, d in flags.items() if d == "hard"]
    assert any(h[:6] in nxt["question"] for h in hard_names), (
        f"🔴 단계보다 다른 것이 먼저 왔다: {nxt['question'][:40]}"
    )


def test_the_timeline_sweep_sits_between_incident_and_cues(session):
    """CDM 2스윕 — 사건을 확보하면 신호로 점프하지 않고 타임라인부터 편다.

    판단 지점은 타임라인 위에서 드러난다. 사건→신호 직행은 복잡한 사건에서
    구조를 잃는 지름길이었다.
    """
    from app.capture.interview import rungs

    ladder = [r for r, _ in rungs("ko")]
    assert ladder.index("timeline") == ladder.index("recall") + 1
    assert ladder.index("cue") == ladder.index("timeline") + 1


def _dig_titled(session, expert, title_seed, lang="ko"):
    """한 영역에 카드 한 장을 빠르게 남긴다 (검증 세션 시험용)."""
    started = service.start_session(session, expert, instrument="moment", lang=lang)
    t = started["turn_id"]
    for a in [f"{title_seed} 상황이 있었다", f"{title_seed} 신호가 보였다",
              f"{title_seed}는 속도 문제다"]:
        r = service.answer_turn(session, t, a, lang=lang)
        t = r["turn_id"]
    cid = r["card"]["id"]
    service.confirm_card(session, cid, edits={"domain": "도장"}, lang=lang)
    return cid


def test_member_checking_ripens_seals_and_queues(session):
    """영역 검증 세션 — 절차 ⑥(member checking)의 이식.

    ① 한 단계에 카드 3장이 쌓이면 오늘의 질문이 검증으로 익는다.
    ② "됐다" → 봉인되고, 다시 3장이 쌓이기 전엔 재검을 묻지 않는다.
    ③ 빠진 것을 부르면 즉시 다음 발굴 주제가 되고, 그 질문의 프레이밍은
       "후배가 물었다" 가 아니라 "검토에서 스스로 짚으셨죠" 다.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    session.add(db.Flag(expert="hong", domain="도장", difficulty="hard"))
    session.commit()

    for seed in ("얼룩", "흐름", "광택"):
        _dig_titled(session, "hong", seed)

    n = service.peek_next_question(session, "hong", lang="ko")
    assert n["source"] == "review" and n.get("step") == "도장", (
        f"3장이 쌓였는데 검증이 익지 않았다: {n['source']}"
    )

    # "됐다" → 봉인
    started = service.start_session(session, "hong", instrument="review",
                                    step="도장", lang="ko")
    assert "3장" in started["question"] or "카드" in started["question"]
    done = service.answer_turn(session, started["turn_id"], "됐다, 다 있어", lang="ko")
    assert done["review_done"]
    n2 = service.peek_next_question(session, "hong", lang="ko")
    assert n2["source"] != "review", "봉인했는데 또 검토를 물었다"

    # 카드 3장 더 → 다시 익고, 이번엔 빠진 것을 부른다
    for seed in ("기포", "번짐", "말림"):
        _dig_titled(session, "hong", seed)
    n3 = service.peek_next_question(session, "hong", lang="ko")
    assert n3["source"] == "review", "재숙성되지 않았다 — 검증은 주기다"

    started = service.start_session(session, "hong", instrument="review",
                                    step="도장", lang="ko")
    out = service.answer_turn(session, started["turn_id"],
                              "겨울철 첫 가동 때 얼룩은 다른 얘기인데 그게 없네", lang="ko")
    assert out["review_done"]
    nxt = service.peek_next_question(session, "hong", lang="ko")
    assert nxt["source"] == "review" or nxt["source"] == "junior"
    # 검토발 공백이 큐 최상단(공백 취급)이며, 프레이밍이 정직한지
    home = service.expert_home(session, "hong", lang="ko")
    assert any("겨울철" in g["question"] for g in home["gaps"])
    dig = service.start_session(session, "hong", lang="ko")
    assert "검토에서" in dig["question"], f"검토발 프레이밍 아님: {dig['question'][:40]}"


def test_the_expert_can_drill_into_any_step_from_the_map(session):
    """드릴다운 — 나열된 리스크(단계)를 전문가가 직접 짚어 들어간다.

    캠페인은 순서를 추천할 뿐이다. 지도에서 단계를 짚으면 그 단계를 겨냥한
    질문으로 세션이 열리고, 나온 카드는 그 영역으로 귀속된다 —
    운전대는 전문가에게.
    """
    service.ensure_expert(session, "hong", display_name="홍길동 수석", lang="ko")
    for d, diff in (("입고 검사", "mid"), ("도장", "hard"), ("출하", "easy")):
        session.add(db.Flag(expert="hong", domain=d, difficulty=diff))
    session.commit()

    # 캠페인 추천(🔴 도장)과 다른 단계를 본인이 짚는다
    started = service.start_session(session, "hong", step="출하", lang="ko")
    assert "출하" in started["question"], "짚은 단계를 겨냥하지 않았다"
    assert started["domain"] == "출하"

    r = service.answer_turn(session, started["turn_id"],
                            "출하 직전에 라벨이 뒤집혀 나간 적이 있었다", lang="ko")
    assert r["card"]["domain"] == "출하", "드릴다운 카드가 영역을 물려받지 않았다"
