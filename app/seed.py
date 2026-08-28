"""데모 시드 — 심사자가 첫 화면에서 바로 만져볼 것이 있어야 한다.

대회 규정 6조는 심사 기간 내내 무료·무제한 접근을 요구한다. 빈 DB 로 배포하면
심사자가 온보딩부터 해야 하고, 그 사이에 4분이 지나간다.

두 사람을 심는다:

* **yudon** — 이 프로젝트가 시작된 실제 사람. 한국 사출 성형 현장. 카드 내용은
  한국어 그대로다 — 그게 "messy, unstructured stream" 의 실물이고, 번역하면
  지식이 아니라 요약이 된다.
* **dale** — 은퇴를 앞둔 하수처리장 운전원. 영어. 같은 기계가 다른 언어·다른
  현장에서도 도는지 심사자가 직접 눌러 확인할 수 있게.

``YDK_SEED=1`` 이면 **DB 가 비었을 때만** 심는다. 기존 데이터는 건드리지 않는다.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select

from app.core.card import CardStatus, Tacitness, Visibility
from app.store import db, service

log = logging.getLogger(__name__)


def _card(session, expert: str, *, lang: str, tacit: Tacitness, **fields) -> str:
    """세션을 거치지 않고 카드를 직접 심는다 — 시드는 발굴 동선의 산출물이지
    발굴 자체가 아니다.

    **이미 있으면 건너뛴다.** 데모 카드를 뒤에 추가해도 기존 배포에 들어가야
    하고, 그렇다고 사용자가 판 것을 지울 수는 없기 때문이다.
    """
    existing = session.scalar(
        select(db.CardRow).where(
            db.CardRow.expert == expert, db.CardRow.title == fields["title"]
        )
    )
    if existing is not None:
        return existing.id
    row = db.CardRow(id=service._uid("c"), expert=expert, title=fields["title"])
    session.add(row)
    session.flush()
    card = service.row_to_card(row)
    for key, value in fields.items():
        if not key.startswith("_"):
            setattr(card, key, value)
    card.status = CardStatus.CONFIRMED
    card.tacitness = tacit
    card.visibility = fields.pop("_visibility", None) or Visibility.PUBLIC
    card.for_whom = fields.pop("_for_whom", "")
    card.open_at = fields.pop("_open_at", None)
    card.instrument = "moment"
    service.write_card(row, card)
    row.lang = lang   # 카드는 파낸 언어로 산다 (docs/design.md §7)
    service._log(session, expert, service.legacy.LedgerEvent.CARD_CONFIRMED, card_id=row.id)
    return row.id


def seed(session) -> bool:
    """데모 상태를 **맞춘다.** 없는 것만 심고, 있는 것은 건드리지 않는다.

    "비었을 때만" 방식이었을 때는 데모 카드를 뒤에 추가해도 이미 떠 있는 배포에
    영원히 반영되지 않았다. 통제권 시연용 카드(봉인·지목)가 정확히 그렇게
    누락됐다. 카드는 제목으로 중복을 막고, 아래 활동(질문·적용 보고)은 한 번만
    심는다 — 매 기동마다 쌓이면 유산 원장 숫자가 거짓이 된다.
    """
    today = date.today()

    # ── yudon — 사출 성형 (한국어 원본) ──────────────────────────────
    service.ensure_expert(
        session, "yudon",
        display_name="유돈",
        sayings="그거 온도 아니야, 속도부터 봐\n숫자 보기 전에 물건부터 봐",
        taboos="원인 모른 채 설정값 되돌리지 마라\n야간에 혼자 금형 열지 마라",
        leaving_on=today + timedelta(days=84),
        lang="ko",
        farewell="김대리, 그리고 뒤에 올 사람들에게.\n\n"
                 "제가 남긴 카드들은 정답이 아닙니다. 제가 그 상황에서 그렇게 "
                 "봤다는 기록일 뿐입니다. 현장이 바뀌면 틀릴 수 있고, 실제로 "
                 "저도 여러 번 틀렸습니다 — 틀렸던 것도 같이 적어뒀습니다.\n\n"
                 "부탁이 하나 있습니다. 카드대로 해보고 안 맞았으면 꼭 "
                 "'안 맞았다'고 눌러주세요. 그게 저한테 돌아옵니다. "
                 "제가 아직 회사에 있는 동안은 제가 고칠 수 있습니다.\n\n"
                 "그리고 '그냥 보면 안다'고 적어둔 것들은 정말 글로는 안 됩니다. "
                 "그건 나가기 전에 옆에서 같이 봅시다. 불러주세요.",
    )
    yudon_card = _card(
        session, "yudon", lang="ko", tacit=Tacitness.HANDS,
        title="플로우마크가 게이트 반대편에만 생기면",
        domain="사출 성형",
        situation="신규 금형 초도 양산 / 사이클 안정화 전",
        cues=["게이트 반대편에만 물결무늬",
              "사출 압력 그래프 초기 피크가 평소보다 느슨",
              "금형 온도계 표시는 정상 — 여기서 대부분 속는다"],
        judgment="금형 온도 문제가 아니라 초기 사출 속도 부족이다",
        action=["1단 속도 +8%", "30샷 관찰", "안 잡히면 게이트 단면 확인"],
        rationale="온도가 원인이면 전면에 고르게 나온다. 한쪽만 = 흐름 선단 문제",
        exceptions=["재생재 비율 30% 넘으면 이 규칙 안 통한다",
                    "겨울철 첫 가동 2시간은 정말 온도 원인일 수 있다"],
        failure="2019년 이 판단으로 속도만 올리다 게이트 마모를 놓쳐 금형 수리 2주",
        unspeakable=["'느슨하다'는 압력 그래프 감각 — 화면 녹화 필요"],
        risk="high",
    )
    _card(
        session, "yudon", lang="ko", tacit=Tacitness.PARTIAL,
        title="협력사 초도품 치수가 튀면 1개만 튀어도 세운다",
        domain="협력사 품질 대응",
        situation="협력사 초도품 입고 검사",
        cues=["초도 로트에서 치수가 공차 상단에 붙어 나옴",
              "협력사 검사성적서는 중앙값만 적혀 있음"],
        judgment="양산 기준(3개 연속)을 초도에 그대로 쓰면 안 된다. 1개면 세운다",
        action=["입고 보류", "협력사에 원자재 로트 번호 요청", "금형 이력 확인"],
        rationale="초도는 공정이 아직 안 잡혀서 분포 자체가 다르다",
        exceptions=["설계 변경 직후 재초도는 2개까지 본다"],
        failure="",
        risk="high",
    )

    # 통제권을 **화면에서 확인할 수 있게** 두 장 더 심는다.
    #
    # 첫 화면은 "봉인·지목·비공개는 당신이 정합니다" 라고 약속한다. 그 약속을
    # 확인할 자리가 없으면 약속은 문구로만 남는다. 아래 두 장이 그 자리다 —
    # 심사자가 "나" 를 바꿔가며 같은 질문을 던지면 답이 달라진다.
    #
    # 내용도 아무거나가 아니다. **가장 값진 판단일수록 오늘 공개하기 곤란하다**
    # 는 것이 통제권의 존재 이유이므로 (docs/self-excavation.md), 딱 그런 것을
    # 심는다.
    _card(
        session, "yudon", lang="ko", tacit=Tacitness.PARTIAL,
        _visibility=Visibility.TARGETED, _for_whom="kim",
        title="야간에 라인 세울지 말지는 누구에게 전화하느냐로 갈린다",
        domain="야간 대응",
        situation="야간 당직 중 판단이 애매한 불량이 나왔을 때",
        cues=["불량률이 애매하게 오르는데 정지 기준에는 안 걸림",
              "생산 일정이 빡빡한 주간"],
        judgment="공식 절차대로 생산팀장부터 찾으면 아침까지 못 세운다. "
                 "품질 쪽에 먼저 알리고 기록을 남긴 다음에 올려야 한다",
        action=["품질 담당에게 먼저 전화", "샘플 3개 확보하고 사진", "그 다음 생산팀장"],
        rationale="기록이 먼저 있으면 아침 회의에서 판단이 뒤집히지 않는다",
        exceptions=["안전 관련이면 순서 무시하고 즉시 정지"],
        failure="",
        risk="high",
    )
    _card(
        session, "yudon", lang="ko", tacit=Tacitness.PARTIAL,
        _visibility=Visibility.SEALED, _open_at=today + timedelta(days=84),
        title="A 협력사 초도품은 담당자가 바뀌기 전까지 그대로 믿지 마라",
        domain="협력사 품질 대응",
        situation="특정 협력사에서 온 초도품 검사",
        cues=["검사성적서 수치가 매번 너무 깨끗함", "재측정하면 값이 다르게 나옴"],
        judgment="성적서를 믿지 말고 우리 게이지로 다시 잰다",
        action=["입고분 전량 자체 재측정", "차이 나면 사진과 함께 기록"],
        rationale="측정 방식이 우리와 다른데 그걸 맞춰본 적이 없다",
        exceptions=["담당자가 바뀌면 다시 판단해야 한다"],
        failure="",
        risk="high",
    )

    # ── dale — 하수처리장 (English) ──────────────────────────────────
    service.ensure_expert(
        session, "dale",
        display_name="Dale",
        sayings="Look at the tank before you look at the trend line.\n"
                "If it smells wrong it is wrong, go find out why.",
        taboos="Never chase a number you cannot smell or see.\n"
               "Never change two settings in the same shift.",
        leaving_on=today + timedelta(days=31),
        lang="en",
        farewell="Rosa, Tom — and whoever comes after.\n\n"
                 "What I left here are not answers. They are notes on how I read "
                 "a plant on a particular day. Plants change. I was wrong more "
                 "than once, and I wrote those down too.\n\n"
                 "One favour. If you try a card and it does not hold, press "
                 "\"it did not\". That comes back to me, and while I am still "
                 "here I can fix it.\n\n"
                 "The ones marked \"you have to be standing there\" — I meant "
                 "that. Come find me before I go and we will look at the tank "
                 "together.",
    )
    dale_card = _card(
        session, "dale", lang="en", tacit=Tacitness.HANDS,
        title="When aeration foam turns from white to chocolate brown",
        domain="wastewater treatment",
        situation="Activated sludge aeration basin, steady influent, no storm event",
        cues=["Foam goes tan then chocolate brown and stops breaking up",
              "Sludge blanket creeping up while dissolved oxygen holds normal",
              "Smell shifts from earthy to wet cardboard — you get this before "
              "the microscope confirms it"],
        judgment="Sludge age is too long and filaments are taking over. This is not "
                 "an organic overload.",
        action=["Increase wasting rate about 10%",
                "Pull a sample and look for Nocardia under the scope",
                "Hold return rate steady — do not chase it with returns"],
        rationale="An overload makes white billowy foam. Brown viscous foam that "
                  "will not break is old sludge, every time.",
        exceptions=["After heavy rain the same brown appears from washed-in road "
                    "grit and clears within a day — do not waste on that",
                    "In the first two weeks after a plant restart the colour means "
                    "nothing yet"],
        failure="In 2014 I read it as an overload and chased it for two weeks. Ended "
                "in a bulking event and a permit violation that cost us the quarter.",
        unspeakable=["The smell difference between earthy and wet cardboard — you "
                     "have to stand at the rail and learn it"],
        risk="high",
    )
    _card(
        session, "dale", lang="en", tacit=Tacitness.SPEAKABLE,
        title="Clarifier weir stringing means the sludge blanket is already high",
        domain="wastewater treatment",
        situation="Secondary clarifier, routine walk-round",
        cues=["Thin strings of solids trailing over the weir",
              "Water still looks clear from the walkway — this is the trap"],
        judgment="Blanket is within a foot of the weir even though the surface looks fine",
        action=["Take a blanket depth reading now, not at end of shift",
                "Raise return rate before you touch wasting"],
        rationale="Clear surface water tells you nothing about depth. Stringing is "
                  "the first visible sign and it is already late.",
        exceptions=["A brand new weir plate sheds strings for the first week and "
                    "means nothing"],
        failure="",
        risk="mid",
    )

    # ── Dale 을 깊게 육성한다 — 심사자가 자기 지식을 넣지 않고도 서가·
    # 문서함·교정·이어파기를 전부 구경할 수 있어야 한다. 심사자는 온보딩을
    # 하지 않는다; 4분 안에 만져지는 것이 전부다.
    _card(
        session, "dale", lang="en", tacit=Tacitness.PARTIAL,
        title="A rising pH at the headworks on a dry morning means an industrial dump",
        domain="wastewater treatment",
        situation="Headworks, dry weather, early shift",
        cues=["Influent pH climbing past 8.5 with no rain in 48 hours",
              "Flow is normal — that is what rules out infiltration",
              "A faint solvent smell at the grit channel before the probe confirms"],
        judgment="Someone upstream is dumping. This is not a sensor drift.",
        action=["Grab a sample bottle now — evidence disappears in an hour",
                "Call the pretreatment coordinator before you adjust anything",
                "Do not neutralise blind; find out what it is first"],
        rationale="Sensor drift moves slowly and both probes never drift together. "
                  "A step change on one parameter with normal flow is a discharge.",
        exceptions=["First Monday of the month the brewery does a permitted "
                    "caustic clean — check the schedule before you call anyone"],
        failure="In 2019 I neutralised first and sampled after. We never identified "
                "the discharger and ate the fine ourselves.",
        risk="high",
    )
    contested_card = _card(
        session, "dale", lang="en", tacit=Tacitness.SPEAKABLE,
        title="If the digester gas flare is pulsing, check the condensate trap first",
        domain="wastewater treatment",
        situation="Anaerobic digester, flare visibly pulsing",
        cues=["Flare flame pulsing in a slow rhythm rather than steady"],
        judgment="Condensate is slugging the gas line — drain the trap before "
                 "touching the pressure settings",
        action=["Drain the condensate trap", "Watch the flare for ten minutes"],
        rationale="Water in the line makes the pressure oscillate at exactly that rhythm.",
        exceptions=[],
        failure="",
        risk="mid",
    )
    # 초안 하나 — "파다 만 판단" 이 서가에서 ⏳ 로 보이고 이어파기가 열린다.
    draft_row = session.scalar(
        select(db.CardRow).where(db.CardRow.expert == "dale",
                                 db.CardRow.title == "Winter foaming is a different animal")
    )
    if draft_row is None:
        draft_sess = db.Session(id=service._uid("s"), expert="dale", instrument="ladder")
        session.add(draft_sess)
        session.flush()
        service.answer_turn  # (참고) 실제 동선과 같은 테이블을 쓴다
        turn1 = db.Turn(id=service._uid("t"), session_id=draft_sess.id,
                        question="Think of one moment in the last six months when this "
                                 "team would have gone badly wrong without you.",
                        rung="recall", targets="situation",
                        answer="Cold snap in January. Foam on the basin but it was not "
                               "the brown kind — different animal in winter.")
        turn2 = db.Turn(id=service._uid("t"), session_id=draft_sess.id,
                        question="What did you see that told you? A screen? A sound? "
                                 "A smell?", rung="cue", targets="cues", answer="")
        session.add_all([turn1, turn2])
        draft_row = db.CardRow(
            id=service._uid("c"), expert="dale",
            title="Winter foaming is a different animal",
        )
        session.add(draft_row)
        session.flush()
        draft_card = service.row_to_card(draft_row)
        draft_card.situation = ("Cold snap in January. Foam on the basin but not the "
                                "brown kind.")
        draft_card.domain = "wastewater treatment"
        service.write_card(draft_row, draft_card)
        draft_row.status = CardStatus.DRAFT.value
        draft_row.lang = "en"
        draft_row.source_turn = draft_sess.id
        draft_sess.card_id = draft_row.id

    # 문서 하나 — 문서함이 "발굴 지도" 로 보이려면 진행도가 중간이어야 한다.
    doc_row = session.scalar(
        select(db.Document).where(db.Document.expert == "dale")
    )
    if doc_row is None:
        doc_row = db.Document(
            id=service._uid("d"), expert="dale",
            title="SOP-12 Aeration Basin Daily Operation",
            domain="wastewater treatment",
            text="SOP-12 Aeration Basin Daily Operation (rev 4)\n"
                 "1. Record dissolved oxygen at 08:00 and 14:00.\n"
                 "2. Maintain DO between 1.5 and 3.0 mg/L.\n"
                 "3. If foam is present, apply defoamer as needed.\n"
                 "4. Report abnormal conditions to the shift supervisor.\n"
                 "5. Waste sludge per the posted schedule.\n",
        )
        session.add(doc_row)
        session.flush()
        # 문서가 말하지 않는 것 4개 — 2개는 이미 카드로 채워진 상태로 심는다.
        service._record_gap(
            session, "dale",
            'The SOP says "apply defoamer as needed" — how do you decide when foam '
            'is a chemistry problem defoamer will not fix? (doc: "apply defoamer as needed")',
            asker="📄", source_doc=doc_row.id)
        service._record_gap(
            session, "dale",
            'What do you check first when DO drifts out of the 1.5–3.0 band while '
            'blowers sound normal? (doc: "Maintain DO between 1.5 and 3.0")',
            asker="📄", source_doc=doc_row.id)
        service._record_gap(
            session, "dale",
            'Which "abnormal conditions" have you learned to report immediately '
            'versus watch for a shift? (doc: "Report abnormal conditions")',
            asker="📄", source_doc=doc_row.id)
        service._record_gap(
            session, "dale",
            'When do you deviate from the posted wasting schedule, and on what '
            'sign? (doc: "Waste sludge per the posted schedule")',
            asker="📄", source_doc=doc_row.id)
        session.flush()
        # 앞의 두 질문은 기존 카드가 답이다 — 진행도 2/4.
        gaps = session.scalars(
            select(db.Gap).where(db.Gap.source_doc == doc_row.id)
            .order_by(db.Gap.created_at)
        ).all()
        gaps[0].filled_card = dale_card
        gaps[1].filled_card = dale_card

    session.commit()

    # 활동은 한 번만 심는다 — 매 기동마다 쌓이면 원장 숫자가 거짓이 된다.
    if session.scalar(select(db.Ask).limit(1)) is not None:
        return True

    # ── 바퀴가 이미 한 바퀴 돈 상태로 심는다 ─────────────────────────
    # 심사자가 빈 원장을 보면 "보람" 이 무슨 말인지 알 수 없다.
    service.ask_alter(session, "yudon", "플로우마크가 한쪽만 나오는데요",
                      asker="kim", lang="ko")
    service.report_anchor(session, yudon_card, "helped", reporter="kim",
                          detail="야간 라인 정지를 막았습니다", lang="ko")
    service.report_anchor(session, yudon_card, "helped", reporter="park",
                          detail="불량률 3.1% → 0.8%", metric="scrap rate",
                          baseline=3.1, observed=0.8, lang="ko")

    service.ask_alter(session, "dale", "the foam went brown overnight, what do I do",
                      asker="rosa", lang="en")
    service.report_anchor(session, dale_card, "helped", reporter="rosa",
                          detail="Caught it before the blanket hit the weir", lang="en")
    # ✔ 배지에는 보고 2건이 필요하다 (YDK_ANCHOR_MIN_REPORTS). 심사자가 배지를
    # 보지 못하면 "검증의 출처는 후배의 실측" 이라는 설계가 화면에서 사라진다.
    service.report_anchor(session, dale_card, "helped", reporter="tom",
                          detail="Wasted 10% and the foam broke up in two days",
                          metric="blanket depth (ft)", baseline=4.2, observed=1.9,
                          lang="en")

    # 답하지 못한 질문 하나 — 공백 큐가 비어 있으면 이 제품의 핵심이 안 보인다.
    service.ask_alter(session, "dale", "how do I calibrate the new UV bank",
                      asker="rosa", lang="en")
    service.ask_alter(session, "dale", "what do I do about the UV bank calibration",
                      asker="tom", lang="en")
    service.ask_alter(session, "yudon", "협력사 도장 불량은 어떻게 잡나요",
                      asker="kim", lang="ko")

    # 교정 흐름이 보이게 — Dale 의 플레어 카드에 "안 맞았다" 보고 하나.
    flare = session.scalar(
        select(db.CardRow).where(
            db.CardRow.expert == "dale",
            db.CardRow.title.like("If the digester gas flare%"))
    )
    if flare is not None:
        service.report_anchor(
            session, flare.id, "missed", reporter="rosa",
            detail="Drained the trap twice — still pulsing. Turned out to be the "
                   "flame arrestor icing up.", lang="en")

    session.commit()
    return True


def seed_if_empty() -> None:
    session = db.SessionLocal()
    try:
        if seed(session):
            log.info("데모 시드 심음 — yudon(ko) · dale(en)")
    except Exception as exc:  # 시드 실패가 기동을 막아서는 안 된다
        log.warning("시드 실패, 빈 상태로 기동: %s", exc)
        session.rollback()
    finally:
        session.close()
