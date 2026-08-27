"""언어 협상과 문안 카탈로그 — **의존성 0**.

대회 규정 6조: *"The Application must, at a minimum, support English language use."*
그래서 영어는 선택 기능이 아니라 통과 조건이다.

설계 원칙 두 개:

1. **코어는 언어를 모른다.** ``app/core`` 는 열거형과 키를 반환하고, 문장은
   표현 층(웹·API)에서 만든다. 판정 로직에 언어가 섞이면 둘 다 망가진다.
2. **기본값은 영어다.** 심사자는 아무것도 누르지 않아도 영어를 본다.
   ``Accept-Language`` 에 한국어가 먼저 오면 한국어로 뜬다 — 유돈은 한국어로 쓴다.

카드의 *내용*(신호·판단·실패담)은 번역하지 않는다. 그건 전문가가 자기 현장
용어로 쓴 원본이고, 번역하는 순간 지식이 아니라 요약이 된다.
"""

from __future__ import annotations

LANGS = ("en", "ko")
DEFAULT = "en"


def pick(accept_language: str | None = None, override: str | None = None) -> str:
    """``?lang=`` 우선, 그다음 ``Accept-Language``, 그다음 영어.

    q-value 를 엄밀히 파싱하지 않는다 — 앞에 나온 태그가 이긴다는 규칙 하나로
    충분하고, 틀려도 예측 가능하다.
    """
    if override in LANGS:
        return override
    if not accept_language:
        return DEFAULT
    for chunk in accept_language.split(","):
        tag = chunk.split(";")[0].strip().lower()
        if tag.startswith("ko"):
            return "ko"
        if tag.startswith("en"):
            return "en"
    return DEFAULT


