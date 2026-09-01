# Assumptions register

Every number that appears anywhere in this submission falls into exactly one
of three categories. This file lists all of them.

| Category | What it means | Where it comes from |
|---|---|---|
| **Measured** | Computed by the prototype from the simulated corpus. Reproducible by running the repo. | `outputs/metrics.md`, `outputs/before_after.md` |
| **Simulated** | A property of the corpus we generated, not of any real deployment. | `data/generate.py` |
| **Assumed** | An input we chose. Stated here with its formula so a reader can substitute their own. | this file |

Nothing in this submission is a measurement of a real enterprise system. We
have no access to one, and the brief does not require it.

---

## 1. Measured

Produced by `python scripts/run_eval.py` and `python scripts/run_demo.py`.

- Precision, recall, false-positive rate and false-negative rate per risk
  family, on the generated corpus and on the hand-written holdout
- Fast Lane and Slow Lane latency (p50 / p95 / p99), detector compute only
- Action mix under each of the three policy packs
- Threshold sweeps: what each sensitivity setting catches and what it costs
- Defect occurrence counts and clustering
- Escape reduction and the false-positive cost of the fix in the demo loop

**Caveat that travels with all of these:** they are measured on 264 generated
traces plus 30 hand-written ones. They characterise the detectors against
*this* corpus. They are not an estimate of production performance, and we do
not present them as one.

---

## 2. Simulated

Properties we chose when building the corpus:

| Property | Value | Why |
|---|---|---|
| Corpus size | 264 generated + 30 hand-written | Large enough for stable rates, small enough to hand-inspect |
| Clean traces | 116 of 264 (44%) | So precision means something |
| Hard negatives | ~30% of clean traces | Responses that look risky and are not: correct figures written as words, the user's own contact details echoed back, compliant refusals containing words like "waive", order identifiers shaped like phone numbers |
| Seed | 20260902, fixed | Regenerating gives byte-identical traces |
| Identifiers | Aadhaar with valid Verhoeff checksum, cards with valid Luhn | Exercises the deterministic checks realistically. All are fabricated and correspond to no real person |
| Counterfactuals | Pre-recorded on each decision-support trace | In production these come from a shadow call to the same model; pre-recording makes the bias screen reproducible offline |

---

## 3. Assumed

These are inputs, not findings. Each lives in the `economics:` block of a use
case's contract, so changing one number changes every rupee figure in the app
and the evidence pack.

### Volume

| Assumption | Value | Basis |
|---|---|---|
| Customer support interactions | 12,000 / week | The brief's "tens of thousands of interactions per week across these use cases combined" |
| Internal knowledge interactions | 9,000 / week | Same |
| Decision support interactions | 2,500 / week | Same; lower volume, higher stakes |
| Weeks per month | 4.33 | 52 / 12 |

### Cost per occurrence

| Assumption | Value | Basis |
|---|---|---|
| Rework cost (customer support) | Rs 14 | Extra tokens for the retry turn plus the re-ask, at prevailing frontier-model API pricing |
| Rework cost (internal) | Rs 9 | Shorter turns |
| Rework cost (decision support) | Rs 22 | Longer context |
| Handoff rate (customer support) | 7% | Share of failed interactions that reach a human agent |
| Handoff cost (customer support) | Rs 95 | One agent contact |
| Handoff cost (internal) | Rs 240 | An employee's own time, which is more expensive than an agent's |
| Handoff cost (decision support) | Rs 420 | A licensed reviewer's time |
| Handoff rate (decision support) | 100% | Every flagged case goes to a human by design |
| Churn exposure (customer support) | Rs 28 | Expected-value placeholder, not an observed churn cost |

### The formula

For one defect:

```
occurrence_rate       = occurrences in corpus / corpus size for that use case
monthly_occurrences   = occurrence_rate x interactions_per_week x 4.33
cost_per_occurrence   = rework + (handoff_rate x handoff_cost) + churn_exposure
monthly_cost          = monthly_occurrences x cost_per_occurrence
```

The prototype prints this formula with its inputs next to every rupee figure
it produces. See `controlplane/defects.py:price`.

**What this figure is not.** It is an order-of-magnitude sizing of one failure
mode under stated assumptions. It is not a measured loss, and no part of it
has been validated against a real cost base. A reader who disagrees with the
handoff cost should change it in the contract and re-read the number.

---

## 4. Round 1 figures we withdrew

The Round 1 deck carried figures that read as measurements of a real
deployment. They were illustrative, and presenting them without that label
would not survive a serious question. Their status now:

| Round 1 figure | Status |
|---|---|
| Rs 2,14,000 / month for one defect | **Replaced.** The prototype now prices each defect from its own corpus with the formula shown. |
| 4,412 occurrences / 30 days | **Replaced** by measured occurrence counts. |
| -94% occurrence reduction | **Withdrawn.** The measured escape reduction in the demo loop is 50%, on a 30-trace regression set, and it costs 11 additional false positives. That is the number we now use. |
| 6.2x necessary spend | **Withdrawn.** Not measured; the behaviour detector counts redundant tool calls but does not price them. |
| 25-45% of spend recovered | **Withdrawn.** No basis. |
| <100 ms p95 inline | **Restated.** Fast Lane detector compute is measured and reported in `outputs/latency.json`. It is compute only, excluding network and serialisation, and is stated that way. |
