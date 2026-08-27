# yudonKnow

> **선배는 떠나도, 판단은 남는다.**
> 퇴직과 함께 사라지는 것은 문서가 아니라 **상황을 읽는 눈**이다.

핵심 전문가의 퇴직으로 사내 지식이 증발하는 문제 — 링크드인에서
*Institutional Knowledge Loss · Brain Drain* 으로 반복되는 그 문제를,
**문서 수집이 아니라 자기 발굴**로 푼다.

```
🧰 연장을 골라 스스로 판다 ─▶ 판단 카드 ─▶ 내가 승인 (공개 범위도 내가)
                                            │
   후배가 분신에게 묻는다 ◀── 분신이 내 카드로만 답한다 + 근거를 편다
        │                                   ▲
   결과를 보고한다 ─▶ ✔ 현장 검증           │
        │                                   │
   못 답한 질문 ─▶ 내 큐로 돌아온다 ─────────┘
        │
   쓰인 흔적이 나에게 돌아온다 — **보람**
```

## 왜 다른가

| 기존 지식관리 | yudonKnow |
|---|---|
| **문서를 올리세요** | **연장을 드립니다.** 전문가는 쓰지 않고, 파고, 답한다 |
| 대상은 "동기 없는 직원" | 대상은 **이미 남기고 싶어 하는 사람.** 부족한 건 의지가 아니라 연장이다 |
| 검색되는 위키 | **대화하는 분신.** 후배는 검색하지 않고 선배에게 묻듯이 묻는다 |
| RAG 챗봇이 없는 걸 지어냄 | **모르면 모른다고 한다.** 그리고 그 공백이 전문가 큐로 돌아간다 |
| 지식은 회사 자산 | **처분권은 본인에게.** 비공개·봉인·지목·전량 내보내기·분신 정지 |
| 커버리지 100% 달성 | **담지 못한 것(🔴 손끝)을 따로 세어 보여준다.** 천장은 0.95 |

## 🧰 자기 발굴 연장 12개

전문가가 **직접 고른다.** AI 는 추천만 한다. 첫 2주는 2개만 열린다 —
선택지가 많으면 아무것도 고르지 않기 때문에.

```
🔨 순간 포착    방금 판단한 게 있나요? 30초, 세 줄.
⚖️ 오답 채점기  제가 틀린 답을 냅니다. 빨간펜만 들어주세요.   ← 효율 1위
🔍 대조 짝      비슷한 두 상황. 무엇이 다른지만.
👂 감각 사다리  '그냥 감으로'를 눈·귀·손·냄새·타이밍·리듬 + 비유로.
📷 가리키기 · 🗣 소리내어 하기 · 🥊 분신과 논쟁 · ✉️ 후계자에게
📉 회한 채굴 · 🎚 경계 슬라이더 · 🗺 머릿속 지도 · 🌡 암묵지 온도계
```

정본: [`docs/self-excavation.md`](docs/self-excavation.md)

## 판단 카드 — 원자 단위

문서도 Q&A 도 아니고 **하나의 상황 판단**이 하나의 카드다.

```
제목  플로우마크가 게이트 반대편에만 생기면
신호  게이트 반대편에만 물결무늬 / 압력 그래프 초기 피크가 느슨   ← 절차서에 없는 것
판단  금형 온도가 아니라 초기 사출 속도 부족
조치  1단 속도 +8% → 30샷 관찰
예외  재생재 30% 초과 시 안 통한다                              ← 없으면 사고 난다
실패담 2019년 속도만 올리다 게이트 마모를 놓쳐 금형 수리 2주
말로 안 되는 것  "느슨하다"는 그래프 감각 → 🔴 도제 항목으로 이관
```

**`신호`가 빈 카드는 인용되지 않는다** (코드로 강제). 신호 없는 판단은
"그때그때 다르다"와 같은 말이라 후배가 쓸 수 없다.

## 읽는 순서

1. [`docs/design.md`](docs/design.md) — 설계 정본 (개념·바퀴·상태기계·아키텍처·미해결)
2. [`docs/self-excavation.md`](docs/self-excavation.md) — **자기 발굴 연장 12개 + 통제권**
3. [`docs/user-flows.md`](docs/user-flows.md) — 사용자 동선 (전문가·후배·관리자 + 도입 4주)
4. [`docs/elicitation-protocol.md`](docs/elicitation-protocol.md) — 인터뷰 5단 사다리
5. [`docs/reuse-map.md`](docs/reuse-map.md) — 기존 레포에서 무엇을 가져왔나
6. [`docs/roadmap.md`](docs/roadmap.md) — P0/P1/P2 + 거버넌스 + 성공지표
7. [`docs/deploy-railway.md`](docs/deploy-railway.md) — 배포

## 빠른 시작

```bash
pip install -e ".[dev]"
uvicorn app.web.app:app --reload     # http://127.0.0.1:8000
pytest                               # 34개
```

`ANTHROPIC_API_KEY` 가 없어도 뜬다 — LLM 은 stub 로 떨어지고 **동선은 그대로 돈다**
(질문 생성은 규칙 기반 사다리, 카드 구조화만 사용자 입력으로).

배포: [`docs/deploy-railway.md`](docs/deploy-railway.md) — Railway + Nixpacks,
`DATABASE_URL` 붙이면 Postgres 자동 인식.

## 기존 자산 재사용

| 출처 | 가져온 것 |
|---|---|
| [alter-ai (coral)](https://github.com/wilcoco/alter-ai) | "키 없이도 뜬다" 규약 · 얇은 LLM 접합면 · **판정을 LLM 에서 뺀 구조** · Railway 배포 골격 · 3-패널 UI |
| [CAMS-KnowledgeNet](https://github.com/wilcoco/CAMS-KnowledgeNet) | 외부 현실 닻(verification) · 잠복/부활 · 탐색 쿼터 · **대리변수 금지** |
| [H2A2H2](https://github.com/wilcoco/H2A2H2) | P→I→C 노드/엣지 스키마 — `Card.to_pic()` 로 포맷 호환 유지 |
| [FDE](https://github.com/wilcoco/FDE) · [workproc](https://github.com/wilcoco/workproc) | 멀티테넌시 요건 · 결과 증명으로 say-do gap 닫기 |

상세 대응표: [`docs/reuse-map.md`](docs/reuse-map.md)

## 레포 구조

```
app/core/      의존성 0 — 카드 · 검색/확신도 · 커버리지 · 유산 원장
app/capture/   연장 12개 · 인터뷰 사다리 · LLM 어댑터(텍스트 in/out 만)
app/alter/     분신 — 카드 밖으로 안 나감 · 근거 결속 · 공백 판정
app/store/     스키마 + 오케스트레이션
app/web/       FastAPI + JSON API + 단일 파일 템플릿
tests/         불변식 + 한 바퀴 통합 (test_the_wheel_closes)
docs/          정본 7문서
```

## 미해결 (건드리되 풀렸다고 주장하지 말 것)

암묵지 병목(🔴 손끝 지식은 12개 연장으로도 안 나온다 — *표시만* 한다) ·
전문가의 자기 편향 · 분신의 권위 고착 · 시간 확보(제품이 아니라 도입 조건) ·
전문가 간 판단 충돌. 상세: [`docs/design.md`](docs/design.md) §8.
