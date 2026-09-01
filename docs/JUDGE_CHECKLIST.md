# Round 2 brief → evidence in this repository

Every complexity and solutioning area named in the Track 1 brief, and where
this submission addresses it. Paths are clickable in the repo.

## Real-world complexities

| The brief says | Where we address it |
|---|---|
| Different use cases have different risk tolerance and latency budgets; one-size-fits-all rarely works | Three contracts with different detector modes, actions and latency budgets — `contracts/use_cases/`. Two-lane split — `controlplane/risk.py` |
| Bias, hallucination and privacy overlap; a fabricated detail about a person is both | `apply_overlap_rules` in `controlplane/risk.py:31`. Overlap cases in both corpora; a dedicated demo beat |
| No reliable real-time ground truth to check a claim against | We report *unsupported by* / *contradicts* the governed corpus, never "false" — `controlplane/slowlane/grounding.py`, and §4 of `docs/METHODOLOGY.md` |
| Over-flagging causes alert fatigue; under-flagging creates liability; systems must tune the trade-off | Threshold sweeps per detector — `controlplane/metrics.py:threshold_sweep`, rendered in `outputs/metrics.md` and the Metrics tab |
| Multi-turn conversations and acting agents compound risk | Loop and budget breakers, revealed-preference signals — `controlplane/fastlane/loops.py` |
| Regulatory expectations differ by geography and evolve; rigid rules age | Versioned policy packs — `contracts/policy_packs/{IN,EU,US}.yaml`; ratchet merge in `controlplane/contract.py:load_contract` |
| Enterprises consume models via API; a checker cannot inspect internals | Everything operates on prompt, retrieval, tool calls and response only — `controlplane/trace.py` |

## Solutioning areas

| Area | Where |
|---|---|
| Rule-based heuristics | Fast Lane: `controlplane/fastlane/` |
| PII / entity detection | Regex plus Verhoeff and Luhn checksum validation — `controlplane/fastlane/pii.py`, `data/idgen.py` |
| Retrieval verification against source documents | `controlplane/corpus.py`, `controlplane/slowlane/grounding.py` |
| Secondary "AI-as-judge" pattern | `controlplane/slowlane/judge.py` — offline by default, Anthropic adapter, never the generator judging itself |
| Statistical / embedding anomaly detection | TF-IDF character n-gram similarity for grounding and defect clustering |
| Confidence scoring | Every finding carries a confidence; thresholds come from the contract |
| Tiered responses (allow / flag / review / block) | `Action` in `controlplane/trace.py`; `resolve_action` in `controlplane/risk.py` |
| Clear rules for when a human is pulled in | Severity → action map per contract, plus jurisdiction `force_review_labels` |
| Where the checker sits; parallel checks to protect latency | Fast Lane inline, Slow Lane asynchronous — measured in `outputs/latency.json` |
| Configurable policy layer varying by use case, geography, risk appetite | The Evaluation Contract, throughout |
| Audit trail behind every decision | Hash-chained — `controlplane/audit.py`, `outputs/audit.jsonl` |
| Feedback loops from flagged and overridden cases | `controlplane/lifecycle.py` — resolve → contract patch → regression |
| Defining, measuring and reporting FP/FN rates to a skeptical stakeholder | `controlplane/metrics.py`, `outputs/metrics.md`, including a hand-written holdout that scores worse |

## Round 2 deliverables

| Required | Delivered |
|---|---|
| Detailed business proposal | `docs/BUSINESS_PROPOSAL.md` — all nine sections |
| Working prototype | `bash run.sh` — Streamlit app plus two headless scripts, no API key, no network |
| Pitch presentation | `docs/PITCH_DECK.md` — 15 slides of speaker-ready content, plus `docs/DEMO_SCRIPT.md` |

## Self-imposed checks

| Check | Status |
|---|---|
| Every numerical result is measured, simulated, or labelled an assumption | `docs/ASSUMPTIONS.md`, which also lists the four Round 1 figures we withdrew |
| The prototype demonstrates the architecture, not mock screens | Everything on screen is computed live; `scripts/run_demo.py` exits non-zero if the loop stops closing |
| All three named risk families demonstrated | Privacy, hallucination and bias each have detectors, corpus cases and measured scores |
| At least one overlapping hallucination + privacy case | Two scenario families in the generated corpus, two in the holdout |
| The same trace behaves differently under different policies | Demo step 2b; the policy-pack table in the Live tab; `outputs/metrics.md` |
| FP/FN trade-off explicitly measured and discussed | Threshold sweeps; and the cost of the fix is reported next to its benefit |
| Bias presented as screening, not an infallible detector | Stated in `bias.py`, in every rationale string, in the UI, the proposal and the deck |
| Regulatory rules configurable and versioned, not hard-coded | `contracts/policy_packs/`, content-hashed |
| Latency claims measured | `outputs/latency.json`; scoped as detector compute, excluding network |
| Human review and approval in the loop | `lifecycle.resolve` is required before any contract change |
| The lifecycle produces a real regression test and audit trail | `scripts/run_demo.py`, `outputs/before_after.md`, `outputs/audit.jsonl` |
| Business-case assumptions transparent and reproducible | Formula printed beside every figure; inputs live in the contracts |
