"""The control plane itself: two lanes, multi-label fusion, one action.

Fast Lane runs inline on every interaction and is deterministic. Slow Lane
runs asynchronously and is allowed to be semantic. Findings from both are
fused into a single decision, because the user gets one response and the
enterprise takes one action.
"""
from __future__ import annotations

import re
import time

from controlplane.contract import ResolvedContract
from controlplane.fastlane import lists, loops, pii
from controlplane.slowlane import bias, grounding
from controlplane.slowlane import policy as policy_slow
from controlplane.trace import Action, Decision, Finding, RiskLabel, Severity, Trace

FAST_LANE = [pii.detect, lists.detect, loops.detect]
SLOW_LANE = [grounding.detect, bias.detect, policy_slow.detect]


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def apply_overlap_rules(trace: Trace, findings: list[Finding]) -> list[Finding]:
    """A fabricated personal detail is both a privacy event and a hallucination.

    The distinguishing test is evidence, not wording: personal data that
    appears in the retrieved context is real data being disclosed; personal
    data that appears nowhere in context was invented by the model. The first
    is a leak, the second is a leak *and* a fabrication -- and the second is
    strictly worse, because there is no source to correct.
    """
    context = " ".join(
        s.content for s in trace.spans if s.kind in ("retrieval", "tool_call") and s.content
    )
    context_digits = _digits(context)

    for f in findings:
        if RiskLabel.PRIVACY not in f.labels or f.detector != "pii":
            continue
        quote = f.evidence[0].quote if f.evidence else ""
        d = _digits(quote)
        in_context = (quote and quote in context) or (len(d) >= 6 and d in context_digits)
        if not in_context:
            f.labels = [RiskLabel.PRIVACY, RiskLabel.HALLUCINATION]
            f.severity = Severity.HIGH
            f.confidence = min(0.97, f.confidence + 0.15)
            f.rationale += (
                " This identifier appears nowhere in the retrieved context, so it was "
                "fabricated: logged as both a privacy exposure and a hallucination."
            )
            f.signature = f.signature.replace("pii:", "overlap:fabricated_")
    return findings


def resolve_action(findings: list[Finding], contract: ResolvedContract) -> tuple[Action, str]:
    """Highest severity determines the immediate response.

    Every label is recorded, but the enterprise takes exactly one action, and
    it is the strictest one any finding demands.
    """
    if not findings:
        return Action.ALLOW, "No finding above the configured thresholds."

    worst = max(findings, key=lambda f: (f.severity.rank, f.confidence))
    action = contract.action_for(worst.severity)
    reason = (
        f"{worst.detector} raised a {worst.severity.value}-severity "
        f"{'/'.join(l.value for l in worst.labels)} finding at confidence "
        f"{worst.confidence:.2f}; the contract maps {worst.severity.value} to {action.value}."
    )

    # A jurisdiction can require human oversight for a whole risk family
    # regardless of how severe this particular instance looked.
    for f in findings:
        if any(l in contract.force_review_labels for l in f.labels):
            if action.rank < Action.HUMAN_REVIEW.rank:
                action = Action.HUMAN_REVIEW
                reason += (
                    f" Raised to human_review: the {contract.jurisdiction} policy pack requires "
                    f"human oversight for {'/'.join(l.value for l in f.labels)} findings."
                )
            break
    return action, reason


def evaluate(trace: Trace, contract: ResolvedContract, slow: bool = True) -> Decision:
    """Run one interaction through the control plane."""
    t0 = time.perf_counter()
    findings: list[Finding] = []
    for check in FAST_LANE:
        findings.extend(check(trace, contract))
    fast_ms = (time.perf_counter() - t0) * 1000

    slow_ms = 0.0
    if slow:
        t1 = time.perf_counter()
        for check in SLOW_LANE:
            findings.extend(check(trace, contract))
        slow_ms = (time.perf_counter() - t1) * 1000

    findings = apply_overlap_rules(trace, findings)
    action, reason = resolve_action(findings, contract)

    return Decision(
        trace_id=trace.trace_id,
        use_case=trace.use_case,
        jurisdiction=contract.jurisdiction,
        contract_version=contract.version,
        action=action,
        findings=sorted(findings, key=lambda f: (-f.severity.rank, -f.confidence)),
        fast_lane_ms=round(fast_ms, 3),
        slow_lane_ms=round(slow_ms, 3),
        reason=reason,
    )
