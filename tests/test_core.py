"""코어 불변식 — 이 파일이 지키는 것들은 설계 결정이지 구현 세부가 아니다."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.alter.persona import Persona, respond
from app.capture.instruments import recommend, unlocked
from app.core.card import Card, CardStatus, Tacitness, Visibility
from app.core.coverage import succession_risk
from app.core.retrieval import retrieve


def make_card(**over) -> Card:
    base = dict(
        id="c1", expert="hong", title="플로우마크가 게이트 반대편에만 생기면",
        domain="사출 성형", situation="신규 금형 초도 양산",
        cues=["게이트 반대편에만 물결무늬", "사출 압력 그래프 초기 피크가 느슨"],
        judgment="금형 온도가 아니라 초기 사출 속도 부족",
        action=["1단 속도 +8%", "30샷 관찰"],
        rationale="온도가 원인이면 전면에 고르게 나온다",
        exceptions=["재생재 30% 초과 시 안 통한다"],
        status=CardStatus.CONFIRMED,
    )
    base.update(over)
    return Card(**base)


# ------------------------------------------------------------- 카드 불변식

def test_card_without_cues_is_never_citable():
    """신호 없는 카드는 '그때그때 다르다' 와 같은 말이라 후배가 못 쓴다.

    완성도가 아무리 높아도 인용 금지. 이건 문턱이 아니라 하드 게이트다.
    """
    card = make_card(cues=[], failure="2019년 게이트 마모를 놓쳤다")
    assert card.completeness >= 0.6
    assert card.citable() is False


def test_draft_and_dormant_are_not_citable():
    assert make_card(status=CardStatus.DRAFT).citable() is False
    assert make_card(status=CardStatus.DORMANT).citable() is False


def test_contested_card_is_still_citable():
    """논쟁 중인 판단을 숨기는 것이 더 위험하다 — 표시한 채 내보낸다."""
    assert make_card(status=CardStatus.CONTESTED).citable() is True


def test_anchor_verdict_comes_from_field_reports_only():
    card = make_card(helped=2)
    assert card.anchor_verdict(min_reports=2) is CardStatus.ANCHORED
    card.missed = 1
    assert card.anchor_verdict(min_reports=2) is CardStatus.CONTESTED


# --------------------------------------------------------------- 통제권

def test_private_card_is_invisible_to_others_but_not_to_the_author():
    card = make_card(visibility=Visibility.PRIVATE)
    assert card.visible_to("hong") is True
    assert card.visible_to("junior") is False


def test_sealed_card_opens_on_the_day_the_expert_chose():
    tomorrow = date.today() + timedelta(days=1)
    card = make_card(visibility=Visibility.SEALED, open_at=tomorrow)
    assert card.visible_to("junior") is False
    assert card.visible_to("junior", today=tomorrow) is True


def test_targeted_card_reaches_only_the_named_successor():
    card = make_card(visibility=Visibility.TARGETED, for_whom="kim")
    assert card.visible_to("kim") is True
    assert card.visible_to("park") is False


def test_retrieval_respects_visibility():
    """비공개 카드가 점수만 올리고 답에 안 쓰이는 상황을 만들지 않는다."""
    card = make_card(visibility=Visibility.PRIVATE)
    assert retrieve([card], "플로우마크가 한쪽만 나와요", viewer="junior").is_gap is True
    assert retrieve([card], "플로우마크가 한쪽만 나와요", viewer="hong").is_gap is False


# ------------------------------------------------- 공백 판정은 LLM 이 안 한다

class ExplodingLLM:
    """호출되면 터진다. 구조가 LLM 을 부르지 않는다는 것을 증명하기 위한 스파이."""

    name = "exploding"

    def answer(self, system, prompt):  # pragma: no cover - 호출되면 실패
        raise AssertionError("공백 판정 경로에서 LLM 이 호출됐다")

    def extract(self, prompt, schema):  # pragma: no cover
        raise AssertionError("공백 판정 경로에서 LLM 이 호출됐다")


def test_gap_decision_never_calls_the_llm():
    """**되돌리지 말 것.**

    LLM 에게 "모르면 모른다고 해" 라고 부탁하는 설계는 실패한다. 확신도가
    바닥 미만이면 LLM 을 호출조차 하지 않고 공백을 반환해야 한다
    (docs/design.md §6 · alter-ai 의 '관문은 LLM 을 호출하지 않는다' 이식).
    """
    persona = Persona(expert="hong", display_name="홍길동 수석")
    for lang, promise in (("en", "I will not make it up"), ("ko", "지어내지 않겠습니다")):
        reply = respond(
            ExplodingLLM(), persona, [make_card()],
            "연차 정산은 어떻게 하나요", days_left=84, lang=lang,
        )
        assert reply.is_gap is True
        assert reply.cards == []
        assert promise in reply.text


def test_stopped_alter_answers_nothing():
    """전문가가 자기 분신을 끌 수 있다 — 남의 결재가 필요 없다."""
    persona = Persona(expert="hong", active=False)
    reply = respond(ExplodingLLM(), persona, [make_card()], "플로우마크가 한쪽만 나와요")
    assert reply.is_gap is True


def test_alter_label_never_impersonates():
    """어느 언어에서도 사람 이름 단독으로 뜨지 않는다.

    영어 지원은 대회 규정 6조의 통과 조건이라 붙인 것이지만, 사칭 금지 규약은
    언어를 타지 않아야 한다 — 번역하면서 규약이 새는 것이 가장 흔한 사고다.
    """
    persona = Persona(expert="hong", display_name="홍길동 수석")
    for lang in ("en", "ko"):
        label = persona.label(lang)
        assert label != "홍길동 수석"
        assert "홍길동 수석" in label
    assert persona.label("ko") == "홍길동 수석의 분신"
    assert persona.label("en") == "홍길동 수석's alter"


# ----------------------------------------------------------------- 도구함

def test_toolbox_starts_with_only_two_instruments():
    """선택지가 많으면 아무것도 고르지 않는다 (self-excavation §5)."""
    keys = {i.key for i in unlocked(0)}
    assert keys == {"moment", "wrong"}
    assert len(unlocked(3)) > 2


def test_recommendation_puts_the_juniors_gap_first():
    """인터뷰 주제는 컨설턴트가 아니라 현장 수요가 정한다."""
    for lang, needle in (("en", "stuck"), ("ko", "후배")):
        suggestions = recommend([make_card()], lang=lang, open_gaps=3, card_count=9)
        assert suggestions[0].instrument.key == "wrong"
        assert needle in suggestions[0].because


def test_recommendation_is_always_explained():
    """근거 없는 추천은 하지 않는다 — 운전대는 전문가에게 있다."""
    for lang in ("en", "ko"):
        for s in recommend([make_card(exceptions=[])], lang=lang, card_count=9):
            assert s.because.strip()


# ---------------------------------------------------------------- 커버리지

def test_coverage_never_claims_completeness():
    """1.0 을 주지 않는 것은 의도다 — '다 캤다' 고 말하지 않기 위해서."""
    cards = [make_card(id=f"c{i}") for i in range(40)]
    risk = succession_risk("hong", cards, days_left=365)
    assert risk.coverage < 1.0


def test_expert_flag_overrides_machine_coverage():
    """기계가 '다 됐다' 고 해도 본인이 아니라면 아닌 것이다."""
    cards = [make_card(id=f"c{i}") for i in range(12)]
    plain = succession_risk("hong", cards, days_left=365).coverage
    flagged = succession_risk("hong", cards, days_left=365, flags={"사출 성형"}).coverage
    assert flagged < plain


def test_risk_rises_as_the_leaving_date_approaches():
    cards = [make_card()]
    assert (
        succession_risk("hong", cards, days_left=10).score
        > succession_risk("hong", cards, days_left=400).score
    )


# ------------------------------------------------------------ 포맷 호환

def test_card_projects_to_pic_graph():
    """coral / H2A2H2 온톨로지에 그대로 부을 수 있어야 한다."""
    graph = make_card(failure="2019년 금형 수리 2주").to_pic()
    types = {n["type"] for n in graph["nodes"]}
    assert {"premise", "inference", "conclusion", "evidence"} <= types
    assert any(e["type"] == "refutes" for e in graph["edges"])


@pytest.mark.parametrize("tacit,emoji", [("speakable", "🟢"), ("partial", "🟡"), ("hands", "🔴")])
def test_tacitness_gauge(tacit, emoji):
    assert Tacitness(tacit).emoji == emoji


# ─────────────────────────────────────────────────────────── 영어 지원

def test_language_negotiation_defaults_to_english():
    """심사자는 아무것도 누르지 않아도 영어를 본다 (대회 규정 6조).

    유돈의 브라우저는 한국어를 먼저 보내므로 한국어로 뜬다 — 같은 규칙 하나로
    둘 다 해결된다.
    """
    from app.i18n import pick

    assert pick(None) == "en"
    assert pick("en-US,en;q=0.9") == "en"
    assert pick("ko-KR,ko;q=0.9,en;q=0.8") == "ko"
    assert pick("fr-FR,fr;q=0.9") == "en"
    assert pick("ko-KR", override="en") == "en"       # ?lang= 이 이긴다
    assert pick("en-US", override="ko") == "ko"
    assert pick("en-US", override="zz") == "en"       # 모르는 값은 무시


def test_every_catalog_key_has_both_languages():
    """한쪽만 채워진 문안은 배포 후에야 드러난다. 여기서 잡는다."""
    from app.i18n import CATALOG, LANGS

    missing = [
        f"{key}.{lang}"
        for key, entry in CATALOG.items()
        for lang in LANGS
        if not entry.get(lang)
    ]
    assert not missing, f"문안이 빠졌다: {missing}"


def test_the_gap_screen_speaks_both_languages():
    """'모른다'를 잘 말하는 것이 이 제품의 기능이다 — 영어에서도 그래야 한다."""
    from app.alter.persona import Persona, gap_message

    persona = Persona(expert="yudon", display_name="Yudon")
    en = gap_message(persona, days_left=84, alternatives=["Park"], lang="en")
    ko = gap_message(persona, days_left=84, alternatives=["Park"], lang="ko")
    assert "will not make it up" in en and "84" in en
    assert "지어내지 않겠습니다" in ko and "84" in ko


def _english_card() -> Card:
    return Card(
        id="d1", expert="dale",
        title="When aeration foam turns from white to chocolate brown",
        domain="wastewater treatment",
        situation="Activated sludge aeration basin, steady influent",
        cues=["Foam goes tan then chocolate brown and stops breaking up",
              "Sludge blanket creeping up while dissolved oxygen holds normal"],
        judgment="Sludge age is too long and filaments are taking over",
        action=["Increase wasting rate about 10%"],
        rationale="An overload makes white billowy foam",
        exceptions=["After heavy rain the same brown appears"],
        status=CardStatus.ANCHORED,
    )


def test_unrelated_english_question_is_always_a_gap():
    """**되돌리지 말 것.**

    데모 시드에서 잡은 실제 버그의 회귀 테스트다. 영어 기능어("the", "about")와
    라틴 문자 부분 일치("rate" ⊂ "calibrate")가 무관한 질문에 확신도를 붙여서,
    분신이 엉뚱한 카드로 자신 있게 답했다.

    후배가 검증할 능력이 없다는 것이 이 제품의 출발 전제이므로, 무관한 질문에
    붙는 확신도는 기능 결함이 아니라 **신뢰 파괴**다.
    """
    card = _english_card()
    for question in (
        "how do I calibrate the new UV bank",
        "what do I do about the UV bank calibration",
        "how do I file my expense report",
        "who should I ask about vacation days",
    ):
        result = retrieve([card], question)
        assert result.is_gap is True, f"무관한 질문에 답했다: {question!r}"
        assert result.confidence == 0.0


def test_a_real_english_question_still_reaches_the_card():
    """정밀도를 올리다 재현율을 죽이면 분신은 아무것도 답하지 못한다."""
    card = _english_card()
    for question in (
        "brown foam on the aeration basin",
        "the foam went brown overnight",
        "sludge blanket is rising",
    ):
        result = retrieve([card], question)
        assert result.is_gap is False, f"답했어야 할 질문을 공백 처리했다: {question!r}"


def test_korean_compound_nouns_still_match_partially():
    """영어 부분 일치를 끈 것이 한국어 복합명사 매칭을 깨뜨리면 안 된다."""
    card = make_card()
    assert retrieve([card], "사출압력 그래프가 이상합니다").is_gap is False
