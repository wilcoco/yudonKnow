# All Things Agentic Hackathon — 출품 정본

> **2026-08-27 규정 원문 대조 완료.** 이전 판은 규정을 요약 전달받아 쓴 것이라
> 오류가 있었다. 아래는 원문 대조본이다. 세션이 바뀌어도 이 파일만 읽으면 이어받는다.

## 좌표

| | |
|---|---|
| 대회 | All Things Agentic Hackathon (주최 Google LLC, 운영 Devpost) |
| 제출 마감 | **2026-09-01 09:00 KST** (= 8/31 17:00 PT) |
| 심사 | 9/1 ~ 10/1 · 발표 10/8경 |
| Devpost draft | `1155717-yudonknow` |
| GCP 프로젝트 ID | **`yudonknow`** · 결제 연결 완료 (`My Billing Account 1`) |
| **선택 카테고리** | **Collaborative Partner** |

---

## 🔴 원문 대조로 새로 드러난 것 — 먼저 볼 것

### ① 영어 지원이 **Stage One 통과 조건**이다

> **Language:** The Application must, **at a minimum, support English language use.**
> All Submission materials must be in English or, if not in English, the Entrant must
> provide an English translation…

**우리 앱은 100% 한국어다.** 템플릿에 한글 6,331자, 파이썬 문자열 170줄.
Stage One 은 pass/fail 이라 여기서 걸리면 심사 자체가 없다. **최우선 작업.**

**결정: `Accept-Language` 기반 자동 전환 + 명시적 토글.**
심사자(영어 브라우저)는 아무것도 안 해도 영어로 뜨고, 유돈은 한국어로 쓴다.
카드 *내용*은 한국어 그대로 둔다 — 그게 "messy unstructured data" 서사의 실물이고,
영어 시드 데이터를 따로 넣어 심사자가 실제로 조작해 볼 수 있게 한다.

### ② $150 크레딧 신청 폼 — **2026-08-29 04:00 KST 마감** (선착순)

> using an existing Google Cloud account for which you may request **$150 in Google
> Cloud credits** by completing this form by **August 28th at 12:00 pm PT** or
> **while supplies last**: https://forms.gle/riGhgDSHkHeMx8Ca6

- 결제 계정이 이미 붙어 있으므로 우리는 **(2) 기존 계정** 경로에 해당한다.
- 1인 1코드. 신청 후 **영업일 기준 72시간 내** 검토. 지급 보장 없음.
- 크레딧 초과분은 참가자 부담.

### ③ 우리 카테고리 심사 기준에 **"efficient vector embedding strategies"** 가 박혀 있다

Architectural Discipline(30%)의 *The Evolving Knowledge Engine* 항목:

> Judges will evaluate your **data architecture**. This includes intelligent schema
> design, **efficient vector embedding strategies**. How efficiently does the system
> manage massive context windows?

우리는 `docs/design.md` §7 에서 **벡터를 의도적으로 뺐다**(카드 수백 장 규모에서
이득 < 배포 복잡도). 판단은 여전히 옳다고 본다. 그러나 30% 배점 항목에 단어가
명시돼 있으므로 **둘 중 하나를 반드시 한다:**

- (A) 근거를 정면으로 쓴다 — "왜 임베딩을 쓰지 않았는가"를 아키텍처 문서와
  영상에서 **설계 판단으로 방어**한다. 확신도가 검색 점수로 계산돼야 하고,
  그 점수가 **공백 판정의 임계값**이 되기 때문에 설명 가능해야 한다는 논리.
- (B) 하이브리드로 얹는다 — 키워드 1차 + 임베딩 재순위. 공백 판정 임계값은
  키워드 점수로 유지(설명 가능성 보존).

**권고: (B)+(A).** 임베딩을 재순위에만 쓰고, 판정은 여전히 코드가 한다고 쓴다.
"쓸 줄 몰라서 안 썼다"와 "쓸 자리를 골라서 썼다"는 심사에서 전혀 다르게 읽힌다.

