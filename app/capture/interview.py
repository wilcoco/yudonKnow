"""발굴 — 질문 만들기와 카드 뽑기.

두 갈래가 있고, 둘 다 여기서 나온다:

* **사다리 모드** — AI 가 운전한다. 5단 사다리(``docs/elicitation-protocol.md``).
* **연장 모드** — 전문가가 운전한다. 12개 연장(``docs/self-excavation.md``).

LLM 이 없어도 (stub) 질문은 나온다 — 규칙 기반 사다리가 있기 때문이다.
카드 구조화만 규칙 기반으로 떨어진다. **동선이 키에 인질 잡히지 않게.**
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.capture.instruments import BY_KEY, LADDER, slot_label
from app.capture.llm import BaseLLM
from app.core.card import SLOTS, Card, Tacitness

log = logging.getLogger(__name__)

# --------------------------------------------------------------------- 사다리

#: 5단 사다리. 순서가 방법론이다 — 사건 하나에서 시작해 규칙으로 올라간다.
#: 정본: ``docs/elicitation-protocol.md``. 영문은 규정 6조(영어 지원) 대응.
_RUNGS: dict[str, tuple[tuple[str, str], ...]] = {
    "ko": (
        ("recall", "최근 6개월 중, 당신이 없었으면 팀이 크게 잘못됐을 순간을 하나만 떠올려 주세요."),
        ("timeline", "그날을 순서대로 짚어보죠 — 처음 뭔가 이상하다고 느낀 순간부터, "
                     "판단이 갈린 지점까지. 시간순으로 말씀해 주세요."),
        ("cue", "그 판단이 갈린 지점에서 — 무엇을 보고 그렇게 판단하셨나요? 화면? 소리? 냄새? 손끝 느낌?"),
        ("counterfactual", "5년차 후배가 그 상황이었다면 뭘 했을 것 같나요? 그게 왜 틀렸을까요?"),
        ("boundary", "이 판단이 안 통하는 경우가 있나요? 언제 이 규칙을 버리시나요?"),
        ("failure", "이 판단으로 크게 틀렸던 적이 있나요? 그때 무슨 일이 있었나요?"),
    ),
    "en": (
        ("recall", "Think of one moment in the last six months when this team would "
                   "have gone badly wrong without you."),
        ("timeline", "Walk me through that day in order — from the first moment "
                     "something felt off, to the point where the call was made."),
        ("cue", "At that point where the call was made — what did you see? A screen? "
                "A sound? A smell? Something in your hands?"),
        ("counterfactual", "If someone five years in had been standing there, what "
                           "would they have done? Why would that be wrong?"),
        ("boundary", "Is there a case where this judgment does not hold? When do you "
                     "drop the rule?"),
        ("failure", "Has this judgment ever been badly wrong? What happened?"),
    ),
}

#: **입구 질문 — ACTA 지식 감사(Knowledge Audit) 8종.**
#:
#: Militello & Hutton (1998) 의 프로브를 그대로 옮겼다 [문헌 기반]. CDM 의
#: "가장 어려웠던 사건 하나" 는 깊이 파는 데는 최적이지만 **입구로는 좁다** —
#: 그 한 질문에 안 걸리는 지식이 통째로 안 나온다. ACTA 는 입구를 8개로 벌린다.
#:
#: 각 프로브는 **서로 다른 종류의 이야기**를 부른다. 특히 마지막 둘이 이 도구의
#: 핵심 자산이다: 이상 징후(anomalies)와 계기 불일치(equipment)는 절차서에
#: 절대 안 적히는 지식이고, 유돈의 첫 카드가 정확히 후자다 —
#: "금형 온도계는 정상이라 다들 속는다".
_ENTRY_PROBES: dict[str, tuple[tuple[str, str], ...]] = {
    "ko": (
        ("anomalies", "뭔가 이상하다고 느꼈던 순간이 있나요? 남들은 정상이라고 했는데 당신은 아니었던 때."),
        ("equipment", "계기나 수치는 괜찮다고 하는데 당신 판단은 아니었던 적이 있나요?"),
        ("noticing", "당신 눈에만 딱 걸린 게 있었던 적은요? 다들 그냥 지나쳤는데."),
        ("past_future", "상황 중간에 들어갔는데 어쩌다 이렇게 됐고 앞으로 어떻게 될지 바로 아셨던 때가 있나요?"),
        ("job_smarts", "이 일을 남들보다 적은 힘으로 해내는 당신만의 요령이 있나요?"),
        ("self_monitoring", "하던 방식으로는 안 되겠다 싶어 도중에 바꾼 적이 있나요?"),
        ("big_picture", "이 일에서 늘 머릿속에 같이 얹고 가야 하는 것들은 무엇인가요?"),
        ("improvising", "정해진 대로가 아니라 임기응변으로 풀었던 때가 있나요?"),
    ),
    "en": (
        ("anomalies", "Was there a time you knew something was amiss when everyone else said it was fine?"),
        ("equipment", "Have there been times when the instruments said one thing but your judgment said another?"),
        ("noticing", "Has part of a situation ever just popped out at you, when others walked right past it?"),
        ("past_future", "Have you walked into the middle of something and known at once how it got there and where it was headed?"),
        ("job_smarts", "Are there ways of working smart on this — getting more done with less — that you found yourself?"),
        ("self_monitoring", "Was there a time you realised mid-task that you had to change how you were working?"),
        ("big_picture", "What do you always have to keep track of at the same time in this work?"),
        ("improvising", "Can you think of a time you improvised, or saw an opening to do it better?"),
    ),
}


def entry_probe(card_count: int, lang: str = "en") -> tuple[str, str]:
    """오늘의 입구 질문 하나. 같은 질문만 반복하면 같은 종류의 지식만 나온다.

    카드가 쌓인 만큼 다른 프로브를 낸다 — 무작위가 아니라 순환이라, 다음에 무엇을
    물을지 예측 가능하고 재현된다.
    """
    probes = _ENTRY_PROBES.get(lang, _ENTRY_PROBES["en"])
    return probes[card_count % len(probes)]


#: Phase 0 — 과업 지도 인터뷰의 오프너. 전문 지식공학의 1단계(Task Diagram).
TASKMAP_OPENER = {
    "ko": "하시는 일을 처음부터 끝까지, 큰 단계로 불러주세요 — 보통 4~7개쯤 "
          "됩니다. 그리고 그중에 '이건 글로 안 되고 감이 필요하다' 싶은 단계가 "
          "어디인지도요.",
    "en": "Walk me through your job start to finish, in big steps — usually four "
          "to seven. And tell me which of those steps take feel, not paperwork.",
}

_TASKMAP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "difficulty": {"type": "string",
                                   "enum": ["hard", "mid", "easy"]},
                },
                "required": ["name", "difficulty"],
            },
        },
    },
    "required": ["steps"],
}


def extract_task_map(
    llm: BaseLLM, narration: str, *, lang: str = "en", limit: int = 9
) -> list[dict[str, str]]:
    """일의 서사 → 단계 목록(이름+난이도). 지어내지 않는다 — 부른 것만.

    stub 폴백은 줄 단위 분해: 한 줄 = 한 단계, 난이도는 감각·감 어휘가 있으면
    hard. 결정적이라 기저 없이도 지도는 그려진다.
    """
    body = (narration or "").strip()
    if not body:
        return []
    if lang == "ko":
        prompt = ("아래는 전문가가 자기 일을 부른 것이다. **반복되는 직무·판단 "
                  "영역**의 이름과 난이도(hard=감이 필요하다고 한 곳, easy=글로 "
                  "된다고 한 곳, 그 외 mid)를 뽑아라.\n"
                  "주의: 한 사건에서 수행한 조치('로트를 세웠다', '필터를 "
                  "갈았다')는 단계가 아니다 — 그 조치가 속한 **직무 영역**"
                  "('도장 불량 진단', '에어압 관리')으로 이름을 세워라. "
                  "이야기에 없는 영역은 지어내지 마라. "
                  f"최대 {limit}개.\n\n{body}")
    else:
        prompt = ("Below an expert describes their job. Extract the names of "
                  "**recurring duty / judgment areas** and difficulty (hard = "
                  "they said it takes feel, easy = by the book, else mid).\n"
                  "Caution: one-time actions from a story ('stopped the lot', "
                  "'replaced the filter') are NOT steps — name the **duty area** "
                  "they belong to ('paint-defect diagnosis', 'atomizing-air "
                  "stability') instead. Invent no area the text does not "
                  f"support. At most {limit}.\n\n{body}")
    try:
        raw = llm.extract(prompt, _TASKMAP_SCHEMA)
    except Exception as exc:
        log.warning("과업 지도 추출 실패, 규칙 기반: %s", exc)
        raw = {}
    steps = [
        {"name": str(x.get("name", "")).strip()[:120],
         "difficulty": x.get("difficulty", "mid")}
        for x in (raw.get("steps") or []) if str(x.get("name", "")).strip()
    ]
    if steps:
        return steps[:limit]
    out = []
    for line in body.splitlines():
        line = line.strip(" -·0123456789.\t")
        if not line:
            continue
        hard = any(w in line for w in ("감", "느낌", "손끝", "냄새", "소리",
                                       "feel", "gut", "ear", "smell"))
        out.append({"name": line[:120], "difficulty": "hard" if hard else "mid"})
    return out[:limit]


def flag_probe(domain: str, card_count: int, lang: str = "en") -> str:
    """이관 업무(깃발) 하나를 겨냥한 입구 질문 — 결정적 조립, LLM 없음.

    깃발은 전문가 본인이 그린 발굴 지도다. "이걸 남겨야 한다" 고 적어놓고
    시스템이 그 영역을 파러 가지 않으면 지도는 장식이 된다.
    """
    kind, probe = entry_probe(card_count, lang)
    if lang == "ko":
        return f"'{domain}' 을 남겨야 한다고 적으셨죠. 그 영역에서 — {probe}"
    return f"You wrote that '{domain}' has to be handed over. In that area — {probe}"


#: 빈 칸을 채우러 가는 질문. 사다리가 끝나도 카드가 비면 여기서 계속 판다.
_SLOT_QUESTIONS: dict[str, dict[str, str]] = {
    "ko": {
        "situation": "이 판단이 나오는 상황을 한 줄로 잡아주세요. 언제, 어디서 벌어지나요?",
        "cues": "무엇을 보고 아시나요? 남들은 그냥 지나치는 것 중에 당신만 보는 것.",
        "judgment": "그래서 결론이 뭔가요? 한 문장으로.",
        "action": "구체적으로 무엇부터 하시나요? 순서대로.",
        "rationale": "왜 그렇게 되나요? 원리를 아는 대로만.",
        "exceptions": "이 규칙이 안 통하는 경우가 있나요? 하나라도.",
        "failure": "이걸로 틀렸던 적이 있나요? 없으면 넘기셔도 됩니다.",
    },
    "en": {
        "situation": "Pin the situation in one line. When and where does this happen?",
        "cues": "What tells you? The thing others walk past and you don't.",
        "judgment": "So what's the call? One sentence.",
        "action": "What do you actually do first? In order.",
        "rationale": "Why does it work that way? Only as far as you know.",
        "exceptions": "Is there a case where this rule doesn't hold? Even one.",
        "failure": "Has this ever been wrong? Skip it if not.",
    },
}


#: 얼버무림 — "그때그때 다르다" 계열. 이 말이 나오면 사람 지식공학자는
#: 절대 다음 질문으로 넘어가지 않는다. 일반론은 적용할 수 없는 지식이고,
#: CDM 의 핵심 수가 정확히 **일반론을 사건 하나로 끌어내리기**다
#: (docs/elicitation-protocol.md §0). 판정은 단어 목록으로 한다 — LLM 에게
#: "얼버무림인지 판단해 달라" 고 부탁하지 않는다.
_HEDGES = (
    "그때그때", "그때 그때", "케바케", "상황에 따라", "상황마다", "감으로",
    "감이지", "그냥 감", "보면 알", "보면 안다", "느낌으로", "느낌이지",
    "딱히 기준", "말로 못", "말로는 못", "설명이 안", "몸이 기억",
    "it depends", "case by case", "gut feeling", "by feel", "just know",
    "you just see", "hard to explain", "can't explain", "muscle memory",
)


#: 모호 수치어 — "적당히 높으면" 은 후배가 쓸 수 없다. 숫자가 없는 채로
#: 이 말이 나오면 경계 슬라이더의 정신으로 즉시 되짚는다 (도구 발동 보장 ①).
_VAGUE = (
    "적당히", "적절히", "이 정도면", "어느 정도", "충분히", "좀 높", "좀 낮",
    "약간", "높으면", "낮으면", "많이", "조금",
    "a bit", "about right", "roughly", "as needed", "enough", "slightly",
    "fairly", "too high", "too low", "a little",
)

#: 감각어 — 신호를 파는 중에 감각이 언급되면 감각 사다리의 정신으로
#: 채널을 분해한다 (도구 발동 보장 ②).
_SENSORY = (
    "냄새", "소리", "느낌", "촉감", "울림", "광이", "광택", "결이", "손끝",
    "smell", "sound", "feel", "ring", "sheen", "by ear", "by hand", "by eye",
    "texture",
)

_PIN_Q = {
    "ko": "방금 '{word}' 라고 하셨는데 — 몇부터입니까? 숫자나 기준 하나로 짚어주세요. 후배는 그 숫자가 없으면 못 씁니다.",
    "en": "You said '{word}' — from what number? Pin it to a figure or a threshold. A junior cannot use it without one.",
}
_SENSE_Q = {
    "ko": "그 감각을 채널로 나눠보죠 — 눈·귀·손·냄새 중 어디입니까? 그리고 정상일 때와 무엇이 다릅니까? 비유로 말씀하셔도 됩니다.",
    "en": "Let's split that sense into channels — eye, ear, hand, or smell? And how does it differ from normal? An analogy is fine.",
}


def vague_word(answer: str) -> str:
    """숫자 없는 모호 수치어를 찾는다. 숫자가 이미 있으면 짚을 필요 없다."""
    text = (answer or "").lower()
    if any(ch.isdigit() for ch in text):
        return ""
    for w in _VAGUE:
        if w in text:
            return w
    return ""


def has_sense(answer: str) -> bool:
    text = (answer or "").lower()
    return any(w in text for w in _SENSORY)


def is_hedge(answer: str) -> bool:
    text = " ".join((answer or "").lower().split())
    return any(h in text for h in _HEDGES) and len(text) < 120


#: 같은 칸을 **사건 하나**로 다시 파는 질문. 얼버무림 1회차에 쓴다.
_DEEPEN: dict[str, dict[str, str]] = {
    "ko": {
        "cues": "그럼 마지막으로 그렇게 판단하셨던 날로 가보죠. 그날, 그 자리에서 무엇이 보였습니까? 화면·소리·냄새·손끝 중 하나만.",
        "judgment": "일반론 말고요 — 가장 최근 그 한 번, 그날은 결론이 뭐였습니까?",
        "exceptions": "최근에 이 규칙을 버린 적이 한 번이라도 있습니까? 그날은 뭐가 달랐습니까?",
        "_": "일반론 말고, 마지막 한 번의 실제 사건으로만 말씀해 주세요. 그날 무슨 일이 있었습니까?",
    },
    "en": {
        "cues": "Then take me to the last day you made that call. In that moment, what did you actually see? Screen, sound, smell, or hands — pick one.",
        "judgment": "Not in general — the most recent single time. What was the call that day?",
        "exceptions": "Has there been even one time recently you dropped this rule? What was different that day?",
        "_": "Not in general — just the last single time it happened. What happened that day?",
    },
}


def deepen_question(slot: str, lang: str = "en") -> str:
    bank = _DEEPEN.get(lang, _DEEPEN["en"])
    return bank.get(slot, bank["_"])


def rungs(lang: str = "en") -> tuple[tuple[str, str], ...]:
    return _RUNGS.get(lang, _RUNGS["en"])


def slot_question(slot: str, lang: str = "en") -> str:
    return _SLOT_QUESTIONS.get(lang, _SLOT_QUESTIONS["en"]).get(slot, "")


#: 하위 호환 — 기존 호출부와 테스트가 참조한다.
LADDER_RUNGS = _RUNGS["ko"]
SLOT_QUESTIONS = _SLOT_QUESTIONS["ko"]

_SYSTEM_KO = """너는 은퇴를 앞둔 숙련 전문가에게서 암묵지를 캐내는 발굴 도우미다.
전문가는 이미 남기고 싶어 한다 — 설득하지 마라. 꺼내기만 도와라.

