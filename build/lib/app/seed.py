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
    발굴 자체가 아니다."""
    row = db.CardRow(id=service._uid("c"), expert=expert, title=fields["title"])
    session.add(row)
    session.flush()
    card = service.row_to_card(row)
    for key, value in fields.items():
        setattr(card, key, value)
    card.status = CardStatus.CONFIRMED
    card.tacitness = tacit
    card.visibility = Visibility.PUBLIC
    card.instrument = "moment"
    service.write_card(row, card)
    service._log(session, expert, service.legacy.LedgerEvent.CARD_CONFIRMED, card_id=row.id)
    return row.id


def seed(session) -> bool:
    """비어 있을 때만 심는다. 심었으면 True."""
    if session.scalar(select(db.Expert).limit(1)) is not None:
        return False

    today = date.today()

    # ── yudon — 사출 성형 (한국어 원본) ──────────────────────────────
    service.ensure_expert(
        session, "yudon",
        display_name="유돈",
        sayings="그거 온도 아니야, 속도부터 봐\n숫자 보기 전에 물건부터 봐",
        taboos="원인 모른 채 설정값 되돌리지 마라\n야간에 혼자 금형 열지 마라",
        leaving_on=today + timedelta(days=84),
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

    # ── dale — 하수처리장 (English) ──────────────────────────────────
    service.ensure_expert(
        session, "dale",
        display_name="Dale",
        sayings="Look at the tank before you look at the trend line.\n"
                "If it smells wrong it is wrong, go find out why.",
        taboos="Never chase a number you cannot smell or see.\n"
               "Never change two settings in the same shift.",
        leaving_on=today + timedelta(days=31),
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

    session.commit()

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
