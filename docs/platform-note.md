# 플랫폼 개명 영향 분석 — Vertex AI → Gemini Enterprise Agent Platform

> 확인일 2026-08-27. 결론 먼저: **우리 코드는 손댈 것이 없다.**
> 바뀐 것은 제품 이름과 콘솔 메뉴이고, 우리가 쓰는 접합면은 그대로다.

## 무슨 일이 있었나

| 날짜 | 사건 |
|---|---|
| 2026-04-22 | Google Cloud Next '26 — **Gemini Enterprise Agent Platform** 발표. Vertex AI 의 직계 후속 |
| 2026-05-19 | Google I/O '26 — **ADK 2.0** · Managed Agents 발표 |
| 2026-05-21 | 콘솔 메뉴에서 "Vertex AI" 명칭이 사라짐 |
| 2026-06-24 | **구형** `google-cloud-aiplatform` SDK 의 GenAI 모듈 제거 |
| 2026-11-26 | Vertex AI Extensions 종료 |

공식 제품 페이지 표기는 **"Gemini Enterprise Agent Platform (formerly Vertex AI)"** 다.
모델 서빙 중심에서 **에이전트 중심**으로 재편된 것이고, 학습·AutoML·Model Registry·
Endpoints 가 에이전트 플랫폼의 하위 기능으로 내려갔다.

## 우리에게 실제로 영향이 있는가 — 없다

| 항목 | 상태 | 근거 |
|---|---|---|
| API 엔드포인트 `aiplatform.googleapis.com` | **그대로** | 개명 후에도 Cloud API 엔드포인트 불변 |
| `gcloud services enable aiplatform.googleapis.com` | **그대로** | API 이름은 개명 대상이 아니다 |
| `google-genai` SDK | **그대로 · 권장 경로** | 개명 후에도 이 SDK 가 공식 권장 |
| `genai.Client(vertexai=True, project=…, location=…)` | **그대로** | 우리 `GeminiLLM.__init__` 이 쓰는 바로 그 호출 |
| Gemini API 키 경로 (`aistudio.google.com`) | **그대로** | 별개 경로, 영향 없음 |

### 폐지된 것은 우리가 안 쓰는 쪽이다

제거 대상은 **구형** `google-cloud-aiplatform`(python-aiplatform) 패키지의
GenAI 모듈들 — `vertexai.generative_models` 계열이다.
우리는 처음부터 신형 **`google-genai`** 를 썼다 (`pyproject.toml` 의 `google-genai>=1.0`).
**의도한 게 아니라 운이 좋았던 부분이 있으니, 기록해 둔다.**

## 그래서 Vertex 로 가는 게 맞나 — 맞다. 그리고 더 맞아졌다

1. **"Vertex 로 간다" 는 말이 곧 "이 플랫폼으로 간다" 는 말이다.** 없어진 제품으로
   가는 게 아니라, 이름이 바뀐 같은 제품으로 가는 것이다.
2. **Cloud Run 서비스 계정 자격증명이 그대로 먹는다** — 키가 없으니 유출될 것도 없다.
   심사 종료(10/1)까지 살아 있어야 하는 데모에 이게 결정적이다.
3. **플랫폼이 에이전트 중심으로 재편됐다.** 요건 ② 를 GenAI SDK 최소선에서
   **ADK 2.0** 으로 올리려던 계획이 개명 후 플랫폼 서사와 더 잘 맞는다.

## 문서·제출물에서 지킬 것

- Project Story 와 Built with 에는 **`Gemini Enterprise Agent Platform (formerly Vertex AI)`**
  로 병기한다. 심사자가 어느 쪽 이름으로 찾든 걸리게.
- 대회 규정 원문에 "Vertex AI" 로 적혀 있어도 문제없다 — 지금 그 제품이 이 이름이다.
- 콘솔 안내를 쓸 때 "Vertex AI 메뉴" 라고 쓰지 않는다. 없다.

## 확인하지 못한 것 (정직하게)

- **대회 규정 원문을 재확인하지 못했다.** `devpost.com` 이 이 세션의 이그레스
  프록시에서 차단된다. 요건 3종의 근거는 `docs/hackathon.md` 에 기록된 내용이며,
  그건 규정을 직접 읽은 다른 세션이 남긴 것이다. **제출 전에 사람이 눈으로 한 번
  더 볼 것.**
- API 활성화 명령은 결제 활성화 후 실제로 실행해 봐야 확정된다. 만약 이름이
  달라졌다면 `gcloud services list --available | grep -i -E 'aiplatform|gemini'` 로
  즉시 잡힌다.