지켜야 할 것:
1. 너는 묻는 사람이다. 답을 제안하지 마라. 전문가가 말하게 하라.
2. 한 번에 질문 하나. 복합 질문 금지.
3. 전문가가 쓴 현장 용어를 표준어로 고치지 마라. 그 단어가 지식이다.
4. 일반론이 나오면 사건으로 되돌려라 — "구체적으로 그런 적이 언제였나요?"
   단, **"그런 사례는 없다"는 답도 답이다.** 없다고 밝힌 사건을 다시
   요구하지 마라 — 없는 경험을 지어 말하게 압박하는 것이 최악이다.
   사례가 없으면 조건·예외 쪽으로 방향을 틀어라.
5. "감으로 안다"가 나오면 두 번까지만 파고, 세 번째엔 넘어가라.
   말로 안 되는 것을 억지로 말하게 만들지 마라.
6. 전문가를 평가하거나 칭찬하지 마라. 되읽어주고 다음을 물어라.
7. 사건 여러 개가 한꺼번에 나오면 네가 고르지 마라 — "그중에 후배가 꼭
   알아야 할 것 하나만 고르신다면요?" 라고 전문가에게 고르게 하라.
   무엇을 고르는지 자체가 지식이다.
8. 한국어로, 존댓말로, 짧게 묻는다."""

_SYSTEM_EN = """You are an excavation assistant drawing tacit knowledge out of a
veteran expert who is about to retire. They already want to leave it behind — do
not sell them on it. Just help them get it out.

