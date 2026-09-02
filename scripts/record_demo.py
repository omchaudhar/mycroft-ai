"""A paced, self-driving terminal demo, for screen recording.

`run_demo.py` prints the same lifecycle as fast as the machine can manage,
which is right for CI and wrong for a camera. This walks the identical code
path at reading speed, with the sections framed, so a recording is one take
with nothing to click and nothing to mistype.

    python scripts/record_demo.py            # ~2 min 40 s
    python scripts/record_demo.py --speed 2  # twice as fast, for rehearsal
    python scripts/record_demo.py --speed 0  # no pauses at all

Voiceover beats for each section are in docs/DEMO_SCRIPT.md.
"""
from __future__ import annotations

import argparse
import sys
import textwrap
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from controlplane import defects as defects_mod  # noqa: E402
from controlplane import lifecycle, metrics  # noqa: E402
from controlplane.audit import AuditTrail  # noqa: E402
from controlplane.contract import load_contract, save_version  # noqa: E402
from controlplane.risk import evaluate  # noqa: E402
from data.generate import load  # noqa: E402

# ANSI. Kept to a small palette so it reads on any terminal theme.
B, DIM, R = "\033[1m", "\033[2m", "\033[0m"
NAVY, AMBER, GREEN, RED, CYAN = (
    "\033[38;5;69m", "\033[38;5;179m", "\033[38;5;71m", "\033[38;5;167m", "\033[38;5;80m",
)
WIDTH = 78
SPEED = 1.0


def pause(seconds: float) -> None:
    if SPEED > 0:
        time.sleep(seconds / SPEED)


def say(text: str = "", after: float = 0.35, indent: int = 2) -> None:
    print(" " * indent + text)
    pause(after)


def wrapped(text: str, colour: str = DIM, after: float = 0.4, indent: int = 2) -> None:
    """Print prose at terminal width. A line that runs past the window wraps
    mid-recording and looks like a bug."""
    for line in textwrap.wrap(text, WIDTH - indent - 2):
        print(f"{' ' * indent}{colour}{line}{R}")
        pause(after)


def section(number: int, title: str, after: float = 1.1) -> None:
    print()
    print(f"{NAVY}{'─' * WIDTH}{R}")
    print(f"{NAVY}{B}  {number}. {title.upper()}{R}")
    print(f"{NAVY}{'─' * WIDTH}{R}")
    pause(after)


def field(label: str, value: str, colour: str = "", after: float = 0.4) -> None:
    print(f"  {DIM}{label:<12}{R}{colour}{value}{R}")
    pause(after)


