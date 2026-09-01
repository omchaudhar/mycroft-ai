"""ControlPlane.ai -- working prototype.

Run:  streamlit run app/streamlit_app.py

Everything on screen is computed live from the repo. No screenshots, no
hard-coded numbers.
"""
from __future__ import annotations

import difflib
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from controlplane import defects as defects_mod  # noqa: E402
from controlplane import lifecycle, metrics  # noqa: E402
from controlplane.audit import AuditTrail  # noqa: E402
from controlplane.contract import (  # noqa: E402
    list_jurisdictions, list_use_cases, load_contract,
)
from controlplane.risk import evaluate  # noqa: E402
from controlplane.slowlane.judge import get_judge  # noqa: E402
from controlplane.trace import Action, Span, Trace  # noqa: E402
from data.generate import load  # noqa: E402

st.set_page_config(page_title="ControlPlane.ai", layout="wide")

ACTION_STYLE = {
    "allow": ("#1a7f37", "ALLOW"),
    "log": ("#7a6400", "LOG"),
    "human_review": ("#b45309", "HUMAN REVIEW"),
    "block": ("#b42318", "BLOCK"),
}


@st.cache_data
def _traces() -> list[Trace]:
    return load(ROOT / "data" / "traces.jsonl")


@st.cache_data
def _holdout() -> list[Trace]:
    return load(ROOT / "data" / "holdout.jsonl")


@st.cache_data
def _metrics_json() -> dict | None:
    p = ROOT / "outputs" / "metrics.json"
    return json.loads(p.read_text()) if p.exists() else None


def action_badge(action: Action) -> None:
    colour, label = ACTION_STYLE[action.value]
    st.markdown(
        f"<div style='display:inline-block;padding:6px 16px;border-radius:6px;"
        f"background:{colour};color:white;font-weight:700;letter-spacing:.06em;'>"
        f"{label}</div>",
        unsafe_allow_html=True,
    )


def show_findings(decision) -> None:
    if not decision.findings:
        st.success("No finding above the thresholds this contract sets.")
        return
    for f in decision.findings:
        lane = "Fast Lane (inline, deterministic)" if f.lane == "fast" else "Slow Lane (asynchronous)"
        with st.expander(
            f"{f.severity.value.upper()} - {f.detector} - "
            f"{' + '.join(l.value for l in f.labels)} @ {f.confidence:.2f}",
            expanded=True,
        ):
            st.caption(lane)
            st.write(f.rationale)
            if f.evidence and f.evidence[0].quote:
                st.markdown("**In the response**")
                st.code(f.evidence[0].quote, language=None)
            if len(f.evidence) > 1 and f.evidence[1].quote:
                label = f.evidence[1].supporting_doc or "counterfactual"
                st.markdown(f"**Evidence ({label})**")
                st.code(f.evidence[1].quote, language=None)


# ======================================================================
st.title("ControlPlane.ai")
st.caption(
    "A configurable Responsible AI control plane. Every number on this page is computed "
    "live from the simulated corpus in this repository -- none of it is real enterprise data."
)

judge = get_judge()
st.info(
    f"**Slow Lane judge: `{judge.name}`** -- {judge.describes_itself_as}. "
    "Set `CONTROLPLANE_JUDGE=anthropic` with an API key to route semantic evaluation to "
    "a model from a different family than the generator.",
)

tab_live, tab_contract, tab_defects, tab_metrics, tab_audit = st.tabs(
    ["Live", "Evaluation Contract", "Defects", "Metrics", "Audit"]
)