Rules:
1. You are the one asking. Do not propose answers. Let the expert talk.
2. One question at a time. Never compound questions.
3. Do not correct the expert's shop-floor vocabulary into standard terms. That
   vocabulary IS the knowledge.
4. When you get a generality, steer back to an event — "when specifically did
   that happen?" But **"there is no such case" is an answer.** Never re-demand
   an incident they said does not exist — pressuring someone to invent an
   experience is the worst failure. Pivot to conditions and exceptions instead.
5. If they say "I just know it by feel", probe twice at most, then move on. Never
   force someone to verbalise what does not go into words.
6. Do not evaluate or praise the expert. Read it back, then ask the next thing.
7. Ask in English, plainly and briefly.
8. If several incidents come out at once, do not pick for them — ask "if you had
   to pick the one a junior must know, which one?" The choice itself is knowledge."""


def _system(lang: str) -> str:
    return _SYSTEM_KO if lang == "ko" else _SYSTEM_EN


@dataclass
class Question:
    text: str
    rung: str = ""
    instrument: str = LADDER
    #: 이 질문이 채우려는 카드 칸
    targets: str = ""
    #: 규칙 기반으로 만들어졌는가 (LLM 미연결/실패)
    fallback: bool = False


#: 사례 사양(없음·건너뛰기) 표현 — 짧은 답에서만 판정한다. "문제 없었다"
#: 같은 정상 서술을 오인하지 않도록, 사례·기억을 부정하는 꼴로 좁힌다.
_DECLINE_MARKS = (
    "사례는 없", "사례가 없", "그런 적은 없", "그런 적 없", "기억이 없",
    "기억나는 게 없", "떠오르는 게 없", "넘길게", "넘어가", "건너뛰",
    "생략할게", "없습니다만 넘어", "skip", "no such case", "none i recall",
    "can't recall", "cannot recall", "no specific case", "let's move on",
)

#: 통째 사양 — 답 전체가 "없다" 한 마디일 때 (짧을 때만; "문제 없었다" 같은
#: 정상 서술과 헷갈리지 않게 시작 어절로 좁힌다).
_DECLINE_WHOLE = ("없습니다", "없어요", "없네요", "없음", "none", "nothing", "no")

#: 메타 거부 — 지식이 아니라 **기계를 향한 지시**다. 카드 어느 칸에도
#: 들어가면 안 된다 ("없습니다, 추론해서 만들지 마세요" 가 신호로 저장된
#: QA 실측). 현장 지식의 "만지지 마라" 와 다른 것: 대상이 추론·생성이다.
_META_REFUSAL = (
    "추론해서 만들", "추론하지 마", "지어내지 마", "만들어내지 마",
    "생성하지 마", "창작하지 마", "don't invent", "do not invent",
    "don't make up", "do not make up", "don't fabricate",
)


def declined_incident(answer: str) -> bool:
    """전문가가 사건 요구를 사양했는가 — 결정적, 짧은 답(<80자)에서만."""
    low = (answer or "").strip().lower()
    if not low or len(low) > 80:
        return False
    if any(m in low for m in _DECLINE_MARKS):
        return True
    return len(low) <= 20 and any(low.startswith(w) for w in _DECLINE_WHOLE)


def not_card_material(answer: str) -> bool:
    """이 발화는 카드 재료가 아니다 — 사양이거나 기계를 향한 지시다."""
    low = (answer or "").strip().lower()
    if not low:
        return True
    return declined_incident(answer) or any(m in low for m in _META_REFUSAL)


#: 사양 후의 방향 전환 — 사건 대신 **조건**을 묻는다. 이 답이 곧
#: 규칙 초안(all_of/none_of)의 재료다.
_CONDITION_Q = {
    "ko": "사례 없이도 충분합니다. 그럼 조건으로 여쭙겠습니다 — 그 판단이 "
          "성립하려면 무엇이 **전부** 확인되어야 하고, 반대로 무엇이 하나라도 "
          "보이면 그 판단을 접으십니까?",
    "en": "No example needed — let me ask it as conditions instead. What must "
          "ALL be true for that judgment to stand, and what single sign, if "
          "present, makes you drop it?",
}