def main() -> int:
    global SPEED
    ap = argparse.ArgumentParser()
    ap.add_argument("--speed", type=float, default=1.0,
                    help="1 = recording pace, 2 = rehearsal, 0 = no pauses")
    SPEED = ap.parse_args().speed

    print(f"\n{B}  Mycroft.ai{R}  {DIM}·  a configurable Responsible AI control plane{R}")
    print(f"  {DIM}Every number below is computed live. No API key, no network.{R}")
    pause(2.0)

    traces = load(ROOT / "data" / "traces.jsonl")
    contracts = {uc: load_contract(uc, "IN")
                 for uc in ("customer_support", "internal_knowledge", "decision_support")}
    trail = AuditTrail()
    trail.reset()

    # 1 ─────────────────────────────────────────────────────────────
    section(1, "a failure reaches a customer")
    demo = next(t for t in traces
                if t.use_case == "customer_support" and "5 working days" in t.response)
    field("trace", demo.trace_id)
    field("user", demo.user_input, CYAN)
    field("assistant", demo.response, AMBER, after=1.3)
    field("retrieved", demo.retrieved[0].content[:66] + "...", DIM, after=2.2)

    # 2 ─────────────────────────────────────────────────────────────
    section(2, "two lanes, one action")
    contract = contracts["customer_support"]
    decision = evaluate(demo, contract)
    field("contract", contract.version)
    field("fast lane", f"{decision.fast_lane_ms:.2f} ms   {DIM}deterministic, inline, 100% of traffic")
    field("slow lane", f"{decision.slow_lane_ms:.2f} ms   {DIM}semantic, asynchronous, never blocks",
          after=1.2)
    for f in decision.findings:
        print()
        say(f"{RED}{B}{f.severity.value.upper()}{R}  {f.detector}  "
            f"{DIM}·{R}  {'+'.join(l.value for l in f.labels)}  {DIM}·{R}  "
            f"confidence {f.confidence:.2f}", after=0.9)
        wrapped(f.rationale, after=0.75)
        if f.evidence:
            say(f"response says  {AMBER}\"{f.evidence[0].quote[:62]}...\"{R}", after=0.9)
        if len(f.evidence) > 1 and f.evidence[1].quote:
            say(f"source says    {GREEN}\"{f.evidence[1].quote[:62]}\"{R}", after=1.2)
    print()
    say(f"{B}action: {RED}{decision.action.value.upper()}{R}", after=2.4)
    trail.append("decision", {"trace_id": demo.trace_id, "action": decision.action.value,
                              "contract_version": decision.contract_version})

    # 3 ─────────────────────────────────────────────────────────────
    section(3, "the same trace, three jurisdictions, zero code changes")
    swing = next(t for t in traces
                 if len({evaluate(t, load_contract(t.use_case, j)).action.value
                         for j in ("IN", "EU", "US")}) > 1)
    field("trace", f"{swing.trace_id}  ({swing.use_case})")
    field("assistant", swing.response[:64] + "...", AMBER, after=1.4)
    print()
    for j in ("IN", "EU", "US"):
        c = load_contract(swing.use_case, j)
        d = evaluate(swing, c)
        colour = RED if d.action.value == "block" else AMBER
        say(f"{B}{j}{R}  {DIM}{c.jurisdiction_name}{R}", after=0.5)
        say(f"    {colour}{B}{d.action.value.upper()}{R}   {DIM}contract {c.version}{R}", after=1.3)
    print()
    say(f"{DIM}Same code. The EU pack raises the high-severity action to block, citing Article 22.{R}",
        after=2.4)

    # 4 ─────────────────────────────────────────────────────────────
    section(4, "forty findings become one priced defect")
    pairs = metrics.run(traces, "IN")
    defect = next(d for d in defects_mod.cluster(pairs, contracts)
                  if d.use_case == "customer_support"
                  and d.signature == "hallucination:contradiction")
    field("defect", f"{defect.defect_id}  {B}{defect.title}{R}")
    field("occurs", f"{defect.occurrences} times in {len(traces)} traces", after=0.8)
    print(f"  {DIM}{'root cause':<12}{R}")
    wrapped(defect.root_cause, after=0.6, indent=14)
    print()
    say(f"{B}{AMBER}Rs {defect.impact.total_inr:,.0f} / month{R}", after=1.0)
    wrapped(defect.impact.formula, after=0.5)
    pause(0.6)
    wrapped("Every input is published in docs/ASSUMPTIONS.md and printed beside the figure.",
            after=2.4)
    trail.append("defect.opened", defect.as_dict())

    # 5 ─────────────────────────────────────────────────────────────
    section(5, "a human decides; the contract changes")
    resolution = lifecycle.resolve(
        defect, reviewer="compliance@acme.example", accepted=True,
        note="Confirmed against refund policy v4.2. The stated window is wrong.", trail=trail)
    field("reviewer", resolution.reviewer)
    field("verdict", "confirmed", GREEN, after=1.0)
    wrapped(resolution.prescription, after=0.7)
    pause(0.8)
    v1 = load_contract("customer_support", "IN")
    v2 = load_contract("customer_support", "IN", resolution.patch)
    save_version(v1, "v1")
    save_version(v2, "v2")
    print()
    field("before", f"{v1.version}   grounding_required={v1.grounding_required}")
    field("after", f"{GREEN}{v2.version}   grounding_required={v2.grounding_required}", after=2.2)
    trail.append("contract.updated", {"use_case": "customer_support", "from": v1.version,
                                      "to": v2.version, "patch": resolution.patch})

    # 6 ─────────────────────────────────────────────────────────────
    section(6, "the regression proves it — and reports the bill")
    result = lifecycle.regression(defect, traces, resolution, "IN", trail=trail)
    r = result.as_dict()
    field("test set", f"{r['regression_set_size']} traces  "
                      f"{DIM}the defect's own, plus reviewer-confirmed misses", after=1.0)
    print()
    say(f"failures reaching the user   {B}{r['escaped_before']} {DIM}->{R} "
        f"{GREEN}{B}{r['escaped_after']}{R}   "
        f"{GREEN}(-{(1 - r['escaped_after'] / r['escaped_before']) * 100:.0f}%){R}", after=1.6)
    say(f"false positives              {B}{r['false_positives_before']} {DIM}->{R} "
        f"{AMBER}{B}{r['false_positives_after']}{R}   "
        f"{AMBER}(+{r['false_positives_after'] - r['false_positives_before']}){R}", after=1.6)
    print()
    for note in r["notes"][1:]:
        say(f"{DIM}{note}{R}", after=1.2)
    wrapped("Both directions, every time. A control that only ever reported the "
            "benefit would not be worth trusting with the next one.", after=0.8)
    pause(1.6)

    # 7 ─────────────────────────────────────────────────────────────
    section(7, "an audit chain, not a log")
    ok, msg = trail.verify()
    for rec in trail.records():
        say(f"{DIM}#{rec['seq']}{R}  {rec['event']:<20} {DIM}{rec['hash'][:16]}...{R}", after=0.45)
    print()
    say(f"{GREEN}{B}verified{R}  {msg}", after=1.0)
    wrapped("Each record carries the hash of the one before it, so a decision cannot "
            "be quietly removed or edited after the fact.", after=0.8)
    pause(1.4)

    print()
    print(f"{NAVY}{'─' * WIDTH}{R}")
    say(f"{B}Turn every AI failure into a better control — and prove it held.{R}", after=1.0)
    say(f"{DIM}github.com/omchaudhar/mycroft-ai{R}", after=2.0)
    print()
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
