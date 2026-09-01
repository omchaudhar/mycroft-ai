"""The defect lifecycle, end to end, headless.

Seven steps: inject, detect, cluster and price, human resolution, contract
change, regression, audit. Exits non-zero if the regression does not improve,
so the loop cannot silently stop closing.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from controlplane import defects as defects_mod  # noqa: E402
from controlplane import lifecycle, metrics  # noqa: E402
from controlplane.audit import AuditTrail  # noqa: E402
from controlplane.contract import load_contract, save_version  # noqa: E402
from controlplane.risk import evaluate  # noqa: E402
from data.generate import load  # noqa: E402

OUT = ROOT / "outputs"
USE_CASES = ["customer_support", "internal_knowledge", "decision_support"]
DEMO_USE_CASE = "customer_support"
DEMO_SIGNATURE = "hallucination:contradiction"
JURISDICTION = "IN"


def rule(title: str) -> None:
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    trail = AuditTrail()
    trail.reset()

    traces = load(ROOT / "data" / "traces.jsonl")
    contracts = {uc: load_contract(uc, JURISDICTION) for uc in USE_CASES}

    # ---- 1. inject -------------------------------------------------
    rule("1. INJECT -- a failure reaches the assistant")
    demo = next(t for t in traces
                if t.use_case == DEMO_USE_CASE and "5 working days" in t.response)
    print(f"trace     : {demo.trace_id}")
    print(f"user      : {demo.user_input}")
    print(f"assistant : {demo.response}")
    print(f"retrieved : {demo.retrieved[0].content if demo.retrieved else '(nothing)'}")

    # ---- 2. detect -------------------------------------------------
    rule("2. DETECT -- two lanes, one action")
    contract = contracts[DEMO_USE_CASE]
    decision = evaluate(demo, contract)
    print(f"contract  : {contract.version}  (jurisdiction {contract.jurisdiction})")
    print(f"action    : {decision.action.value.upper()}")
    print(f"reason    : {decision.reason}")
    print(f"latency   : fast lane {decision.fast_lane_ms} ms | "
          f"slow lane {decision.slow_lane_ms} ms")
    for f in decision.findings:
        print(f"  - [{f.lane}] {f.detector}: {f.severity.value} @ {f.confidence:.2f} "
              f"{[l.value for l in f.labels]}")
        print(f"      {f.rationale}")
        if f.evidence:
            print(f"      response says : \"{f.evidence[0].quote[:90]}\"")
        if len(f.evidence) > 1 and f.evidence[1].quote:
            print(f"      source says   : \"{f.evidence[1].quote[:90]}\"")
    trail.append("decision", {"trace_id": demo.trace_id, "action": decision.action.value,
                              "contract_version": decision.contract_version,
                              "labels": [l.value for l in decision.labels]})

    # ---- 2b. the same trace, a different jurisdiction ----------------
    rule("2b. THE SAME TRACE, A DIFFERENT POLICY PACK -- no code change")
    # Pick a trace the jurisdictions actually disagree about, rather than
    # asserting that they would.
    swing = None
    for t in traces:
        acts = {j: evaluate(t, load_contract(t.use_case, j)).action for j in ("IN", "EU", "US")}
        if len({a.value for a in acts.values()}) > 1:
            swing = t
            break
    print(f"trace     : {swing.trace_id} ({swing.use_case})")
    print(f"assistant : {swing.response[:96]}")
    for j in ("IN", "EU", "US"):
        c = load_contract(swing.use_case, j)
        d = evaluate(swing, c)
        print(f"\n  {j} -- {c.jurisdiction_name}")
        print(f"     contract : {c.version}")
        print(f"     detectors: " + ", ".join(f"{k}={v.mode}" for k, v in c.detectors.items()))
        print(f"     action   : {d.action.value.upper()}")
        print(f"     because  : {d.reason}")
        for note in c.notes:
            print(f"     policy   : {note}")
    trail.append("jurisdiction.comparison", {
        "trace_id": swing.trace_id,
        "actions": {j: evaluate(swing, load_contract(swing.use_case, j)).action.value
                    for j in ("IN", "EU", "US")},
    })

    # ---- 3. cluster and price ---------------------------------------
    rule("3. DEFECT -- forty traces become one priced, owned item")
    pairs = metrics.run(traces, JURISDICTION)
    all_defects = defects_mod.cluster(pairs, contracts)
    defect = next(d for d in all_defects
                  if d.use_case == DEMO_USE_CASE and d.signature == DEMO_SIGNATURE)
    print(f"defect    : {defect.defect_id} -- {defect.title}")
    print(f"labels    : {[l.value for l in defect.labels]}  severity={defect.severity.value}")
    print(f"occurs    : {defect.occurrences} times in {len(traces)} traces; "
          f"{defect.escaped} of those reached the user unflagged")
    print(f"root cause: {defect.root_cause}")
    print(f"impact    : Rs {defect.impact.total_inr:,.0f}/month")
    print(f"            {defect.impact.formula}")
    trail.append("defect.opened", defect.as_dict())

    # ---- 4. human resolution -----------------------------------------
    rule("4. HUMAN RESOLUTION -- nothing changes without a person")
    resolution = lifecycle.resolve(
        defect, reviewer="compliance@acme.example", accepted=True,
        note="Confirmed against refund policy v4.2. The stated window is wrong.",
        trail=trail,
    )
    print(f"reviewer  : {resolution.reviewer}")
    print(f"accepted  : {resolution.accepted}")
    print(f"note      : {resolution.note}")
    print(f"prescribed: {resolution.prescription}")
    print(f"patch     : {resolution.patch}")

    # ---- 5. contract change ------------------------------------------
    rule("5. CONTRACT -- the fix is a versioned configuration change")
    v1 = load_contract(DEMO_USE_CASE, JURISDICTION)
    v2 = load_contract(DEMO_USE_CASE, JURISDICTION, resolution.patch)
    p1 = save_version(v1, "v1")
    p2 = save_version(v2, "v2")
    print(f"before    : {v1.version}  grounding_required={v1.grounding_required}")
    print(f"after     : {v2.version}  grounding_required={v2.grounding_required}")
    print(f"written   : {p1.relative_to(ROOT)}")
    print(f"            {p2.relative_to(ROOT)}   (diff these in git)")
    trail.append("contract.updated", {"use_case": DEMO_USE_CASE, "from": v1.version,
                                      "to": v2.version, "patch": resolution.patch})

    # ---- 6. regression ------------------------------------------------
    rule("6. REGRESSION -- prove the fix held, and say what it cost")
    result = lifecycle.regression(defect, traces, resolution, JURISDICTION, trail=trail)
    r = result.as_dict()
    print(f"regression set     : {r['regression_set_size']} traces "
          f"(the defect's own traces plus reviewer-confirmed misses)")
    print(f"escaped before     : {r['escaped_before']}")
    print(f"escaped after      : {r['escaped_after']}")
    print(f"escape reduction   : "
          f"{'n/a' if r['escape_reduction'] is None else f'{r['escape_reduction'] * 100:.0f}%'}")
    print(f"passed             : {r['passed']}")
    for n in r["notes"]:
        print(f"  - {n}")

    # ---- 7. audit -------------------------------------------------------
    rule("7. AUDIT -- a chain, not a log")
    ok, msg = trail.verify()
    print(f"verify    : {ok} -- {msg}")
    for rec in trail.records():
        print(f"  #{rec['seq']} {rec['ts']} {rec['event']:20s} {rec['hash'][:12]}...")
    print(f"\nwritten   : {trail.path.relative_to(ROOT)}")

    # ---- report ----------------------------------------------------------
    lines = [
        "# Defect lifecycle: before and after\n",
        "Generated by `python scripts/run_demo.py`.\n",
        f"**Defect {defect.defect_id} -- {defect.title}**\n",
        f"- Use case: `{defect.use_case}`, jurisdiction `{JURISDICTION}`",
        f"- Signature: `{defect.signature}`",
        f"- Occurrences in the corpus: {defect.occurrences} of {len(traces)} traces",
        f"- Root cause: {defect.root_cause}",
        f"- Estimated cost: Rs {defect.impact.total_inr:,.0f}/month",
        f"- Pricing formula: {defect.impact.formula}\n",
        "## The fix\n",
        f"{resolution.prescription}\n",
        "```yaml",
        f"# {v1.version}  ->  {v2.version}",
        f"patch: {resolution.patch}",
        "```\n",
        "## Regression result\n",
        "| Measure | Before | After |",
        "|---|---:|---:|",
        f"| Contract version | `{r['contract_before']}` | `{r['contract_after']}` |",
        f"| Failures reaching the user | {r['escaped_before']} | {r['escaped_after']} |",
        f"| False positives ({r['false_positive_family']}, whole use case) | "
        f"{r['false_positives_before']} | {r['false_positives_after']} |",
        "",
        f"Escape reduction: **"
        f"{'n/a' if r['escape_reduction'] is None else f'{r['escape_reduction'] * 100:.0f}%'}**"
        f" on a regression set of {r['regression_set_size']} traces.\n",
        "### What the fix cost\n",
    ]
    lines += [f"- {n}" for n in r["notes"][1:]]
    lines += [
        "\nThis is the whole trade, stated in both directions. A control that only ever "
        "reported the benefit would not be worth trusting with the next one.\n",
        "## Audit chain\n",
        f"`{msg}` -- see `outputs/audit.jsonl`.\n",
    ]
    (OUT / "before_after.md").write_text("\n".join(lines) + "\n")
    print("written   : outputs/before_after.md")

    if not result.passed:
        print("\nFAIL: the regression did not improve on the defect's own traces.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