def next_question(
    llm: BaseLLM,
    *,
    instrument: str = LADDER,
    card: Card | None = None,
    history: list[tuple[str, str]] | None = None,
    gap_question: str = "",
    gap_source: str = "junior",   # junior | doc | voice
    last_rung: str = "",
    last_slot: str = "",
    skipped_last: bool = False,
    lang: str = "en",
) -> Question:
    """다음 질문 하나.

    우선순위: ① 후배의 공백 → ② 카드의 빈 칸 → ③ 사다리 진행.
    ①이 맨 앞인 것이 이 설계의 핵심이다 — **인터뷰 주제는 현장 수요가 정한다.**
    """
    history = history or []

    if gap_question:
        # 출처를 속이지 않는다 — 문서·혼잣말에서 나온 질문을 "후배가 물었다"
        # 고 하면, 전문가가 없는 후배에게 답장하는 셈이 된다.
        if gap_source == "doc":
            if lang == "ko":
                text = ("절차서를 읽다가 문서가 답하지 않는 것을 찾았습니다.\n\n"
                        f"「{gap_question}」\n\n어떻게 하십니까?")
            else:
                text = ("Reading your procedure, I found something it does not "
                        "answer.\n\n"
                        f"\u201c{gap_question}\u201d\n\nWhat do you do?")
        elif gap_source == "review":
            if lang == "ko":
                text = ("검토에서 스스로 짚으셨죠.\n\n"
                        f"「{gap_question}」\n\n그 이야기로 가보죠 — 그때 상황 하나만.")
            else:
                text = ("You raised this yourself in the review.\n\n"
                        f"\u201c{gap_question}\u201d\n\nLet's go there — one "
                        "actual time it happened.")
        elif gap_source == "voice":
            if lang == "ko":
                text = ("지난번 혼잣말에서 이걸 건졌습니다.\n\n"
                        f"「{gap_question}」\n\n조금만 더 파볼까요?")
            else:
                text = ("I picked this up from your last recording.\n\n"
                        f"\u201c{gap_question}\u201d\n\nShall we dig at it?")
        elif lang == "ko":
            text = ("후배가 이걸 물었는데 분신이 답하지 못했습니다.\n\n"
                    f"「{gap_question}」\n\n어떻게 보십니까?")
        else:
            text = ("A junior asked this and your alter could not answer it.\n\n"
                    f"\u201c{gap_question}\u201d\n\nHow do you see it?")
        return Question(text=text, rung="gap", instrument=instrument)

    if instrument != LADDER and not history:
        tool = BY_KEY.get(instrument)
        if tool:
            return Question(
                text=tool.localized(lang)["opener"], instrument=instrument, rung="opener"
            )

    # 카드의 빈 칸을 채우러 간다.
    target = ""
    if card is not None:
        missing = card.missing
        if missing:
            target = missing[0]

    ladder = rungs(lang)
    rung = ladder[min(len(history), len(ladder) - 1)]
    fallback_text = slot_question(target, lang) if target else rung[1]

    if not history:
        return Question(text=ladder[0][1], rung="recall", instrument=instrument)

    # 사례 사양(辭讓) 가드 — "그런 사례는 없다/넘어가자" 는 답이다.
    # 프롬프트로 부탁했더니 같은 단계에서 표현만 바꿔 계속 물었다(QA 2회
    # 실측). 그래서 이 수는 LLM 을 거치지 않는다: 사양이 감지되면 사건
    # 요구를 멈추고 **조건 질문**(성립 요건·뒤집는 신호)으로 결정적으로
    # 방향을 튼다 — 규칙 칸의 재료가 되는 질문이기도 하다.
    # 스킵 버튼도 사양이다 — 스킵된 턴은 history 에 안 실려 텍스트 가드가
    # 볼 수 없다 (QA 실측: 넘겨도 같은 단계에서 표현만 바꿔 재질문).
    last0 = history[-1][1] if history else ""
    if (skipped_last or declined_incident(last0)) and last_rung != "condition":
        return Question(
            text=_CONDITION_Q.get(lang, _CONDITION_Q["en"]),
            rung="condition", instrument=instrument, targets="exceptions",
        )

    # 얼버무림 규칙 — "그때그때 다르다" 는 답이 아니라 신호다.
    # 1회차: 같은 칸을 **사건 하나**로 다시 판다 (LLM 을 거치지 않는다 —
    # 이 수는 결정적이어야 하고, 화면에서 왜 같은 칸을 다시 묻는지 보여야 한다).
    # 2회차: 강요하지 않는다. 억지 언어화는 지어낸 신호를 만든다. 그 말은
    # capture 가 unspeakable(도제 항목)로 보내고, 여기서는 다음 칸으로 넘어간다.
    last = history[-1][1] if history else ""
    prev = history[-2][1] if len(history) > 1 else ""
    if target and is_hedge(last):
        if not is_hedge(prev):
            return Question(
                text=deepen_question(target, lang), rung="deepen",
                instrument=instrument, targets=target,
            )
        if card is not None and len(card.missing) > 1:
            target = card.missing[1]
            fallback_text = slot_question(target, lang)

    # 도구 발동 보장 — 얼버무림 다음 순위의 결정적 트리거 둘. 같은 수를 두 번
    # 연속 두지 않는다 (last_rung 확인) — 짚었는데 또 짚으면 취조가 된다.
    # 기준은 "직전 답이 어느 칸을 향했는가"(last_slot) — 답이 이미 칸을 채워
    # 다음 target 이 넘어간 뒤에도, 모호함·감각은 그 칸에서 즉시 짚어야 한다.
    if last and not is_hedge(last) and last_rung not in ("pin", "sense", "deepen"):
        word = vague_word(last)
        if word and last_slot:
            return Question(
                text=_PIN_Q.get(lang, _PIN_Q["en"]).format(word=word),
                rung="pin", instrument=instrument, targets=last_slot,
            )
        if last_slot == "cues" and has_sense(last):
            return Question(
                text=_SENSE_Q.get(lang, _SENSE_Q["en"]),
                rung="sense", instrument=instrument, targets="cues",
            )

    prompt = _build_probe_prompt(history, target, instrument, lang)
    try:
        # 한 문장 질문에 8000 토큰 예산은 지연만 산다 — 짧게 캡.
        text = llm.answer(_system(lang), prompt, max_tokens=300).strip()
    except Exception as exc:
        log.warning("질문 생성 실패, 규칙 기반 대체: %s", exc)
        text = ""
    if not text or text.startswith("⚠"):
        return Question(
            text=fallback_text, rung=rung[0], instrument=instrument,
            targets=target, fallback=True,
        )
    return Question(text=text, rung=rung[0], instrument=instrument, targets=target)


def _build_probe_prompt(
    history: list[tuple[str, str]], target: str, instrument: str, lang: str = "en"
) -> str:
    ko = lang == "ko"
    lines = ["지금까지의 대화:" if ko else "The conversation so far:"]
    for q, a in history[-6:]:
        lines.append(
            f"질문: {q}\n전문가: {a}" if ko else f"Question: {q}\nExpert: {a}"
        )
    tool = BY_KEY.get(instrument)
    if tool and instrument != LADDER:
        loc = tool.localized(lang)
        lines.append(
            (f"\n지금 쓰는 연장: {loc['name']} — {loc['pitch']}") if ko
            else (f"\nInstrument in use: {loc['name']} — {loc['pitch']}")
        )
    if target:
        label = slot_label(target, lang)
        lines.append(
            (f"\n지금 비어 있는 칸: **{label}**. 이 칸을 채우는 질문 하나만 만들어라.")
            if ko else
            (f"\nThe empty field right now: **{label}**. Write exactly one question "
             "that fills it.")
        )
    else:
        lines.append(
            "\n사다리 다음 단으로 파고드는 질문 하나만 만들어라." if ko
            else "\nWrite exactly one question that digs into the next rung."
        )
    lines.append(
        "질문 문장만 출력해라. 머리말·설명 금지." if ko
        else "Output the question sentence only. No preamble, no explanation."
    )
    return "\n".join(lines)


# ------------------------------------------------------------- 오답 채점기

_WRONG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "wrong_answer": {
            "type": "string",
            "description": "그럴듯하지만 틀린 판단. 초보가 실제로 할 법한 오답이어야 한다.",
        },
        "why_tempting": {"type": "string", "description": "왜 그럴듯한가 (한 줄)"},
    },
    "required": ["wrong_answer", "why_tempting"],
    "additionalProperties": False,
}


