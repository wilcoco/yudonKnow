## Inspiration

**Most AI answers your questions. This one asks you.** Every AI product I had built until now waited to be asked. This one is backwards, and the reason it is backwards is the entire project.

Yudon is a close friend of mine, a few years from retirement. He wants to leave what he knows to the people coming up behind him — the will is already there. I watched him try: open a blank document and he stops at "what do I even write." Twenty years of judgment does not come out on request. Ask him how he knows a defect is a speed problem and not a temperature problem, and he says: *"you just see it."*

I also run a manufacturing company, and when Yudon asked, I was in the middle of hands-on automation projects on my own lines. That is exactly where the realisation landed: **automation takes the procedures — the judgment walks out the door.** My injection, painting, and assembly lines are run by people with forty-plus years in their hands, all within sight of retirement. This tool is being built for them, in the most literal sense of the hackathon's Bring-Your-Own-Friction mandate.

He is not withholding anything. **He does not know what he knows until someone asks him the right question.** That is not a motivation problem and not a writing problem — it is an *interviewing* problem. Extracting tacit knowledge has always required a human knowledge engineer sitting across the table. There are not enough of them, they are expensive, and they do not scale to every retiring expert in every plant. So the agent takes that seat. The human is the source; the agent is the interviewer.

The numbers say this gap is universal. APQC's survey of 1,000 organizations (*Navigating the Great Retirement with KM & AI*): **92%** do not consistently capture knowledge from soon-to-be retirees, while **58%** of C-suite respondents are *very worried* about exactly that loss. They know. They still don't do it — because **85%** have not operationalised AI for knowledge management. It is not a motivation problem. It is a tooling problem.

**yudonKnow** — what Yudon knows, and what you don't.

## What it does

**1. It hands the expert a toolbox, not a text editor.** Twelve self-excavation instruments; the expert picks, the agent only recommends. The most effective is the *Wrong-Answer Grader*: the agent proposes a plausible but wrong judgment and the expert grabs a red pen — people cannot explain their own expertise, but they catch someone else's error in three seconds. Others: *Contrast Pairs*, the *Sensory Ladder* (splitting "I just feel it" into eye / ear / hand / smell / timing), *Moment Capture* (30 seconds, three lines, right after a decision).

**2. Everything becomes a judgment card, not a document.** One situation-judgment per card: situation, **cues**, judgment, action, rationale, **exceptions**, and the war story of when it went wrong. Cues and exceptions are the two fields that never make it into a procedure manual — and a card with an empty `cues` field is **never citable**, enforced in code, not by convention. Corrections are never knowledge: "there was no smell — do not record one" is classified as a meta-correction and can never become a cue (a deterministic filter at compile time, hardened by external QA).

**3. What cannot be said is recorded as unsayable.** When the expert says "you just feel it" and the sensory ladder fails, that goes into an `unspeakable` field and the card is flagged 🔴 — routed to in-person apprenticeship instead of being faked into prose. The 🔴 share is reported next to coverage, always, and coverage is capped at 0.95 so the system can never claim it got everything.

**4. The alter stays behind and keeps working with the juniors.** Juniors ask the way they'd ask the person at the next desk. The alter answers **only from the cards**, opens the source card beside every answer, leads with a deterministic "Do now" top-3 taken from the cited card's action steps, and never impersonates — the label is always "Yudon's alter," never Yudon.

**5. When it doesn't know, it says so — and that decision is not the model's.** Confidence is computed in plain Python from retrieval scores. Below the floor, the LLM is **never called at all** and the question becomes a gap. A test named `test_gap_decision_never_calls_the_llm` enforces the structure. Hostile input — prompt injection, data-exfiltration requests — is quarantined by a deterministic classifier: refused *and* kept out of the expert's queue, so an attack can never masquerade as a junior's question.

**6. Approved rules run deterministically — the compiler's execution layer.** The AI pre-drafts decision rules from the card (all-of / none-of / priority, canonical signal IDs so the same sign is asked exactly once) — and nothing runs until the expert reviews and saves. Juniors then walk a structured triage, one question at a time: yes/no/unknown per sign, evaluated by a pure Python engine that stops early the moment an urgent judgment is established. One urgent sign escalates; a reassuring verdict needs its whole gate confirmed; unknowns never downgrade; on conflict the urgent judgment executes and the milder one is explicitly held. A card whose exceptions the questionnaire cannot ask about is excluded from triage entirely — an un-askable exception is a misdiagnosis waiting to happen. Same answers, same verdict, every time — the LLM discovers protocols, it never executes them.

**7. The gap goes back to the expert, and that closes the loop.** Unanswered questions queue on the expert's home screen, ranked by how many juniors asked and how soon the expert leaves. The next excavation topic is set by real demand, not by a consultant. When a junior reports back that the advice worked, that lands in the expert's Legacy Ledger — and the ledger is audit-grade: the owner's own asks and self-reports are excluded from settlement by construction, duplicates are merged, and only citations and explicit field reports are ever counted. No vanity metrics, so the same numbers that give the expert their pride can, under an HR policy, pay their royalty.