#: 문안. ``{키: {언어: 문장}}``. 값에 ``{}`` 자리표시자를 쓸 수 있다.
CATALOG: dict[str, dict[str, str]] = {
    # ── 공통 ──────────────────────────────────────────────────────────
    "app.tagline": {
        "en": "The senior leaves. The judgment stays.",
        "ko": "선배는 떠나도, 판단은 남는다.",
    },
    "app.sub": {
        "en": "What retires with an expert is not documents — it is the eye that "
              "reads a situation. yudonKnow hands them instruments to dig it out "
              "themselves, and leaves an alter the juniors keep working with.",
        "ko": "퇴직과 함께 사라지는 것은 문서가 아니라 상황을 읽는 눈입니다. "
              "yudonKnow 는 스스로 파낼 연장을 쥐여주고, 후배가 계속 같이 일할 "
              "분신을 남깁니다.",
    },
    "nav.expert": {"en": "Expert", "ko": "전문가"},
    "nav.junior": {"en": "Junior", "ko": "후배"},
    "nav.admin": {"en": "Admin", "ko": "관리자"},
    "nav.me": {"en": "me", "ko": "나"},
    "nav.open": {"en": "Open", "ko": "열기"},
    "nav.id": {"en": "your id", "ko": "아이디"},
    "nav.home": {"en": "Home", "ko": "홈"},
    "lang.switch": {"en": "한국어", "ko": "English"},
    "stub.mode": {
        "en": "stub mode — every flow still runs",
        "ko": "stub 모드 · 동선은 그대로 돕니다",
    },

    # ── 랜딩 ──────────────────────────────────────────────────────────
    "landing.yours.title": {
        "en": "What you leave here is yours.",
        "ko": "여기 남기는 것은 당신 것입니다.",
    },
    "landing.yours.body": {
        "en": "· Private — only you\n· Sealed — opens on a date you pick\n"
              "· Targeted — one named successor\n· Export everything, any time\n"
              "· If your alter talks nonsense, you switch it off\n"
              "· War stories are never linked to HR records",
        "ko": "· 지금은 나만 보기 (비공개)\n· 내가 정한 날에 열기 (봉인)\n"
              "· 특정 후배에게만 (지목)\n· 언제든 전량 내보내기\n"
              "· 분신이 헛소리하면 당신이 끕니다\n"
              "· 실패담은 인사 기록과 연결되지 않습니다",
    },
    "landing.who": {"en": "Who are you here as?", "ko": "누구로 들어오시나요"},
    "landing.expert.body": {
        "en": "Pick an instrument and dig. Three minutes leaves one judgment behind.",
        "ko": "연장을 골라 스스로 팝니다. 3분이면 판단 하나가 남습니다.",
    },
    "landing.expert.cta": {"en": "Leave what I know", "ko": "내 지식 남기기"},
    "landing.junior.body": {
        "en": "Ask the senior's alter. The source card always comes with the answer.",
        "ko": "선배의 분신에게 묻습니다. 근거 카드가 항상 함께 옵니다.",
    },
    "landing.junior.ph": {"en": "senior's id (e.g. yudon)", "ko": "선배 아이디 (예: yudon)"},
    "landing.junior.cta": {"en": "Ask the alter", "ko": "분신에게 묻기"},
    "landing.admin.body": {
        "en": "Who leaves, and what goes with them. The sort order is the intervention order.",
        "ko": "누가 나가면 무엇이 비는지. 정렬 순서가 곧 개입 순서입니다.",
    },
    "landing.admin.cta": {"en": "Succession risk board", "ko": "승계 리스크 보드"},
    "landing.wheel": {"en": "One turn of the wheel", "ko": "한 바퀴"},
    "landing.wheel.body": {
        "en": "① Pick an instrument and dig → ② a judgment card → ③ you approve it "
              "(and set who may see it)\n④ A junior asks your alter → ⑤ it answers "
              "from your cards and lays the evidence beside it\n⑥ The junior reports "
              "what happened → ✔ verified in the field\n⑦ What the alter could not "
              "answer returns to your queue → that sets where you dig next\n"
              "⑧ The traces come back to you — that is the point.",
        "ko": "① 연장을 골라 판다 → ② 판단 카드 → ③ 내가 승인 (공개 범위도 내가)\n"
              "④ 후배가 분신에게 묻는다 → ⑤ 내 카드로 답한다 + 근거를 함께 편다\n"
              "⑥ 후배가 결과를 보고한다 → ✔ 현장 검증\n"
              "⑦ 분신이 못 답한 것은 내 큐로 돌아온다 → 다음에 팔 곳이 정해진다\n"
              "⑧ 쓰인 흔적이 나에게 돌아온다 — 보람",
    },
    "landing.ask.need_id": {
        "en": "Enter the senior's id.", "ko": "선배 아이디를 입력해 주세요.",
    },

    # ── 온보딩 ────────────────────────────────────────────────────────
    "ob.title": {"en": "It's yours.", "ko": "당신 것입니다."},
    "ob.lede": {
        "en": "Three questions. We will not ask you for a document.",
        "ko": "세 가지만 여쭙습니다. 문서는 요구하지 않습니다.",
    },
    "ob.q1": {
        "en": "1. What can this team not do without you?",
        "ko": "1. 당신이 없으면 이 팀이 못 하는 일은 무엇인가요?",
    },
    "ob.q1.ph": {
        "en": "One per line. For example:\nReading defect causes on a new mould's "
              "first run\nFirst response to a supplier quality incident\n"
              "Predicting equipment failure from how it sounds",
        "ko": "한 줄에 하나씩. 예)\n신규 금형 초도 양산 때 불량 원인 판독\n"
              "협력사 품질 사고 초기 대응\n설비 이상음으로 고장 예측",
    },
    "ob.q1.note": {
        "en": "You can add more at any time.", "ko": "나중에 얼마든지 늘릴 수 있습니다.",
    },
    "ob.q2": {
        "en": "2. How you talk — your alter will speak like this",
        "ko": "2. 당신의 말투 — 분신이 이걸로 말합니다",
    },
    "ob.q2.ph1": {
        "en": "Things you say often (one per line)\ne.g. It's not the temperature. "
              "Look at the speed first.",
        "ko": "자주 하시는 말 (한 줄에 하나)\n예) 그거 온도 아니야, 속도부터 봐",
    },
    "ob.q2.ph2": {
        "en": "What you tell juniors never to do (one per line)\ne.g. Never reset to "
              "defaults before you know the cause.",
        "ko": "후배에게 절대 하지 말라고 가르치는 것 (한 줄에 하나)\n"
              "예) 원인 모른 채 설정값 되돌리지 마라",
    },
    "ob.q3": {
        "en": "3. How long are you here?",
        "ko": "3. 언제까지 계시나요?",
    },
    "ob.q3.note": {
        "en": "(optional — so we dig the urgent areas first)",
        "ko": "(선택 — 급한 곳부터 파기 위해서입니다)",
    },
    "ob.start": {"en": "Start", "ko": "시작하기"},
    "ob.need_id": {
        "en": "Enter your id at the top first.", "ko": "상단에 아이디를 입력해 주세요.",
    },

    # ── 전문가 홈 ─────────────────────────────────────────────────────
    "home.stop_alter": {"en": "Pause my alter", "ko": "내 분신 잠시 멈추기"},
    "home.start_alter": {"en": "Switch my alter back on", "ko": "내 분신 다시 켜기"},
    "home.export": {"en": "Export my cards", "ko": "내 카드 내보내기"},
    "home.meet": {"en": "Meet my alter", "ko": "내 분신 만나보기"},
    "home.staying": {"en": "still here", "ko": "재직 중"},
    "home.left": {"en": "{} days since leaving", "ko": "퇴직 후 {}일"},
    "home.stats": {
        "en": "{alive} judgments live · {verified} verified in the field · "
              "cited {cited} times · helped {helped} / missed {missed}",
        "ko": "살아있는 판단 {alive} · 현장 검증 {verified} · 인용 {cited}회 · "
              "도움됨 {helped} / 안 맞음 {missed}",
    },
    "home.gaps.head": {
        "en": "🔴 Juniors asked these and I could not answer — {} of them",
        "ko": "🔴 후배가 물었는데 제가 못 답한 것 {}건",
    },
    "home.gaps.count": {"en": "asked {} times", "ko": "{}번 물었습니다"},
    "home.gaps.cta": {
        "en": "Three minutes is enough to answer this →",
        "ko": "3분이면 답할 수 있습니다 →",
    },
    "home.contested.head": {
        "en": "⚠ Juniors said these did not hold — {} of them",
        "ko": "⚠ 후배가 \"안 맞았다\"고 한 판단 {}건",
    },
    "home.contested.body": {
        "en": "helped {helped} / missed {missed}",
        "ko": "도움됨 {helped} / 안 맞음 {missed}",
    },
    "home.map": {"en": "🗺 Map of what's in your head", "ko": "🗺 머릿속 지도"},
    "home.map.cards": {"en": "cards {}", "ko": "카드 {}"},
    "home.map.empty": {
        "en": "No areas yet. Plant a flag below.",
        "ko": "아직 영역이 없습니다. 아래에서 깃발을 꽂아보세요.",
    },
    "home.flag.ph": {
        "en": "🚩 Plant a flag on an area still untouched",
        "ko": "아직 크게 남은 영역에 🚩 깃발 꽂기",
    },
    "home.flag.cta": {"en": "Plant", "ko": "꽂기"},
    "home.hands": {
        "en": "🔴 {} of these do not go into words — they are collected separately "
              "as apprenticeship items.",
        "ko": "🔴 손끝 지식 {}건은 글로 담기지 않습니다 — 도제 항목으로 따로 모았습니다.",
    },
    "home.toolbox": {
        "en": "🧰 Toolbox — what will you dig with today?",
        "ko": "🧰 도구함 — 오늘 무엇으로 파시겠습니까",
    },
    "home.tool.start": {"en": "Start with this", "ko": "이걸로 시작"},
    "home.tool.mins": {"en": "about {} min", "ko": "약 {}분"},
    "home.locked": {
        "en": "{} more instruments unlock once a few judgments pile up. Too many "
              "choices and nobody picks any.",
        "ko": "연장 {}개는 판단이 몇 개 쌓이면 열립니다. 선택지가 많으면 아무것도 "
              "고르지 않게 되니까요.",
    },

    # ── 발굴 세션 ─────────────────────────────────────────────────────
    "sess.from_gap": {
        "en": "This is where a junior got stuck.", "ko": "후배가 막힌 곳입니다.",
    },
    "sess.answer.ph": {
        "en": "Say it the way you'd say it out loud. No need to tidy it up.",
        "ko": "말하듯이 적어주세요. 정리하지 않으셔도 됩니다.",
    },
    "sess.next": {"en": "Next question", "ko": "다음 질문"},
    "sess.skip": {"en": "I'll skip this one", "ko": "이건 넘길게요"},
    "sess.building": {"en": "The judgment taking shape", "ko": "지금 만들어지는 판단"},
    "sess.tacit.q": {"en": "🌡 Does this go into words?", "ko": "🌡 이건 읽어서 되나요?"},
    "sess.vis.q": {"en": "Who may see this?", "ko": "누가 볼 수 있나요?"},
    "sess.confirm": {"en": "Leave it like this", "ko": "이대로 남기기"},
    "sess.wrap_up": {
        "en": " · a good place to wrap up", "ko": " · 슬슬 마무리해도 좋습니다",
    },
    "sess.blocker": {
        "en": "Without cues — what you see that others miss — a junior cannot use "
              "this judgment.",
        "ko": "신호(무엇을 보고 아는가)가 비면 후배가 이 판단을 쓸 수 없습니다.",
    },
    "sess.need_answer": {
        "en": "Even one line helps. If it's really hard, skip it.",
        "ko": "한 줄만이라도 적어주세요. 정 어려우면 넘기셔도 됩니다.",
    },
    "sess.no_card": {
        "en": "No judgment has formed yet. One more answer.",
        "ko": "아직 판단이 만들어지지 않았습니다. 한 번만 더 답해주세요.",
    },
    "sess.saved": {"en": "Left behind.", "ko": "남겼습니다."},
    "sess.filled_gap": {
        "en": " This unblocks the junior who was stuck on 「{}」.",
        "ko": " 후배가 막혔던 「{}」이 이걸로 뚫립니다.",
    },
    "sess.wrong.prompt": {
        "en": "Here is my answer. Is it right?", "ko": "제가 낸 답입니다. 맞습니까?",
    },
    "sess.wrong.note": {
        "en": "If it's wrong, just point at the part that's wrong.",
        "ko": "틀렸다면 어디가 틀렸는지만 오른쪽에 적어주세요.",
    },

    # ── 통제권 선택지 ─────────────────────────────────────────────────
    "vis.public": {"en": "Open to the company", "ko": "사내 공개"},
    "vis.targeted": {"en": "Only one person I name", "ko": "지목한 사람에게만"},
    "vis.sealed": {"en": "Sealed — opens on a date I pick", "ko": "봉인 — 내가 정한 날에 열기"},
    "vis.private": {"en": "Private — only me", "ko": "비공개 — 나만"},
    "vis.who.ph": {"en": "For whom? (id)", "ko": "누구에게? (아이디)"},
    "vis.when.ph": {"en": "Open on? (2026-12-31)", "ko": "언제 열까요? (2026-12-31)"},
    "tacit.speakable": {
        "en": "🟢 Read it and you can do it", "ko": "🟢 읽으면 따라 할 수 있다",
    },
    "tacit.partial": {
        "en": "🟡 Read it, then try it a few times", "ko": "🟡 읽고 몇 번 해봐야 한다",
    },
    "tacit.hands": {
        "en": "🔴 It's in the hands — you have to watch",
        "ko": "🔴 손끝이다 — 옆에서 봐야 한다",
    },

    # ── 카드 칸 ───────────────────────────────────────────────────────
    "slot.situation": {"en": "Situation", "ko": "상황"},
    "slot.cues": {"en": "Cues", "ko": "신호"},
    "slot.judgment": {"en": "Judgment", "ko": "판단"},
    "slot.action": {"en": "Action", "ko": "조치"},
    "slot.rationale": {"en": "Why", "ko": "근거"},
    "slot.exceptions": {"en": "Exceptions", "ko": "예외"},
    "slot.failure": {"en": "War story", "ko": "실패담"},

    # ── 분신 화면 ─────────────────────────────────────────────────────
    "alter.of": {"en": "{}'s alter", "ko": "{}의 분신"},
    "alter.disclaimer": {
        "en": "This answer comes from judgment cards the expert left, not from a "
              "person. Nothing is written without a source.",
        "ko": "이 답은 사람이 아니라 남겨진 판단 카드에서 나옵니다. 근거 없이는 한 "
              "문장도 만들지 않습니다.",
    },
    "alter.ask.ph": {
        "en": "Ask the way you'd ask them — e.g. flow marks only on one side",
        "ko": "선배에게 묻듯이 물어보세요 — 예) 플로우마크가 한쪽만 나와요",
    },
    "alter.ask.cta": {"en": "Ask", "ko": "묻기"},
    "alter.evidence": {"en": "Evidence", "ko": "근거"},
    "alter.verified": {"en": "✔ verified in the field", "ko": "✔ 현장 검증"},
    "alter.unverified": {"en": "not verified yet", "ko": "아직 검증 전"},
    "alter.cues": {"en": "What tells you", "ko": "무엇을 보고 아는가"},
    "alter.action": {"en": "Do this", "ko": "조치"},
    "alter.exceptions": {
        "en": "⚠ Exceptions — drop this rule here", "ko": "⚠ 예외 — 여기선 이 규칙 버리세요",
    },
    "alter.failure": {"en": "When it went wrong", "ko": "실패담"},
    "alter.unspeakable": {
        "en": "🔴 Not captured in words:", "ko": "🔴 글로 안 담긴 부분:",
    },
    "alter.contested": {
        "en": "⚠ Someone recently reported this did not hold.",
        "ko": "⚠ 이 판단은 최근 안 맞았다는 보고가 있습니다.",
    },
    "alter.gap.note": {
        "en": "Saying \"I don't know\" is a feature here, not a failure. It will not "
              "make something up.",
        "ko": "모른다고 말하는 것도 이 분신의 기능입니다. 지어내지 않습니다.",
    },
    "alter.report.ok": {"en": "I tried it — it worked", "ko": "이대로 해서 잘 됐다"},
    "alter.report.no": {"en": "It didn't hold", "ko": "안 맞았다"},
    "alter.report.ok.q": {"en": "What got better? (optional)", "ko": "무엇이 좋아졌나요? (선택)"},
    "alter.report.no.q": {
        "en": "What was different? This goes straight to them.",
        "ko": "무엇이 달랐나요? 선배에게 그대로 전해집니다.",
    },
    "alter.report.ok.done": {
        "en": "Reported. It shows on their screen right away — your 30 seconds is "
              "what they get back.",
        "ko": "보고했습니다. 선배 화면에 바로 뜹니다 — 당신의 30초가 선배의 보람이 됩니다.",
    },
    "alter.report.no.done": {
        "en": "Sent. They will look at this judgment again.",
        "ko": "전달했습니다. 선배가 이 판단을 다시 봅니다.",
    },
    "alter.stubbed": {
        "en": "No LLM connected — showing the source cards verbatim.",
        "ko": "LLM 미연결 — 카드 원문을 그대로 보여드렸습니다.",
    },
    "alter.footer": {
        "en": "An alter never impersonates a person. When it doesn't know, it says so.",
        "ko": "분신은 사람을 사칭하지 않습니다. 모르면 모른다고 말합니다.",
    },
    "alter.gone": {"en": "they have already left", "ko": "이미 떠나셨습니다"},
    "alter.dday": {"en": "leaves in {} days", "ko": "재직 D-{}"},

    # ── 분신이 내는 문장 (LLM 을 거치지 않는 것들) ────────────────────
    "alter.msg.stopped": {
        "en": "{label} is paused right now. They switched it off themselves.",
        "ko": "{label}은 지금 멈춰 있습니다. 본인이 직접 정지시켜 두었습니다.",
    },
    "alter.msg.gap": {
        "en": "This is not an area {name} left behind.\nI will not make it up.",
        "ko": "이건 {name}님이 남기지 않은 영역입니다.\n지어내지 않겠습니다.",
    },
    "alter.msg.gap.sent": {
        "en": "▸ Your question was passed on as-is",
        "ko": "▸ 질문을 그대로 전달했습니다",
    },
    "alter.msg.gap.dday": {"en": " (leaves in {} days)", "ko": " (재직 D-{})"},
    "alter.msg.gap.alt": {
        "en": "▸ Others who left something in this area: {}",
        "ko": "▸ 비슷한 영역을 남긴 사람: {}",
    },
    "alter.msg.apprentice": {
        "en": "They marked this as something you cannot get from reading. Watch it "
              "done in person if you can.",
        "ko": "이 판단은 읽어서 되는 종류가 아니라고 표시해 두셨습니다. 가능하면 직접 "
              "옆에서 보세요.",
    },
    "alter.msg.stub": {
        "en": "⚠ No LLM connected — here are the judgment cards, verbatim.",
        "ko": "⚠ LLM 미연결 — 남기신 판단 카드를 그대로 보여드립니다.",
    },

    # ── 관리자 ────────────────────────────────────────────────────────
    "admin.title": {
        "en": "Who leaves, and what goes with them", "ko": "누가 나가면 무엇이 비나",
    },
    "admin.lede": {
        "en": "The sort order is the intervention order. Assign excavation sessions "
              "from the top.",
        "ko": "정렬 순서가 곧 개입 순서입니다. 맨 위부터 인터뷰를 배정하세요.",
    },
    "admin.empty": {
        "en": "No experts registered yet.", "ko": "아직 등록된 전문가가 없습니다.",
    },
    "admin.risk": {"en": "risk {}", "ko": "리스크 {}"},
    "admin.cards": {"en": "{} cards", "ko": "카드 {}"},
    "admin.gaps": {"en": "{} unanswered", "ko": "미답 공백 {}"},
    "admin.cov": {
        "en": "coverage {cov}% · 🔴 in-the-hands {hands}% · emptiest area: {weak}",
        "ko": "커버리지 {cov}% · 🔴 손끝 {hands}% · 가장 빈 영역: {weak}",
    },
    "admin.ask": {"en": "Ask this alter", "ko": "분신에게 물어보기"},
    "admin.caveat": {
        "en": "※ This is <b>not a personal performance metric.</b> The moment it is "
              "used for surveillance, excavation stops. Always read coverage next to "
              "the 🔴 in-the-hands share — that is what could <b>not</b> be captured.",
        "ko": "※ 이 화면은 <b>개인 성과 지표가 아닙니다.</b> 감시로 쓰이는 순간 발굴이 "
              "멈춥니다. 커버리지 %는 항상 🔴 손끝 비율과 함께 읽으세요 — 담지 "
              "<b>못한</b> 양이 거기 있습니다.",
    },
    "risk.high": {"en": "critical", "ko": "심각"},
    "risk.mid": {"en": "moderate", "ko": "중"},
    "risk.low": {"en": "low", "ko": "저"},

    # ── 유산 원장 ─────────────────────────────────────────────────────
    "ledger.card_confirmed": {
        "en": "You left one judgment behind", "ko": "판단 하나를 남기셨습니다",
    },
    "ledger.cited": {
        "en": "answered using your judgment", "ko": "당신의 판단으로 답했습니다",
    },
    "ledger.helped": {"en": "says it helped", "ko": "도움이 됐다고 합니다"},
    "ledger.missed": {
        "en": "says it did not hold here — worth a look",
        "ko": "이 경우엔 안 맞았다고 합니다 — 한번 봐주세요",
    },
    "ledger.anchored": {"en": "verified in the field", "ko": "현장에서 검증됐습니다"},
    "ledger.gap_filled": {
        "en": "You unblocked where a junior was stuck",
        "ko": "후배가 막혔던 곳을 뚫어주셨습니다",
    },
    "ledger.thanks": {"en": "A junior left thanks", "ko": "후배가 감사를 남겼습니다"},
    "ledger.headline.both": {
        "en": "{askers} juniors came to you. Your judgment answered {cited} of their "
              "questions.",
        "ko": "후배 {askers}명이 물었고, 그중 {cited}번을 당신의 판단으로 답했습니다.",
    },
    "ledger.headline.alive": {
        "en": "{alive} judgments are alive. Nobody has asked yet — but they are here.",
        "ko": "판단 {alive}개가 살아 있습니다. 아직 아무도 묻지 않았지만, 남아 있습니다.",
    },
    "ledger.headline.empty": {
        "en": "Nothing left behind yet. Three minutes leaves the first one.",
        "ko": "아직 아무것도 남기지 않으셨습니다. 3분이면 첫 하나가 남습니다.",
    },

    # ── 오류 (규칙 위반은 사용자에게 그대로 보여준다) ─────────────────
    "err.no_expert": {
        "en": "Could not find '{}'.", "ko": "'{}' 를 찾을 수 없습니다.",
    },
    "err.no_card": {"en": "Could not find that card.", "ko": "그 카드를 찾을 수 없습니다."},
    "err.no_turn": {
        "en": "Could not find that question.", "ko": "그 질문을 찾을 수 없습니다.",
    },
    "err.no_session": {"en": "Could not find the session.", "ko": "세션을 찾을 수 없습니다."},
    "err.already_answered": {
        "en": "You already answered that one.", "ko": "이미 답하신 질문입니다.",
    },
    "err.bad_verdict": {"en": "That report value is not valid.", "ko": "보고 값이 올바르지 않습니다."},
    "err.no_cues": {
        "en": "Cues are empty. Without 'what tells you', a junior cannot use this. "
              "One line is enough.",
        "ko": "신호가 비어 있습니다. '무엇을 보고 아는가' 없이는 후배가 쓸 수 없습니다. "
              "한 줄만 채워주세요.",
    },
    "warn.no_exceptions": {
        "en": "Exceptions are empty. A judgment with no exceptions is dangerous for "
              "a junior.",
        "ko": "예외가 비어 있습니다. 예외 없는 판단은 후배에게 위험합니다.",
    },
}


def t(key: str, lang: str = DEFAULT, /, *args: object, **kwargs: object) -> str:
    """문안 하나. 없는 키는 키 자체를 돌려준다 — 빈 화면보다 낫다."""
    entry = CATALOG.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get(DEFAULT) or key
    if args or kwargs:
        try:
            return text.format(*args, **kwargs)
        except (IndexError, KeyError):
            return text
    return text


def bundle(lang: str = DEFAULT) -> dict[str, str]:
    """템플릿·브라우저로 통째로 넘길 한 언어분 사전."""
    return {key: (entry.get(lang) or entry.get(DEFAULT) or key)
            for key, entry in CATALOG.items()}