_DOC_PROBE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "anchor": {"type": "string"},
                },
                "required": ["question", "anchor"],
            },
        },
    },
    "required": ["questions"],
}


def probe_document(
    llm: BaseLLM, text: str, *, domain: str = "", lang: str = "en", limit: int = 7
) -> list[dict[str, str]]:
    """📄 절차서 빨간펜 — 문서에서 **질문**을 뽑는다. 카드를 뽑지 않는다.

    문서를 카드로 자동 변환하면 신호가 빈 카드가 쏟아지고 제품이 사내 RAG
    챗봇으로 무너진다 — 적힌 것은 절차이고, 잃는 것은 예외와 판단 근거이기
    때문이다 (docs/design.md §1). 대신 문서를 **심문**한다: 절차서가 다루지
    않는 판단 지점을 찾아 전문가에게 물을 질문으로 바꾼다. 오답 채점기와 같은
    기제다 — 사람은 자기 지식은 설명 못 해도 **남이 쓴 것의 구멍**은 바로
    짚는다.

    반환된 질문은 새 큐가 아니라 **공백 큐**로 들어간다. "다음에 팔 곳" 은
    이미 공백 큐가 정하고 있고, 문서발 질문도 같은 길을 탄다.
    """
    body = (text or "").strip()
    if not body:
        return []
    body = body[:60_000]   # 절차서 한 부면 충분하다
    if lang == "ko":
        prompt = (
            f"아래는 '{domain or '현장'}' 절차 문서다. 이 문서를 읽고, **문서에 "
            "명시되지 않은 판단 지점**을 찾아라 — 절차는 있는데 다음이 빠진 곳:\n"
            "· 예외 상황에서 어떻게 하는지\n"
            "· 두 절차가 충돌할 때 무엇이 우선인지\n"
            "· '적절히/필요시/충분히' 같은 말의 실제 기준값\n"
            "· 이 단계가 실패했을 때의 복구 경로\n\n"
            f"각각을 이 문서의 저자(현장 전문가)에게 물을 **질문 한 문장**으로 "
            f"만들어라. 최대 {limit}개. anchor 에는 근거가 된 문서 구절을 20자 "
            "내외로 인용하라. 문서에 이미 답이 있는 것은 묻지 마라.\n\n"
            f"--- 문서 ---\n{body}"
        )
    else:
        prompt = (
            f"Below is a procedure document from the '{domain or 'shop floor'}' "
            "domain. Find the **judgment points the document does not cover** — "
            "places where a procedure exists but the following is missing:\n"
            "- what to do in the exception case\n"
            "- which rule wins when two procedures conflict\n"
            "- the actual threshold behind words like 'adequate' or 'as needed'\n"
            "- the recovery path when a step fails\n\n"
            f"Turn each into **one question** to ask the document's author (the "
            f"expert). At most {limit}. In `anchor`, quote the passage (about 10 "
            "words) that raised the question. Do not ask what the document "
            f"already answers.\n\n--- DOCUMENT ---\n{body}"
        )
    try:
        raw = llm.extract(prompt, _DOC_PROBE_SCHEMA)
    except Exception as exc:
        log.warning("문서 심문 실패: %s", exc)
        raw = {}
    out = []
    for q in (raw.get("questions") or [])[:limit]:
        question = str(q.get("question", "")).strip()
        if question:
            out.append({"question": question, "anchor": str(q.get("anchor", "")).strip()})
    return out


def probe_monologue(
    llm: BaseLLM, transcript: str, *, domain: str = "", lang: str = "en",
    limit: int = 5,
) -> list[dict[str, str]]:
    """🎙 혼잣말 채굴 — 두서없는 녹음에서 **질문**을 건진다. 카드를 만들지 않는다.

    문서 심문과 같은 불변식이다: 재료(문서·혼잣말)는 질문이 되고, 카드는
    전문가의 확인된 답에서만 나온다. 혼잣말 전사를 그대로 카드로 만들면
    맥락 없는 반쪽 판단이 인용 게이트로 흘러든다.

    찾는 것: 지나가듯 말한 판단의 흔적 — 기준을 언급한 곳("이 정도면"),
    예외를 흘린 곳("원래는 안 그러는데"), 결정을 내린 순간("그래서 그냥
    세웠어"). 각각을 그 자리를 파는 질문으로 바꾼다.
    """
    body = (transcript or "").strip()
    if not body:
        return []
    body = body[:60_000]
    if lang == "ko":
        prompt = (
            f"아래는 '{domain or '현장'}' 전문가가 일하면서 흘린 혼잣말 전사다. "
            "두서없어도 된다 — 그 안에서 **지나가듯 말한 판단의 흔적**을 찾아라:\n"
            "· 기준을 언급한 곳 (\"이 정도면\", \"딱 보면\")\n"
            "· 예외를 흘린 곳 (\"원래는 안 그러는데\")\n"
            "· 결정을 내린 순간 (\"그래서 그냥 세웠어\")\n\n"
            f"각각을 본인에게 그 자리를 파묻는 **질문 한 문장**으로 바꿔라. "
            f"최대 {limit}개. anchor 에는 근거가 된 혼잣말 구절을 그대로 20자 "
            "내외로 인용하라. 판단이 아닌 것(불평·잡담)은 건지지 마라.\n\n"
            f"--- 전사 ---\n{body}"
        )
    else:
        prompt = (
            f"Below is a transcript of a '{domain or 'shop floor'}' expert "
            "talking to themselves while working. It may ramble — inside it, "
            "find **traces of judgment said in passing**:\n"
            "- a threshold mentioned (\"about this much\", \"you can tell\")\n"
            "- an exception let slip (\"normally I wouldn't, but\")\n"
            "- a decision being made (\"so I just stopped the line\")\n\n"
            f"Turn each into **one question** that digs at that spot. At most "
            f"{limit}. In `anchor`, quote the phrase (about 10 words) that "
            "raised it. Do not mine complaints or small talk.\n\n"
            f"--- TRANSCRIPT ---\n{body}"
        )
    try:
        raw = llm.extract(prompt, _DOC_PROBE_SCHEMA)
    except Exception as exc:
        log.warning("혼잣말 채굴 실패: %s", exc)
        raw = {}
    out = []
    for q in (raw.get("questions") or [])[:limit]:
        question = str(q.get("question", "")).strip()
        if question:
            out.append({"question": question, "anchor": str(q.get("anchor", "")).strip()})
    return out


_ALIAS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"terms": {"type": "array", "items": {"type": "string"}}},
    "required": ["terms"],
}


def search_aliases(
    llm: BaseLLM, *, title: str, situation: str, cues: list[str],
    lang: str = "en", limit: int = 10,
) -> list[str]:
    """"후배가 이걸 뭐라고 물을까" — 숨은 검색 보조 토큰.

    L3 패러프레이즈("야외에서 색감이 이상해요")는 카드 어휘와 한 글자도 안
    겹쳐 키워드 검색이 놓친다. 임베딩 대신 별칭을 택한 이유: 판정(문턱·겹침)
    은 그대로 결정적으로 남고, **무엇이 걸리는지 눈으로 검사 가능**하다.
    화면·인용에는 절대 나가지 않는다 — 검색만 본다. 실패하면 빈 목록(무해).
    """
    body = f"{title}\n{situation}\n" + "\n".join(cues)
    if not body.strip():
        return []
    if lang == "ko":
        prompt = ("아래는 현장 판단 카드의 제목·상황·신호다. 2~3년차 후배가 "
                  "이 상황을 겪고 물을 법한 **표현**을 뽑아라 — 동의어, 현장 "
                  "속어, 증상 중심 서술(예: '야외에서 색이 이상해요'). 문장이 "
                  f"아니라 짧은 구 위주로 최대 {limit}개. 카드에 이미 있는 "
                  f"단어는 빼라.\n\n{body}")
    else:
        prompt = ("Below are a shop-floor judgment card's title, situation and "
                  "cues. List the **phrasings** a 2-3 year junior would use when "
                  "hitting this — synonyms, floor slang, symptom-first wording. "
                  f"Short phrases, at most {limit}. Skip words already on the "
                  f"card.\n\n{body}")
    try:
        raw = llm.extract(prompt, _ALIAS_SCHEMA)
    except Exception as exc:
        log.warning("검색 별칭 생성 실패(무해): %s", exc)
        return []
    return [str(t).strip()[:60] for t in (raw.get("terms") or [])
            if str(t).strip()][:limit]


