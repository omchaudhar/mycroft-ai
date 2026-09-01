"""The defect lifecycle: detect, resolve, change the contract, prove it held.

The loop only closes if the last step is a measurement. A fix that is not
regression-tested is a claim, and a claim is what the enterprise already had
before it bought anything.

Two honesty constraints are built in here:

* A contract change reduces what *escapes*, not what the model gets wrong. We
  measure and report escape reduction, never "accuracy improvement".
* Every fix costs something. `apply_fix` measures the additional false
  positives the change introduces across the whole use case, and reports that
  next to the benefit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from controlplane.audit import AuditTrail
from controlplane.contract import ResolvedContract, load_contract
from controlplane.defects import Defect
from controlplane.metrics import counts_by_family, run
from controlplane.trace import RiskLabel, Trace

# What a human review of each defect class actually changes. Some defects have
# no contract fix at all -- saying so is more useful than pretending otherwise.
PRESCRIPTIONS: list[tuple[str, dict[str, Any], str]] = [
    # The minimal change that addresses the miss, and only that. Raising
    # sensitivity as well was measured and rejected: it added false positives
    # without catching anything the grounding requirement did not already catch.
    ("hallucination",
     {"requirements": {"grounding_required": True}, "revision": 2},
     "Require every answer to be backed by a governed document, so the assistant "
     "must refuse rather than improvise when the corpus does not cover the question."),
    ("overlap:fabricated",
     {"detectors": {"pii": {"mode": "strict"}, "hallucination": {"mode": "strict"}},
      "revision": 2},
     "Treat identifiers absent from context as high severity, and raise "
     "grounding to strict so the fabrication is caught on its own."),
    ("policy:explanation",
     {"detectors": {"policy": {"mode": "strict"}}, "revision": 2},
     "Raise explanation-quality checks to strict so adverse recommendations "
     "must cite a permitted factor."),
    ("bias",
     {"detectors": {"bias": {"mode": "strict"}}, "revision": 2},
     "Lower the counterfactual divergence threshold so smaller movements "
     "reach a human."),
]

NO_CONTRACT_FIX = (
    "behaviour:loop",
    "behaviour:budget",
)


@dataclass
class Resolution:
    defect_id: str
    accepted: bool
    reviewer: str
    note: str
    patch: Optional[dict[str, Any]] = None
    prescription: str = ""


@dataclass
class RegressionResult:
    defect_id: str
    n_traces: int
    escaped_before: int
    escaped_after: int
    contract_before: str
    contract_after: str
    fp_before: int
    fp_after: int
    fp_family: str
    passed: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def escape_reduction(self) -> Optional[float]:
        if not self.escaped_before:
            return None
        return (self.escaped_before - self.escaped_after) / self.escaped_before

    def as_dict(self) -> dict:
        return {
            "defect_id": self.defect_id,
            "regression_set_size": self.n_traces,
            "escaped_before": self.escaped_before,
            "escaped_after": self.escaped_after,
            "escape_reduction": (round(self.escape_reduction, 4)
                                 if self.escape_reduction is not None else None),
            "contract_before": self.contract_before,
            "contract_after": self.contract_after,
            "false_positives_before": self.fp_before,
            "false_positives_after": self.fp_after,
            "false_positive_family": self.fp_family,
            "passed": self.passed,
            "notes": self.notes,
        }


def prescribe(defect: Defect) -> tuple[Optional[dict[str, Any]], str]:
    for prefix in NO_CONTRACT_FIX:
        if defect.signature.startswith(prefix):
            return None, (
                "No contract change applies. This is an orchestration defect: the fix is in "
                "the agent's control flow, and the control plane's job is to keep the "
                "regression test that proves it was fixed."
            )
    for prefix, patch, why in PRESCRIPTIONS:
        if defect.signature.startswith(prefix):
            return patch, why
    return None, "No prescription registered for this signature; needs a reviewer."


def resolve(defect: Defect, reviewer: str, accepted: bool, note: str = "",
            trail: Optional[AuditTrail] = None) -> Resolution:
    """A human confirms or rejects the finding. Nothing changes without this."""
    patch, why = prescribe(defect)
    res = Resolution(defect_id=defect.defect_id, accepted=accepted, reviewer=reviewer,
                     note=note, patch=patch if accepted else None, prescription=why)
    if trail:
        trail.append("defect.resolved", {
            "defect_id": defect.defect_id, "reviewer": reviewer, "accepted": accepted,
            "note": note, "prescription": why, "patch": res.patch,
        })
    return res


def regression(defect: Defect, all_traces: list[Trace], resolution: Resolution,
               jurisdiction: str = "IN",
               trail: Optional[AuditTrail] = None) -> RegressionResult:
    """Re-run the defect's own traces under the old and the new contract.

    The regression set is not written by hand: it is exactly the traces that
    produced the defect, so the test cannot drift away from the failure.
    """
    # The regression set is the traces that produced the defect, plus every
    # trace a reviewer has since confirmed shows the same failure. That second
    # group is the important one: it is where the misses live, and a fix that
    # only re-passes the cases already caught proves nothing.
    #
    # In production the reviewer-confirmed group comes out of the human review
    # queue. In this prototype it comes from the corpus labels, which is the
    # same thing one step earlier.
    family_label = defect.labels[0] if defect.labels else RiskLabel.HALLUCINATION
    ids = set(defect.trace_ids)
    subset = [
        t for t in all_traces
        if t.use_case == defect.use_case
        and (t.trace_id in ids or family_label in t.labels)
    ]
    same_use_case = [t for t in all_traces if t.use_case == defect.use_case]
    fam_for = {"pii": "privacy", "hallucination": "hallucination", "bias": "bias",
               "policy": "policy", "behaviour": "behaviour"}
    family = defect.labels[0].value if defect.labels else "hallucination"

    before_pairs = run(subset, jurisdiction)
    before_all = run(same_use_case, jurisdiction)
    escaped_before = sum(1 for _, d in before_pairs if not d.blocked_or_reviewed)
    fp_before = counts_by_family(before_all, applicable_only=False)[family].fp
    c_before = load_contract(defect.use_case, jurisdiction).version

    if not resolution.accepted or resolution.patch is None:
        result = RegressionResult(
            defect_id=defect.defect_id, n_traces=len(subset),
            escaped_before=escaped_before, escaped_after=escaped_before,
            contract_before=c_before, contract_after=c_before,
            fp_before=fp_before, fp_after=fp_before, fp_family=family,
            passed=False, notes=[resolution.prescription],
        )
    else:
        after_pairs = run(subset, jurisdiction, overrides=resolution.patch)
        after_all = run(same_use_case, jurisdiction, overrides=resolution.patch)
        escaped_after = sum(1 for _, d in after_pairs if not d.blocked_or_reviewed)
        fp_after = counts_by_family(after_all, applicable_only=False)[family].fp
        c_after = load_contract(defect.use_case, jurisdiction, resolution.patch).version
        result = RegressionResult(
            defect_id=defect.defect_id, n_traces=len(subset),
            escaped_before=escaped_before, escaped_after=escaped_after,
            contract_before=c_before, contract_after=c_after,
            fp_before=fp_before, fp_after=fp_after, fp_family=family,
            passed=escaped_after < escaped_before or escaped_before == 0,
            notes=[resolution.prescription],
        )
        # What the fix costs operationally is not the false-positive count but
        # how many extra interactions land in a human's queue.
        reviews_before = sum(1 for _, d in before_all if d.blocked_or_reviewed)
        reviews_after = sum(1 for _, d in after_all if d.blocked_or_reviewed)
        result.notes.append(
            f"Human review load moves from {reviews_before} to {reviews_after} of "
            f"{len(same_use_case)} {defect.use_case} interactions "
            f"({reviews_after - reviews_before:+d})."
        )
        cost = fp_after - fp_before
        result.notes.append(
            f"Cost of this fix: {cost:+d} false positives on {family} across "
            f"{len(same_use_case)} {defect.use_case} traces."
            if cost else
            f"This fix introduced no additional false positives on {family} across "
            f"{len(same_use_case)} {defect.use_case} traces."
        )

    if trail:
        trail.append("regression.run", result.as_dict())
    return result