### ④ 이전 브리프의 오류 — "Unlikely Hero" 는 우리 카테고리가 아니다

원문에서 *"Did they build this for an 'Unlikely Hero' outside of standard corporate
roles?"* 는 **Fortified Enterprise Fleet** 항목에 있다. 이전 판은 이걸
Collaborative Partner 근거로 적었다. **삭제한다.**

우리 카테고리에 실제로 있는 문장은 이것뿐이다:

> **For Collaborative Partner:** Does the agent **actively synthesize or mutate data,
> rather than just reading it?** Did the team **ingest unusual, messy, or highly
> complex unstructured data streams?**

- *synthesize or mutate* → 대화를 **판단 카드로 변형**한다. 읽기만 하지 않는다. ✅
- *messy unstructured streams* → 퇴직 앞둔 제조 현장 전문가의 암묵지. ✅

### ⑤ 요건 ② 는 **이미 충족**돼 있다

> at least one Google Agent Framework: Google ADK, **GenAI SDK**, Antigravity SDK or GenKit

`google-genai` 를 이미 쓰므로 요건은 충족. **ADK 는 생존이 아니라 상승 요인**이다.
영어화·배포보다 우선순위가 낮다. 시간이 남으면 얹는다.

---

## 필수 요건 (3개 전부 — 하나라도 빠지면 Stage One 탈락)

| # | 요건 | 상태 |
|---|---|---|
| ① | Gemini 3.5+ (Gemini API 또는 Vertex AI → 現 Gemini Enterprise Agent Platform) | ✅ `app/capture/llm.py::GeminiLLM` |
| ② | Google 에이전트 프레임워크 1개 이상 | ✅ **GenAI SDK 로 충족** (ADK 는 추가 상승) |
| ③ | GCP 인프라 1개 이상 (Cloud Run / Cloud SQL / Firestore / GKE / Pub/Sub) | ⬜ Cloud Run + Cloud SQL — 결제 붙었으니 진행 가능 |

플랫폼 개명 영향은 `docs/platform-note.md`. **요약: 코드는 손댈 것 없다.**
규정 원문도 "Recommended Tech to use (Gemini Enterprise Agent Platform)" 로 신명칭을 쓴다.

---

## 자격 — 확인 완료

- 제외 국가 목록(이탈리아·퀘벡·크림·쿠바·이란·시리아·북한·수단·벨라루스·러시아)에
  **한국은 없다.** ✅
- 제출 기간 2026-08-03 ~ 08-31. 최초 커밋 `4df61ca` **2026-08-27**. → 기간 내 생성 ✅
- ⚠️ **정부기관 소속이면 이해충돌로 부적격**이 될 수 있다(규정 3조). 해당 없으면 무시.
- 재사용 disclosure 영문 원문은 `docs/project-story.md`. 규정이 요구하는
  *"must disclose any other pre-existing code or work incorporated"* 를 그것으로 충족한다.

---

## 심사 배점 (Stage Two, 각 1~5점 → 평균)

| 항목 | 비중 | 우리 대응 |
|---|---|---|
| Innovation & Operational Utility | 40% | 대화→카드 **변형** · 공백 큐 자율 라우팅 · 발굴 연장 12개 |
| Architectural Discipline & Tech Stack | 30% | **기저 교체 가능성이 실물로 증명됨** · 의존성 0 코어 · 상태기계 |
| Demo & Production Readiness | 30% | 4분 영상(무편집 라이브 + Cloud Run 증빙) · 아키텍처 다이어그램 · 영문 README |

Stage Three 보너스 (최대 +1.0, 최종 6점 만점):
- 블로그/영상 **+0.2** — ⚠️ *"이 해커톤 출품용으로 제작했다"는 문구를 반드시 본문에 넣을 것.* 공개(비공개·미등록 불가)
- 소셜 **+0.2** — 해시태그 `#AllThingsAgenticHackathon`
- 추가 구글 모델(Gemma·Veo·Lyria) **각 +0.2, 최대 +0.6**

