# 데모 영상 대본 — 4:00, 촬영 실행판 (v0.3.5 기준)

**규정**: ≤4분 · 문제 개요 포함 · **백엔드가 Google Cloud 에서 도는 것을
화면으로 증명** · 영어 또는 영어 자막 · YouTube/Vimeo 공개 링크.
**형식**: 화면 녹화 + 한국어 내레이션(또는 무음) + 영어 자막. 대기 시간은
컷 편집으로 줄이되 조작·결과는 실화면 그대로.

**베이스 URL**: `https://yudonknow-530548975242.us-central1.run.app`
**시연 계정**: `vet-qa-1` (영어 카드 3장 + 승인 규칙) · 새 전문가 1명 즉석 생성

---

## 촬영 전 체크리스트 (10분)

1. 브라우저 새 프로필(북마크·확장 숨김), 창 1280×800, 언어는 **?lang=en**.
2. 마이크 권한 미리 허용 (음성 장면 리허설 1회).
3. 탭 4개 미리 열기: ① `/?lang=en` ② `/expert?lang=en&as=demo-live`
   ③ `/protocol/vet-qa-1?lang=en` ④ Google Cloud Console → Cloud Run →
   yudonknow 서비스 상세 (리전 us-central1 이 보이는 화면).
4. 리허설: 분신 질문 1회 던져 응답 시간 체감(15~23s — 편집점).
5. 녹화 도구에 시스템 오디오 포함(TTS 음성이 들리게).

---

## 타임라인

### 0:00–0:22 · 문제 (자막 + 랜딩)
**화면**: ① 랜딩 `/?lang=en`. 스크롤 없이 두 문이 보이는 상태.
**내레이션(자막)**:
> I run a factory. My molders and painters with 40 years in their hands are
> retiring — and automation takes the procedures, but the judgment walks out
> the door.
> yudonKnow is an AI agent that interviews a retiring expert, and stays
> behind as their alter.
**동작**: 마지막 문장에서 "How it works" 헤더 클릭 → 6단계 카드 잠깐 노출.

### 0:22–0:35 · Cloud Run 증명 (규정 요건)
**화면**: ④ Cloud Console 탭 — 서비스명 yudonknow · Region us-central1 ·
Revision v0.3.5 트래픽 100%. 3초. 다시 앱 탭으로.
**자막**: > Live on Google Cloud Run — everything you'll see is production.

### 0:35–1:30 · 전문가 발굴 (에이전트가 먼저 움직인다)
**화면**: ② `/expert?lang=en&as=demo-live` — 온보딩 3칸 빠르게(이름만
"Demo Expert") → 홈 진입, **오늘의 질문이 이미 기다리고 있는 장면**이
첫 컷 (에이전트가 묻는다 — 채팅창이 아니라).
**동작**: 🎙 말로 답하기 클릭 → 음성으로 한 문장 답 (예: 실제 사출/도장
경험 한 토막. 유돈 케이스면 최고). AI 후속 질문이 오는 것까지.
**자막**:
> The agent runs the knowledge engineer's playbook — task maps, incident
> digging, member checking. You just talk.
> Every answer lands in a judgment card: situation, cues, judgment, action,
> exceptions.
**편집**: 질문 생성 대기(~5s)는 상태 문구 1초 보여주고 컷.

### 1:30–2:00 · 승인 = 권한 (규칙 초안)
**화면**: vet-qa-1 서가(`/expert?lang=en&as=vet-qa-1` → 서가) → GREEN 카드
편집 열기 → **규칙 칸에 AI 초안이 미리 채워진 것**("✍ AI-drafted …") 클로즈업
→ 저장.
**자막**:
> The AI drafts the rules — all-of, none-of, priority — from the card itself.
> Nothing runs until the expert reviews and saves. **The LLM discovers;
> only approved rules execute.**

### 2:00–2:50 · 결정론 판정 문진 (하이라이트)
**화면**: ③ `/protocol/vet-qa-1?lang=en` → 🚦 Structured triage.
**동작 3연타**:
1. "vomited once" 만 **Yes** → 판정: **escalate** — 미확인 조건 목록이
   판단보다 먼저. 자막: > One reassuring sign is never enough. Unknowns
   never downgrade — they escalate.
2. GREEN 조건 전부 Yes/위험 신호 No → **GREEN 성립**. 자막: > The whole
   gate must hold before it reassures.
3. 위험 신호(unproductive retching, tight belly)까지 Yes → **⚠ 배너:
   2 judgments stand — executing priority 3, GREEN held.** 자막: > On
   conflict, the urgent judgment executes. Deterministic — same answers,
   same verdict, auditable.

### 2:50–3:20 · 후배의 언어로 묻기 → 인용 → 즉시 기록
**화면**: `/alter/vet-qa-1?lang=en` — 질문 입력(재서술):
"my cat keeps squatting in the box but nothing comes out"
**결과**: 인용 [#카드] 달린 답. 이어 전문가 홈 통계 — **used in N answers ·
card citations M** 이 +1 된 것.
**자막**: > The alter answers only from the cards, citing them — a mechanical
check discards uncited answers. Every use lands on the retiree's ledger.
**편집**: 응답 대기 15~20s 는 단계 문구(Searching → Composing → Verifying)
2초 보여주고 컷.

### 3:20–3:40 · 회고록 + 명세서 (한 인터뷰, 두 자산)
**화면**: `/memoir/vet-qa-1?lang=en&as=vet-qa-1` 표지→장 스크롤 (초안 배지
→ 승인 서술 하나 보이면 최고) → 명세서(답변 채택/카드 인용 병기) 3초.
**자막**: > The same interview typesets a career memoir — drafts become
record only when the author approves — and a usage statement: the verifiable
basis for paying retirees for knowledge that keeps working.

### 3:40–4:00 · 클로징 (CEO, 얼굴 또는 자막)
**대사** (project-story.md 클로징 그대로, 자막):
> Yudon is a close friend of mine, a few years from retirement. He asked
> me for this. This is for the people who run my lines: a knowledge system
> while they are here, a memoir when they leave, and a ledger that keeps
> paying them for every verified use after.
> **He leaves. His judgment stays on the line — and every time it works,
> so does his name.**

---

## 예비 컷 (시간 남으면 2:50 뒤에 10초)
공백 정직성: 안 판 주제 질문 → "they did not leave that behind" + 질문이
전문가 큐에 쌓이는 화면. 자막: > When it doesn't know, it says so — and the
question routes back to the expert. No hallucinated triage, ever.

## 리스크 대응
- 음성 인식 실패 시: 텍스트 입력으로 이어가고 그 테이크 사용 (오토 모드
  버튼이 화면에 보이는 것만으로 음성 지원은 전달됨).
- 분신 응답이 30s 넘으면: 그 테이크는 버리고 재질문 (429 백오프 가능성).
- 판정 문진은 결정론 — 리허설과 본촬영 결과가 항상 같다. 여기서 시간을 벌 것.