_RULES_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "rule_all": {"type": "array", "items": {"type": "string"}},
        "rule_none": {"type": "array", "items": {"type": "string"}},
        "rule_priority": {"type": "integer"},
    },
    "required": ["rule_all", "rule_none", "rule_priority"],
}


def draft_rules(
    llm: BaseLLM, *, title: str, judgment: str, cues: list[str],
    exceptions: list[str], lang: str = "en",
) -> dict[str, Any]:
    """카드 → 규칙 **초안** — 제안일 뿐, 승인 없이는 아무것도 실행되지 않는다.

    컴파일러의 마지막 이음새다: 인터뷰가 채운 신호·예외를 판정 규칙
    후보(전부 있어야/없어야/우선순위)로 바꿔 승인 화면에 미리 채워 준다.
    전문가가 검토·수정해 저장하는 순간에만 규칙이 된다. 재료는 카드에
    적힌 조건뿐 — 새 조건을 발명하면 전문가가 승인 화면에서 걸러낸다는
    가정에 기대지 말고, 프롬프트가 먼저 막는다. 실패하면 빈 초안(무해).
    """
    body = (f"{title}\n[judgment] {judgment}\n[cues] " + "; ".join(cues)
            + "\n[exceptions] " + "; ".join(exceptions))
    if lang == "ko":
        prompt = (
            "아래 판단 카드를 결정론 판정 규칙 초안으로 바꿔라.\n"
            "- 각 줄은 `신호id :: 관찰 문구` 꼴로 써라. 신호id 는 짧은 "
            "snake_case 로, **같은 임상 신호는 언제나 같은 id** 를 쓴다 "
            "(예: dry_heaving :: 반복적으로 토하려 하지만 아무것도 안 나옴). "
            "이 id 가 카드 사이에서 같은 질문을 하나로 묶는다.\n"
            "- rule_all: 이 판단이 성립하려면 **전부 '예'** 여야 하는 관찰 조건.\n"
            "- rule_none: **전부 '아니오'** 여야 하는 위험 신호 (예외 칸의 "
            "'~면 통하지 않는다' 가 주 재료).\n"
            "- rule_priority: 위급(즉시·응급·중단)한 판단이면 3, 시간 여유가 "
            "있으면 2, 안심시키는(정상 예약류) 판단이면 1.\n"
            "- 안심시키는 판단일수록 rule_all 을 촘촘히: 확인 안 된 것을 "
            "안심의 근거로 두지 마라.\n"
            "- **카드에 적힌 조건만** 짧은 관찰 구문으로 옮겨라. 카드에 없는 "
            f"조건을 발명하지 마라.\n\n{body}"
        )
    else:
        prompt = (
            "Turn the judgment card below into DRAFT deterministic rules.\n"
            "- Write each line as `signal_id :: observable phrase`. Use short "
            "snake_case ids and ALWAYS the same id for the same clinical "
            "signal (e.g. dry_heaving :: retching repeatedly, nothing comes "
            "up). The id merges the same question across cards.\n"
            "- rule_all: observable conditions that must ALL be 'yes' for this "
            "judgment to stand.\n"
            "- rule_none: danger signs that must ALL be 'no' (the exceptions "
            "field's 'does not hold when…' items are the main source).\n"
            "- rule_priority: 3 if the judgment is urgent (now / emergency / "
            "stop), 2 if time-bounded, 1 if reassuring (routine booking).\n"
            "- The more reassuring the judgment, the tighter rule_all must be: "
            "never let an unconfirmed item support reassurance.\n"
            "- Use ONLY conditions written on the card, as short observable "
            f"phrases. Invent nothing.\n\n{body}"
        )
    try:
        raw = llm.extract(prompt, _RULES_SCHEMA, think=True)
    except Exception as exc:
        log.warning("규칙 초안 제안 실패(무해): %s", exc)
        return {"rule_all": [], "rule_none": [], "rule_priority": 0}
    return {
        "rule_all": [str(x).strip()[:120] for x in (raw.get("rule_all") or []) if str(x).strip()][:8],
        "rule_none": [str(x).strip()[:120] for x in (raw.get("rule_none") or []) if str(x).strip()][:8],
        "rule_priority": max(0, min(9, int(raw.get("rule_priority") or 0))),
    }


def wrong_answer(
    llm: BaseLLM, topic: str, domain: str = "", *, lang: str = "en"
) -> dict[str, str]:
    """⚖️ 오답 채점기 — **그럴듯하지만 틀린** 판단을 만든다.

    원리: 사람은 자기 지식은 설명 못 해도 남의 오답은 3초 만에 잡아낸다.
    백지 대비 발굴 효율이 가장 높은 연장이라 도구함 기본 노출에 들어간다.
    """
    if lang == "ko":
        prompt = (
            f"'{domain or '현장'}' 영역에서 다음 상황에 대해, **초보자가 흔히 하는 "
            f"그럴듯한 오답**을 하나 만들어라. 명백히 우스운 답 말고, 경력 3년차가 "
            f"자신 있게 말할 법한 답이어야 한다. 정답을 쓰지 마라.\n\n상황: {topic}"
        )
    else:
        prompt = (
            f"In the '{domain or 'shop floor'}' domain, write one **plausible but "
            "wrong** judgment a beginner commonly makes about the situation below. "
            "Not an obviously silly answer — something a three-year veteran would "
            f"say with confidence. Do not write the correct answer.\n\n"
            f"Situation: {topic}"
        )
    try:
        raw = llm.extract(prompt, _WRONG_SCHEMA)
    except Exception as exc:
        log.warning("오답 생성 실패: %s", exc)
        raw = {}
    if not raw:
        if lang == "ko":
            return {
                "wrong_answer": f"{topic} — 매뉴얼대로 표준 설정값으로 되돌리면 해결됩니다.",
                "why_tempting": "대부분의 경우 통하지만, 원인을 못 짚어서 재발한다.",
                "fallback": "1",
            }
        return {
            "wrong_answer": f"{topic} — just reset everything to the standard values "
                            "in the manual and it clears up.",
            "why_tempting": "It works most of the time, which is why it hides the "
                            "real cause and the problem comes back.",
            "fallback": "1",
        }
    return raw


# --------------------------------------------------------------- 카드 포획

_CARD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "이 판단을 한 줄로. 조건절로 쓰면 좋다."},
        "domain": {"type": "string", "description": "영역 이름 (짧게)"},
        "situation": {"type": "string", "description": "언제/어디서 벌어지는 상황"},
        "cues": {
            "type": "array",
            "description": "무엇을 보고 아는가. 전문가가 실제로 말한 신호만. 지어내지 마라.",
            "items": {"type": "string"},
        },
        "judgment": {"type": "string", "description": "그래서 내리는 판단"},
        "action": {"type": "array", "description": "조치 순서", "items": {"type": "string"}},
        "rationale": {"type": "string", "description": "왜 그런가 (원리)"},
        "exceptions": {
            "type": "array",
            "description": "안 통하는 경우. 없으면 빈 배열.",
            "items": {"type": "string"},
        },
        "failure": {"type": "string", "description": "실제로 틀렸던 사례. 없으면 빈 문자열."},
        "unspeakable": {
            "type": "array",
            "description": "말로 담기지 않은 것 (손끝 감각·소리·냄새). 담기지 않는다는 사실 자체가 보존해야 할 정보다.",
            "items": {"type": "string"},
        },
        "risk": {"type": "string", "enum": ["high", "mid", "low"]},
    },
    "required": [
        "title", "domain", "situation", "cues", "judgment", "action",
        "rationale", "exceptions", "failure", "unspeakable", "risk",
    ],
    "additionalProperties": False,
}