## How we built it

Python, FastAPI, SQLAlchemy, server-rendered Jinja — deployed on Google Cloud Run + Cloud SQL, with Gemini 3.5 (Google GenAI SDK on Vertex AI) doing the interviewing and the alter's voice.

The architecture rule set on day one: **the model joins only at the output layer — text in, text out.** The `BaseLLM` seam has exactly two methods, `answer` and `extract`. No judgment is delegated to the model: gap detection, citability gates, verification badges, verdict evaluation, and coverage are all decided by code and by people. That rule got tested for real when the base model moved from Anthropic to Gemini: **one file changed** (`app/capture/llm.py`), every test passed, and the Anthropic adapter stays in the tree as a live fallback — swappability is only proven while the alternative still compiles. `app/core/` has zero dependencies — no framework, no ORM, no SDK — and `test_isolation.py` fails the build if anyone imports one into it.

The interview method is not invented here, and we say so. The elicitation ladder is the **Critical Decision Method** (Klein et al., 1989) and **ACTA** (Militello & Hutton, 1998) — three decades of cognitive task analysis in firefighting, aviation and medicine. What stopped CDM from reaching Yudon was never the method; it was that a CDM interview takes a trained knowledge engineer two to four hours plus analysis. That price fits a nuclear plant, not a mould shop. **An LLM removes the unit-cost constraint** — an economic change, not a methodological one. Where we deliberately step off the lineage: the analyst is gone (the expert drives), extraction is not the end (the output is a working alter and a closed loop), and verification comes from the field, not from authority — the ✔ badge exists only when a junior reports what actually happened.

### The OpenAI Build Week winner is the first half of our wheel

veTriage — 1st place, Work & Productivity at OpenAI Build Week — is a deterministic phone-triage protocol that a 61-year-old veterinarian talked out of herself over one week of ChatGPT conversations, then froze into linked screens. That is manual elicitation: one motivated expert, one week, one workflow. yudonKnow productizes exactly that act: the agent runs the knowledge engineer's interview, the cards compile into the same kind of branching protocol, and then go where a frozen protocol can't — a dead end routes to the alter, an unanswered question routes back to the expert's dig queue, and a "didn't hold" report demotes the card until the expert fixes it. Said with respect: that winner is a brilliant artifact. **yudonKnow is the platform that produces such artifacts, from conversation alone,** for every retiring expert who will never spend a week building one.

We tested the claim head-on (`docs/vetriage-experiment.md`): playing a veterinarian armed with veTriage's own clinical rules, we let yudonKnow interview us — 13 turns, two pathways (blocked male cat, GDV). The interview extracted the same front-desk triage structure plus assets the hand-built app doesn't carry: the failure story behind the rule and the trap vocabulary ("constipated is the word that fools everyone"). Ten synthetic cases: 0 missed emergencies, 7/8 exact classification agreement (1 safe-side refusal), and on the two pathways we deliberately did not dig, the alter invented nothing. One conversation, two assets: an executable protocol for the organization, a memoir chapter for the person.

## Challenges we ran into

**A confident wrong answer is the failure mode that kills the product.** When I seeded an English demo dataset, the alter answered *"how do I calibrate the new UV bank"* with a confident, unrelated card: Korean stopwords but no English ones, and a partial-match rule for Korean compound nouns firing on Latin script (`"rate"` inside `"calibrate"`). For a product whose premise is that the junior *cannot evaluate the answer*, that is not a bug — it is death. Partial matching is now Korean-only and a regression test keeps it that way.

**The expert's own corrections tried to become knowledge.** In external judge-QA, "There was no sound or smell — do not record one" survived into a card's cue list and surfaced as a checkbox in the protocol. The fix is layered and deterministic: meta-corrections and statements of absence are classified and blocked at capture, at merge, and at approval-save; a sensory denial pivots the interview to relational/distributional/timing cues instead of re-asking the channel question.

**Reward integrity broke the moment money was imaginable.** A tester showed the card owner could ask their own alter and click "it helped" — inflating their own settlement basis. Now self-use answers normally but is excluded from citations and the ledger at write time *and* read time, self-reports are rejected outright, and duplicate reports don't double-count.

**Latency was a thinking budget, not a quota.** Judges saw 20–26s question turns and assumed we needed a better pricing tier. The logs showed zero 429s — schema-extraction calls were burning 16–19s of model *thinking*. Turning thinking off for extraction (keeping it only where output feeds the decision engine) cut turns to 1–4s. Money would not have fixed it.

**Korean text matching without a morphological analyzer**, **"unknown" as a first-class state** (every retrieval path must return nothing without the LLM ever being constructed), **coverage that refuses to reach 100%** (an early version hit 1.0 and it read as a lie), and **not letting the toolbox become a menu** (all twelve instruments visible from day one; overload is held back by recommending three, not by hiding).

## Accomplishments that we're proud of

