# 구글 에셋 준비 — 사장님이 직접 해야 하는 것

> 대회 필수요건 3개 중 ②③ 이 계정에 묶여 있다. 코드는 준비돼 있고, **계정이 병목**이다.
> 순서대로. 1번이 안 끝나면 나머지가 전부 막힌다.

---

## ① Google Cloud 계정 + 결제 활성화 　⏱ 10분 　🔴 최우선

전부의 전제조건이다. 이것만 되면 나머지는 내가 CLI 로 처리할 수 있다.

1. <https://console.cloud.google.com> → 구글 계정으로 로그인
2. **결제(Billing) 계정 생성** — 카드 등록이 필요하다.
   무료 체험 크레딧이 붙고(가입 화면에 표시되는 실제 금액·기간을 확인할 것),
   **크레딧 소진 시 자동 과금되지 않고 멈춘다**(업그레이드 전까지).
3. **새 프로젝트 생성** — 이름 `yudonknow` 정도.
4. 생성 후 **프로젝트 ID** 를 나에게 알려준다. (이름이 아니라 ID. 보통 `yudonknow-473012` 꼴)

> 💡 이미 GCP 계정이 있고 무료 체험을 써 버렸다면 그대로 진행해도 된다.
> Cloud Run + Cloud SQL 최소 구성은 심사 기간(~10/1) 한 달 운영에 몇 달러 수준이다.
> 안전장치로 **예산 알림**을 $20 쯤에 걸어두는 걸 권한다 (Billing → Budgets & alerts).

**나에게 넘길 것: 프로젝트 ID**

---

## ② Gemini 접근 — 두 갈래, 둘 다 대회 요건을 충족한다 　⏱ 3분

코드는 이미 양쪽을 다 받는다 (`app/capture/llm.py::GeminiLLM`).

### (A) Gemini API 키 — 지금 당장 테스트하려면 이쪽
1. <https://aistudio.google.com/apikey> → **Create API key**
2. ①에서 만든 프로젝트를 고른다

### (B) Gemini Enterprise Agent Platform — Cloud Run 배포에는 이쪽이 낫다

> ⚠️ **콘솔에서 "Vertex AI" 를 찾지 말 것.** 2026-04-22 Next '26 에서
> **Gemini Enterprise Agent Platform (formerly Vertex AI)** 로 개명됐고,
> 2026-05-21 부터 콘솔 메뉴에 "Vertex AI" 라는 이름이 안 나온다.
> **폐지가 아니라 개명이다** — 엔드포인트(`aiplatform.googleapis.com`)도,
> 우리가 쓰는 SDK 호출부도 그대로다. 자세한 건 `docs/platform-note.md`.

- 키가 아예 필요 없다. Cloud Run 의 **서비스 계정 자격증명이 그대로 먹는다.**
- 유출될 키가 없으니 운영이 안전하고, 심사 기간 내내 살아 있어야 하는 데모에 유리하다.
- 내가 프로젝트 ID 만 받으면 설정한다.

**권고: 둘 다 준비.** 로컬 확인은 (A), 배포는 (B).

> ⚠️ **API 키를 채팅창에 붙여넣지 말 것.** Secret Manager 나 Cloud Run 환경변수에
> 직접 넣는다. 나는 키 없이도 배포 스크립트를 다 짤 수 있다.

**나에게 넘길 것: (A)를 발급했다는 사실만. 키 값은 본인이 콘솔에 직접 입력.**

---

## ③ API 활성화 　⏱ 2분 · 또는 내가 gcloud 로 처리

콘솔에서 클릭하거나, 결제 활성화만 되면 내가 한 줄로 켠다.

| API | 왜 필요한가 |
|---|---|
| `aiplatform.googleapis.com` | 필수요건 ① Gemini. 개명 후에도 **API 이름은 그대로**다 |
| Cloud Run Admin API | 필수요건 ③ 호스팅 |
| Cloud Build API | 소스 → 컨테이너 빌드 |
| Artifact Registry API | 빌드된 이미지 보관 |
| Cloud SQL Admin API | Postgres — **인터뷰 원본이 재배포에 살아남으려면 필수** |
| Secret Manager API | API 키 보관 |

```bash
gcloud services enable aiplatform.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com \
  sqladmin.googleapis.com secretmanager.googleapis.com
```

---

## ④ YouTube 채널 　⏱ 5분

4분 데모 영상을 **공개(Public)** 로 올려야 한다. 비공개·미등록이면 심사 불가.

- 구글 계정 있으면 채널은 자동으로 있다. 첫 업로드 시 채널명만 정하면 된다.
- **영어 또는 영어 자막 필수.** 한국어로 찍고 자막을 다는 게 현실적이다.
- **편집 없는 라이브 실행 + Cloud Run 콘솔 화면 증빙**이 요건이다.

---

## ⑤ 이미 되어 있는 것 — 확인만

| 항목 | 상태 |
|---|---|
| Devpost 계정 · draft `1155717-yudonknow` | ✅ 생성 완료 |
| 공개 GitHub 저장소 `wilcoco/yudonKnow` | ✅ public |
| 제출 자격 (제출 기간 내 최초 커밋) | ✅ `4df61ca` 2026-08-27 |
| 재사용 disclosure 문안 | ✅ `docs/project-story.md` |

---

## ⑥ 보너스 (+0.2씩, 여유 있으면) 　심사 총점 6점 중 최대 +1.0

| 보너스 | 필요한 계정 | 배점 |
|---|---|---|
| 블로그 글 | dev.to 또는 Medium (구글/깃허브 로그인) | +0.2 |
| 소셜 공유 `#AllThingsAgenticHackathon` | X 또는 LinkedIn | +0.2 |
| 추가 구글 모델 (Gemma · Veo · Lyria) | 위 GCP 계정 그대로 | 각 +0.2 (최대 0.6) |

> Veo 로 데모 영상 인트로를 만들면 **보너스와 영상 품질을 동시에** 챙긴다.
> Lyria 는 배경음. 우선순위는 낮지만 마감 여유가 생기면 가장 값싼 점수다.

---

## 정리 — 지금 사장님이 할 일 딱 셋

```
1. GCP 프로젝트 만들고 결제 활성화     → 프로젝트 ID 를 나에게
2. AI Studio 에서 Gemini API 키 발급   → 발급했다는 사실만 (키는 본인 보관)
3. 예산 알림 $20 설정                  → 사고 방지
```

이 셋이 끝나면 내가 Dockerfile · Cloud Run 배포 · Cloud SQL 연결 · ADK 에이전트 층까지
계정 없이 준비해 둔 것을 한 번에 올린다.

**계정 없이 지금 내가 진행할 수 있는 것:** Dockerfile, Cloud Run 서비스 정의,
Cloud SQL 접속 계층, ADK 공백 큐 에이전트, 시드 데이터, 영문 README, 아키텍처 다이어그램.