### Architectural Discipline 에서 내세울 것

> 기저 LLM 은 산출물 층위로만 접합한다. 기저 교체 가능성이 전략 자산이다.

이게 말이 아니라 사실이라는 증거: **기저를 Anthropic → Gemini 로 바꾸는 데
`app/capture/llm.py` 한 파일만 바뀌었다.** 인터뷰어도 분신도 손대지 않았고
테스트 34개가 그대로 통과했다. 심사 기준의 *"How well did your team decouple
systems?"* 에 그대로 답이 된다. Anthropic 어댑터를 **지우지 않고 남긴 것**도 의도다.

---

## 노려볼 수 있는 상 (한 프로젝트당 최대 1개)

| 상 | 금액 | 우리 해당 여부 |
|---|---|---|
| Grand Prize | $50,000 | 전 부문 최고점 |
| **The Collaborative Partner** | $20,000 | ✅ 선택 카테고리 |
| Startup Excellence | $20,000 | 법인 + 법인 이메일 필요 — 해당되면 신청 |
| **Individual/Hobbyist (Best Team/Solo Build)** | $10,000 × 2 | ✅ 자동 해당 |
| **Best Architectural Design** | $5,000 × 2 | ✅ 우리 서사가 정면으로 겨냥 |
| Best Multimodal UX | $5,000 × 2 | 음성 발굴 붙이면 사정권 |
| Honorable Mentions | $2,000 × 5 | — |

총 상금 $180,000 / 16개 상.

---

## 제출물 체크리스트 (규정 6조 원문 기준)

- [ ] **영어 지원** ← 🔴 Stage One 조건
- [ ] 작동하는 프로젝트 (필수요건 ①②③)
- [ ] **호스팅 URL** — 심사 종료 **10/1 까지 무료·무제한으로 살아 있어야 한다**
- [x] 공개 저장소 `wilcoco/yudonKnow` (비공개면 `testing@devpost.com` +
      `cloudhackathons@google.com` 접근권 필요)
- [ ] **README spin-up 가이드 (영문)** — "로컬 실행 또는 클라우드 배포 단계별"
- [ ] **아키텍처 다이어그램** — Gemini ↔ 백엔드 ↔ DB ↔ 프론트 연결이 보이게
- [ ] **4분 데모 영상** — YouTube/Vimeo **공개**, 영어 또는 영어 자막,
      **무편집 라이브 실행** + **Cloud Run 콘솔/`.run` URL 증빙 필수**
- [ ] Project Story (features · technologies · data sources · **findings and learnings**)
- [ ] 카테고리 = Collaborative Partner
- [ ] Built with 태그

---

## 남은 일정 (제출까지 ~4일 21시간)

| 우선 | 할 것 | 담당 |
|---|---|---|
| 🔴 지금 | **$150 크레딧 폼** (8/29 04:00 KST 마감) | 사장님 |
| 🔴 D-4 | **영어 지원(i18n)** — Stage One 조건 | 나 |
| 🔴 D-4 | **Cloud Run + Cloud SQL 배포** — 요건 ③ | 나 (Cloud Shell 명령 전달) |
| 🟡 D-3 | 임베딩 재순위 (배점 ③ 대응) · 영문 시드 데이터 | 나 |
| 🟡 D-3 | ADK 에이전트 (상승 요인) | 나 |
| 🟠 D-2 | 아키텍처 다이어그램 · 영문 README | 나 |
| 🟠 D-1 | 4분 영상 촬영/자막 · Project Story 확정 · 제출 | 같이 |
| 🟢 여유 | 블로그(+0.2) · 소셜(+0.2) · Veo 인트로(+0.2) | — |

**코드 2.5일 · 영상과 문서 1.5일.** 심사 30% 가 문서와 영상이다. 여기서 줄이면 손해.
