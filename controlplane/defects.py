"""From findings to defects.

A finding is one bad response. Nobody can act on four thousand of them. A
defect is the *pattern*: one owner, one root cause, one priced impact, one
regression set. Turning findings into defects is what makes the feedback loop
finishable rather than a dashboard that grows forever.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from controlplane.contract import Economics, ResolvedContract
from controlplane.trace import Decision, Finding, RiskLabel, Severity, Trace

WEEKS_PER_MONTH = 4.33


@dataclass
class Impact:
    """Priced with explicit inputs. Every figure below is reproducible from
    the contract's economics block and the measured occurrence rate."""

    occurrence_rate: float
    monthly_occurrences: float
    rework_inr: float
    handoff_inr: float
    churn_inr: float
    total_inr: float
    formula: str

    def as_dict(self) -> dict:
        return {
            "occurrence_rate": round(self.occurrence_rate, 5),
            "monthly_occurrences": round(self.monthly_occurrences, 1),
            "rework_inr": round(self.rework_inr),
            "handoff_inr": round(self.handoff_inr),
            "churn_inr": round(self.churn_inr),
            "total_inr": round(self.total_inr),
            "formula": self.formula,
        }


def price(occurrences: int, sample_size: int, econ: Economics) -> Impact:
    rate = occurrences / sample_size if sample_size else 0.0
    monthly = rate * econ.interactions_per_week * WEEKS_PER_MONTH
    rework = monthly * econ.rework_cost_per_incident_inr
    handoff = monthly * econ.handoff_rate * econ.handoff_cost_inr
    churn = monthly * econ.churn_exposure_per_incident_inr
    return Impact(
        occurrence_rate=rate,
        monthly_occurrences=monthly,
        rework_inr=rework,
        handoff_inr=handoff,
        churn_inr=churn,
        total_inr=rework + handoff + churn,
        formula=(
            f"rate {occurrences}/{sample_size} = {rate:.4f} x {econ.interactions_per_week} "
            f"interactions/week x {WEEKS_PER_MONTH} weeks = {monthly:.1f} occurrences/month; "
            f"x (Rs {econ.rework_cost_per_incident_inr} rework + {econ.handoff_rate} handoff rate "
            f"x Rs {econ.handoff_cost_inr} + Rs {econ.churn_exposure_per_incident_inr} churn "
            f"exposure) per occurrence"
        ),
    )


@dataclass
class Defect:
    defect_id: str
    use_case: str
    signature: str
    labels: list[RiskLabel]
    severity: Severity
    title: str
    occurrences: int
    escaped: int
    trace_ids: list[str] = field(default_factory=list)
    examples: list[dict] = field(default_factory=list)
    root_cause: str = ""
    impact: Optional[Impact] = None
    status: str = "open"

    def as_dict(self) -> dict:
        return {
            "defect_id": self.defect_id, "use_case": self.use_case,
            "signature": self.signature, "labels": [l.value for l in self.labels],
            "severity": self.severity.value, "title": self.title,
            "occurrences": self.occurrences, "escaped": self.escaped,
            "trace_ids": self.trace_ids, "examples": self.examples,
            "root_cause": self.root_cause,
            "impact": self.impact.as_dict() if self.impact else None,
            "status": self.status,
        }


