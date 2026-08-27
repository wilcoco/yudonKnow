# 아키텍처

![Architecture](architecture.svg)

> 한 문장: **모델은 맨 바깥에 있고, 모델이 말한 것은 아무것도 결정하지 않는다.**

---

## 1. 요청 하나가 지나가는 길

후배가 `/alter/dale` 에서 질문을 하나 던졌을 때:

| # | 어디서 | 무슨 일 |
|---|---|---|
| 1 | `app/web/api.py` | 언어 협상(`Accept-Language`) 후 `service.ask_alter()` 로 넘긴다 |
| 2 | `app/store/service.py` | DB 에서 카드를 조립해 **코어 객체**로 만든다 |
| 3 | `app/core/retrieval.py` | 통제권(`visible_to`)·인용 자격(`citable`)을 **검색 단계에서** 걸고 점수를 낸다 |
| 4 | **공백 관문** | `confidence < 0.35` 면 **여기서 끝난다.** LLM 은 호출되지 않는다 |
| 5 | `app/capture/llm.py` | 통과했을 때만. 카드와 질문을 텍스트로 넘긴다 |
| 6 | Gemini | 답을 텍스트로 돌려준다 |
| 7 | `service.py` | 인용 기록·유산 원장에 남기고 화면으로 |

**4번이 이 그림의 전부다.** 나머지는 평범한 웹앱이다.

---

## 2. 왜 관문이 LLM 앞에 있는가

모델에게 *"모르면 모른다고 해"* 라고 부탁하는 설계는 실패한다. 부탁이기 때문이다.

여기서는 확신도가 `app/core/retrieval.py` 의 검색 점수로 **평범한 파이썬에서**
계산되고, 기준 미달이면 어댑터가 **생성조차 되지 않는다.**

```python
if result.is_gap:
    # LLM 은 여기서 호출되지 않는다. 이 줄이 이 파일의 존재 이유다.
    return AlterReply(text=gap_message(...), cards=[], is_gap=True)
```

`tests/test_core.py::test_gap_decision_never_calls_the_llm` 이 이 구조를 강제한다 —
호출되면 터지는 스파이 LLM 을 넣어서 검사한다. **부탁이 아니라 배선이다.**

### 이게 왜 제품의 사활인가

이 도구의 출발 전제가 *"후배는 틀린 답을 검증할 능력이 없다"* 이다. 그러니
**무관한 질문에 붙는 확신도는 기능 결함이 아니라 신뢰 파괴**다.

실제로 한 번 샜다. 영어 데모 시드를 심자마자 분신이
*"how do I calibrate the new UV bank"* 에 전혀 무관한 카드로 자신 있게 답했다.
원인 두 개 — 한국어 불용어만 있고 영어 불용어가 없었고, 한국어 복합명사용
부분일치 규칙이 라틴 문자에서 `"rate"` ⊂ `"calibrate"` 로 터졌다.
지금은 부분일치가 한국어 전용이고
`test_unrelated_english_question_is_always_a_gap` 이 재발을 막는다.

---

## 3. 층 분리 — 무엇이 무엇을 모르는가

```
app/core/      의존성 0. 프레임워크·ORM·SDK 를 모른다.
               카드 · 검색/확신도 · 커버리지 · 유산 원장
               ↑ tests/test_isolation.py 가 import 를 검사해 빌드를 깬다

app/capture/   연장 12개 · 5단 사다리 · LLM 어댑터
app/alter/     분신 — 카드 결속 · 근거 편성 · 공백 판정
app/store/     SQLAlchemy 스키마 + 오케스트레이션 (여기만 DB 를 안다)
app/web/       FastAPI + JSON API + 서버 렌더 화면 4개
app/i18n.py    언어 협상. 의존성 0
```

**코어가 DB 를 모르는 것이 다이어그램에도 나타난다** — 저장소 화살표는
`service.py` 에 붙지 `app/core` 를 관통하지 않는다.

**코어는 언어도 모른다.** `legacy.py` 는 문장 대신 `headline_key` 와 이벤트를
돌려주고, 문장은 표현 층이 만든다. 판정 로직에 언어가 섞이면 둘 다 망가진다.

---

## 4. 접합면이 두 개뿐인 이유

```python
class BaseLLM(Protocol):
    def answer(self, system: str, prompt: str) -> str: ...
    def extract(self, prompt: str, schema: dict) -> dict: ...
```

