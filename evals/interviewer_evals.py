"""면접자 골든셋 평가 — 기저를 바꾸는 날, 인터뷰 품질이 조용히 무너지는 것을 잡는다.

pytest 가 아니라 **실기저 평가**다 (LLM 필요, 비결정적). 실행:

    YDK_LLM_PROVIDER=gemini YDK_VERTEX_PROJECT=<proj> YDK_VERTEX_LOCATION=global \\
        python evals/interviewer_evals.py

판정은 구조적 성질만 본다 — 문구가 아니라 **면접 수(手)가 유지되는가**:
비협조 페르소나 4종(횡설수설·일반론 도피·딴소리·무성의)에 대해 사람
지식공학자라면 두었을 수를 두는가. 문안 취향 채점은 하지 않는다.
근거: docs/elicitation-protocol.md §5 (2026-08-28 수동 실측의 자동화).
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from app.capture.interview import next_question  # noqa: E402
from app.capture.llm import get_llm  # noqa: E402
from app.core.card import Card  # noqa: E402

LLM = get_llm()
FAILS: list[str] = []


def check(name: str, ok: bool, detail: str) -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} — {detail[:90]}")
    if not ok:
        FAILS.append(name)


def q_after(history, card=None, lang="ko", last_slot="", last_rung=""):
    return next_question(
        LLM, instrument="moment", card=card, history=history,
        last_rung=last_rung, last_slot=last_slot, lang=lang,
    ).text


CARD_KO = Card(id="c1", expert="e", title="", situation="협력사 초도품 검사 중 이상 감지")

# ① 사건 3개 횡설수설 → 하나만 잡거나, 전문가에게 고르게 한다.
q = q_after([("방금 무슨 상황이었나요?",
              "아이고 많죠. 작년 프레스 금형 깨진 거, 재작년 도금 전량 회수, "
              "얼마 전 신입이 지그 거꾸로 물린 거. 하루이틀이 아니에요")],
            card=Card(id="c1", expert="e", title=""), last_slot="situation")
hits = sum(w in q for w in ("금형", "도금", "지그"))
check("multi-incident", hits == 1 or ("하나" in q and "고르" in q),
      f"언급 사건 수={hits} · {q}")

# ② 일반론 도피 → 사건·구체로 끌어내린다.
q = q_after([("방금 무슨 상황이었나요?", "신규 라인 초도 검사 때였죠"),
             ("무엇을 보고 아셨나요?", "품질은 결국 온도 관리가 중요합니다. 기본에 충실해야죠")],
            card=CARD_KO, last_slot="cues")
check("generality-pull", any(w in q for w in ("그때", "당시", "구체", "그날", "실제", "어떤")),
      q)

# ③ 딴소리 → 사건으로 복귀 (푸념에 반응하지 않는다).
q = q_after([("방금 무슨 상황이었나요?", "협력사 초도품 검사하다 이상해서 세웠어요"),
             ("무엇을 보고 아셨나요?", "요즘 애들은 기본이 안 돼 있어요. 우리 때는 어깨 너머로 배웠는데")],
            card=CARD_KO, last_slot="cues")
check("rant-return", ("초도품" in q or "검사" in q or "세우" in q or "이상" in q)
      and "요즘" not in q, q)

# ④ 무성의 → 무안 주지 않고 구체 프레임으로 재질문.
q = q_after([("방금 무슨 상황이었나요?", "도금 두께 검사였어요"),
             ("무엇을 보고 아셨나요?", "네 뭐 그렇죠")],
            card=CARD_KO, last_slot="cues")
check("curt-retry", any(w in q for w in ("구체", "어떤", "무엇", "그때", "당시")), q)

# ⑤ 캡처 언어 — 영어 발화는 영어 카드로 (한글 혼입 0).
from app.capture.interview import capture  # noqa: E402
draft = capture(LLM, [
    ("What was the situation?",
     "New torque guns, all green readings, but I stopped the line."),
    ("What told you?",
     "The sound — a ring after the click. The bolt is stretching."),
], lang="en")
blob = str(draft.data)
check("capture-lang-en", not any("가" <= ch <= "힣" for ch in blob),
      draft.data.get("title", "")[:60])

print()
if FAILS:
    print(f"✗ {len(FAILS)} failed: {FAILS}")
    sys.exit(1)
print("✓ 면접 수(手) 5종 유지 — 기저 교체 후에도 이 파일이 통과해야 한다.")