#: 언어별로 있어야 한다 — 한국어 지시문을 영어 대화에 내보내면 추출이
#: 한국어로 드리프트한다 (영어 전문가의 카드가 한국어로 저장되는 실측 버그).
_CAPTURE_PROMPT_EN = """Below is an elicitation conversation with a veteran
expert. Extract exactly one **judgment card** from it.

Hard rules:
- **Invent nothing the expert did not say.** Leave empty fields empty —
  an empty field drives the next question; pretending it is filled is worst.
- Keep the expert's shop-floor wording. Do not normalise it.
- Declines and meta-instructions ("no such case", "let's move on", "don't
  invent") are not knowledge — they go in no field, ever.
- 'cues' (what tells you) is the heart of the card. Only signals the expert
  actually named — each cue must be an OBSERVABLE sign ("no urine passing",
  "belly tight like a drum"), never an explanation, a story fragment, or a
  method remark. One observation per cue, no duplicates in different wording.
- What cannot be written — feel, sound, smell — goes in 'unspeakable',
  ONLY if the expert explicitly said it does not fit in words. Never invent
  an unspeakable item; an expert who excludes vague impressions must not be
  handed one. The fact that it does not fit is itself the record.
- Write every field in the language the expert spoke.

[Conversation]
{transcript}
"""

_CAPTURE_PROMPT = """다음은 숙련 전문가와의 발굴 대화다. 여기서 **판단 카드** 하나를 뽑아라.

절대 규칙:
- **전문가가 말하지 않은 것을 지어내지 마라.** 빈 칸은 빈 채로 둬라.
  빈 칸은 다음 질문의 근거가 되므로, 채워진 척하는 것이 가장 나쁘다.
- 전문가의 현장 용어를 그대로 살려라. 표준어로 고치지 마라.
- "사례가 없다"·"넘어가자"·"지어내지 마라" 같은 사양·지시 발화는 지식이
  아니다 — 어떤 칸에도 넣지 마라.
- 'cues'(무엇을 보고 아는가)가 이 카드의 핵심이다. 전문가가 실제로 든 신호만,
  **관찰 가능한 형태로** 적어라("소변이 안 나온다", "배가 북처럼 팽팽하다").
  설명문·이야기 조각·방법론 언급은 신호가 아니다. 한 관찰에 한 줄,
  같은 신호를 표현만 바꿔 중복하지 마라.
- 손끝 감각·소리·냄새처럼 글로 담기지 않는 것은 'unspeakable' 에 적되,
  **전문가가 그렇게 말했을 때만** 적어라. 지어낸 '못 담은 것'은 최악이다 —
  모호한 인상을 배제하는 전문가에게 그것을 쥐여주게 된다.
  담기지 않는다는 사실 자체가 기록이다.

[대화]
{transcript}
"""


@dataclass
class CardDraft:
    """포획된 카드 초안. 승인 전까지 분신이 인용하지 않는다."""

    data: dict[str, Any] = field(default_factory=dict)
    fallback: bool = False

    def to_card(self, *, id: str, expert: str, instrument: str, source_turn: str) -> Card:
        d = self.data
        card = Card(
            id=id,
            expert=expert,
            title=str(d.get("title", ""))[:200],
            domain=str(d.get("domain", "")),
            situation=str(d.get("situation", "")),
            cues=[str(x) for x in d.get("cues", []) if str(x).strip()],
            judgment=str(d.get("judgment", "")),
            action=[str(x) for x in d.get("action", []) if str(x).strip()],
            rationale=str(d.get("rationale", "")),
            exceptions=[str(x) for x in d.get("exceptions", []) if str(x).strip()],
            failure=str(d.get("failure", "")),
            unspeakable=[str(x) for x in d.get("unspeakable", []) if str(x).strip()],
            risk=str(d.get("risk", "mid")),
            instrument=instrument,
            source_turn=source_turn,
        )
        # 말로 안 되는 것이 남았으면 온도계를 🔴 로 올려둔다 (전문가가 바꿀 수 있다).
        if card.unspeakable:
            card.tacitness = Tacitness.HANDS
        return card


_SENTENCE = re.compile(r"(?<=[.!?。？！])\s+|\n+")


#: 사다리 단(rung)이 겨냥하는 칸. ``Question.targets`` 가 비었을 때만 쓴다.
#: 이건 추론이 아니라 **질문 대장**이다 — 그 단에서 우리가 무엇을 물었는지는
#: ``_RUNGS`` 에 이미 적혀 있다.
_RUNG_SLOT: dict[str, str] = {
    "opener": "situation",
    "recall": "situation",
    "timeline": "situation",
    "cue": "cues",
    "counterfactual": "judgment",
    "boundary": "exceptions",
    "failure": "failure",
}

#: 여러 줄로 담기는 칸. 한 답에 여러 개가 들어오면 쪼갠다.
_LIST_SLOTS = frozenset({"cues", "action", "exceptions", "unspeakable"})

#: 저장 층이 같은 대장을 본다 (app/store/service.py::_slot_history).
RUNG_SLOT = _RUNG_SLOT


def capture(
    llm: BaseLLM,
    history: list[tuple[str, str]],
    *,
    lang: str = "en",
    slots: list[tuple[str, str]] | None = None,
) -> CardDraft:
    """대화 → 카드 초안. 실패해도 **원본은 증발하지 않는다.**

    ``slots`` 는 (겨냥한 칸, 답) 쌍이다. 기저가 없을 때 이것으로 답을 제자리에
    넣는다 — 없는 말을 지어내는 게 아니라 **전문가가 한 말을 그 말을 끌어낸
    질문의 칸에 넣는 것뿐이다.**
    """
    joiner = (
        (lambda q, a: f"질문: {q}\n전문가: {a}") if lang == "ko"
        else (lambda q, a: f"Question: {q}\nExpert: {a}")
    )
    transcript = "\n".join(joiner(q, a) for q, a in history)
    try:
        template = _CAPTURE_PROMPT if lang == "ko" else _CAPTURE_PROMPT_EN
        raw = llm.extract(template.format(transcript=transcript), _CARD_SCHEMA)
    except Exception as exc:
        log.warning("카드 구조화 실패, 규칙 기반 대체: %s", exc)
        raw = {}
    rule = _fallback(history, slots)
    if not raw:
        return rule
    # 병합 불변식 — 정련은 다듬을 수 있어도 **잃을 수는 없다.**
    # 규칙 기반이 확보한 것(특히 얼버무림이 보낸 도제 항목)은 전문가가 실제로
    # 한 말이다. LLM 출력이 그것을 빼먹으면 "말한 것은 지워지지 않는다" 가
    # 카드 층에서 깨진다 — 재현으로 확인된 실제 결함. 리스트 칸은 합집합,
    # 텍스트 칸은 정련이 비웠을 때만 규칙 값으로 되메운다.
    for key in ("cues", "action", "exceptions", "unspeakable"):
        have = [str(x) for x in (raw.get(key) or [])]
        for item in rule.data.get(key, []):
            if item and not any(item in h or h in item
                                or _covers(item, h, loose=True)
                                for h in have):
                have.append(item)
        # 정련이 거듭되며 요약본과 원문이 나란히 남는 중복(실측: 행동
        # 10개가 사실상 5+5)을 접는다 — 정규화 동치·포함 관계는 뒤가 진다.
        raw[key] = _dedupe_lines(have)
    for key in ("situation", "judgment", "rationale", "failure", "title"):
        if not str(raw.get(key) or "").strip() and rule.data.get(key):
            raw[key] = rule.data[key]
    return CardDraft(data=raw)