**텍스트 in / 텍스트 out.** 내부 표현에 개입하지 않는다.

이게 말이 아니라 사실이라는 증거: 기저를 Anthropic → Gemini 로 바꾸는 데
**`app/capture/llm.py` 한 파일만 바뀌었다.** 발굴 사다리도 분신도
`app/core/` 의 점수 규칙도 손대지 않았고 테스트 전부 통과했다.

**Anthropic 어댑터를 지우지 않고 남긴 것도 의도다** — 교체 가능성은 대안이
컴파일되는 동안에만 증명된다. `YDK_LLM_PROVIDER` 하나로
`Gemini → Anthropic → stub` 순으로 떨어진다.

### stub 이 있는 이유

키가 없으면 stub 으로 떨어지고, **답을 지어내는 대신 자기가 stub 이라고 밝힌다.**
그럴듯한 가짜를 만들면 카드가 쓰레기로 차고 검증 프로토콜이 무너진다.
그리고 발굴 → 카드 → 분신 → 공백 → 닻 동선은 stub 에서도 그대로 돈다 —
**기저 독립성의 실측이기도 하다.**

---

## 5. Google Cloud 위에서

| 구성요소 | 무엇 | 왜 |
|---|---|---|
| **Cloud Run** | 컨테이너 서빙, `min-instances=0` | 놀 때 과금 없음. 심사 기간 5주를 자비로 감당할 수 있는 이유 |
| **Cloud SQL (Postgres)** | 카드·세션·공백·닻·원장 | 컨테이너 파일시스템은 인메모리다. **이걸 안 붙이면 재배포 한 번에 전문가의 20분이 사라진다** |
| **Gemini 3.5 / GenAI SDK** | 인터뷰 질문 생성 · 카드 구조화 · 분신 응답 | 필수요건 ①②. **Vertex 경로라 API 키가 없다** — 런타임 서비스 계정이 그대로 인증된다 |
| **Secret Manager** | DB 접속 문자열 | 비밀번호가 명령 이력이나 환경변수 목록에 남지 않게 |

배포 절차: [`deploy-cloudrun.md`](deploy-cloudrun.md).
플랫폼 개명(Vertex AI → Gemini Enterprise Agent Platform) 영향은
[`platform-note.md`](platform-note.md) — **코드는 손댈 것이 없다.**

### 배포 후 반드시 걸러야 하는 것

브라우저로는 정상과 구분이 안 되는 실패가 둘 있다.

```bash
curl -s "$URL/api/health"     # "store" 가 "sqlite" 면 Cloud SQL 미연결
                              # → 재배포마다 데이터 증발
curl -s -X POST "$URL/api/alter/dale/ask" ... | grep stubbed
                              # "stubbed": true 면 Gemini 미연결
                              # → 앱은 떠도 필수요건 ① 이 사실상 미충족
```

---

## 6. 데이터가 남는 방식

- **원본 발화(`turns.answer`)는 어떤 경로로도 삭제되지 않는다.** 카드는 해석이고
  해석은 틀릴 수 있다. 원본이 있어야 재해석이 가능하다.
- **카드는 삭제 대신 잠복(`dormant`)** 한다. 조건이 바뀌어 되살아나는 판단이
  현장에 실제로 있다.
- **유산 원장은 append-only.** 판정 이력은 감사 가능해야 한다.
- 카드는 `Card.to_pic()` 으로 **P→I→C 그래프로 투영**된다 — 이 레포가 캔 지식을
  coral/H2A2H2 온톨로지에 그대로 부을 수 있게 ([`reuse-map.md`](reuse-map.md)).

---

## 7. 의도적으로 안 넣은 것

[`design.md`](design.md) §7 · [`lineage.md`](lineage.md) 참고. 요약하면:

- **벡터 검색을 1차 경로로 쓰지 않는다.** 확신도가 **공백 판정의 임계값**이 되므로
  왜 그 점수가 나왔는지 사람이 즉시 설명할 수 있어야 한다. 임베딩은 재순위
  후보이지 판정 근거가 아니다.
- **자동 승격 관문 없음.** 검증자는 알고리즘이 아니라 현장이다.
- **포인트 경제 없음.** 퇴직 임박 전문가에게 사내 포인트는 동기가 아니다.
