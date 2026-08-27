# CLAUDE.md — yudonKnow 레포 작업 지침

## 이 프로젝트가 무엇인가 (30초 버전)
퇴직하는 전문가의 **암묵지를 스스로 파낼 연장**을 쥐여주고, 파낸 판단을
카드로 굳혀, 그 카드로만 말하는 **분신(alter)** 을 남겨 후배가 대화로
물려받게 하는 승계 도구. 전문가에게 돌아가는 것은 **보람**이다.

**"문서 수집 도구"가 아니라 "자기 발굴 도구"다.** 이 구분이 제품의 전부다.
사용자는 설득할 대상이 아니라 이미 남기고 싶어 하는 사람이고, 부족한 것은
의지가 아니라 연장이다.

## 필독 순서 (코드 작성 전)
1. `docs/design.md` — 설계 정본 v0.1
2. `docs/self-excavation.md` — 연장 12개 + 통제권 (제품 차별점의 정본)
3. `docs/user-flows.md` — 화면·동선
4. `docs/elicitation-protocol.md` — 인터뷰 사다리
5. `docs/reuse-map.md` — 기존 레포에서 무엇을 가져왔고 무엇을 안 가져왔나

## 되돌리지 말 것 (테스트가 강제하는 설계 결정)

| 규칙 | 강제하는 테스트 |
|---|---|
| **공백 판정은 LLM 이 하지 않는다.** 확신도 미달이면 LLM 호출 없이 공백 반환 | `test_gap_decision_never_calls_the_llm` |
| **`신호(cues)` 없는 카드는 인용 불가** — 완성도와 무관한 하드 게이트 | `test_card_without_cues_is_never_citable` |
| **분신은 사칭하지 않는다** — 표시는 언제나 "OOO의 분신" | `test_alter_label_never_impersonates` |
| **통제권은 전문가에게** — 비공개·봉인·지목·분신 정지 | `test_sealed_card_stays_shut...` 외 |
| **커버리지는 1.0 에 닿지 않는다** (천장 0.95) | `test_coverage_never_claims_completeness` |
| **연장은 처음부터 전부 보인다.** 과부하는 감추기가 아니라 **추천 3개 상한**으로 막는다 | `test_every_instrument_is_available_from_the_first_day` · `test_overload_is_held_back_by_the_suggestion_not_by_hiding` |
| **`app/core` 는 프레임워크·DB 를 import 하지 않는다** | `tests/test_isolation.py` |
| **한 바퀴가 닫힌다** — 승인 카드가 후배 답에 실제로 인용된다 | `test_the_wheel_closes` |
| **발굴만으로 카드가 채워진다** — 기저 없이도. 답은 그 답을 끌어낸 질문의 칸에 들어간다 (`Turn.targets`) | `tests/test_excavation.py` |
| **문서는 질문이 되지 카드가 되지 않는다** — 절차서 빨간펜은 공백 큐에만 쓴다 | `test_a_document_becomes_questions_never_cards` |
| **카드는 파낸 언어로 산다** — 검색은 언어를 넘지 않는다 | `test_the_wheel_closes` (영어 질문 → 공백) |

## 설계 원칙 (위반 금지)
- LLM 은 **산출물 층위**로만 접합 (텍스트 in/out). 교체 가능성이 전략 자산.
- **판정을 LLM 에 위임하지 않는다.** 공백·검증 배지는 코드와 사람이 정한다.
- ✔ 배지의 출처는 전문가의 권위가 아니라 **후배의 적용 보고(닻)**.
  조회수·좋아요 같은 **대리변수 금지**.
- 카드는 삭제하지 않고 **잠복(dormant)**. **원본 발화는 영구 보존.**
- 전문가가 고친 것이 기계 추출보다 우선한다 (승인된 카드는 덮어쓰지 않는다).
- 전문가 화면에 기계 어휘를 쓰지 않는다 (상태값·확신도 수치 노출 금지).
- 담지 **못한** 것(🔴 손끝)을 감추지 않는다. 커버리지와 항상 함께 보고.

## 기존 자산 재사용 (새로 만들지 말 것)
- `wilcoco/alter-ai` — config·LLM 어댑터·stub 폴백·ServiceError·Railway 골격·3패널 UI
- `wilcoco/CAMS-KnowledgeNet` — verification(현실 닻)·tree(잠복/부활)·탐색 쿼터
- `wilcoco/H2A2H2` — P→I→C 스키마 (`Card.to_pic()` 포맷 호환 유지)
- 대응표: `docs/reuse-map.md`. **안 가져온 것**(포인트 경제·자동 승격 관문·
  Next.js 스택·벡터 DB)에는 이유가 적혀 있다. 되돌리려면 세미나 합의부터.

## 사용자 소통 규약
- 주요 주장에 "문헌 기반 / 내 보간" 구분과 확신도 표기.
- 사용자 아이디어를 기존 범주로 분류할 때 **차이점 반드시 병기.**
- 스코프 축소·기존 패러다임 회귀 방향의 제안은 스스로 의심할 것.
- 설계 변경은 대화로 합의한 뒤 `docs/` 에 반영.

## 미해결 (건드리되 풀렸다고 주장하지 말 것)
암묵지 병목(🔴 손끝) · 전문가 자기 편향 · 분신 권위 고착 · 발굴 시간 확보 ·
전문가 간 판단 충돌. 상세: `docs/design.md` §8.

## 구현 현황 (2026-08, P0 한 바퀴 완료)
- 진입점 `app/web/app.py`, 오케스트레이션 `app/store/service.py`.
- 화면: `/` 랜딩 · `/expert` 전문가(온보딩·홈·발굴 3단) · `/alter/{id}` 후배 ·
  `/admin` 승계 리스크 보드.
- 테스트 44개 통과. stub 모드(키 없음)에서도 **발굴 → 카드 → 승인 → 인용**
  전 동선 동작 확인 (`tests/test_excavation.py` 가 손으로 칸을 채우지 않고 판다).
  stub 에서 강등되는 것은 **품질**이다: 질문 생성이 규칙 기반으로 떨어지고,
  카드 구조화가 "답을 겨냥한 칸에 넣기"로 떨어지고, 분신이 카드 원문을 그대로
  낸다. 동선이 끊기지는 않는다.
- **코드를 고치기 전에 `docs/design.md` §7(의도적으로 안 하는 것)을 읽을 것.**
  거기 적힌 것은 미구현이지 미완성이 아니다.