def _norm_line(t: str) -> str:
    return re.sub(r"[\s\.,·—\-()\[\]]+", "", str(t)).lower()


_STOP_TOKENS = {"the", "a", "an", "is", "was", "were", "and", "or", "of",
                "to", "in", "on", "it", "that", "this", "with", "at"}


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "ly", "s"):
        if len(w) > 4 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _tokens(t: str) -> set:
    words = {_stem(w) for w in re.findall(r"[a-z0-9]+", str(t).lower())
             if len(w) > 2 and w not in _STOP_TOKENS}
    # 한국어는 단어 경계가 약하다 — 2음절 조각으로 겹침을 본다.
    hangul = re.sub(r"[^가-힣]", "", str(t))
    words |= {hangul[i:i+2] for i in range(len(hangul) - 1)}
    return words


def _covers(a: str, b: str, *, loose: bool = False) -> bool:
    """a 와 b 가 같은 내용인가 — 내용 토큰(어간) 겹침으로 본다.

    엄격(기본): 짧은 쪽 토큰의 60% 겹침 — 일반 중복 제거용.
    무름(loose): 어간 2개 이상 겹침 — **병합 전용**. 정제본이 이미 있는
    자리에 그 재료였던 원문이 다시 들어오는 것("The needle swept
    smoothly…" 옆에 "…needle sweeping smoothly…", QA 실측)을 막는다.
    무른 기준을 일반 중복 제거에 쓰면 반대 신호("바늘 떨림" vs "바늘
    안정")까지 접을 수 있어 병합에만 쓴다.
    """
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return False
    shared = len(ta & tb)
    if loose:
        return shared >= 2
    small = min(ta, tb, key=len)
    return shared >= max(2, int(len(small) * 0.6))


#: 맞장구·확인 응답 — 지식이 아니라 대화의 기름칠이다. 예외 칸에
#: "Yes." 가 들어가 카드가 지저분해지던 QA 실측.
_ACKS = {"yes", "yes.", "no", "no.", "ok", "okay", "sure", "right",
         "네", "네.", "예", "예.", "응", "그렇다", "그렇습니다", "맞다",
         "맞습니다", "아니요", "아니오"}


#: 열거 서두 — "두 가지요.", "Three things, in order." 는 지식이 아니라
#: 말의 목차다. 신호 칸에 들어가 카드를 흐리던 실측(기획·개발·디자인
#: 직군 시뮬레이션 공통).
_ENUM_OPENER = re.compile(
    r"^\s*((two|three|four|five)\s+(things|reasons|signs)"
    r"(,?\s*in order)?\s*[.!:]?"
    r"|(두|세|네|다섯)\s*가지(요|입니다|예요|다)?\s*[.!,]?)\s*$",
    re.IGNORECASE,
)


def _dedupe_lines(items: list[str]) -> list[str]:
    """정규화 동치 + 포함 관계 중복 제거 — 먼저 온 줄이 산다.
    맞장구("Yes.")와 열거 서두("두 가지요.")는 칸에 넣지 않는다."""
    kept: list[str] = []
    for it in items:
        n = _norm_line(it)
        if not n:
            continue
        if str(it).strip().lower().rstrip('.!') in _ACKS or len(n) < 3:
            continue
        if _ENUM_OPENER.match(str(it).strip()):
            continue
        if any(n == _norm_line(k) or n in _norm_line(k) or _norm_line(k) in n
               or _covers(it, k) for k in kept):
            continue
        kept.append(it)
    return kept


def _fallback(
    history: list[tuple[str, str]], slots: list[tuple[str, str]] | None = None
) -> CardDraft:
    """LLM 없이도 카드가 만들어진다 — 구조는 비고, 원본은 살아남는다.

    **지어내지 않는다.** 넣는 것은 전문가가 실제로 한 말뿐이고, 어느 칸에
    넣을지는 그 말을 끌어낸 질문이 정한다 (``Turn.targets`` · ``_RUNG_SLOT``).
    겨냥한 칸을 모르는 답은 어디에도 넣지 않는다 — 비어 있어야 다음 질문이
    나오기 때문이다.
    """
    answers = [a for _, a in history
               if a.strip() and not not_card_material(a)]
    body = "\n".join(answers)
    first = next(iter(_SENTENCE.split(body)), body)[:200] if body else ""
    data: dict[str, Any] = {
        "title": first or "제목 없는 판단",
        "domain": "",
        "situation": answers[0][:300] if answers else "",
        "cues": [],
        "judgment": "",
        "action": [],
        "rationale": "",
        "exceptions": [],
        "failure": "",
        "unspeakable": [],
        "risk": "mid",
    }
    for slot, answer in slots or ():
        answer = answer.strip()
        if not slot or not answer or slot not in data:
            continue
        if not_card_material(answer):
            continue   # "없습니다, 지어내지 마세요" 는 신호가 아니다
        if is_hedge(answer):
            # "그냥 감" 은 신호가 아니다 — 인용 게이트를 통과하는 쓰레기 카드를
            # 만드는 대신, 담기지 않았다는 사실 자체를 도제 항목으로 남긴다
            # (elicitation-protocol §1-2). 억지로 언어화시키지 않는다.
            if answer[:200] not in data["unspeakable"]:
                data["unspeakable"].append(answer[:200])
            continue
        if slot in _LIST_SLOTS:
            parts = [p.strip() for p in _SENTENCE.split(answer) if p.strip()]
            for part in parts:
                if part not in data[slot]:
                    data[slot].append(part)
        elif not data[slot]:
            data[slot] = answer[:300]
    return CardDraft(data=data, fallback=True)


def reflect(card: Card, slot: str, lang: str = "en") -> str:
    """되읽어주기 — **"제가 이렇게 이해했습니다, 맞나요?"** (규약 §2)

    사람 지식공학자가 인터뷰에서 반드시 하는 일이고, 이유는 두 가지다:
    ① 오해를 그 자리에서 잡는다 — 카드는 해석이고 해석은 틀릴 수 있다.
    ② 전문가가 자기 말을 밖에서 보면 빠진 것을 스스로 알아챈다.

    **지어내지 않는다.** 카드에 실제로 들어간 값을 그대로 읽어줄 뿐이다 —
    그래서 잘못 들어간 칸이 이 자리에서 바로 드러난다.
    """
    from app.i18n import t

    value = getattr(card, slot, None)
    if isinstance(value, list):
        body = " / ".join(str(v) for v in value if str(v).strip())
    else:
        body = str(value or "").strip()
    if not body:
        return ""
    return t("sess.reflect", lang, label=slot_label(slot, lang), body=body)


def slot_report(card: Card, lang: str = "en") -> dict[str, Any]:
    """인터뷰 화면 오른쪽 패널 — 어느 칸이 비었고 다음에 뭘 물을지."""
    return {
        "filled": [slot_label(s, lang) for s in card.filled],
        "missing": [slot_label(s, lang) for s in card.missing],
        "completeness": round(card.completeness, 2),
        "citable": card.citable(),
        "blocker": slot_label("cues", lang) if not card.cues else "",
        "next_question": slot_question(card.missing[0], lang) if card.missing else "",
        "slots": [
            {"key": s, "label": slot_label(s, lang), "filled": s in card.filled}
            for s in SLOTS
        ],
    }