- **The wheel actually closes**, and a test proves it: a judgment the expert approved is cited in a junior's answer, the junior's report lands on the expert's ledger, and an unanswered question becomes the next interview.
- **Seventeen external QA rounds in five days** (a ChatGPT-based adversarial tester playing retiree, junior, HR/legal, security, AI-tech, UX, enterprise buyer, and hackathon judge) took the build from a 72-point "idea demo" through two No-Go verdicts to **94/100**, every fix landing as a regression test first — **120 automated checks** now hold the line.
- **Adversarial receipts, reproducible live**: prompt injection gets a refusal and never reaches the expert's queue; an all-"no" questionnaire yields no fabricated verdict; the dashboard and the usage statement cross-verify.
- **The veTriage reproduction experiment** above — same protocol structure from interview alone, zero missed emergencies, zero fabrication on undug pathways.
- **A privacy model the expert actually controls**: private / named-person / sealed-until-date per card, alter kill-switch, and access denials that say exactly why without leaking what.

## What we learned

**Willingness is not the bottleneck; instruments are.** Yudon wanted to do this from the first conversation. The hard part is that wanting to explain and being able to explain are different problems, and almost every knowledge-management product solves the wrong one.

**Control has to come before capability.** The first screen should not be a feature tour; it should be the rights: seal this until the day I choose, keep this private, send this to one specific junior, export everything, switch my alter off. People do not dig deep into knowledge they don't own.

**Saying "I don't know" well is a feature, not a failure mode.** The moment the alter fabricates, a junior who cannot evaluate the answer loses all reason to trust it.

**The "digital me" market clones people who already produced content.** Delphi, Coachvox, Personal AI ingest existing output — blogs, podcasts — into RAG with a persona prompt. That cannot even start for a plant-floor expert: Yudon has twenty years of judgment and zero hours of content. And where their guardrails are prompt-level instructions, ours refuse in code. They ingest what was left behind. We interview into existence what was never written down.

**The literature already knew things I was about to get wrong.** I had built the interview on CDM's classic opener — "the hardest call you ever made." It is superb for depth and too narrow as a door. ACTA's Knowledge Audit opens eight doors, and one of them — *"have the instruments ever said one thing while your judgment said another?"* — is literally Yudon's first card: the mold thermometer reads normal, and that is exactly where everyone gets fooled. And Nisbett & Wilson (1977) validated a gate I had set on instinct: observation reports (`cues`) are comparatively reliable, self-explanation (`rationale`) is where confabulation lives — so `cues` is the hard gate for citation and `rationale` may stay empty. The honest counterpart: this tool is recall-based, so recall bias is reduced, not solved. The coverage number refuses to reach 1.0 for the same reason.

## What's next

**Paying retirees professionally, not just kindly.** The ledger was built for gratitude, but it refuses vanity metrics, so it is audit-grade for settlement: citations and explicit field reports only, self-dealing excluded by construction. Next is the weighting policy (citation < "it helped" < field-verified ✔ < prevented-loss, repeat use across juniors compounding) and recording the reporter-owner relationship. One thing we would argue in any company: inside a firm's culture and long-term relationships, the fraud pressure that would plague a public marketplace largely disappears — the counterparties know each other, reputations persist, and HR sits on the loop. The policy lives in HR; the product's job is a ledger clean enough to settle on.

Also: corporate SSO. The demo deliberately ships an identity switcher instead of a login: this product has two roles, and one judge, alone, must be able to walk the full wheel in minutes — ask as a junior, receive the question as the senior, answer it into a card, watch the alter cite it back. An account wall would cut that wheel in half, and the synthetic demo data gives authentication nothing to protect. The production design is already fixed: Entra ID OIDC with the immutable `oid` claim as the actor id — permission checks are centralised in two functions, so the swap is a days-scale integration that also upgrades the compensation ledger to authenticated identities. Then: voice-first excavation, the apprenticeship export for 🔴 cards, negative-evidence fields ("it is *not* the smell" narrows a junior's search), memoir chapters by era and turning points once cards accumulate, and two experts' alters that disagree — which the current version deliberately does not adjudicate; it shows both.

## Pre-existing work disclosure

This project was created during the Submission Period (first commit: 2026-08-27). Per the "New Projects Only" rule, we disclose pre-existing work incorporated into it — all authored by the same author, documented in `docs/reuse-map.md`:

- **github.com/wilcoco/alter-ai** — configuration skeleton, the "runs without an API key" stub-fallback convention, the two-method `BaseLLM` seam, SQLAlchemy schema style, deployment skeleton.
- **github.com/wilcoco/CAMS-KnowledgeNet** — external-reality anchor model (baseline / observed / direction), dormant/revive state machine, exploration quota.
- **github.com/wilcoco/H2A2H2** — the P→I→C graph vocabulary (`Card.to_pic()`).

Everything else — the judgment-card domain model, the elicitation ladder, the 12 instruments, the gap queue, the deterministic verdict engine, the Gemini integration (Gemini 3.5 via the Google GenAI SDK on Vertex AI), and the Google Cloud deployment (Cloud Run, Cloud SQL, Secret Manager, Cloud Build) — was built during the Submission Period. 