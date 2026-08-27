# Devpost 제출 문안 — 붙여넣기용 정본

> Devpost draft `1155717-yudonknow`. 폼 필드별로 그대로 복사한다.
> 심사가 영어권이므로 **Project Story 본문은 영문**, 아래 한국어 주석은 참고용.

---

## Elevator pitch (한 줄, 200자 이내)

```
An agent that interviews a retiring expert to dig out the judgment they can't
write down, then stays behind as their alter — so juniors keep working with it.
```

---

## Project Story (Markdown — 그대로 붙여넣는다)

```markdown
## Yudon is my friend

He retires in a few years. He wants to leave what he knows to the people
coming up behind him. The will is already there — that is not the problem.

I watched him try. Open a blank document and he stops at "what do I even
write." Twenty years of judgment does not come out on request. Ask him how he
knows a molding defect is a speed problem and not a temperature problem, and
he says: *"you just see it."*

That sentence is the entire problem with institutional knowledge loss. On
LinkedIn it gets discussed as brain drain, and the proposed fix is always the
same — write a handover document, fill the wiki, build a RAG chatbot over
company files. All three fail in the same place. What is written down is the
**procedure**. What walks out the door is the **exceptions and the reasons**.

So I did not build a place to upload documents. I built a set of tools to dig
with, and a way for what he digs out to stay behind as something that still
works.

**yudonKnow** — what Yudon knows, and what you don't.

## What it does

**1. It hands the expert a toolbox, not a text editor.**
Twelve self-excavation instruments, and the expert picks which one to use —
the agent only recommends. The most effective one is the *Wrong-Answer
Grader*: the agent proposes a plausible but wrong judgment, and the expert
grabs a red pen. People cannot explain their own expertise, but they catch
someone else's error in three seconds. Others: *Contrast Pairs* (two nearly
identical situations — what separates them? discriminating cues only surface
in comparison), the *Sensory Ladder* (splitting "I just feel it" into eye /
ear / hand / smell / timing / rhythm, ending with a forced metaphor), *Moment
Capture* (30 seconds, three lines, right after a decision).

**2. Everything becomes a judgment card, not a document.**
One situation-judgment per card: situation, **cues**, judgment, action,
rationale, **exceptions**, and the war story of when it went wrong. Cues and
exceptions are the two fields that never make it into a procedure manual, and
without them a junior cannot use the knowledge at all. A card with an empty
`cues` field is **never citable** — enforced in code, not by convention.

**3. What cannot be said is recorded as unsayable.**
The tacit-knowledge bottleneck is real and this project does not solve it.
When the expert says "you just feel it" and the sensory ladder fails, that
goes into an `unspeakable` field and the card is flagged 🔴 — routed to
in-person apprenticeship instead of being faked into prose. The percentage of
🔴 cards is reported next to coverage, always. Coverage is also capped at
0.95 so the system can never claim it got everything.

**4. The alter stays behind and keeps working with the juniors.**
Juniors don't search. They ask the way they'd ask the person at the next desk.
The alter answers **only from the cards**, always shows the source card beside
the answer, and never impersonates — the label on screen is always
"Yudon's alter," never Yudon.

**5. When it doesn't know, it says so — and that decision is not the model's.**
Confidence is computed in plain Python from retrieval scores. Below the floor,
the LLM is **never called at all** and the question becomes a gap. Asking a
model to "say you don't know if you don't know" is a design that fails. A test
named `test_gap_decision_never_calls_the_llm` enforces the structure.

**6. The gap goes back to the expert, and that closes the loop.**
Unanswered questions queue up on the expert's home screen, ranked by how many
juniors asked and how soon the expert leaves. **The next excavation topic is
set by real demand, not by a consultant.** And when a junior reports back that
the advice worked, that lands in the expert's Legacy Ledger — because these
tools don't die from bad technology, they die when the expert quits on the
third session. Something has to come back.

## How I built it

Python, FastAPI, SQLAlchemy, server-rendered Jinja — deployed on Google Cloud
Run, with Gemini doing the interviewing and the alter's voice.

The architecture rule I set on day one: **the model joins only at the output
layer — text in, text out.** The `BaseLLM` seam has exactly two methods,
`answer` and `extract`. No judgment is delegated to the model: gap detection,
citability gates, verification badges, and coverage are all decided by code
and by people.

That rule got tested for real when I moved the base model from Anthropic to
Gemini. **One file changed** — `app/capture/llm.py`. The elicitation ladder,
the alter, and every scoring rule in `app/core/` were untouched, and all 34
tests passed. I deliberately kept the Anthropic adapter in the tree as a
fallback provider, because swappability is only proven while the alternative
still compiles.

`app/core/` has zero dependencies — no framework, no ORM, no SDK — and a test
(`test_isolation.py`) fails the build if anyone imports one into it.

## What I learned

**Willingness is not the bottleneck; instruments are.** I started out thinking
the hard part was motivating experts. It isn't. Yudon wanted to do this from
the first conversation. The hard part is that wanting to explain and being
able to explain are different problems, and almost every knowledge-management
product solves the wrong one.

**Control has to come before capability.** Early on I put the feature tour on
the first screen. It should be the rights: seal this until the day I choose,
keep this private, send this to one specific junior, export everything, and
switch my own alter off without asking anyone. People do not dig deep into
knowledge they don't own — and the deepest judgment is exactly what's at
stake.

**Saying "I don't know" well is a feature, not a failure mode.** The moment
the alter fabricates, a junior who cannot evaluate the answer loses all reason
to trust it, and the product is dead.

**Naming a specific successor unlocks more than addressing "the org."** Write
"for the organization" and you get platitudes. Write "for Kim, three months
from now" and you get the truth.

## Challenges

**Korean text matching without a morphological analyzer.** Korean particles
mean `플로우마크가` and `플로우마크` are different tokens. Shipping a JVM-based
analyzer to Cloud Run for a few hundred cards was the wrong trade, so the
retriever strips a small particle set, does partial matching for compound
nouns, and discounts the denominator to forgive predicate noise. One rule,
predictable when wrong.

**Making "unknown" a first-class state.** Every retrieval path had to be able
to return nothing without the LLM ever being constructed. That constraint
shaped the whole module boundary.

**Coverage that refuses to reach 100%.** An early version hit 1.0 and it read
as a lie — the fingertip knowledge was still in his hands. The ceiling is now
0.95 and a test enforces it.

**Not letting the toolbox become a menu.** Twelve instruments is overwhelming.
Only two unlock at the start; the rest open once cards accumulate.

## What's next

Voice-first excavation (experts talk far better than they type), the
apprenticeship export for the 🔴 cards, and handling the case where two
experts' alters disagree — which the current version deliberately does not
adjudicate, it just shows both.

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

---

## Built with (태그 — 최대 25개)

```
gemini · google-ai-studio · vertex-ai · google-adk · google-genai-sdk
google-cloud · cloud-run · cloud-sql · secret-manager · artifact-registry
python · fastapi · sqlalchemy · pydantic · uvicorn · jinja2 · postgresql
sqlite · docker · html · css · javascript · pytest
```

## Try it out links

| 라벨 | 값 |
|---|---|
| Live demo (Cloud Run) | `https://…run.app` ← **배포 후 채운다** |
| Source code | `https://github.com/wilcoco/yudonKnow` |
| Design summary | (설계 요약 페이지 URL) |

## 이미지 갤러리 (3:2, 최대 15장)

1. 전문가 홈 — 보람 블록 + 공백 큐 + 도구함
2. 발굴 3단 화면 — 왼쪽 질문 / 가운데 답 / 오른쪽 카드가 채워지는 중
3. ⚖️ 오답 채점기 화면
4. 후배 화면 — 답 + 근거 카드(예외·실패담 펼쳐진 상태)
5. **분신이 "모른다"고 말하는 화면** ← 이게 제일 중요하다
6. 관리자 승계 리스크 보드
7. 아키텍처 다이어그램
8. Cloud Run 콘솔 (배포 증빙)

## 카테고리

**Collaborative Partner** (근거는 `docs/hackathon.md`)