# Root-cause hypotheses. Each names the artifact a human would actually edit,
# which is what makes a defect assignable rather than merely interesting.
ROOT_CAUSES = {
    "hallucination:contradiction": (
        "The generator restates a governed figure from memory instead of the retrieved "
        "document. Root cause is prompt-level: the system prompt does not require the "
        "answer to quote the retrieved policy."
    ),
    "hallucination:ungrounded_answer": (
        "The assistant answers questions the governed corpus does not cover, and invents "
        "plausible detail to fill the gap. Root cause is scope: nothing requires it to refuse "
        "when it has no source."
    ),
    "hallucination:unsupported": (
        "The generator answers outside the governed corpus. Root cause is coverage: either "
        "retrieval returned nothing usable, or the assistant was not instructed to refuse "
        "when it has no source."
    ),
    "overlap:fabricated_phone": (
        "The generator invents contact details to sound helpful. Root cause is prompt-level: "
        "no instruction forbids generating identifiers absent from context."
    ),
    "overlap:fabricated_person_name": (
        "The generator invents a named individual. Root cause is prompt-level: no instruction "
        "forbids naming people absent from context."
    ),
    "policy:explanation:attribute": (
        "The generator justifies an adverse recommendation with a protected attribute. Root "
        "cause is prompt and tooling: protected fields are present in the model's context at all."
    ),
    "policy:explanation:one": (
        "The generator reaches for a proxy phrase when the permitted factors are marginal. "
        "Root cause is prompt-level: no required justification template."
    ),
    "policy:explanation:missing_factor": (
        "An adverse recommendation is issued with no permitted factor cited. Root cause is "
        "output-shape: the response is free text rather than a structured reason code."
    ),
    "bias": (
        "The recommendation is sensitive to a protected attribute. Root cause is upstream: the "
        "attribute or a close proxy is reaching the model."
    ),
    "behaviour:loop": (
        "The agent re-issues an identical tool call because the result is not being carried "
        "forward in context. Root cause is orchestration, not the model."
    ),
}

TITLES = {
    "hallucination:contradiction": "Response restates a governed figure incorrectly",
    "hallucination:unsupported": "Response asserts figures found in no governed source",
    "hallucination:ungrounded_answer": "Answer has no supporting document in the governed corpus",
    "overlap:fabricated_phone": "Assistant invents a contact number for a person",
    "overlap:fabricated_person_name": "Assistant invents a named individual",
    "policy:explanation:attribute": "Adverse recommendation justified by a protected attribute",
    "policy:explanation:one": "Adverse recommendation justified by a proxy attribute",
    "policy:explanation:missing_factor": "Adverse recommendation cites no permitted factor",
    "behaviour:loop": "Agent repeats an identical tool call",
    "behaviour:budget": "Agent exceeds its tool-call budget",
}


def _root_cause(signature: str) -> str:
    for key, text in ROOT_CAUSES.items():
        if signature.startswith(key):
            return text
    return "Root cause not yet classified; needs a reviewer."


def _title(signature: str) -> str:
    for key, text in TITLES.items():
        if signature.startswith(key):
            return text
    return signature.replace(":", " / ")


def cluster(pairs: list[tuple[Trace, Decision]],
            contracts: dict[str, ResolvedContract]) -> list[Defect]:
    """Group findings into defects by failure signature, not by topic.

    Forty traces about forty different orders that all fail the same way are
    one defect. Two traces about the same order that fail differently are two.
    """
    sample_size: dict[str, int] = defaultdict(int)
    for t, _ in pairs:
        sample_size[t.use_case] += 1

    buckets: dict[tuple[str, str], list[tuple[Trace, Decision, Finding]]] = defaultdict(list)
    for t, d in pairs:
        for f in d.findings:
            buckets[(t.use_case, f.signature)].append((t, d, f))

    defects: list[Defect] = []
    for (use_case, signature), items in sorted(buckets.items(), key=lambda kv: -len(kv[1])):
        contract = contracts[use_case]
        worst = max(items, key=lambda x: (x[2].severity.rank, x[2].confidence))[2]
        labels: list[RiskLabel] = []
        for _, _, f in items:
            for l in f.labels:
                if l not in labels:
                    labels.append(l)
        escaped = sum(1 for _, d, _ in items if not d.blocked_or_reviewed)
        did = "DEF-" + hashlib.sha1(f"{use_case}:{signature}".encode()).hexdigest()[:6].upper()
        defects.append(
            Defect(
                defect_id=did,
                use_case=use_case,
                signature=signature,
                labels=labels,
                severity=worst.severity,
                title=_title(signature),
                occurrences=len(items),
                escaped=escaped,
                trace_ids=[t.trace_id for t, _, _ in items],
                examples=[
                    {
                        "trace_id": t.trace_id,
                        "user_input": t.user_input,
                        "response": t.response,
                        "quote": f.evidence[0].quote if f.evidence else "",
                        "evidence": f.evidence[1].quote if len(f.evidence) > 1 else "",
                        "rationale": f.rationale,
                        "action": d.action.value,
                    }
                    for t, d, f in items[:3]
                ],
                root_cause=_root_cause(signature),
                impact=price(len(items), sample_size[use_case], contract.economics),
            )
        )
    return defects
