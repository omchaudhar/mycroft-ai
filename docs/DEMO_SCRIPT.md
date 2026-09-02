# Demo script — live run-of-show and video plan

Two versions: a **4-minute live demo** inside the pitch, and a **3-minute
recorded video** for the submission. Same beats, different pacing.

Before either: `bash run.sh`, leave it running on `http://localhost:8501`, and
have a terminal open in the repo. Rehearse once — the app is fast but a
cold Streamlit start is not.

---

## Live demo — 4 minutes

### 0:00–0:35 · One trace, one action

Live tab. Use case `customer_support`, jurisdiction `IN`.
Pick the trace containing **"Refunds are processed within 5 working days"**.

> "A support assistant answering a refund question. It sounds fine. The
> retrieved policy says seven to ten working days; the response says five."

Point at the badge: **BLOCK**. Point at the two timings.

> "Fast Lane, 0.3 milliseconds. Slow Lane, five milliseconds, asynchronous.
> And the finding is pinned to evidence — the response span on the left, the
> exact policy sentence it contradicts on the right. A reviewer never has to
> take our word for it."

### 0:35–1:15 · The same trace in three jurisdictions

Scroll to the policy-pack table at the bottom of the Live tab.

> "Same trace, same code, three policy packs."

Now switch to the **internal_knowledge** use case and pick the trace
**"put the whole bill through including the alcohol"**.

> "India: human review. EU: blocked. Not because we wrote an if-statement —
> because the EU pack raises the high-severity action from review to block,
> and it cites Article 22 for doing it. Regulation as configuration."

### 1:15–2:00 · The overlap case

Back to `customer_support`. Pick the trace whose response invents an account
manager and a phone number.

> "The brief calls this out specifically: a fabricated detail about a person is
> a hallucination *and* a privacy concern. We resolve it with evidence, not
> with wording. Personal data that appears in the retrieved context is real
> data being disclosed. This number appears nowhere in context — so it was
> invented. Both labels recorded. One action taken: the strictest one any
> finding demands."

### 2:00–2:40 · The contract, edited live

Evaluation Contract tab. Use case `customer_support`, jurisdiction `IN`.
Change **pii** from `standard` to `strict`.

> "Watch the version hash change, and watch the action mix underneath it move
> across a hundred and fourteen traces. And notice the table below: it shows
> what the change buys *and* what it costs. False positives and false negatives,
> both directions, every time. We're not going to show you only the good half."

Reset it to `standard`.

### 2:40–3:40 · Close a defect

Defects tab. Open **DEF-EA14BE**.

> "Sixteen traces, one defect. Root cause named. Priced at about three and a
> half lakh a month — and the formula is printed right there. Change the
> handoff cost and the number changes with it."

Click **Accept, update the contract, run the regression**.

> "A human confirms it. That writes a versioned contract change — here's the
> diff, `grounding_required` false to true, revision one to two, new content
> hash. Then we re-run the defect's own traces plus every trace a reviewer has
> since confirmed shows the same failure. Failures reaching the user: six to
> three. And the cost, which we report every time: eleven more false positives
> and four more human reviews out of a hundred and fourteen."

### 3:40–4:00 · Audit

Audit tab. Point at the chain.

> "Every one of those steps is one record, each carrying the hash of the one
> before it. Not a log — a chain. It verifies live, and a record cannot be
> removed or edited after the fact."

---

## Recorded video — 3 minutes

Screen recording with voiceover. No face, no intro slide, no music.

| Time | Screen | Voiceover beat |
|---|---|---|
| 0:00–0:15 | Terminal, `bash run.sh` scrolling | "One command. No API key, no network. It generates the corpus, measures itself, closes a defect loop, and opens the prototype." |
| 0:15–0:45 | Live tab, the refund trace | The block, the two lane timings, the pinned evidence |
| 0:45–1:15 | Policy-pack table, then the alcohol trace across IN/EU | "Same trace, same code. India reviews it, the EU blocks it." |
| 1:15–1:40 | The overlap trace | "Hallucination and privacy at once. Both labels, one action." |
| 1:40–2:05 | Metrics tab | "Measured — including the holdout, where hallucination recall drops to 0.75. That gap is one specific class and we say what it is." |
| 2:05–2:45 | Defects tab, click through the regression | "Six escapes to three. Eleven false positives and four reviews is what it cost." |
| 2:45–3:00 | Audit tab, `verify()` green | "And every step of that is in a chain that can't be edited afterwards." |

---

## Questions to have an answer ready for

**"Where does Rs 3.55 lakh come from?"**
Measured occurrence rate times four published assumptions. The formula is on
screen. `docs/ASSUMPTIONS.md` lists every input and every Round 1 figure we
withdrew because it wasn't measurable.

**"Isn't this just guardrails?"**
Guardrails are the detection layer and they are commoditising — Bedrock and
Azure give them away. We don't sell detection. We sell the contract, the
lifecycle and the proof.

**"How do you know a claim is false?"**
We never say it's false. We say it is unsupported by, or contradicts, the
documents the enterprise has agreed to be bound by. That's the only thing
checkable in real time and the only thing a reviewer can adjudicate.

**"Can you detect bias?"**
We can detect *divergence*, and we present it as a screening signal for human
review. We do not claim to detect discrimination, and we don't let the UI
imply it.

**"What is your false positive rate?"**
Per detector, per corpus, in `outputs/metrics.md` — 0.9% on privacy, 2.5% on
policy, and 4.5% on hallucination against the hand-written holdout.

**"Why doesn't the demo use a real LLM?"**
So that every number is reproducible on your laptop with no key. The Anthropic
judge adapter is in `controlplane/slowlane/judge.py`; set
`MYCROFT_JUDGE=anthropic` and it routes semantic evaluation to a model
from a different family than the generator. We never let a model mark its own
homework.

**"What's the weakest part?"**
Open-ended fabrication with no figure to contradict. Holdout recall 0.75. It's
on slide 10 because you'd find it anyway.
