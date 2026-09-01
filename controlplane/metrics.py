"""Measurement. Numbers reported to a skeptical stakeholder must be produced
here, from the corpus, and not written by hand anywhere else.

The trade-off this file exists to expose: a detector tuned to miss nothing
will flag things that are fine, and a detector tuned to stay quiet will let
things through. There is no threshold that avoids both, so the contract has
to choose -- and the choice should be visible.
"""
from __future__ import annotations

import statistics
from dataclasses import asdict, dataclass
from typing import Iterable, Optional

from controlplane.contract import ResolvedContract, load_contract
from controlplane.risk import evaluate
from controlplane.trace import Decision, RiskLabel, Trace

FAMILIES = [
    RiskLabel.PRIVACY,
    RiskLabel.HALLUCINATION,
    RiskLabel.BIAS,
    RiskLabel.POLICY,
    RiskLabel.BEHAVIOUR,
]


@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    @property
    def precision(self) -> Optional[float]:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else None

    @property
    def recall(self) -> Optional[float]:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else None

    @property
    def fp_rate(self) -> Optional[float]:
        """Share of traces that do NOT carry this risk but were flagged for it."""
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else None

    @property
    def fn_rate(self) -> Optional[float]:
        """Share of traces that DO carry this risk and were missed."""
        return self.fn / (self.fn + self.tp) if (self.fn + self.tp) else None

    @property
    def f1(self) -> Optional[float]:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p and r else None


def run(traces: Iterable[Trace], jurisdiction: str = "IN",
        overrides: Optional[dict] = None) -> list[tuple[Trace, Decision]]:
    cache: dict[str, ResolvedContract] = {}
    out = []
    for t in traces:
        if t.use_case not in cache:
            cache[t.use_case] = load_contract(t.use_case, jurisdiction, overrides)
        out.append((t, evaluate(t, cache[t.use_case])))
    return out


def counts_by_family(pairs: list[tuple[Trace, Decision]],
                     applicable_only: bool = True) -> dict[str, Counts]:
    """Per-risk-family confusion counts.

    A detector that a contract has switched off is not scored on that use
    case: counting a check nobody asked for as a miss would flatter or punish
    the system for a governance decision rather than a detection one.
    """
    out = {f.value: Counts() for f in FAMILIES}
    detector_for = {
        RiskLabel.PRIVACY: "pii",
        RiskLabel.HALLUCINATION: "hallucination",
        RiskLabel.BIAS: "bias",
        RiskLabel.POLICY: "policy",
        RiskLabel.BEHAVIOUR: "behaviour",
    }
    cache: dict[tuple[str, str], ResolvedContract] = {}
    for t, d in pairs:
        key = (t.use_case, d.jurisdiction)
        if key not in cache:
            cache[key] = load_contract(t.use_case, d.jurisdiction)
        contract = cache[key]
        truth = set(t.labels)
        pred = set(d.labels)
        for fam in FAMILIES:
            if applicable_only and not contract.enabled(detector_for[fam]):
                continue
            c = out[fam.value]
            if fam in truth and fam in pred:
                c.tp += 1
            elif fam in pred:
                c.fp += 1
            elif fam in truth:
                c.fn += 1
            else:
                c.tn += 1
    return out


def latency(pairs: list[tuple[Trace, Decision]]) -> dict[str, dict[str, float]]:
    fast = sorted(d.fast_lane_ms for _, d in pairs)
    slow = sorted(d.slow_lane_ms for _, d in pairs)

    def pct(xs: list[float], q: float) -> float:
        if not xs:
            return 0.0
        i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
        return round(xs[i], 3)

    return {
        "fast_lane_ms": {"p50": pct(fast, 0.5), "p95": pct(fast, 0.95), "p99": pct(fast, 0.99),
                         "max": round(max(fast), 3) if fast else 0.0,
                         "mean": round(statistics.fmean(fast), 3) if fast else 0.0},
        "slow_lane_ms": {"p50": pct(slow, 0.5), "p95": pct(slow, 0.95), "p99": pct(slow, 0.99),
                         "max": round(max(slow), 3) if slow else 0.0,
                         "mean": round(statistics.fmean(slow), 3) if slow else 0.0},
        "n": len(pairs),
    }


def action_mix(pairs: list[tuple[Trace, Decision]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for _, d in pairs:
        out[d.action.value] = out.get(d.action.value, 0) + 1
    return out


def threshold_sweep(traces: list[Trace], detector: str, use_case: str,
                    jurisdiction: str = "IN",
                    modes: tuple[str, ...] = ("permissive", "standard", "strict")) -> list[dict]:
    """Re-run one detector at each sensitivity and record what it costs.

    This is the table a governance owner actually needs: not "which threshold
    is best" but "what do I buy and what do I pay at each one".
    """
    subset = [t for t in traces if t.use_case == use_case]
    rows = []
    for mode in modes:
        pairs = run(subset, jurisdiction, overrides={"detectors": {detector: {"mode": mode}}})
        fam = {"pii": "privacy", "hallucination": "hallucination", "bias": "bias",
               "policy": "policy", "behaviour": "behaviour"}[detector]
        c = counts_by_family(pairs, applicable_only=False)[fam]
        rows.append({
            "mode": mode,
            "tp": c.tp, "fp": c.fp, "fn": c.fn, "tn": c.tn,
            "precision": c.precision, "recall": c.recall,
            "fp_rate": c.fp_rate, "fn_rate": c.fn_rate,
            "blocked_or_reviewed": sum(1 for _, d in pairs if d.blocked_or_reviewed),
        })
    return rows


def as_dict(counts: dict[str, Counts]) -> dict[str, dict]:
    out = {}
    for k, c in counts.items():
        d = asdict(c)
        d.update(precision=c.precision, recall=c.recall, fp_rate=c.fp_rate,
                 fn_rate=c.fn_rate, f1=c.f1)
        out[k] = d
    return out