# ----------------------------------------------------------------------
with tab_live:
    traces = _traces() + _holdout()
    c1, c2 = st.columns([1, 1])
    with c1:
        use_case = st.selectbox("Use case", list_use_cases(), index=0)
    with c2:
        jurisdiction = st.selectbox("Jurisdiction", list_jurisdictions(),
                                    index=list_jurisdictions().index("IN"))

    pool = [t for t in traces if t.use_case == use_case]
    labels = {
        f"{t.trace_id} - {', '.join(l.value for l in t.labels) or 'clean'} - {t.response[:56]}...": t
        for t in pool
    }
    pick = st.selectbox(f"Trace ({len(pool)} in this use case)", list(labels))
    trace = labels[pick]

    st.markdown("**User**")
    st.info(trace.user_input)
    st.markdown("**Assistant response**")
    st.warning(trace.response)
    if trace.retrieved:
        with st.expander("Retrieved context"):
            for s in trace.spans:
                if s.kind in ("retrieval", "tool_call") and s.content:
                    st.caption(f"{s.kind} - {s.name} - {s.doc_id or ''}")
                    st.code(s.content, language=None)

    contract = load_contract(use_case, jurisdiction)
    decision = evaluate(trace, contract)

    st.divider()
    a, b, c, d = st.columns([1.1, 1, 1, 1.6])
    with a:
        st.markdown("**Action**")
        action_badge(decision.action)
    b.metric("Fast Lane", f"{decision.fast_lane_ms:.2f} ms",
             help=f"Budget for this use case: {contract.latency_budget_ms} ms")
    c.metric("Slow Lane", f"{decision.slow_lane_ms:.2f} ms", help="Asynchronous; never blocks the user")
    d.metric("Contract", contract.version)
    st.caption(decision.reason)

    if len(decision.labels) > 1:
        st.error(
            "**Overlapping risks.** " + " + ".join(l.value for l in decision.labels) +
            " were all recorded. Every label is logged; the highest severity decides the action.",
        )

    show_findings(decision)

    st.divider()
    st.subheader("The same trace under every policy pack")
    st.caption("No code changes between these rows. Only the jurisdiction's policy pack.")
    rows = []
    for j in list_jurisdictions():
        cj = load_contract(use_case, j)
        dj = evaluate(trace, cj)
        rows.append({
            "Jurisdiction": f"{j} - {cj.jurisdiction_name}",
            "Action": dj.action.value,
            "Findings": len(dj.findings),
            **{k: v.mode for k, v in cj.detectors.items()},
            "Contract": cj.version,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------
with tab_contract:
    st.subheader("Jurisdiction -> Policy Pack -> Evaluation Contract -> Detector configuration")
    st.caption(
        "Regulatory requirements are policy configuration, not application logic. A policy "
        "pack can only raise strictness; it can never relax what a use case already requires."
    )
    c1, c2 = st.columns(2)
    uc = c1.selectbox("Use case", list_use_cases(), key="ct_uc")
    ju = c2.selectbox("Jurisdiction", list_jurisdictions(), key="ct_j",
                      index=list_jurisdictions().index("IN"))
    base = load_contract(uc, ju)

    st.markdown("#### Try a change")
    st.caption("Edit the contract and watch the decisions move. Nothing here is a code change.")
    cols = st.columns(5)
    overrides: dict = {"detectors": {}}
    for i, (name, cfg) in enumerate(base.detectors.items()):
        modes = ["off", "permissive", "standard", "strict"]
        chosen = cols[i].selectbox(name, modes, index=modes.index(cfg.mode), key=f"m_{name}")
        overrides["detectors"][name] = {"mode": chosen}
    edited = load_contract(uc, ju, overrides)

    if base.notes:
        for n in base.notes:
            st.caption(f"Policy pack: {n}")

    c1, c2 = st.columns(2)
    c1.metric("Contract version (as written)", base.version)
    c2.metric("Contract version (as edited)", edited.version)

    pool = [t for t in _traces() if t.use_case == uc]
    before = metrics.run(pool, ju)
    after = metrics.run(pool, ju, overrides=overrides)
    mix = pd.DataFrame([
        {"Contract": "as written", **metrics.action_mix(before)},
        {"Contract": "as edited", **metrics.action_mix(after)},
    ]).fillna(0)
    st.markdown(f"#### Effect on all {len(pool)} `{uc}` traces")
    st.dataframe(mix, use_container_width=True, hide_index=True)

    cb = metrics.counts_by_family(before, applicable_only=False)
    ca = metrics.counts_by_family(after, applicable_only=False)
    rows = []
    for fam in cb:
        if cb[fam].tp + cb[fam].fn + ca[fam].tp + ca[fam].fn == 0:
            continue
        rows.append({
            "Risk": fam,
            "FP (written)": cb[fam].fp, "FP (edited)": ca[fam].fp,
            "FN (written)": cb[fam].fn, "FN (edited)": ca[fam].fn,
        })
    st.caption("What the change buys, and what it costs -- both directions, always.")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.markdown("#### Resolved contract")
    st.code(edited.to_yaml(), language="yaml")
    if base.regulatory_references:
        st.markdown("**This policy pack cites**")
        for r in base.regulatory_references:
            st.caption(f"- {r}")

# ----------------------------------------------------------------------
with tab_defects:
    st.subheader("Findings become defects; defects get closed")
    st.caption(
        "A finding is one bad response. A defect is the pattern behind forty of them: one "
        "root cause, one price, one regression set, one owner."
    )
    ju = st.selectbox("Jurisdiction", list_jurisdictions(), key="df_j",
                      index=list_jurisdictions().index("IN"))
    traces = _traces()
    contracts = {uc: load_contract(uc, ju) for uc in list_use_cases()}
    pairs = metrics.run(traces, ju)
    defect_list = defects_mod.cluster(pairs, contracts)

    table = pd.DataFrame([{
        "Defect": d.defect_id, "Use case": d.use_case, "Title": d.title,
        "Signature": d.signature, "Severity": d.severity.value,
        "Occurrences": d.occurrences, "Escaped": d.escaped,
        "Est. Rs/month": round(d.impact.total_inr),
    } for d in defect_list])
    st.dataframe(table, use_container_width=True, hide_index=True, height=320)

    ids = [d.defect_id for d in defect_list]
    chosen = st.selectbox("Open a defect", ids,
                          format_func=lambda i: f"{i} - {next(d for d in defect_list if d.defect_id == i).title}")
    defect = next(d for d in defect_list if d.defect_id == chosen)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Occurrences", defect.occurrences)
    c2.metric("Reached the user", defect.escaped)
    c3.metric("Severity", defect.severity.value)
    c4.metric("Estimated cost", f"Rs {defect.impact.total_inr:,.0f}/mo")
    st.caption(f"Pricing: {defect.impact.formula}")
    st.markdown(f"**Root cause hypothesis.** {defect.root_cause}")

    st.markdown("**Examples**")
    for ex in defect.examples:
        with st.expander(f"{ex['trace_id']} - action {ex['action']}"):
            st.caption("User"); st.write(ex["user_input"])
            st.caption("Assistant"); st.warning(ex["response"])
            if ex["evidence"]:
                st.caption("Source says"); st.code(ex["evidence"], language=None)
            st.caption(ex["rationale"])

    st.divider()
    st.markdown("#### Human resolution")
    reviewer = st.text_input("Reviewer", "compliance@acme.example")
    note = st.text_input("Note", "Confirmed against the governed policy.")
    patch, why = lifecycle.prescribe(defect)
    st.caption(f"Prescribed change: {why}")
    if patch:
        st.code(json.dumps(patch, indent=2), language="json")

    if st.button("Accept, update the contract, run the regression", type="primary"):
        trail = AuditTrail()
        res = lifecycle.resolve(defect, reviewer, True, note, trail=trail)
        result = lifecycle.regression(defect, traces, res, ju, trail=trail)
        r = result.as_dict()
        if not patch:
            st.warning(why)
        else:
            v1 = load_contract(defect.use_case, ju)
            v2 = load_contract(defect.use_case, ju, res.patch)
            st.markdown("**Contract diff**")
            diff = difflib.unified_diff(
                v1.to_yaml().splitlines(), v2.to_yaml().splitlines(),
                fromfile=v1.version, tofile=v2.version, lineterm="",
            )
            st.code("\n".join(diff) or "(no change)", language="diff")

            a, b, c = st.columns(3)
            a.metric("Regression set", r["regression_set_size"])
            b.metric("Reached the user", f"{r['escaped_before']} -> {r['escaped_after']}",
                     delta=r["escaped_after"] - r["escaped_before"], delta_color="inverse")
            c.metric(f"False positives ({r['false_positive_family']})",
                     f"{r['false_positives_before']} -> {r['false_positives_after']}",
                     delta=r["false_positives_after"] - r["false_positives_before"],
                     delta_color="inverse")
            if r["escape_reduction"] is not None:
                st.success(f"Escape reduction: {r['escape_reduction'] * 100:.0f}% "
                           f"({'passed' if r['passed'] else 'did not pass'})")
            for n in r["notes"]:
                st.caption(f"- {n}")
            st.caption("The cost is reported next to the benefit, every time.")

# ----------------------------------------------------------------------
with tab_metrics:
    st.subheader("Measured, not asserted")
    data = _metrics_json()
    if st.button("Re-run the evaluation"):
        with st.spinner("Running scripts/run_eval.py ..."):
            subprocess.run([sys.executable, str(ROOT / "scripts" / "run_eval.py")], check=False)
        st.cache_data.clear()
        data = _metrics_json()

    if not data:
        st.warning("Run `python scripts/run_eval.py` to generate outputs/metrics.json.")
    else:
        st.caption(f"Judge backend: `{data['judge_backend']}` -- {data['judge_description']}")
        for key, title, blurb in (
            ("generated", "Generated corpus",
             "Labelled by construction: the generator knows which risk it planted."),
            ("holdout", "Hand-written adversarial holdout",
             "Written after the detectors, to test the risk rather than the templates."),
        ):
            blk = data[key]
            st.markdown(f"#### {title} ({blk['n']} traces)")
            st.caption(blurb)
            rows = []
            for fam, c in blk["counts"].items():
                if c["tp"] + c["fp"] + c["fn"] == 0:
                    continue
                rows.append({
                    "Risk": fam, "TP": c["tp"], "FP": c["fp"], "FN": c["fn"], "TN": c["tn"],
                    "Precision": None if c["precision"] is None else round(c["precision"], 3),
                    "Recall": None if c["recall"] is None else round(c["recall"], 3),
                    "FP rate": None if c["fp_rate"] is None else round(c["fp_rate"], 3),
                    "FN rate": None if c["fn_rate"] is None else round(c["fn_rate"], 3),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown("#### Latency")
        st.caption("Detector compute measured in-process; excludes network and serialisation.")
        lat = data["latency"]
        st.dataframe(pd.DataFrame([
            {"Lane": k.replace("_ms", "").replace("_", " "), **v} for k, v in lat.items()
            if isinstance(v, dict)
        ]), use_container_width=True, hide_index=True)

        st.markdown("#### The trade-off we are actually choosing")
        st.caption(
            "Over-flagging causes alert fatigue; under-flagging causes liability. There is no "
            "setting that avoids both, so the contract has to pick -- with the cost visible."
        )
        for key, rows in data["threshold_sweeps"].items():
            st.markdown(f"**{key}**")
            st.dataframe(pd.DataFrame([{
                "Mode": r["mode"], "TP": r["tp"], "FP": r["fp"], "FN": r["fn"],
                "Precision": None if r["precision"] is None else round(r["precision"], 3),
                "Recall": None if r["recall"] is None else round(r["recall"], 3),
                "Sent to review or blocked": r["blocked_or_reviewed"],
            } for r in rows]), use_container_width=True, hide_index=True)

# ----------------------------------------------------------------------
with tab_audit:
    st.subheader("A chain, not a log")
    st.caption(
        "Each record carries the hash of the one before it, so a decision cannot be quietly "
        "removed or edited after the fact."
    )
    trail = AuditTrail()
    ok, msg = trail.verify()
    (st.success if ok else st.error)(msg)
    records = list(trail.records())
    if not records:
        st.info("No records yet. Run `python scripts/run_demo.py`, or resolve a defect above.")
    else:
        st.dataframe(pd.DataFrame([{
            "seq": r["seq"], "timestamp": r["ts"], "event": r["event"],
            "hash": r["hash"][:16] + "...", "prev": r["prev_hash"][:16] + "...",
        } for r in records]), use_container_width=True, hide_index=True)
        pick = st.selectbox("Inspect a record", [r["seq"] for r in records])
        st.json(next(r for r in records if r["seq"] == pick))
