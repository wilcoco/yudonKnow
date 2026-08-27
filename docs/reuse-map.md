# 기존 자산 인용 지도 (Reuse Map)

> 새로 만들지 않는다. 이미 검증한 것을 가져온다.
> 이 레포는 wilcoco 의 기존 두 레포에서 **구조·규약·배포 골격**을 그대로 잇는다.

---

## 1. 출처별 인용 목록

### `github.com/wilcoco/alter-ai` (coral) — 골격의 8할

| 가져온 것 | 여기서 어디로 | 무엇을 바꿨나 |
|---|---|---|
| `app/config.py` — 환경변수 전량 기본값 + `postgres://` URL 정규화 | `app/config.py` | 정책 상수를 발굴/검증용으로 교체 |
| **"키 없이도 뜬다"** 규약 (`StubLLM` 폴백) | `app/capture/llm.py` | 그대로. stub 이 **답을 지어내지 않고 stub 임을 밝히는** 것까지 동일 |
| `BaseLLM` 프로토콜 — `answer` / `extract` 두 개뿐인 얇은 접합면 | `app/capture/llm.py` | 그대로. 기저 교체 가능성이 전략 자산이라는 원칙 유지 |
| **판정권을 LLM 에서 뺀 구조** (관문이 LLM 을 호출조차 안 함) | `app/alter/persona.py` 의 공백 판정 | 관문 → **공백 판정**으로 대상만 바뀜. 테스트로 강제하는 것도 동일 |
| `app/store/db.py` SQLAlchemy 스키마 스타일 · `init_db()` · lifespan | `app/store/db.py` | 도메인 테이블 교체 |
| `ServiceError` → 400 응답 예외 핸들러 | `app/web/app.py` | 그대로 |
| `railway.json` · `Procfile` · `runtime.txt` · `requirements.txt(-e .[postgres])` | 루트 | 시작 명령의 앱 경로만 교체 |
| `docs/deploy-railway.md` 구성 (Postgres vs Volume 선택 포함) | `docs/deploy-railway.md` | 환경변수 표 교체 |
| 3-패널 화면 + 단일 파일 Jinja 템플릿 + CSS 변수 다크모드 | `app/web/templates/*.html` | 산호초 팔레트 → 승계 팔레트. 3단 배치는 **인터뷰 화면**으로 재사용 |
| `/` 사용자 화면 · `/console` 운영자 화면 분리 | `/expert` `/alter` vs `/admin` | 역할 3분할로 확장 |
| 정직성 규약 — "미해결은 미해결이라고 쓴다" | `docs/design.md §8` | 그대로 (암묵지 병목 포함) |

### `github.com/wilcoco/CAMS-KnowledgeNet` (nightwish) — 검증 경제학

| 가져온 것 | 여기서 어디로 | 무엇을 바꿨나 |
|---|---|---|
| `verification.py` — **외부 현실 닻**(baseline/observed/direction) | `app/core/card.py` 의 `Anchor` + `anchored` 상태 | 측정 주체가 **후배의 적용 보고**로 바뀜 |
| `scoring.py` — 링크 **순서** 가중 (인기 아닌 안목) | `app/core/retrieval.py` 의 early-recognition 가중 | v0.1 은 가중 1.0 고정 (액수/인기로 노출을 사지 못하게) |
| `tree.py` — **잠복(dormant)/부활**, "삭제하지 않는다" | `app/core/card.py` 상태 기계 | 그대로 |
| 탐색 쿼터 (마태 효과 보정) | `app/core/retrieval.py::EXPLORE_QUOTA` | 그대로 |
| **대리변수 금지** (조회수·좋아요 안 씀) | `app/core/legacy.py` | 그대로. 인용 + 명시적 적용 보고만 집계 |
| `economy.py` 포인트/스테이킹 | **v0.1 미채택** | 퇴직 임박 전문가에게 사내 포인트는 동기가 아님 → P2 후보 |
| `governance.py` 규칙변경권 분권 | **v0.1 미채택** | 전문가 간 판단 충돌 문제(design §8-4)의 P2 후보 |

### `github.com/wilcoco/H2A2H2` — 그래프 포맷 호환

| 가져온 것 | 여기서 어디로 |
|---|---|
| P→I→C 노드/엣지 타입 (`premise` `inference` `conclusion` `concept` `claim` `evidence` / `infers` `supports` `refutes` `relates_to` `cites`) | `app/core/card.py::Card.to_pic()` — 판단 카드를 그래프로 투영 |

**카드 ↔ P→I→C 대응**

```
상황(situation) ─┐
신호(cues)       ─┴─▶ premise
판단(judgment)   ─┐
근거(rationale)  ─┴─▶ inference
조치(action)     ────▶ conclusion
예외(exceptions) ────▶ premise  + edge:refutes → inference
실패담(failure)  ────▶ evidence + edge:refutes → conclusion
영역(domain)     ────▶ concept
```

> 포맷을 맞춰두는 이유: 이 레포가 캔 지식을 coral/H2A2H2 온톨로지에 **그대로 부을 수
> 있어야** 한다. 승계 도구는 입구이고, 그쪽이 저수지다.

### `github.com/wilcoco/FDE` (FlowDesk) · `workproc` — 제품화 참고

| 참고한 것 | 어디에 |
|---|---|
| 멀티테넌시 · 그룹별 격리 · 한 그룹 독립 추출 | `docs/roadmap.md` P2 (사내 도입 시 필수 요건) |
| "say-do gap 을 결과 증명으로 닫는다" 패턴 | 후배 **적용 보고(닻)** 동선 (J3) |
| OKR/노하우 베이스의 실패 교훈 — *쓸 사람이 안 쓴다* | 전문가 홈의 **보람 최상단 배치** 결정 근거 |

---

## 2. 의도적으로 **안** 가져온 것

| 안 가져온 것 | 이유 |
|---|---|
| 포인트/UBI/스테이킹 경제 | v0.1 의 동기는 화폐가 아니라 **보람**. 화폐를 먼저 붙이면 발굴이 게임화되어 카드 질이 떨어진다 |
| 승격 관문(promotion gate)의 손상 시험 | 이 도구의 검증자는 알고리즘이 아니라 **후배의 현장 결과**다. 관문을 자동화하면 배지가 다시 권위가 된다 |
| Next.js/Prisma 스택 (FDE·workproc 계열) | 배포 최단거리 우선. FastAPI + Jinja 는 이미 두 레포에서 Railway 로 검증됨 |
| 벡터 DB / 임베딩 | 카드 수백 장 규모에서 이득 < 배포 복잡도. P1 재검토 |

---

## 3. 이식 시 지켜야 할 규약 (원 레포에서 함께 옴)

1. `app/core` 는 프레임워크·DB 를 **import 하지 않는다** (`tests/test_isolation.py` 가 강제).
2. LLM 은 **텍스트 in/out 경계에서만** 접합한다. 내부 표현 개입 금지.
3. **판정을 LLM 에 위임하지 않는다.** 공백 판정·검증 배지는 코드와 사람이 정한다.
4. 삭제 대신 **잠복**. 원본 발화는 영구 보존.
5. 미해결은 미해결이라고 문서에 쓴다. 풀렸다고 주장하지 않는다.
