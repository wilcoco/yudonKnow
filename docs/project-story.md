# Devpost 제출 문안 — 붙여넣기용 정본

> Devpost draft `1155717-yudonknow`. 폼 필드별로 그대로 복사한다.
> 심사가 영어권이므로 **Project Story 본문은 영문**, 아래 한국어 주석은 참고용.

---

## Elevator pitch (한 줄, 200자 이내)

```
Most AI answers your questions. This one asks you. An agent interviews a
retiring expert to dig out the judgment they can't write down, then stays
behind as their alter so juniors keep working with it.
```

---

## Project Story (Markdown — 그대로 붙여넣는다)

```markdown
## Most AI answers your questions. This one asks you.

Every AI product I had built until now waited to be asked. This one is
backwards, and the reason it is backwards is the entire project.

## Yudon is my friend

He retires in a few years. He wants to leave what he knows to the people
coming up behind him. The will is already there — that is not the problem.

I watched him try. Open a blank document and he stops at "what do I even
write." Twenty years of judgment does not come out on request. Ask him how he
knows a molding defect is a speed problem and not a temperature problem, and
he says: *"you just see it."*

He is not withholding anything. **He does not know what he knows until someone
asks him the right question.** That is not a motivation problem and not a
writing problem — it is an *interviewing* problem, and interviewing is a skill
that has a literature behind it. Extracting tacit knowledge has always required
a human knowledge engineer sitting across the table. There are not enough of
them, they are expensive, and they do not scale to every retiring expert in
every plant.

So the agent takes that seat. The human is the source; the agent is the
interviewer. That inversion decides everything downstream — what a card holds,
what the alter may say, and when it has to refuse.

That sentence is the entire problem with institutional knowledge loss. On
LinkedIn it gets discussed as brain drain, and the proposed fix is always the
same — write a handover document, fill the wiki, build a RAG chatbot over
company files. All three fail in the same place. What is written down is the
**procedure**. What walks out the door is the **exceptions and the reasons**.

So I did not build a place to upload documents. I built a set of tools to dig
with, and a way for what he digs out to stay behind as something that still
works.

**yudonKnow** — what Yudon knows, and what you don't.

## The gap that makes this worth building

APQC surveyed 1,000 organizations for *Navigating the Great Retirement with KM
& AI*. Two numbers from it sit next to each other:

- **92%** do not consistently capture knowledge from soon-to-be retirees.
- **58%** of C-suite respondents are *very worried* about exactly that loss.

They know. They still don't do it. Two more numbers say why: **85%** have not
operationalised AI for knowledge management, and **41%** rarely or never even
attempt to collect know-how from people who are leaving. Meanwhile the share of
US manufacturing workers over 55 has gone from roughly 10% to roughly 25% since
1995.

That gap between knowing and doing is the whole thesis. It is not a motivation
problem. It is a tooling problem.

## Standing on cognitive task analysis, and where I step off it

Eliciting tacit knowledge is a solved research problem. The **Critical Decision
Method** (Klein, Calderwood & MacGregor, 1989) and **ACTA** (Militello &
Hutton, 1998) have been doing this in firefighting, aviation, military and
medicine for three decades. My five-rung elicitation ladder is CDM's structure
— recall a specific non-routine incident, probe the cues, run the
counterfactual, find the boundary, mine the failure. I did not invent that and
I don't claim to.

What stopped CDM from reaching Yudon is not the method. It is that a CDM
interview takes a trained knowledge engineer two to four hours, and the
analysis takes several times longer again. That price is affordable if you are
a nuclear plant or an air force. It is not affordable for a mould shop with one
retiring expert. The knowledge-acquisition bottleneck that killed the expert
systems era was never a methodology failure — it was a unit-cost failure.

**An LLM removes that constraint.** That is the actual reason this is buildable
now, and it is an economic change, not a methodological one.

Three places where I deliberately step off the lineage:

1. **The analyst is gone.** CDM assumes a trained interviewer. Here the expert
   drives and picks their own instrument. That buys reach and costs me the bias
   correction a human analyst provided — the gap queue is my only external
   check, and it is not a complete one. That trade is written down in
   `docs/design.md` §8, not hidden.
2. **CTA stops at extraction.** It produces a report, a cognitive demands
   table, a training curriculum. Nobody designs the path by which a junior
   pulls that back out mid-shift. Here the output is a working alter, and the
   wheel closes: cited → applied → reported → gap → dug again.
3. **Verification comes from the field, not from authority.** CTA validates by
   expert review. The ✔ badge here comes only from a junior reporting what
   actually happened when they used the card.

The last one matters most to me. The literature treats Collins' *somatic* tacit
knowledge as a concept; I count it as an operating metric. The 🔴 share — what
did **not** go into words — is reported next to coverage, always, and coverage
is capped at 0.95 so the system can never claim it got everything.

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

This one nearly bit me. When I seeded an English demo dataset, the alter
answered *"how do I calibrate the new UV bank"* with a confident, completely
unrelated card. Two causes: I had Korean stopwords but no English ones, so
"how / do / the" matched card text; and my partial-match rule for Korean
compound nouns fired on Latin script, where `"rate"` is a substring of
`"calibrate"` and `"the"` of `"then"`. For a product whose entire premise is
that the junior *cannot evaluate the answer*, a confident wrong answer is not a
bug — it is the failure mode that kills the product. Partial matching is now
Korean-only, and `test_unrelated_english_question_is_always_a_gap` keeps it
that way.

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

**The "digital me" market clones people who already produced content.** The
dominant pattern (Delphi, Coachvox, Personal AI) ingests a person's existing
output — blog posts, podcasts, videos — into an embedding corpus and runs RAG
with a persona prompt. That works for thought leaders. It cannot even start
for a plant-floor expert: Yudon has twenty years of judgment and zero hours of
content. The interview-recording family (StoryFile, HereAfter) does capture by
asking, but stores raw clips — no judgment structure, no per-unit
verification, no gap that routes back to the expert. And Delphi's "strictness"
setting does tell the clone to stay on-topic — as a prompt-level instruction.
Ours refuses in code: below the retrieval-confidence floor the LLM is never
called, every generated paragraph must survive a mechanical citation check,
and each card carries its own field-verification lifecycle. They ingest what
was left behind. We interview into existence what was never written down.

**Most "tribal knowledge AI" products mine documents, which is the opposite
problem.** The tools I looked at ingest work orders, technician notes and
failure histories to generate SOPs. That extracts from what was already
written down — and what was already written down is precisely not the tacit
part. You cannot mine your way to the thing nobody recorded. You have to ask a
person, and you have to ask well.

**Naming a specific successor unlocks more than addressing "the org."** Write
"for the organization" and you get platitudes. Write "for Kim, three months
from now" and you get the truth.

**The literature already knew things I was about to get wrong.** I had built
the interview on the Critical Decision Method's classic opener — *"the hardest
call you ever made."* It is superb for depth and too narrow as a door: the
knowledge an expert uses quietly every day is never recalled as *hard*. ACTA's
Knowledge Audit (Militello & Hutton, 1998) opens eight doors instead of one,
and one of them — *"have the instruments ever said one thing while your
judgment said another?"* — is **literally Yudon's first card**: the mold
thermometer reads normal, and that is exactly where everyone gets fooled. I had
captured that card by luck. Now the tool asks for it on purpose.

**And one finding told me a design decision was right for a reason I hadn't
known.** Nisbett & Wilson (1977) showed people have no introspective access to
their own decision processes; Ericsson & Simon (1984) concluded that
after-the-fact explanation is not usable data. My schema already made `cues`
("what did you see") the hard gate for citation while letting `rationale`
("why does it work") stay empty. I had done that on instinct, to keep juniors
from getting rules they could not apply. The literature says the same thing
from the other side: observation reports are comparatively reliable,
self-explanation is where confabulation lives. The gate is in the right place.

The honest counterpart: this tool is recall-based, so it does not meet the
Ericsson & Simon bar for concurrent verbalisation. Recall bias is reduced, not
solved. The protocol document says so, and the coverage number refuses to
reach 1.0 for the same reason.

## What would make this professional, not just kind

Goodwill gets the first cards. It does not survive contact with an org chart.
For a company to run this **professionally**, the retiree should be paid in
proportion to how much their alter actually gets used — a small usage royalty
tied to citations and "it helped" reports, and paid gap-filling sessions after
departure (which also answers who fills the queue once the expert is gone).

The ledger was built for gratitude, but it turns out to be audit-grade for
settlement — precisely because it refuses vanity metrics. It counts only
citations and explicit field reports, so the same numbers that give the expert
their pride can, under an HR policy, give them their fee. The boundary that
matters: settle on **field-verified use**, never on card count — pay per card
and you get thin cards. That policy lives in HR, not in code; what the product
contributes is a ledger clean enough to settle on.

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
gemini · gemini-enterprise-agent-platform · google-ai-studio · vertex-ai · google-adk · google-genai-sdk
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
7. 아키텍처 다이어그램 — `docs/architecture.png` (2400×1600, 3:2 그대로 업로드)
8. Cloud Run 콘솔 (배포 증빙)

## 카테고리

**Collaborative Partner** (근거는 `docs/hackathon.md`)
