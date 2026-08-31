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
    "landing.inversion": {
        "en": "Most AI answers your questions. This one asks you.",
        "ko": "대부분의 AI 는 당신의 질문에 답합니다. 이건 당신에게 묻습니다.",
    },
    "landing.yours.title": {
        "en": "What you leave here is yours.",
        "ko": "여기 남기는 것은 당신 것입니다.",
    },
    "landing.yours.body": {
        "en": "· Private — only you\n· Sealed — opens on a date you pick\n"
              "· Targeted — one named successor\n· Export everything, any time\n"
              "· If your alter talks nonsense, you switch it off\n"
              "· War stories are never linked to HR records\n"
              "· Every verified use is counted — a usage statement you can bill with",
        "ko": "· 지금은 나만 보기 (비공개)\n· 내가 정한 날에 열기 (봉인)\n"
              "· 특정 후배에게만 (지목)\n· 언제든 전량 내보내기\n"
              "· 분신이 헛소리하면 당신이 끕니다\n"
              "· 실패담은 인사 기록과 연결되지 않습니다\n"
              "· 쓰인 만큼 셉니다 — 사용 명세서로 회사에 청구할 수 있습니다",
    },
    "landing.procedure": {
        "en": "① Task map → ② incident harvest → ③ timeline → ④ deep probes → "
              "⑤ judgment cards → ⑥ member checking — the knowledge-engineer's "
              "procedure, run by the agent, voice-first.",
        "ko": "① 과업 지도 → ② 사건 채집 → ③ 타임라인 → ④ 심화 → ⑤ 판단 카드 → "
              "⑥ 검증 — 지식공학자가 하던 절차 그대로, AI가 음성으로 진행합니다.",
    },
    "landing.judge.t": {"en": "One-click demo entry", "ko": "원클릭 데모 입장"},
    "landing.judge.c": {
        "en": "No sign-up, no password — pick a seat. Production identity is SSO.",
        "ko": "가입도 비밀번호도 없습니다 — 자리만 고르세요. 실배포 신원은 SSO 입니다.",
    },
    "landing.judge.watch": {"en": "Watch Dale's expert page", "ko": "Dale 전문가 화면 구경"},
    "landing.judge.ask": {"en": "Ask Dale's alter as a junior", "ko": "후배로 Dale 분신에 묻기"},
    "landing.judge.mine": {"en": "Be the expert (5 min)", "ko": "내가 전문가 되기 (5분)"},
    "landing.judge.note": {
        "en": "Showcase experts are read-only; everything opens on the expert you create.",
        "ko": "전시 전문가는 구경 전용입니다. 직접 만든 전문가에서는 전부 열립니다.",
    },
    "home.readonly": {
        "en": "👀 Viewing mode — this is a showcase expert. Browse the shelf, the "
              "memoir and the statement; digging and controls open on your own "
              "expert (make one in about 5 minutes from the landing page).",
        "ko": "👀 구경 모드 — 전시용 전문가입니다. 서가·회고록·명세서를 둘러보세요. "
              "발굴과 제어는 본인 전문가에서 열립니다 (첫 화면에서 약 5분).",
    },
    # 두 개의 문 — 역할은 자기분류가 아니라 행동에서 나온다.
    "door.expert.t": {"en": "🧑‍🏭 Enter as the senior", "ko": "🧑‍🏭 선배로 입장"},
    # 문 안의 역할 설명 — 시작 화면이 곧 안내다: 이 문으로 들어가면
    # 무엇을 하게 되는지 세 걸음으로.
    "door.expert.steps": {
        "en": "① The AI interviews you — you just talk (voice works)\n"
              "② You review and approve each judgment card — and the rules "
              "that may run\n"
              "③ What stays: your alter for the juniors, a memoir, and a "
              "usage statement that pays you back",
        "ko": "① AI가 인터뷰합니다 — 당신은 말만 하면 됩니다 (음성 가능)\n"
              "② 판단 카드와 실행 규칙을 검토·승인합니다\n"
              "③ 남는 것: 후배를 위한 분신, 회고록, 그리고 쓰인 만큼 "
              "돌아오는 사용 명세서",
    },
    "door.junior.steps": {
        "en": "① Ask in your own words — or walk the structured triage\n"
              "② Every answer cites the senior's card; open it and check\n"
              "③ Report \"helped / didn't hold\" after you try it — that "
              "earns the ✔ and pays the senior",
        "ko": "① 내 말로 묻거나, 판정 문진을 밟습니다\n"
              "② 모든 답에 선배의 근거 카드가 붙습니다 — 펴서 확인하세요\n"
              "③ 현장에서 써보고 '도움됐다/안 맞았다'를 보고하세요 — 그게 "
              "✔ 가 되고 선배에게 돌아갑니다",
    },
    "door.expert.c": {
        "en": "The AI interviews you — 3 minutes leaves a draft, 7 leaves a "
              "reviewed judgment card.",
        "ko": "AI 가 인터뷰합니다 — 3분이면 초안, 7분이면 검토까지 마친 "
              "판단 카드 한 장이 남습니다.",
    },
    "door.junior.t": {"en": "💬 Enter as the junior", "ko": "💬 후배로 입장"},
    "door.junior.c": {
        "en": "Ask — the alters answer only from their seniors' cards.",
        "ko": "질문하세요 — 분신은 선배가 남긴 카드로만 답합니다.",
    },
    "door.judge": {
        "en": "🎫 Judges use the same two doors — no sign-up, no password. Quick:",
        "ko": "🎫 심사위원도 같은 두 문입니다 — 가입·비밀번호 없음. 빠른 입장:",
    },
    "door.judge.mine": {"en": "expert in one click", "ko": "원클릭 전문가 되기"},
    # 통합 질문창 — 선배를 몰라도 질문부터. 답은 각 분신의 방에서.
    "portal.title": {
        "en": "Don't know whom to ask? Start with the question",
        "ko": "누구에게 물을지 모르면, 질문부터",
    },
    # 예시는 전시 전문가의 카드에 **실제로 걸리는** 질문이어야 한다 —
    # 첫 검색이 "없습니다" 로 끝나는 입구는 고장으로 보인다 (프로덕션 실측).
    "portal.ph": {
        "en": "e.g. The aeration foam went brown overnight — what now?",
        "ko": "예: 플로우마크가 게이트 반대쪽에만 생겨요",
    },
    "portal.btn": {"en": "Who left a judgment?", "ko": "누가 판단을 남겼나"},
    "portal.none": {
        "en": "No senior has left a judgment on this yet. Pick an alter below and "
              "ask anyway — the question reaches the senior as a gap.",
        "ko": "아직 이 질문에 판단을 남긴 선배가 없습니다. 아래 분신을 골라 그대로 "
              "물어보세요 — 질문은 공백으로 선배에게 전해집니다.",
    },
    "portal.hits": {"en": "cards that touch this: {}", "ko": "걸린 판단 {}장"},
    "portal.open": {"en": "Ask this alter →", "ko": "이 분신에게 묻기 →"},
    # 분신이 답을 짓는 동안의 단계 문구 — 20초가 침묵이면 고장으로 보인다.
    "alter.wait.search": {"en": "Searching the judgment cards…", "ko": "판단 카드를 찾는 중…"},
    "alter.wait.answer": {
        "en": "Composing the answer from the cards found…",
        "ko": "찾은 카드로 답을 짓는 중…",
    },
    "alter.wait.check": {
        "en": "Verifying every paragraph cites a real card…",
        "ko": "모든 문단의 근거 인용을 검증하는 중…",
    },
    # 화면 언어 ≠ 발굴 언어 — 번역 누락이 아니라 설계다. 그렇다고 말없이
    # 두면 번역 누락으로 보인다 (QA 실측).
    "home.dig_lang": {
        "en": "🔤 This expert digs in {lang} — the questions and cards stay in "
              "the language they were dug in.",
        "ko": "🔤 이 전문가는 {lang}로 발굴합니다 — 질문과 카드는 판 언어로 남습니다.",
    },
    "langname.ko": {"en": "Korean", "ko": "한국어"},
    "langname.en": {"en": "English", "ko": "영어"},
    "demo.identity": {
        "en": "Demo identity — no authentication, by design: a lightweight "
              "switcher lets judges test the senior and the junior roles "
              "immediately, on synthetic data. In production, owner access, "
              "visibility, and verified usage are bound to corporate SSO. This "
              "demo focuses on the knowledge-extraction and reuse engine.",
        "ko": "데모 신원 — 인증이 없는 것은 의도된 설계입니다: 가벼운 신원 "
              "전환으로 심사자가 선배·후배 역할을 즉시 오가며 시험할 수 "
              "있습니다(데이터는 합성). 실배포에서는 소유자 접근·공개범위·"
              "검증 사용이 사내 SSO 에 묶입니다. 이 데모의 초점은 지식 "
              "발굴·재사용 엔진입니다.",
    },
    "landing.demo_scope": {
        "en": "Demo scope: card content honors your visibility settings; "
              "profile name and usage counts are visible in this demo. "
              "Production scopes those behind corporate SSO.",
        "ko": "데모 범위: 카드 내용은 공개 설정을 따르지만, 프로필 이름과 "
              "사용 횟수는 이 데모에서 보입니다. 실배포에선 사내 SSO 가 "
              "이 범위를 잠급니다.",
    },
    "memoir.nothing_public": {
        "en": "This expert has not made anything public. The memoir is theirs.",
        "ko": "이 전문가는 공개로 남긴 것이 없습니다. 회고록은 본인의 "
              "것입니다.",
    },
    "landing.alters": {"en": "The alters left behind", "ko": "남겨진 분신들"},
    "landing.alter.cards": {"en": "{} judgment cards", "ko": "판단 카드 {}장"},
    "landing.alter.days": {"en": "retires in {} days", "ko": "은퇴까지 {}일"},
    "landing.mine.title": {"en": "Leave mine", "ko": "내 분신 만들기"},
    "landing.mine.body": {
        "en": "Answer as I ask — 3 minutes leaves a draft, 7 a reviewed card. "
              "It is yours — you set who may see it, and you can switch it off.",
        "ko": "묻는 대로 답하시면 3분에 초안, 7분에 검토된 카드가 남습니다. "
              "그건 당신 것입니다 — 공개 범위도, 끄는 것도 당신이 정합니다.",
    },
    "landing.admin.link": {
        "en": "Who leaves, and what goes empty — succession risk board →",
        "ko": "누가 나가면 무엇이 비는지 — 승계 리스크 보드 →",
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
    "landing.junior.ph": {"en": "senior's id", "ko": "선배 아이디"},
    "landing.junior.pick": {"en": "Whose alter?", "ko": "누구의 분신에게"},
    "landing.junior.cta": {"en": "Ask the alter", "ko": "분신에게 묻기"},
    "landing.admin.body": {
        "en": "Who leaves, and what goes with them. The sort order is the intervention order.",
        "ko": "누가 나가면 무엇이 비는지. 정렬 순서가 곧 개입 순서입니다.",
    },
    "landing.admin.cta": {"en": "Succession risk board", "ko": "승계 리스크 보드"},
    "nav.how": {"en": "How it works", "ko": "어떻게 작동하나"},
    # 프로토콜 뷰 — 대화가 아니라 절차로 밟는 후배 화면
    "proto.title": {"en": "{}'s field protocol", "ko": "{} 님의 현장 절차"},
    "proto.sub": {
        "en": "Compiled from the judgment cards — every screen cites its card. "
              "Pick what you see; the protocol branches on the expert's own "
              "exceptions.",
        "ko": "판단 카드에서 컴파일된 절차입니다 — 모든 화면에 근거 카드가 "
              "붙습니다. 보이는 것을 고르세요. 분기는 전문가 본인이 남긴 "
              "예외를 따릅니다.",
    },
    "proto.step1": {"en": "① Where are you?", "ko": "① 어느 일입니까?"},
    "proto.step2": {"en": "② What do you see?", "ko": "② 무엇이 보입니까?"},
    "proto.step3": {"en": "③ The judgment", "ko": "③ 판단"},
    "proto.match": {"en": "{} judgments", "ko": "판단 {}건"},
    "proto.matchsig": {"en": "{} of your signs match this card",
                        "ko": "고른 신호 중 {}개가 이 카드에 맞음"},
    # 안전 게이트 — 이 화면은 판정 엔진이 아니다 (외부 QA 실측: GREEN 류
    # 카드가 신호 하나로 통째 출력되는 것은 안전 도메인에서 못 쓴다).
    "proto.notengine": {
        "en": "This screen reads the expert's judgments — it does not decide "
              "for you. Before acting on a reassuring judgment, confirm every "
              "unchecked sign below. When an urgent judgment and a reassuring "
              "one both match, the urgent one wins.",
        "ko": "이 화면은 전문가의 판단을 열람하는 것이지 대신 판정하지 "
              "않습니다. 안심시키는 판단을 적용하기 전에 아래 미확인 신호를 "
              "전부 확인하세요. 위급한 판단과 안심시키는 판단이 같이 걸리면 "
              "위급한 쪽이 우선입니다.",
    },
    "proto.unmet": {
        "en": "⛔ Not yet confirmed — check these before applying this judgment",
        "ko": "⛔ 아직 확인 안 됨 — 이 판단을 적용하기 전에 확인하세요",
    },
    "proto.conflict": {
        "en": "⚠ {} judgments match together — the more urgent one takes "
              "priority. Never let a milder card cancel an urgent one.",
        "ko": "⚠ 판단 {}개가 함께 걸렸습니다 — 더 위급한 판단이 우선입니다. "
              "온화한 카드가 위급한 카드를 지우게 두지 마세요.",
    },
    "proto.first": {"en": "Do first", "ko": "먼저 할 것"},
    "proto.branch": {"en": "⚠ When this does NOT hold", "ko": "⚠ 이럴 땐 통하지 않는다"},
    "proto.fail": {"en": "It cost them once", "ko": "치른 값이 있다"},
    "proto.why": {"en": "Why", "ko": "왜"},
    "proto.basis": {"en": "Basis card", "ko": "근거 카드"},
    "proto.none": {
        "en": "None of these signs? The expert may not have left this yet — "
              "ask the alter; unanswered questions reach the expert.",
        "ko": "보이는 신호가 여기 없습니까? 아직 안 남긴 판단일 수 있습니다 — "
              "분신에게 물으세요. 못 답한 질문은 전문가에게 전해집니다.",
    },
    "proto.ask": {"en": "Ask the alter instead →", "ko": "분신에게 묻기 →"},
    "proto.verify": {
        "en": "Used this in the field? Report it on the alter page — that is "
              "what earns the ✔.",
        "ko": "현장에서 써보셨으면 분신 화면에서 보고해 주세요 — ✔ 은 그렇게만 "
              "붙습니다.",
    },
    "alter.protocol": {"en": "📋 Step-by-step protocol", "ko": "📋 절차로 밟기"},
    # 판정 모드 — 예/아니오/모름 3상 문진. '모름' 이 1급 시민이다.
    "proto.triage.t": {
        "en": "🚦 Structured triage — one question at a time",
        "ko": "🚦 판정 문진 — 한 번에 한 질문",
    },
    "proto.triage.c": {
        "en": "One questionnaire across ALL approved rules — no task picking, "
              "so an urgent judgment can never hide behind a different task "
              "name. Deterministic; unknowns never downgrade.",
        "ko": "승인된 규칙 전부를 **업무 구분 없이** 한 문진으로 충돌 "
              "검사합니다 — 위급 판단이 다른 업무명 뒤에 숨을 수 없습니다. "
              "결정론 실행이고, '모름'은 절대 하향되지 않습니다.",
    },
    "proto.triage.hint": {
        "en": "Answer one sign at a time; the verdict board updates after each "
              "answer and stops early the moment an urgent judgment is "
              "established.",
        "ko": "신호를 하나씩 답하면 답할 때마다 판이 갱신되고, 위급 판단이 "
              "성립하는 순간 조기 종료됩니다.",
    },
    "proto.browse.totriage": {
        "en": "Need a verdict? → Structured triage (one question at a time)",
        "ko": "판정이 필요하면 → 판정 문진 (한 번에 한 질문)",
    },
    "proto.browse3": {"en": "③ Read the judgments", "ko": "③ 판단 열람"},
    "proto.ruled_in_browse": {
        "en": "🚦 This judgment runs only in Structured triage — it has "
              "approved rules and is not shown as reading material.",
        "ko": "🚦 이 판단은 판정 문진에서만 실행됩니다 — 승인된 규칙이 있어 "
              "열람으로는 펼치지 않습니다.",
    },
    "proto.browse_fold": {
        "en": "📖 Reading only — not a verdict. Open to read the card.",
        "ko": "📖 열람 전용 — 판정이 아닙니다. 카드를 읽으려면 펼치세요.",
    },
    "proto.v.multi": {
        "en": "⚠ {n} judgments stand at once — executing priority {p} "
              "\u201c{t}\u201d; the rest are held.",
        "ko": "⚠ 판단 {n}건 동시 성립 — 우선순위 {p} 「{t}」 실행, 나머지는 "
              "보류합니다.",
    },
    "proto.v.held": {
        "en": "Held — a more urgent judgment is executing",
        "ko": "보류 — 더 위급한 판단이 실행됨",
    },
    "proto.gate.fold": {
        "en": "⛔ {} signs unconfirmed — confirm them, then open the judgment",
        "ko": "⛔ 미확인 신호 {}개 — 확인한 뒤 판단을 펼치세요",
    },
    "proto.triage.locked": {
        "en": "🚦 Structured triage opens when a card has approved rules AND "
              "its exceptions are covered by ask-able conditions — an exception "
              "the questionnaire cannot ask about would be a misdiagnosis "
              "waiting to happen. The approval screen pre-fills a draft and "
              "warns about uncovered exceptions.",
        "ko": "🚦 판정 문진은 카드에 승인된 규칙이 있고 **예외까지 문진으로 "
              "물을 수 있게 덮였을 때** 열립니다 — 예외를 못 묻는 문진은 "
              "오판이 되기 때문입니다. 승인 화면이 규칙 초안을 미리 채우고, "
              "안 덮인 예외를 경고합니다.",
    },
    "proto.restricted.t": {
        "en": "This protocol is not open to you",
        "ko": "이 프로토콜은 열람 권한이 없습니다",
    },
    "proto.restricted.c": {
        "en": "{} left these judgments private, for a named person, or sealed "
              "until a date. Nothing is shown so nothing leaks. If this is your "
              "own page, enter with the identity you created it under.",
        "ko": "{} 님이 이 판단들을 비공개·지목·봉인으로 남겼습니다. 내용이 새지 "
              "않도록 아무것도 표시하지 않습니다. 본인 페이지라면 만들 때의 "
              "신원으로 들어와 주세요.",
    },
    "proto.restricted.back": {
        "en": "Ask the alter instead", "ko": "분신에게 물어보기",
    },
    "proto.step_n": {"en": "Question {i} of {n}", "ko": "질문 {i} / {n}"},
    "proto.tri.skip": {"en": "Don't know — skip", "ko": "모름 — 넘어가기"},
    "proto.early": {
        "en": "An urgent judgment stands — questionnaire ends here.",
        "ko": "위급 판단이 성립했습니다 — 문진을 여기서 마칩니다.",
    },
    "proto.strip.standing": {"en": "still possible", "ko": "아직 가능"},
    "proto.strip.out": {"en": "ruled out", "ko": "배제"},
    "proto.strip.waiting": {"en": "not checked", "ko": "미확인"},
    "proto.counts": {"en": "{a} answered · {s} not needed",
                      "ko": "답한 질문 {a} · 불필요해진 질문 {s}"},
    "proto.browse_note": {"en": "Browse cards by area — not a decision flow",
                           "ko": "영역별 카드 열람 — 판정 흐름이 아닙니다"},
    "proto.showall": {"en": "See all questions at once", "ko": "질문 전체를 한 번에 보기"},
    "proto.tri.yes": {"en": "Yes", "ko": "예"},
    "proto.tri.no": {"en": "No", "ko": "아니오"},
    "proto.tri.unk": {"en": "Don't know", "ko": "모름"},
    "proto.evaluate": {"en": "Get the judgment →", "ko": "판정 받기 →"},
    "proto.v.applies": {"en": "The judgment stands", "ko": "판단 성립"},
    "proto.v.escalate": {
        "en": "⚠ Cannot be ruled out — do NOT downgrade. Confirm the items "
              "below or escalate now.",
        "ko": "⚠ 배제할 수 없습니다 — 하향하지 마세요. 아래 항목을 확인하거나 "
              "지금 상향하세요.",
    },
    "proto.v.refuted": {"en": "Ruled out by your answers", "ko": "답에 의해 배제됨"},
    "proto.v.insufficient": {"en": "Not triggered by your answers", "ko": "해당 신호 없음"},
    "proto.v.open": {
        "en": "No approved judgment stands on these answers — this is exactly "
              "when you ask the alter; the question reaches the expert.",
        "ko": "이 답으로는 성립하는 승인 판단이 없습니다 — 이럴 때가 분신에게 "
              "물을 때입니다. 질문은 전문가에게 전해집니다.",
    },
    "proto.v.blockers": {"en": "Confirm before this applies:", "ko": "성립 전 확인할 것:"},
    "proto.v.refutedby": {"en": "ruled out by", "ko": "배제 근거"},
    "proto.engine_note": {
        "en": "Deterministic run — only rules the expert approved execute; "
              "the AI is not consulted. Same answers, same verdict, every time.",
        "ko": "결정론 실행입니다 — 전문가가 승인한 규칙만 실행되고 AI 는 "
              "개입하지 않습니다. 같은 답이면 언제나 같은 판정입니다.",
    },
    # 전문가 승인 화면의 규칙 칸
    "cv.f.rule_all": {"en": "Rules — ALL must be true for this judgment (one per line; empty = reading only)",
                       "ko": "규칙 — 전부 '예' 여야 성립 (줄마다 하나 · 비우면 열람 전용)"},
    "cv.f.rule_none": {"en": "Rules — must ALL be absent", "ko": "규칙 — 전부 '아니오' 여야 성립"},
    "cv.f.rule_priority": {"en": "Priority on conflict (0 = reading, higher wins)",
                            "ko": "충돌 시 우선순위 (0 = 열람 전용 · 높을수록 우선)"},
    "cv.rule_uncovered": {
        "en": "⚠ {n} exception(s) on this card are not yet covered by the "
              "rules — add each as a none_of condition. Until then this card "
              "is reading-only in structured triage (a questionnaire that "
              "cannot ask about an exception would misjudge).",
        "ko": "⚠ 이 카드의 예외 {n}건이 아직 규칙에 반영되지 않았습니다 — "
              "각 예외를 '없어야(none_of)' 조건으로 추가하세요. 그 전까지 이 "
              "카드는 판정 문진에서 열람 전용입니다 (예외를 못 묻는 문진은 "
              "오판합니다).",
    },
    # 상태명 정직화 — 필수 조건 하나 충족을 '성립' 처럼 읽히게 하지 않는다.
    "cv.rule_draft": {
        "en": "✍ AI-drafted from this card's cues and exceptions — review, fix, "
              "then save. Nothing runs until you save.",
        "ko": "✍ 이 카드의 신호·예외에서 AI가 제안한 초안입니다 — 검토·수정 후 "
              "저장하세요. 저장 전에는 아무것도 실행되지 않습니다.",
    },
    "cv.f.unspeakable": {
        "en": "Not in words (delete lines the machine invented — this is your "
              "record, and only you edit it)",
        "ko": "글로 못 담은 것 (기계가 지어낸 줄은 지우세요 — 당신의 기록이고, "
              "고치는 손도 당신뿐입니다)",
    },
    "cv.f.rule_note": {
        "en": "Rules you approve here run deterministically on the protocol "
              "screen. Unknown answers never downgrade — they escalate.",
        "ko": "여기서 승인한 규칙만 절차 화면에서 결정론으로 실행됩니다. "
              "'모름' 은 절대 하향되지 않고 상향됩니다.",
    },
    "how.title": {"en": "How it works — one turn of the wheel",
                   "ko": "어떻게 작동하나 — 한 바퀴"},
    "how.1.t": {"en": "1 · The AI interviews you", "ko": "1 · AI가 인터뷰한다"},
    "how.1.c": {
        "en": "Not a chatbot waiting for input — it runs the knowledge "
              "engineer's procedure: task map, incident digging, deepening, "
              "your own review. You just answer.",
        "ko": "입력을 기다리는 챗봇이 아니라 지식공학자의 절차(과업 지도 → "
              "사건 채굴 → 심화 → 본인 검토)로 묻습니다. 당신은 답만 하면 됩니다.",
    },
    "how.2.t": {"en": "2 · Answers become judgment cards", "ko": "2 · 답이 판단 카드가 된다"},
    "how.2.c": {
        "en": "Situation · cues · judgment · action · exceptions · failure. "
              "You approve every card and set who may see it.",
        "ko": "상황·신호·판단·행동·예외·실패. 모든 카드는 본인이 승인하고 "
              "공개 범위도 본인이 정합니다.",
    },
    "how.3.t": {"en": "3 · The alter answers juniors", "ko": "3 · 분신이 후배에게 답한다"},
    "how.3.c": {
        "en": "Only from your cards, citing them paragraph by paragraph — a "
              "mechanical check discards any uncited answer. No cards, no "
              "answer: the question queues back to you instead.",
        "ko": "오직 당신의 카드로만, 문단마다 카드를 인용하며 — 인용 없는 답은 "
              "기계 검증이 통째로 버립니다. 근거가 없으면 답하지 않고, 그 질문이 "
              "당신의 발굴 큐로 돌아옵니다.",
    },
    "how.4.t": {"en": "4 · The field verifies", "ko": "4 · 현장이 검증한다"},
    "how.4.c": {
        "en": "Juniors report \"it helped\" or \"it didn't hold\" — the only "
              "source of the ✔ badge. No views, no likes.",
        "ko": "후배가 \"도움됐다 / 안 맞았다\" 를 보고합니다 — ✔ 배지의 유일한 "
              "출처. 조회수·좋아요는 세지 않습니다.",
    },
    "how.5.t": {"en": "5 · A memoir, not a database", "ko": "5 · 회고록이 남는다"},
    "how.5.c": {
        "en": "The same digging typesets a career memoir — drafts woven by AI, "
              "on the record only after the author approves.",
        "ko": "같은 발굴이 직업 회고록으로 조판됩니다 — AI가 엮은 초안은 본인이 "
              "승인해야 기록이 됩니다.",
    },
    "how.6.t": {"en": "6 · Use returns to the retiree", "ko": "6 · 쓰임이 은퇴자에게 돌아간다"},
    "how.6.c": {
        "en": "Every citation and field report lands on a usage statement — "
              "the verifiable basis for compensating knowledge after "
              "retirement.",
        "ko": "모든 인용과 현장 보고가 사용 명세서에 쌓입니다 — 퇴직 후 지식 "
              "보상의 검증 가능한 근거입니다.",
    },
    "how.honesty": {
        "en": "The rule underneath: judgment is never delegated to the LLM. "
              "Gap decisions, citation checks, memoir honesty — all "
              "deterministic code, all auditable. Generation is convenience; "
              "the cards are the truth.",
        "ko": "바닥의 원칙: 판정을 LLM에 위임하지 않습니다. 공백 판정·인용 "
              "검증·회고록 검열 — 전부 결정적 코드고, 전부 검사 가능합니다. "
              "생성은 편의고, 카드가 진실입니다.",
    },
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
    "ob.title": {
        "en": "Interview prep — one judgment card will stay behind",
        "ko": "인터뷰 준비 — 판단 카드 한 장을 남깁니다",
    },
    # 시작하면 무엇이 이어지는지 예고 — 초행이 "눌러도 되나" 를 넘게 한다.
    "ob.preview": {
        "en": "What happens next: ① the AI interviews you (voice works) → "
              "② you review the judgment card it builds → ③ you decide who "
              "may see it. It stays yours.",
        "ko": "시작하면: ① AI가 인터뷰합니다 (음성 가능) → ② 만들어진 판단 "
              "카드를 검토·승인합니다 → ③ 공개 범위는 당신이 정합니다. "
              "끝까지 당신 것입니다.",
    },
    "ob.have_cards": {
        "en": "Already have cards here? →", "ko": "이미 만든 카드가 있나요? →",
    },
    "ob.open_mine": {"en": "Open my cards", "ko": "내 카드 열기"},
    "ob.returning": {
        "en": "Been here before? Type your name in the ID box at the top and "
              "press Open — this form is only for a first visit.",
        "ko": "이미 파던 분이신가요? 상단 아이디 칸에 이름을 넣고 '열기'를 "
              "누르세요 — 이 화면은 처음 오신 분용입니다.",
    },
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
    "ob.start": {"en": "Start the AI interview (3 min for a draft, ~7 for a reviewed card)",
                   "ko": "AI 인터뷰 시작하기 (3분이면 초안, 약 7분이면 검토된 카드)"},
    #: 로그인이 없는 도구다. 이름은 화면 구석이 아니라 **첫 질문**으로 받는다 —
    #: 처음 온 사람은 상단 입력칸이 필수인 줄 모른다.
    "ob.q0": {
        "en": "1. What should we call you?",
        "ko": "1. 어떻게 불러드릴까요?",
    },
    "ob.q0.ph": {
        "en": "your name or employee id — e.g. hong",
        "ko": "성함이나 사번 — 예) 홍길동",
    },
    "ob.q0.note": {
        "en": "No password. This is the name your alter will carry, and how you come "
              "back to your own cards.",
        "ko": "비밀번호는 없습니다. 분신이 달고 다닐 이름이자, 내 카드로 다시 "
              "돌아오는 열쇠입니다.",
    },
    "ob.need_name": {
        "en": "Start with your name — the first box below (0).",
        "ko": "성함이나 사번부터요 — 아래 0번 칸입니다.",
    },
    "ob.new_here": {
        "en": "A fresh seat — pick what we should call you below and the "
              "interview starts.",
        "ko": "새 자리입니다 — 아래에서 부를 이름만 정하면 인터뷰가 "
              "시작됩니다.",
    },
    "dl.done": {"en": "Downloaded ✓", "ko": "내려받았습니다 ✓"},
    "ob.need_id": {
        "en": "Enter your id at the top first.", "ko": "상단에 아이디를 입력해 주세요.",
    },

    # ── 전문가 홈 ─────────────────────────────────────────────────────
    "home.stop_alter": {"en": "Pause my alter", "ko": "내 분신 잠시 멈추기"},
    "home.start_alter": {"en": "Switch my alter back on", "ko": "내 분신 다시 켜기"},
    "nav.library": {"en": "My study", "ko": "내 서재"},
    "nav.methods": {"en": "Other ways", "ko": "다른 방법"},
    "today.answer": {"en": "Answer — just talk", "ko": "답하기 — 말로 하면 됩니다"},
    "today.skip": {"en": "Not this one", "ko": "이 질문은 나중에"},
    "today.src.junior": {"en": "A junior asked and your alter could not answer:",
                          "ko": "후배가 물었는데 분신이 답하지 못했습니다:"},
    "today.src.doc": {"en": "Found in your procedure — it does not say:",
                       "ko": "절차서를 읽다 찾았습니다 — 문서가 답하지 않는 것:"},
    "today.src.voice": {"en": "Picked up from your recording:",
                         "ko": "혼잣말에서 건졌습니다:"},
    "today.src.flag": {"en": "You said this must be handed over:",
                        "ko": "남겨야 한다고 적으신 영역입니다:"},
    "today.src.map": {
        "en": "First, the map — where does the feel live in your job?",
        "ko": "먼저 지도부터 — 당신 일에서 '감'이 사는 곳이 어딘지요:",
    },
    "review.invite": {
        "en": "'{step}' has new cards piled up — shall we read them back and "
              "check nothing is missing?",
        "ko": "'{step}' 에 카드가 쌓였습니다 — 한번 읽어드릴 테니 빠진 게 "
              "없는지 봐주시겠어요?",
    },
    "review.opener": {
        "en": "Here is what we hold for '{step}' — {n} cards:\n{listing}\n\n"
              "Is a judgment missing? Name just one. If it is all there, say "
              "\"that's all\". (To fix a card's content, open it in your study.)",
        "ko": "'{step}' 에서 지금까지 뽑은 카드 {n}장입니다:\n{listing}\n\n"
              "빠진 판단이 있으면 하나만 불러주세요. 다 있으면 \"됐다\" 고 "
              "하시면 됩니다. (카드 내용을 고치실 건 서가에서 열어 고치세요.)",
    },
    "review.sealed": {
        "en": "'{step}' reviewed and sealed — I will ask again after a few more "
              "cards pile up.",
        "ko": "'{step}' 검토 완료 — 카드가 몇 장 더 쌓이면 다시 여쭙겠습니다.",
    },
    "review.queued": {
        "en": "Queued: \"{what}\" — your next visit digs exactly that.",
        "ko": "「{what}」 를 큐에 올렸습니다 — 다음 질문이 바로 그걸 팝니다.",
    },
    "today.src.review": {
        "en": "Time to check what we hold:", "ko": "쌓인 것을 확인할 차례입니다:",
    },
    "camp.title": {
        "en": "Where it breaks without you —", "ko": "당신이 없으면 비는 곳 —",
    },
    "camp.more": {"en": "map & shelf →", "ko": "지도·서가 →"},
    "map.done": {
        "en": "Got the map: {summary}. {hard} step(s) marked as feel-heavy — "
              "we dig those first. Your next visit starts there.",
        "ko": "지도를 그렸습니다: {summary}. '감이 필요한' 단계 {hard}곳 — "
              "거기부터 팝니다. 다음에 오시면 그 질문이 기다립니다.",
    },
    "today.src.probe": {"en": "Today's opener:", "ko": "오늘의 첫 질문:"},
    "home.memoir": {"en": "Memoir", "ko": "회고록"},
    "memoir.series": {"en": "A record of judgment", "ko": "판단의 기록"},
    "memoir.title": {"en": "What I knew, and how I knew it",
                     "ko": "내가 알던 것, 그리고 어떻게 알았는가"},
    "memoir.print": {"en": "Print", "ko": "인쇄"},
    "alter.memoir": {"en": "📖 {}'s memoir", "ko": "📖 {} 님의 회고록"},
    "memoir.weaving": {
        "en": "Weaving the judgment cards into this chapter…",
        "ko": "판단 카드를 회고록으로 엮고 있습니다…",
    },
    "memoir.draft_note": {
        "en": "Draft woven by AI from your judgment cards. Fix anything that "
              "differs from what actually happened, then approve — nothing is "
              "on the record until you do.",
        "ko": "판단 카드를 바탕으로 AI가 엮은 초안입니다. 실제 경험과 다른 "
              "부분을 고친 뒤 승인해 주세요 — 승인 전에는 기록이 아닙니다.",
    },
    "memoir.draft_badge": {"en": "DRAFT — not yet approved by the author",
                            "ko": "초안 — 본인 승인 전"},
    "memoir.approved_note": {
        "en": "— approved by the author; woven from the cards below.",
        "ko": "— 본인이 승인한 서술입니다. 아래 판단 카드에서 엮었습니다.",
    },
    "memoir.approve": {"en": "Approve this chapter", "ko": "이 장 승인"},
    "memoir.approve.done": {"en": "Approved.", "ko": "승인되었습니다."},
    "memoir.retry": {"en": "Could not weave this chapter — reload to retry.",
                      "ko": "서술을 엮지 못했습니다 — 새로고침으로 다시 시도하세요."},
    "memoir.prose_note": {
        "en": "— woven by machine from the judgment cards below; the cards are "
              "the record, this passage is the binding.",
        "ko": "— 아래 판단 카드에서 기계가 엮은 서술입니다. 기록은 카드이고, "
              "이 문단은 제본입니다.",
    },
    "memoir.appendix": {"en": "Appendix", "ko": "부록"},
    "memoir.hands": {"en": "What never fit into words", "ko": "글로 담지 못한 것"},
    "memoir.hands.note": {
        "en": "These were marked by the author as things you must stand next to "
              "them to learn. They are listed, not faked into prose.",
        "ko": "저자가 '옆에서 봐야 배운다' 고 표시한 것들입니다. 문장으로 "
              "지어내는 대신, 목록으로 남깁니다.",
    },
    "memoir.epilogue": {
        "en": "These judgments led {cited} answers, stood as evidence {ccit} "
              "times, and were reported to have helped {helped} times — "
              "they keep working.",
        "ko": "이 판단들은 {cited}번의 답을 이끌었고, {ccit}번 근거로 섰으며, "
              "{helped}번 현장에서 도움이 되었다고 보고되었습니다 — 지금도 "
              "일하고 있습니다.",
    },
    "memoir.colophon": {
        "en": "Compiled by yudonKnow from what its author dug out · {}",
        "ko": "저자가 파낸 것으로 yudonKnow 가 엮음 · {}",
    },
    "home.statement": {"en": "Usage statement", "ko": "지식 사용 명세서"},
    "statement.title": {
        "en": "Usage statement — {name}, as of {date}",
        "ko": "지식 사용 명세서 — {name} · {date} 기준",
    },
    # 두 수는 다른 것을 센다 — 답변 채택은 "분신의 답 하나에 쓰였다"(원장,
    # 답 단위), 카드 인용은 "근거로 선 카드 수"(한 답이 두 카드를 인용하면
    # 2). 같은 이름으로 두면 정산 근거의 신뢰가 깨진다 (QA 실측: 22 vs 12).
    "statement.totals": {
        "en": "Used in {cited} answers · card citations {ccit} · Helped {helped} · "
              "Field-verified {anchored} · Did not hold {missed}",
        "ko": "답변 채택 {cited}회 · 카드 인용 {ccit}건 · 도움됨 {helped}건 · "
              "현장 검증 {anchored}건 · 안 맞음 {missed}건",
    },
    "statement.card": {
        "en": "lead in {cited} answers · cited as basis {ccit} · helped {helped} · "
              "verified {anchored} · did not hold {missed}",
        "ko": "대표 답변 {cited}회 · 근거 인용 {ccit}건 · 도움됨 {helped} · "
              "검증 {anchored} · 안 맞음 {missed}",
    },
    "statement.note": {
        "en": "This statement is yours to hand to HR — a bill you present, not a "
              "screen they watch (the demo has no sign-in; production puts this "
              "behind SSO, owner-only). It counts only citations and explicit field "
              "reports (no views, no likes), so it can serve directly as a "
              "settlement basis for a knowledge-royalty policy. Rates and payment "
              "are HR policy, not product. \"Did not hold\" is listed too — an "
              "honest invoice negotiates better.",
        "ko": "이 명세서는 당신이 인사팀에 내미는 문서입니다 — 조회하는 화면이 "
              "아니라 청구하는 문서입니다 (데모에는 로그인이 없고, 실배포는 "
              "SSO 로 본인만 열게 됩니다). 조회수·좋아요 없이 인용과 명시적 "
              "적용 보고만 세므로, 지식 사용료 정책의 정산 근거로 그대로 쓸 수 "
              "있습니다. 단가와 지급은 제품이 아니라 인사 정책입니다. "
              "'안 맞음'도 함께 적습니다 — 정직한 청구서가 협상에 더 셉니다.",
    },
    "statement.download": {"en": "Download (JSON)", "ko": "내려받기 (JSON)"},
    "statement.close": {"en": "Close", "ko": "닫기"},
    "home.export": {"en": "Export my cards", "ko": "내 카드 내보내기"},
    "home.meet": {"en": "Meet my alter", "ko": "내 분신 만나보기"},
    "home.staying": {"en": "still here", "ko": "재직 중"},
    "home.left": {"en": "{} days since leaving", "ko": "퇴직 후 {}일"},
    "home.stats": {
        # 대시보드는 활동(본인 미리보기 포함), 명세서는 검증된 타인 사용만 —
        # 두 수가 다른 것이 정상임을 화면이 직접 말한다 (심사 QA #3).
        "en": "{alive} judgments live · {verified} field-verified · used in "
              "{used} answers · {cited} card citations · \"helped\" {helped} / "
              "\"didn't hold\" {missed} · unanswered {gaps} — dashboard "
              "activity includes owner previews; the statement bills verified "
              "third-party use only",
        "ko": "살아있는 판단 {alive} · 현장 검증 {verified} · 답변 채택 {used}회 · "
              "카드 인용 {cited}건 · '도움됐다' {helped} / '안 맞았다' {missed} · "
              "미응답 {gaps} — 대시보드 활동(본인 미리보기 포함) 기준, "
              "명세서는 검증된 타인 사용만 정산합니다",
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
    "home.map": {"en": "🗺 Work to hand over", "ko": "🗺 이관할 업무"},
    "home.map.cards": {"en": "cards {}", "ko": "카드 {}"},
    "home.map.empty": {
        "en": "Nothing listed yet. Add the work you need to hand over.",
        "ko": "아직 없습니다. 이관할 업무를 적어주세요.",
    },
    "home.flag.ph": {
        "en": "Add work to hand over — e.g. first response to a supplier quality incident",
        "ko": "이관할 업무 추가 — 예) 협력사 품질 사고 초기 대응",
    },
    "home.flag.cta": {"en": "Add", "ko": "추가"},
    "home.hands": {
        "en": "🔴 {} of these do not go into words — they are collected separately "
              "as apprenticeship items.",
        "ko": "🔴 손끝 지식 {}건은 글로 담기지 않습니다 — 도제 항목으로 따로 모았습니다.",
    },
    #: 사건 하나에서 시작한다 (docs/elicitation-protocol.md §0). 도구를 먼저
    #: 고르게 하면 전문가에게 도구 지식을 요구하는 셈이 된다.
    "home.story": {"en": "🔨 Start with one thing that happened",
                   "ko": "🔨 있었던 일 하나로 시작하기"},
    "home.story.q": {
        "en": "Think of one moment in the last six months when this team would have "
              "gone badly wrong without you.",
        "ko": "최근 6개월 중, 당신이 없었으면 팀이 크게 잘못됐을 순간을 하나만 "
              "떠올려 주세요.",
    },
    "home.story.ph": {
        "en": "Just say what happened. No need to tidy it up.",
        "ko": "있었던 일을 그냥 말하듯이 적어주세요. 정리하지 않으셔도 됩니다.",
    },
    "home.story.note": {
        "en": "We take it from here — the next questions follow what you just said, "
              "and you never have to pick a method.",
        "ko": "다음은 저희가 이어갑니다 — 방금 하신 말에서 질문이 이어지고, "
              "방법을 고르실 일은 없습니다.",
    },
    "home.story.cta": {"en": "Start here", "ko": "이걸로 시작"},
    "home.toolbox.more": {
        "en": "Or pick a method yourself (12)",
        "ko": "직접 방법을 고르시려면 (12가지)",
    },
    #: 문서는 질문이 되지 카드가 되지 않는다 (docs/design.md §7).
    # ── 서가·세 개의 문·문서함·혼잣말·남긴 직후 ─────────────────────
    "card.untitled": {"en": "Untitled judgment", "ko": "제목 없는 판단"},
    "shelf.head": {"en": "🗂 What you have left behind", "ko": "🗂 남긴 것들"},
    "shelf.helped": {"en": "helped {}", "ko": "도움됨 {}"},
    "shelf.draft": {"en": "Half-dug — tap to keep going.", "ko": "파다 만 판단 — 눌러서 이어가세요."},
    "shelf.contested": {"en": "A junior says it did not hold — tap to fix.",
                        "ko": "후배가 안 맞았다고 합니다 — 눌러서 고쳐주세요."},
    "shelf.fix": {"en": "Fix this card", "ko": "이 카드 고치기"},
    "shelf.view": {"en": "Open this card", "ko": "이 카드 보기"},
    # 전시 전문가의 활동 인물(Rosa·Tom 등)은 합성이다 — 표시 없이 두면
    # 실데이터로 읽힌다 (QA 지적).
    "demo.synthetic": {
        "en": "🎬 Showcase expert — the juniors and reports on this screen "
              "are synthetic demo data.",
        "ko": "🎬 전시 전문가입니다 — 이 화면의 후배·보고 인물은 합성 시연 "
              "데이터입니다.",
    },
    "statement.detail": {"en": "event log", "ko": "사용 내역"},
    "doors.head": {"en": "How would you like to leave something today?",
                   "ko": "오늘은 어떻게 남기시겠어요?"},
    "door1.t": {"en": "Just ask me", "ko": "그냥 물어봐 주세요"},
    "door1.c": {"en": "You answer, we do the rest. A question is already waiting — "
                      "a junior's, a document's, or today's opener.",
                "ko": "답만 하시면 됩니다. 후배의 질문이든, 문서에서 나온 것이든, "
                      "오늘의 첫 질문이든 — 이미 하나 준비돼 있습니다."},
    "door1.cta": {"en": "Take today's question", "ko": "오늘의 질문 받기"},
    "door2.t": {"en": "I have something to leave", "ko": "남기고 싶은 게 있어요"},
    "door3.t": {"en": "Here, take my stuff", "ko": "재료를 드릴게요"},
    "door3.c": {"en": "Hand over a procedure or just ramble — we find what is "
                      "missing and turn it into questions. Nothing becomes a card "
                      "until you answer.",
                "ko": "절차서를 주시든 두서없이 말씀하시든 — 빠진 곳을 찾아 질문으로 "
                      "바꿔둡니다. 답하시기 전에는 아무것도 카드가 되지 않습니다."},
    "mono.t": {"en": "Or just talk", "ko": "그냥 말할게요"},
    "mono.c": {"en": "Ramble while you work. We mine the judgment said in passing.",
               "ko": "일하면서 흘리듯 말씀하세요. 지나가듯 말한 판단을 저희가 건집니다."},
    "mono.ph": {"en": "Paste or record a rambling monologue…",
                "ko": "두서없는 혼잣말을 붙여넣거나 녹음하세요…"},
    "mono.cta": {"en": "Mine it", "ko": "건져주세요"},
    "mono.none": {"en": "No judgment traces found — complaints and small talk are left alone.",
                  "ko": "판단의 흔적을 찾지 못했습니다 — 불평과 잡담은 건지지 않습니다."},
    "mono.done": {"en": "{} questions queued from your monologue.",
                  "ko": "혼잣말에서 질문 {}개를 건져 큐에 넣었습니다."},
    "docs.progress": {"en": "{q} judgment points · {f} filled", "ko": "판단 지점 {q} · 채움 {f}"},
    "docs.open": {"en": "Show what it does not say", "ko": "말하지 않는 것 보기"},
    "docs.answer": {"en": "Answer now", "ko": "지금 답하기"},
    "ag.title": {"en": "It stays.", "ko": "남았습니다."},
    "ag.lede": {"en": "This judgment now answers even when you are not there.",
                "ko": "이제 이 판단은 당신이 없어도 답합니다."},
    "ag.demo.head": {"en": "Watch your alter use it", "ko": "분신이 이걸로 답하는 모습"},
    "ag.demo.q": {"en": "If a junior asks — \"{}\"", "ko": "후배가 이렇게 묻는다면 — \"{}\""},
    "ag.demo.busy": {"en": "Your alter is answering…", "ko": "분신이 답하는 중…"},
    "ag.demo.note": {"en": "This preview is not recorded anywhere — your ledger "
                           "counts only real juniors.",
                     "ko": "이 시연은 어디에도 기록되지 않습니다 — 원장은 진짜 "
                           "후배만 셉니다."},
    "ag.home": {"en": "Back to my page", "ko": "내 화면으로"},
    "ag.again": {"en": "Dig one more", "ko": "하나 더 파기"},
    "invite.body": {
        "en": "This card is for {who} only. Send them this link — \"a judgment "
              "left just for you\" is the strongest invitation there is.",
        "ko": "{who}에게만 남긴 카드입니다. 이 링크를 보내주세요 — \"당신에게만 "
              "남긴 판단\" 만큼 강한 초대장은 없습니다.",
    },
    "invite.copy": {"en": "Copy", "ko": "복사"},
    "cv.utter": {"en": "What you actually said — kept verbatim while this card lives",
                 "ko": "당신이 실제로 한 말 — 이 카드가 살아 있는 동안 원문 그대로 보존"},
    "cv.talk": {
        "en": "💬 Dig this judgment further (talk with the AI)",
        "ko": "💬 이 판단 더 파기 (AI와 대화)",
    },
    "cv.dormant": {"en": "🗄 Put it to rest", "ko": "🗄 서랍에 넣기"},
    "cv.draft_needs_judgment": {
        "en": "Saved as a draft — a card needs a judgment (\"so what do you "
              "do?\") before it can answer juniors. Keep digging to finish it.",
        "ko": "초안으로 저장했습니다 — 카드가 후배에게 답하려면 판단(\"그래서 "
              "어떻게 하나\")이 있어야 합니다. 이어서 파면 완성됩니다.",
    },
    "cv.dormant.sure": {"en": "Tap again to confirm — juniors stop seeing it; nothing is deleted",
                        "ko": "한 번 더 누르면 확정 — 후배에게 안 보이게 됩니다. 지워지진 않습니다"},
    "cv.dormant.done": {
        "en": "Resting. Juniors no longer see this card; the original words are kept. "
              "Edit and save to wake it.",
        "ko": "잠복했습니다. 후배에게 더는 보이지 않고, 원본 발화는 보존됩니다. "
              "수정 후 저장하면 다시 깨어납니다.",
    },
    "sess.method": {
        "en": "Questions follow the cognitive-task-analysis playbook — ACTA "
              "knowledge audit & task diagram, CDM timeline, vague-word "
              "pinning, member checking. (docs/elicitation-protocol.md)",
        "ko": "질문은 인지 과업 분석(CTA) 문헌의 사다리를 따릅니다 — ACTA "
              "지식 감사·과업 지도, CDM 타임라인, 모호어 짚기, 본인 검토. "
              "(docs/elicitation-protocol.md)",
    },
    "cv.edit": {"en": "Fix this card (what you write wins over the machine)",
                "ko": "카드 고치기 (당신이 고친 것이 기계보다 우선합니다)"},
    "cv.reports": {"en": "What juniors reported", "ko": "후배들의 보고"},
    "cv.f.title": {"en": "Title", "ko": "제목"},
    "cv.f.situation": {"en": "Situation", "ko": "상황"},
    "cv.f.cues": {"en": "Cues — one per line", "ko": "신호 — 한 줄에 하나"},
    "cv.f.judgment": {"en": "The call", "ko": "판단"},
    "cv.f.action": {"en": "Actions — one per line", "ko": "조치 — 한 줄에 하나"},
    "cv.f.rationale": {"en": "Why it works", "ko": "근거"},
    "cv.f.exceptions": {"en": "When it does not hold — one per line",
                        "ko": "예외 — 한 줄에 하나"},
    "cv.f.failure": {"en": "When it went wrong", "ko": "실패담"},
    "cv.save": {"en": "Save my version", "ko": "내 버전으로 저장"},
    "cv.resume": {"en": "⛏ Keep digging this one", "ko": "⛏ 이어서 파기"},
    "cv.warn.anchored": {"en": "This card is field-verified (✔). If you change its "
                               "substance, verification starts over — reports about "
                               "the old text cannot vouch for the new one.",
                         "ko": "이 카드는 현장 검증(✔)을 받았습니다. 내용을 고치면 "
                               "검증은 처음부터 다시 받습니다 — 옛 내용에 대한 보고가 "
                               "새 내용을 보증할 수는 없으니까요."},
    "cv.reset_done": {"en": "Substance changed — verification reset.",
                      "ko": "내용이 바뀌어 검증이 초기화되었습니다."},
    "cv.b.anchored": {"en": "field-verified", "ko": "현장 검증"},
    "cv.b.contested": {"en": "contested", "ko": "교정 요청"},
    "cv.b.draft": {"en": "⏳ half-dug", "ko": "⏳ 파다 만 판단"},
    "slot.unspeakable": {"en": "Could not be put into words", "ko": "말로 안 됨"},
    "home.doc": {"en": "📄 Red-pen a procedure", "ko": "📄 절차서 빨간펜"},
    "home.doc.q": {
        "en": "Paste a procedure you wrote or inherited. I will find what it "
              "does not say and ask you.",
        "ko": "쓰시던 절차서나 물려받은 문서를 붙여넣어 주세요. 문서가 말하지 "
              "않는 것을 찾아 여쭙겠습니다.",
    },
    "home.doc.ph": {
        "en": "Paste the document text here (.txt / .md also accepted below)",
        "ko": "문서 내용을 여기 붙여넣으세요 (.txt / .md 파일도 아래에서 됩니다)",
    },
    "home.doc.file": {"en": "or pick a text file", "ko": "또는 텍스트 파일 선택"},
    "home.doc.note": {
        "en": "The document is not stored and never becomes cards by itself — "
              "what it is missing becomes questions in your queue, and only "
              "your answers become cards.",
        "ko": "문서는 저장되지 않고, 그대로 카드가 되지도 않습니다 — 빠진 곳이 "
              "질문이 되어 큐에 쌓이고, 당신의 답만 카드가 됩니다.",
    },
    "home.doc.cta": {"en": "Find what's missing", "ko": "빠진 것 찾기"},
    "home.doc.busy": {"en": "Reading…", "ko": "읽는 중…"},
    "home.doc.none": {
        "en": "Nothing missing that I could see — this one covers its judgment calls.",
        "ko": "빠진 판단 지점을 찾지 못했습니다 — 이 문서는 꽤 꼼꼼합니다.",
    },
    "home.doc.done": {
        "en": "{} questions queued — they will come up first in your next dig.",
        "ko": "질문 {}개를 큐에 넣었습니다 — 다음 발굴에서 먼저 나옵니다.",
    },
    "home.toolbox": {
        "en": "🧰 Ways to record — pick one, or use the suggestion above",
        "ko": "🧰 기록하는 방법 — 하나 고르시거나 위 추천을 쓰세요",
    },
    "home.tool.start": {"en": "Start with this", "ko": "이걸로 시작"},
    "home.tool.mins": {"en": "about {} min", "ko": "약 {}분"},
    "home.all_tools": {
        "en": "{} ways in total. You never have to read the list — the suggestion "
              "above picks one for you.",
        "ko": "모두 {}가지입니다. 목록을 다 읽으실 필요는 없습니다 — 위 추천이 "
              "하나 골라 드립니다.",
    },

    # ── 발굴 세션 ─────────────────────────────────────────────────────
    #: 🎙 말로 답하기 — "전문가가 말하는 편이 훨씬 잘 나온다" (roadmap P1-1).
    #: 소리내어 하기(think-aloud)가 Ericsson & Simon 의 수행 중 발화 기준을
    #: 만족하는 유일한 연장인데, 키보드로는 성립하지 않는다.
    "auto.on": {"en": "Voice mode on — tap to stop", "ko": "음성 대화 중 — 누르면 멈춤"},
    "auto.off": {"en": "Talk instead of typing", "ko": "타자 대신 말로 하기"},
    "auto.speaking": {"en": "asking…", "ko": "질문 읽는 중…"},
    "auto.listening": {"en": "listening — just talk, pause when done",
                        "ko": "듣고 있습니다 — 말씀하시고, 끝나면 잠깐 쉬세요"},
    "auto.writing": {"en": "writing it down…", "ko": "받아 적는 중…"},
    "auto.quiet": {"en": "Heard nothing — tap 🎙 to try again or just type.",
                   "ko": "들리는 말이 없었습니다 — 🎙 를 다시 누르시거나 타자로 하셔도 됩니다."},
    "sess.wrap.note": {
        "en": "That's a full dig — the card on the right is ready. Set who may "
              "see it and press \"Leave it like this\", or keep going if there's more.",
        "ko": "한 판을 다 팠습니다 — 오른쪽 카드가 준비됐습니다. 공개 범위를 "
              "정하고 [이대로 남기기]를 누르세요. 더 있으면 계속하셔도 됩니다.",
    },
    "sess.wrap.speak": {
        "en": "We have a full card. If that sounds right, press save on the "
              "right — or keep talking if there is more.",
        "ko": "카드가 한 장 찼습니다. 이대로 맞으면 오른쪽에서 남기기를 눌러 "
              "주시고, 더 하실 말씀이 있으면 계속 말씀하세요.",
    },
    "sess.mic": {"en": "Speak instead", "ko": "말로 답하기"},
    "sess.mic.stop": {"en": "Stop & transcribe", "ko": "그만 말하고 받아적기"},
    "sess.mic.unsupported": {
        "en": "This browser cannot record audio.", "ko": "이 브라우저는 녹음을 지원하지 않습니다.",
    },
    "sess.mic.denied": {
        "en": "Microphone permission was refused.", "ko": "마이크 권한이 거절되었습니다.",
    },
    "sess.mic.empty": {
        "en": "Could not hear anything — try once more.", "ko": "들리는 말이 없었습니다 — 한 번만 다시요.",
    },
    #: 면접자가 왜 이걸 묻는지 숨기지 않는다 — Collaborative Partner 는
    #: "leads the way" 다. 길을 이끌면 어디로 가는지 말해줘야 한다.
    #: 실패담을 묻는 그 순간에 약속을 다시 보여준다 — 랜딩에서 본 문구를
    #: 기억하라고 요구하지 않는다. 이 약속이 깨지면 5단은 영원히 안 나온다
    #: (elicitation-protocol §1-5).
    "sess.safety": {
        "en": "War stories are never linked to HR records — that is a standing "
              "promise of this tool.",
        "ko": "실패담은 인사 기록과 연결되지 않습니다 — 이 도구의 변하지 않는 "
              "약속입니다.",
    },
    "sess.why": {"en": "Filling in: {}", "ko": "지금 채우는 칸 — {}"},
    "sess.why.deepen": {
        "en": "\"It depends\" can't be handed down — so let's go to one actual day.",
        "ko": "'그때그때 다르다'는 물려줄 수 없어서, 실제 있었던 하루로 내려갑니다.",
    },
    "sess.reflect": {
        "en": "So — {label}: {body}\nHave I got that right? If not, say it again "
              "your way and I will take yours.",
        "ko": "제가 이렇게 이해했습니다 — {label}: {body}\n맞습니까? 아니면 그대로 "
              "다시 말씀해 주세요. 하신 말씀이 우선입니다.",
    },
    "sess.from_gap": {
        "en": "This is where a junior got stuck.", "ko": "후배가 막힌 곳입니다.",
    },
    "sess.leave_unsaved": {
        "en": "You have an answer you haven't sent yet. Leave without saving it?",
        "ko": "아직 보내지 않은 답이 있습니다. 저장하지 않고 나가시겠어요?",
    },
    "sess.answer.ph": {
        "en": "Say it the way you'd say it out loud. No need to tidy it up.",
        "ko": "말하듯이 적어주세요. 정리하지 않으셔도 됩니다.",
    },
    "sess.privacy.hint": {
        "en": "No real names needed — say the role instead (\"the HR lead\", "
              "\"a logistics client\"). Names you do say are kept out of the card.",
        "ko": "실명·회사명은 안 적으셔도 됩니다 — 역할로 말씀해 주세요"
              "(\"인사 책임자\", \"물류 고객사\"). 말씀하신 이름은 카드에는 담기지 않습니다.",
    },
    "sess.next": {"en": "Next question", "ko": "다음 질문"},
    "sess.waiting": {"en": "Listening…", "ko": "듣는 중…"},
    "sess.skip": {"en": "I'll skip this one", "ko": "이건 넘길게요"},
    "sess.building": {"en": "The judgment taking shape", "ko": "지금 만들어지는 판단"},
    "sess.tacit.q": {"en": "🌡 Does this go into words?", "ko": "🌡 이건 읽어서 되나요?"},
    "sess.vis.q": {"en": "Who may see this?", "ko": "누가 볼 수 있나요?"},
    "sess.confirm": {"en": "Leave it like this", "ko": "이대로 남기기"},
    "sess.savedraft": {"en": "Save draft & leave", "ko": "초안으로 저장하고 나가기"},
    "sess.saving": {"en": "Saving — drafting search aliases…",
                     "ko": "저장 중 — 검색 별칭을 뽑는 중…"},
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
    #: 통제권은 문구가 아니라 화면에서 확인되어야 한다. 데모에는 인증이 없으므로
    #: 신원을 바꿔가며 같은 질문을 던져 보게 안내한다 — 그게 권한 모델의 시연이다.
    "alter.farewell.title": {
        "en": "What {} wanted to say to you", "ko": "{}님이 남기는 말",
    },
    "alter.farewell.close": {"en": "Thanks — let's talk", "ko": "잘 읽었습니다 — 물어볼게요"},
    "alter.farewell.link": {
        "en": "Read what {} left for you again", "ko": "{}님이 남기는 말 다시 읽기",
    },
    "alter.explored": {
        "en": "newly left — still being proven", "ko": "새로 남긴 판단 — 검증 쌓는 중",
    },
    "alter.report.send": {"en": "Send", "ko": "보내기"},
    "alter.report.cancel": {"en": "Cancel", "ko": "취소"},
    "fu.body": {
        "en": "Last time you got an answer from the card \"{}\" — did it hold "
              "up on the floor? Your report is what earns it the ✔.",
        "ko": "지난번에 「{}」 카드로 답을 받으셨죠 — 현장에서 맞던가요? "
              "당신의 보고가 그 카드의 ✔ 을 만듭니다.",
    },
    "fu.later": {"en": "Not yet", "ko": "아직요"},
    "alter.notanswer": {
        "en": "This didn't answer my question — send it to the senior",
        "ko": "이건 제 질문에 대한 답이 아니었어요 — 선배에게 전달하기",
    },
    "alter.notanswer.done": {
        "en": "Sent — it joins the senior's queue and they get a ping.",
        "ko": "전달됐습니다 — 선배의 큐에 오르고 알림이 갑니다.",
    },
    "alter.thanks.ph": {
        "en": "One line to the senior — it reaches them by name",
        "ko": "선배에게 한마디 — 이름과 함께 전해집니다",
    },
    "alter.thanks.cta": {"en": "Send thanks", "ko": "전하기"},
    "alter.thanks.done": {
        "en": "Delivered — it will be on their ledger.", "ko": "전해졌습니다 — 선배의 원장에 오릅니다.",
    },
    "alter.steps": {
        "en": "① Ask the way you'd ask the person at the next desk · "
              "② open the basis card under the answer and check it · "
              "③ after you try it on the floor, report \"helped\" or "
              "\"didn't hold\" — that report is what earns the ✔.",
        "ko": "① 옆자리에 묻듯 물어보세요 · ② 답 아래 근거 카드를 펴서 "
              "확인하세요 · ③ 현장에서 써본 뒤 '도움됐다/안 맞았다'로 "
              "보고하세요 — 그 보고가 ✔ 를 만듭니다.",
    },
    "alter.example": {"en": "e.g. {q}", "ko": "예: {q}"},
    # 언어 벽의 정직한 안내 — "아무 언어나 됩니다" 는 거짓이다. 검색은
    # 언어를 넘지 않는다(카드는 판 언어로 산다, 테스트 고정).
    "alter.langwall": {
        "en": "{who} recorded in {lang} — questions must be in {lang} to "
              "reach the cards.",
        "ko": "{who} 님은 {lang}로 기록했습니다 — 질문도 {lang}로 해야 "
              "카드에 닿습니다.",
    },
    "alter.langwall.switch": {"en": "Switch view to {lang} →",
                               "ko": "{lang} 화면으로 보기 →"},
    "alter.farewell.lang": {
        "en": "(left in {lang})", "ko": "({lang}로 남긴 인사입니다)",
    },
    "alter.as.try": {"en": "Try as:", "ko": "이 신원으로 눌러보기:"},
    "alter.as.visitor": {"en": "a visitor", "ko": "손님"},
    "alter.as.named": {"en": "{} — the named successor", "ko": "{} — 지목된 후배"},
    "alter.viewer.hint": {
        "en": "Cards obey their owner's setting: a private card answers only its "
              "owner, a card left for one named person answers only them, and a "
              "sealed one answers no one until its date. Change who you are above "
              "and ask again. Demo has no sign-in; corporate SSO plugs in here.",
        "ko": "카드는 남긴 사람의 설정을 따릅니다: 비공개 카드는 본인에게만, 지목된 "
              "사람에게 남긴 판단은 그 사람에게만 답하고, 봉인한 판단은 정한 날까지 "
              "아무에게도 답하지 않습니다. 위 '나' 칸을 바꿔 다시 물어보세요. "
              "데모에는 로그인이 없고, 실배포는 여기에 사내 SSO가 붙습니다.",
    },
    "alter.ask.notice": {
        "en": "Unanswered questions are saved to the senior's dig queue with "
              "your id — that is how gaps get filled.",
        "ko": "답 못한 질문은 질문자 아이디와 함께 선배의 발굴 큐에 저장됩니다 — "
              "공백은 그렇게 채워집니다.",
    },
    "alter.donow": {"en": "Do now", "ko": "지금 할 일"},
    "alter.donow.src": {"en": "from card: {}", "ko": "근거 카드: {}"},
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
    "alter.gone": {"en": "already retired — the alter answers on", "ko": "이미 은퇴하셨습니다 — 분신이 대신 답합니다"},
    "alter.dday": {"en": "retires in {} days — ask while they are here", "ko": "은퇴까지 {}일 — 계실 때 물어보세요"},

    # ── 분신이 내는 문장 (LLM 을 거치지 않는 것들) ────────────────────
    "alter.msg.stopped": {
        "en": "{label} is paused right now. They switched it off themselves.",
        "ko": "{label}은 지금 멈춰 있습니다. 본인이 직접 정지시켜 두었습니다.",
    },
    "alter.msg.ungrounded": {
        "en": "⚠ The generated answer did not pass the evidence check, so here are "
              "the judgment cards verbatim — nothing invented.",
        "ko": "⚠ 생성된 답이 근거 검증을 통과하지 못해, 남기신 판단 카드를 "
              "그대로 보여드립니다 — 지어낸 것 없이.",
    },
    "alter.msg.restricted.private": {
        "en": "{name} did leave judgment in this area — but kept it private, "
              "visible only to themselves. That is their call to make.\n"
              "If you need it, ask them directly.",
        "ko": "{name}님은 이 영역에 판단을 남기셨습니다 — 다만 본인만 보도록 "
              "비공개로 두셨어요. 그건 본인의 권한입니다.\n"
              "필요하시면 직접 여쭤보세요.",
    },
    "alter.msg.restricted.targeted": {
        "en": "{name} did leave judgment in this area — but left it for one "
              "named person, and it answers only them. That is their call to "
              "make.\nIf you need it, ask them directly.",
        "ko": "{name}님은 이 영역에 판단을 남기셨습니다 — 다만 지정한 사람에게만 "
              "열리도록 남기셨어요. 그건 본인의 권한입니다.\n"
              "필요하시면 직접 여쭤보세요.",
    },
    "alter.msg.restricted.sealed": {
        "en": "{name} did leave judgment in this area — but sealed it until a "
              "date they chose. That is their call to make.\n"
              "If you need it, ask them directly.",
        "ko": "{name}님은 이 영역에 판단을 남기셨습니다 — 다만 정한 날짜까지 "
              "봉인해 두셨어요. 그건 본인의 권한입니다.\n"
              "필요하시면 직접 여쭤보세요.",
    },
    "alter.msg.restricted": {
        "en": "{name} did leave judgment in this area — but it is opened only to "
              "a named person or on a chosen date. That is their call to make.\n"
              "If you need it, ask them directly.",
        "ko": "{name}님은 이 영역에 판단을 남기셨습니다 — 다만 지정한 사람에게만, "
              "혹은 정한 날짜에 열리도록 잠가 두셨어요. 그건 본인의 권한입니다.\n"
              "필요하시면 직접 여쭤보세요.",
    },
    "alter.msg.gap.notqueued": {
        "en": "▸ Not queued: your own questions (and questions to a paused "
              "alter) do not enter the dig queue — that queue maps juniors' "
              "demand. Dig it directly from your expert home.",
        "ko": "▸ 큐에 넣지 않았습니다: 본인 질문(과 정지된 분신에 온 질문)은 "
              "발굴 큐에 올라가지 않습니다 — 큐는 후배 수요의 지도입니다. "
              "전문가 홈에서 바로 파세요.",
    },
    "alter.msg.quarantined": {
        "en": "This is not an area {name} left behind, and this question was "
              "not passed on to them.\nI will not make it up, and I do not "
              "relay instructions aimed at the system.",
        "ko": "이건 {name}님이 남기지 않은 영역이고, 이 질문은 선배에게 "
              "전달하지 않았습니다.\n지어내지 않고, 시스템을 겨눈 지시는 "
              "전달하지 않습니다.",
    },
    "alter.msg.gap": {
        "en": "This is not an area {name} left behind.\nI will not make it up.",
        "ko": "이건 {name}님이 남기지 않은 영역입니다.\n지어내지 않겠습니다.",
    },
    #: 언어 경계. "안 남겼다" 가 아니라 "다른 언어로 남겼다" 다 — 카드는 있다.
    "lang.name.ko": {"en": "Korean", "ko": "한국어"},
    "lang.name.en": {"en": "English", "ko": "영어"},
    "alter.msg.cards.one": {"en": "1 judgment card", "ko": "판단 카드 1장"},
    "alter.msg.cards.many": {"en": "{} judgment cards", "ko": "판단 카드 {}장"},
    "alter.msg.lang_wall": {
        "en": "{name} left {count} — in {language}.\n"
              "They are here, but not in a language you asked in, and I will not "
              "translate them: a judgment in summary is no longer a judgment.\n"
              "Ask in {language} and this alter answers.",
        "ko": "{name}님은 {count}을 {language}로 남기셨습니다.\n"
              "카드는 여기 있지만 물어보신 언어가 아니고, 번역하지 않습니다 — "
              "요약된 판단은 더 이상 판단이 아니기 때문입니다.\n"
              "{language}로 물으시면 이 분신이 답합니다.",
    },
    "alter.msg.lang_wall.alt": {
        "en": "▸ Left in your language: {}",
        "ko": "▸ 같은 언어로 남긴 사람: {}",
    },
    "alter.msg.gap.sent": {
        "en": "▸ Your question was recorded, word for word, in this senior's "
              "dig queue — they see it (with your id) next time they excavate",
        "ko": "▸ 질문이 선배의 발굴 큐에 그대로 기록됐습니다 — 다음 발굴 때 "
              "선배가 (질문자 아이디와 함께) 봅니다",
    },
    "alter.msg.gap.dday": {"en": " (they retire in {} days)", "ko": " (은퇴까지 {}일)"},
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
    "err.demo_readonly": {
        "en": "This is a showcase expert — read-only during judging. Watch their "
              "shelf and memoir, ask their alter, send reports and thanks. To feel "
              "the expert side, create your own in about five minutes.",
        "ko": "전시용 전문가입니다 — 심사 기간에는 읽기 전용이에요. 서가와 "
              "회고록을 구경하고, 분신에게 묻고, 보고와 감사는 보낼 수 있습니다. "
              "전문가 쪽을 느껴보시려면 5분이면 본인 것을 만들 수 있어요.",
    },
    "err.no_expert": {
        "en": "Could not find '{}'.", "ko": "'{}' 를 찾을 수 없습니다.",
    },
    "err.no_card": {"en": "Could not find that card.", "ko": "그 카드를 찾을 수 없습니다."},
    "err.self_report": {
        "en": "This is your own card — a report on your own judgment does not "
              "count toward the badge or the statement. It needs a junior's field report.",
        "ko": "본인 카드입니다 — 본인 판단에 대한 보고는 배지·명세에 반영되지 "
              "않습니다. 후배의 현장 보고가 필요합니다.",
    },
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
