# Cloud Run 배포 — Cloud Shell 붙여넣기용

> 필수요건 ③ (GCP 인프라)를 충족하는 경로다. `docs/hackathon.md` 참고.
> **심사 종료(2026-10-01)까지 이 URL 이 살아 있어야 한다.**
>
> 이 문서의 명령은 **Cloud Shell** 에 붙여넣는 것을 전제한다. 브라우저에서 이미
> 인증돼 있고 `gcloud`·`docker` 가 깔려 있어서, 로컬에 아무것도 설치할 필요가 없다.
> 콘솔 우상단 `>_` 아이콘이 Cloud Shell 이다.

---

## 0. 준비 — 한 번만

```bash
export PROJECT=yudonknow            # 프로젝트 ID (이름 아님)
export REGION=us-central1
export SERVICE=yudonknow
export SQL_INSTANCE=yudonknow-db
export REPO=yudonknow
export SA=yudonknow-run

gcloud config set project "$PROJECT"
```

### API 활성화

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com
```

> `aiplatform.googleapis.com` 은 플랫폼이 **Gemini Enterprise Agent Platform** 으로
> 개명된 뒤에도 이름이 그대로다. 콘솔 메뉴에서 "Vertex AI" 를 찾지 말 것 —
> 자세한 건 `docs/platform-note.md`.

---

## 1. 소스 가져오기

```bash
git clone -b claude/expert-knowledge-preservation-tool-vtj127 \
  https://github.com/wilcoco/yudonKnow.git
cd yudonKnow
```

---

## 2. Cloud SQL (Postgres) — 인터뷰 원본이 재배포에 살아남게

**이걸 건너뛰면 재배포 한 번에 전문가의 20분이 사라진다.**
컨테이너 파일시스템은 인메모리다.

```bash
# 인스턴스 (몇 분 걸린다)
gcloud sql instances create "$SQL_INSTANCE" \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region="$REGION" \
  --storage-size=10GB \
  --storage-auto-increase

# 티어가 거부되면 --tier=db-g1-small 로 바꿔서 다시.

gcloud sql databases create yudonknow --instance="$SQL_INSTANCE"

# 비밀번호는 만들어서 곧장 Secret Manager 로 — 화면에 찍지 않는다.
DB_PASS="$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)"
gcloud sql users create ydk --instance="$SQL_INSTANCE" --password="$DB_PASS"

CONN="$(gcloud sql instances describe "$SQL_INSTANCE" --format='value(connectionName)')"
echo "connection name: $CONN"

# Cloud Run 은 유닉스 소켓으로 붙는다. 앱이 postgresql:// 를 psycopg URL 로
# 정규화하므로(app/config.py) 이 형태 그대로 넣으면 된다.
printf 'postgresql://ydk:%s@/yudonknow?host=/cloudsql/%s' "$DB_PASS" "$CONN" \
  | gcloud secrets create ydk-database-url --data-file=-
```

---

## 3. 서비스 계정 — 키 없이 Gemini 를 쓴다

```bash
gcloud iam service-accounts create "$SA" --display-name="yudonKnow Cloud Run"
SA_EMAIL="$SA@$PROJECT.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA_EMAIL" --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding "$PROJECT" \
  --member="serviceAccount:$SA_EMAIL" --role="roles/cloudsql.client"
gcloud secrets add-iam-policy-binding ydk-database-url \
  --member="serviceAccount:$SA_EMAIL" --role="roles/secretmanager.secretAccessor"
```

> **API 키를 만들지 않는다.** Cloud Run 의 서비스 계정 자격증명이 그대로 Gemini 에
> 먹는다. 유출될 키가 없고, 심사 기간 내내 살아 있어야 하는 데모에서 이게 결정적이다.

---

## 4. 이미지 빌드

```bash
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker --location="$REGION"

IMAGE="$REGION-docker.pkg.dev/$PROJECT/$REPO/app:latest"
gcloud builds submit --tag "$IMAGE" .
```

---

## 5. 배포

```bash
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --service-account="$SA_EMAIL" \
  --add-cloudsql-instances="$CONN" \
  --set-secrets="DATABASE_URL=ydk-database-url:latest" \
  --set-env-vars="YDK_VERTEX_PROJECT=$PROJECT,YDK_VERTEX_LOCATION=$REGION,YDK_LLM_PROVIDER=gemini,YDK_SEED=1" \
  --min-instances=0 \
  --max-instances=3 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300

gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)'
```

- `--allow-unauthenticated` 는 **규정 요구사항**이다: *"free of charge and without
  any restriction, for testing… until the Judging Period ends."*
- `--min-instances=0` 으로 놀 때는 과금이 거의 없다. 콜드 스타트가 몇 초 붙는데,
  4분 영상에서는 첫 호출을 미리 한 번 깨워두고 찍으면 된다.
- `YDK_SEED=1` — DB 가 비었을 때만 심는다. 심사자가 첫 화면에서 바로 만져볼 것이
  있어야 한다 (`app/seed.py`).

---

## 6. 확인 — 여기서 반드시 걸러야 하는 것

```bash
URL="$(gcloud run services describe "$SERVICE" --region="$REGION" --format='value(status.url)')"

# (1) 살아 있는가 + 무엇에 붙었는가
curl -s "$URL/api/health"
# 기대: {"status":"ok",...,"llm":"gemini-...","llm_enabled":true,"store":"postgresql"}
```

**`"store":"postgresql"` 이 아니면 Cloud SQL 이 안 붙은 것이다** — 그대로 두면
재배포마다 데이터가 날아간다.

```bash
# (2) Gemini 가 실제로 답하는가 — 모델명이 틀리면 조용히 stub 으로 떨어진다
curl -s -X POST "$URL/api/alter/dale/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"the aeration foam went brown overnight","asker":"judge"}' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print("stubbed:", d["stubbed"]); print(d["text"][:200])'
```

**`stubbed: true` 면 필수요건 ① 이 사실상 미충족이다.** 앱은 뜨지만 Gemini 가
안 붙은 것이고, 화면만 봐서는 구분이 안 된다. 이때는 모델 ID 를 의심한다:

```bash
# 기본값은 gemini-3.5-pro 다. 사용 가능한 이름이 다르면 바꿔서 재배포한다.
gcloud run services update "$SERVICE" --region="$REGION" \
  --update-env-vars="YDK_GEMINI_MODEL=<실제 모델 ID>"
```

> ⚠️ **모델 ID 는 배포 시점에 반드시 눈으로 확인할 것.** 이 문서를 쓴 세션은
> `gemini-3.5-pro` 가 현재 Vertex 에서 유효한 정확한 ID 인지 직접 확인하지 못했다.
> 규정은 "Gemini 3.5 or newer" 를 요구하므로, 3.5 이상이기만 하면 어느 변형이든 된다.

```bash
# (3) 화면 4개
for p in / /expert /alter/dale /admin; do
  echo "$p $(curl -s -o /dev/null -w '%{http_code}' "$URL$p")"
done

# (4) 영어 심사자가 보는 화면인지 (규정 6조)
curl -s -H 'Accept-Language: en-US,en;q=0.9' "$URL/" | grep -o '<h1>.*</h1>'
# 기대: <h1>The senior leaves. The judgment stays.</h1>
```

---

## 7. 비용 — 크레딧 없이도 감당되는 수준

크레딧 신청 폼은 마감됐다(선착순 소진). 자비로 돌려도 심사 기간 5주 기준:

| 항목 | 대략 |
|---|---|
| Cloud Run (min-instances=0) | 무료 티어 안. 거의 0 |
| **Cloud SQL db-f1-micro** | **월 $8~10 — 유일하게 의미 있는 비용.** scale-to-zero 가 안 된다 |
| Gemini 호출 | 심사자 몇 번 수준이면 무시할 만함 |
| Artifact Registry | 몇 센트 |

**Billing → Budgets & alerts 에서 $20 알림을 걸어둘 것.**

심사 끝나고(10/1 이후) 정리:

```bash
gcloud run services delete "$SERVICE" --region="$REGION"
gcloud sql instances delete "$SQL_INSTANCE"
```

---

## 8. 재배포 (코드 고친 뒤)

```bash
cd yudonKnow && git pull
gcloud builds submit --tag "$IMAGE" .
gcloud run deploy "$SERVICE" --image="$IMAGE" --region="$REGION"
```

기존 환경변수·시크릿·Cloud SQL 연결은 유지된다. 시드는 DB 가 비었을 때만 도므로
재배포해도 쌓인 카드는 그대로다.

---

## 로컬에서 돌리기 (심사자용 — README 에도 같은 내용이 있다)

```bash
pip install -e ".[dev]"
YDK_SEED=1 uvicorn app.web.app:app --reload   # http://127.0.0.1:8000
pytest                                        # 40개
```

`ANTHROPIC_API_KEY` 도 `GOOGLE_API_KEY` 도 없이 뜬다 — LLM 만 stub 으로 떨어지고
발굴 → 카드 → 분신 → 공백 → 닻 동선은 그대로 돈다.
