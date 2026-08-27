# Railway 배포

`alter-ai` 에서 검증된 배포 골격을 그대로 쓴다.

## 한 번만 하면 되는 것

1. **Railway → New Project → Deploy from GitHub repo** → `wilcoco/yudonKnow` 선택,
   브랜치는 `claude/expert-knowledge-preservation-tool-vtj127`.
2. Nixpacks 가 `requirements.txt` 를 읽어 자동 빌드한다. 시작 명령·헬스체크는
   `railway.json` 에 있으므로 따로 설정할 필요가 없다.
3. **Settings → Networking → Generate Domain** 으로 공개 URL 생성.

이 상태로 이미 뜬다. 아래는 붙이면 좋아지는 것이지 필수가 아니다.

## LLM 붙이기

`ANTHROPIC_API_KEY` 를 Variables 에 넣는다. 없으면 **stub 모드**로 뜬다 —
인터뷰 사다리·카드·분신·공백·닻·유산 원장의 **동선은 그대로 돌고**, 질문 생성과
카드 자동 구조화만 규칙 기반으로 대체된다. `/api/health` 의 `llm` 필드로 확인.

| 변수 | 기본값 | 설명 |
|---|---|---|
| `ANTHROPIC_API_KEY` | (없음) | 없으면 stub 인터뷰어 |
| `YDK_MODEL` | `claude-opus-5` | 기저는 교체 가능한 부품 |
| `YDK_MAX_TOKENS` | `8000` | |
| `YDK_INTERVIEW_TURNS` | `7` | 한 세션 목표 질문 수 (20분 기준) |
| `YDK_RETRIEVAL_TOP_K` | `6` | 분신이 한 답에 끌어올 카드 수 |
| `YDK_EXPLORE_QUOTA` | `0.25` | 검색 결과 중 신규·저인용 카드 강제 배정 비율 |
| `YDK_CONFIDENCE_FLOOR` | `0.35` | 이 아래면 **답하지 않고** 공백으로 넘긴다 |
| `YDK_ANCHOR_MIN_REPORTS` | `2` | ✔ 현장 검증 배지에 필요한 최소 적용 보고 수 |

## 데이터 영속

기본은 SQLite (`./data/yudonknow.db`). **Railway 파일시스템은 재배포마다
초기화되므로, 인터뷰를 쌓으려면 둘 중 하나가 필요하다:**

- **Postgres 추가 (권장)** — `+ New → Database → PostgreSQL` 을 붙이면
  `DATABASE_URL` 이 자동 주입되고 앱이 집어 쓴다. `postgres://` 접두사는
  코드에서 SQLAlchemy 드라이버 URL 로 정규화한다.
- **Volume 마운트** — Volume 을 `/data` 에 붙이고 `YDK_DATA_DIR=/data` 설정.

> 인터뷰 원본 발화는 삭제하지 않는 설계다. Postgres 를 붙이지 않은 채
> 파일럿을 시작하면 재배포 한 번에 전문가의 20분이 사라진다. **먼저 붙일 것.**

## 확인

```bash
curl https://<your-domain>/api/health
# {"status":"ok","version":"0.1.0","llm":"claude-opus-5","llm_enabled":true,"store":"postgresql"}
```

헬스체크는 DB 왕복(`SELECT 1`)까지 하므로 앱만 뜨고 DB 가 죽은 상태를 잡아낸다.

## 로컬에서 돌리기

```bash
pip install -e ".[dev]"
uvicorn app.web.app:app --reload
# http://127.0.0.1:8000
pytest
```
