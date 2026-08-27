# All Things Agentic Hackathon — 출품 정본

> 세션이 바뀌어도 이 파일만 읽으면 이어받을 수 있게 쓴다.
> 대회 컨텍스트는 대화에 두지 않는다.

## 좌표

| | |
|---|---|
| 대회 | All Things Agentic Hackathon (주최 Google LLC, 운영 Devpost) |
| 제출 마감 | **2026-09-01 09:00 KST** (= 8/31 17:00 PT) |
| 심사 | 9/1 ~ 10/1 · 발표 10/8경 |
| Devpost draft | `1155717-yudonknow` (생성 완료) |
| 참가자 수 | 9,494명 · 상금 총 $180,000 · 상 17개 |
| **선택 카테고리** | **Collaborative Partner** |

## 자격 — 확인 완료

룰 6조 *New Projects Only*:

> Projects must be newly created during the Submission Period... but **must
> disclose any other pre-existing code or work incorporated** into the Project.

- 제출 기간: 2026-08-03 ~ 08-31
- 이 레포 최초 커밋: **`4df61ca` 2026-08-27 02:49:50 +0000** → **기간 내 생성. 자격 충족.**
- 기존 자산 재사용분은 `docs/reuse-map.md` 에 이미 표로 정리돼 있다.
  → **그 표가 곧 disclosure**. 영문본이 아래 있다. Project Story 에 반드시 넣는다.

## 필수 요건 (3개 전부 — 하나라도 빠지면 Stage One 탈락)

| # | 요건 | 상태 |
|---|---|---|
| ① | **Gemini 3.5+** (Gemini API 또는 Vertex AI) | ✅ `app/capture/llm.py::GeminiLLM` |
| ② | **Google 에이전트 프레임워크** (ADK / GenAI SDK / Antigravity SDK / GenKit) | 🟡 GenAI SDK 로 최소 충족. **ADK 에이전트 얹는 중** |
| ③ | **GCP 인프라 1개 이상** (Cloud Run / Cloud SQL / Firestore / GKE / Pub/Sub) | ⬜ Cloud Run + Cloud SQL 예정 |

## 왜 Collaborative Partner 인가

대회 정의:

> Build an agent that **leads the way and takes notes**. It should **ask
> clarifying questions, guide the user step-by-step**, and have a clear way to
> **capture feedback**, so it **constantly adapts** to the user's unique way of
> thinking.

| 대회 요구 | 이 레포에 이미 있는 것 |
|---|---|
| ask clarifying questions · guide step-by-step | 인터뷰 5단 사다리 `app/capture/interview.py` |
| takes notes | 판단 카드 `app/core/card.py` |
| capture feedback | 적용 보고(닻) → `anchored` 승격 |
| constantly adapts | 공백 큐 → 전문가 재발굴 루프 |

심사 세부가 이쪽을 향한다:

- *"Did the team ingest unusual, messy, or highly complex unstructured data streams?"*
  → **퇴직 앞둔 제조 현장 전문가의 암묵지.** 플로우마크를 보고 금형 온도가
  아니라 초기 사출 속도라고 짚는 감각. 이보다 messy 한 unstructured stream 이 없다.
- *"Did they build this for an **Unlikely Hero** outside of standard corporate roles?"*
  → 대상이 정확히 그 사람이다.

## 심사 배점

| 항목 | 비중 | 우리 대응 |
|---|---|---|
| Innovation & Operational Utility | 40% | 공백 큐 자율 라우팅 · 발굴 연장 12개 |
| Architectural Discipline & Tech Stack | 30% | **기저 교체 가능성이 실물로 증명됨** (아래) |
| Demo & Production Readiness | 30% | 4분 영상 + 아키텍처 다이어그램 + README |

보너스 (최대 +1.0 / 6점 만점):
블로그 +0.2 · 소셜 `#AllThingsAgenticHackathon` +0.2 · 추가 구글 모델(Gemma·Veo·Lyria) 각 +0.2 (최대 0.6)

### Architectural Discipline 에서 내세울 것

`docs/reuse-map.md` 에 적힌 alter-ai(coral) 규약 —

> 기저 LLM 은 산출물 층위로만 접합한다. 기저 교체 가능성이 전략 자산이다.

이게 말이 아니라 사실이라는 증거: **기저를 Anthropic → Gemini 로 바꾸는 데
`app/capture/llm.py` 한 파일만 바뀌었다.** 인터뷰어도 분신도 손대지 않았다.
접합면이 `answer` / `extract` 두 개뿐이라서다. 심사 기준의
*"How well did your team decouple systems?"* 에 그대로 답이 된다.

Anthropic 어댑터를 지우지 않고 **대체 기저로 남겨둔 것**도 의도다 — 교체
가능성은 코드가 남아 있을 때만 증명된다.

## 제출물 체크리스트

- [ ] 작동하는 프로젝트 (필수요건 ①②③)
- [ ] 호스팅 URL (Cloud Run) — **심사 종료 10/1 까지 살아 있어야 한다**
- [ ] 공개 저장소. 비공개면 `testing@devpost.com` + `cloudhackathons@google.com` 접근권
- [ ] README spin-up 가이드 (**영어**)
- [ ] 아키텍처 다이어그램
- [ ] 4분 데모 영상 — YouTube 공개, **영어 또는 영어 자막**,
      편집 없는 라이브 실행 + **Cloud Run 콘솔 화면 증빙 필수**
- [ ] Project Story (아래 disclosure 포함)
- [ ] 카테고리 = Collaborative Partner
- [ ] Built with 태그 (최대 25개)

## Disclosure 원문 — Project Story 에 그대로 넣는다

```markdown
## Pre-existing work disclosure

This project was created during the Submission Period (first commit:
2026-08-27). Per the "New Projects Only" rule, we disclose the pre-existing
work incorporated into it — all of it authored by the same author and
documented in `docs/reuse-map.md`:

- **github.com/wilcoco/alter-ai** — configuration skeleton, the
  "runs without an API key" convention (stub fallback), the two-method
  `BaseLLM` seam (`answer` / `extract`), SQLAlchemy schema style, and the
  deployment skeleton.
- **github.com/wilcoco/CAMS-KnowledgeNet** — external-reality anchor model
  (baseline / observed / direction), order-weighted link scoring, the
  dormant/revive state machine, and the exploration quota.
- **github.com/wilcoco/H2A2H2** — the P→I→C graph node/edge vocabulary, used
  to project a judgment card onto a graph (`Card.to_pic()`).

Everything else — the judgment-card domain model, the 5-rung elicitation
ladder, the 12 self-excavation instruments, the gap queue, the Gemini
integration, the ADK agent layer, and the Google Cloud deployment — was
built during the Submission Period.
```

## 남은 일정 (마감까지 ~4.5일)

| 일 | 할 것 |
|---|---|
| D-4 | ① Gemini 접합 **(완료)** · ③ Cloud Run + Cloud SQL 배포 |
| D-3 | ② ADK 공백 큐 에이전트 |
| D-2 | 아키텍처 다이어그램 · README 영문화 · 시드 데이터 |
| D-1 | 4분 영상 촬영/자막 · Project Story · 제출 |
| 여유 | 보너스(블로그·소셜) |

**코드 3일 · 영상과 문서 1.5일.** 심사 30% 가 문서와 영상이다. 여기서 줄이면 손해.
