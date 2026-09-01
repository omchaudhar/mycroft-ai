"""Fast Lane: allow/deny lists and unauthorised-commitment phrases.

Deterministic string rules. These are the checks an enterprise can state in
one line and defend in an audit, so they belong inline rather than in the
semantic lane.
"""
from __future__ import annotations

import re
import time

from controlplane.contract import ResolvedContract
from controlplane.trace import Evidence, Finding, RiskLabel, Severity, Trace

# Phrases that commit the enterprise to something an assistant cannot commit
# to. Each carries the negation guard that stops "I cannot waive" from firing.
DENY_PHRASES: list[tuple[str, str, Severity]] = [
    (r"\b(i|we)\s+(can\s+)?guarantee\b", "commits to a guaranteed outcome", Severity.HIGH),
    (r"\bi('ll| will)\s+waive\b", "waives a fee without authorisation", Severity.HIGH),
    (r"\bno inspection needed\b", "bypasses a required inspection step", Severity.HIGH),
    (r"\bi would advise you to file\b", "gives legal advice", Severity.HIGH),
    (r"\bnever checks\b", "advises circumventing a control", Severity.HIGH),
    (r"\byou are entitled to\b", "asserts a statutory entitlement", Severity.MEDIUM),
]

NEGATION = re.compile(
    r"\b(not able to|cannot|can't|unable to|aren't authorised|are not authorised|"
    r"isn't|is not|won't|will not|don't|do not)\b[^.]{0,40}$"
)


def detect(trace: Trace, contract: ResolvedContract) -> list[Finding]:
    if not contract.enabled("policy"):
        return []
    t0 = time.perf_counter()
    text = trace.response
    findings: list[Finding] = []
    for pattern, why, severity in DENY_PHRASES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            prefix = text[max(0, m.start() - 60):m.start()]
            if NEGATION.search(prefix):
                continue
            conf = 0.88 if severity is Severity.HIGH else 0.7
            if conf < contract.threshold("policy"):
                continue
            findings.append(
                Finding(
                    detector="deny_list",
                    labels=[RiskLabel.POLICY],
                    severity=severity,
                    confidence=conf,
                    lane="fast",
                    rationale=f"Unauthorised commitment: {why}.",
                    evidence=[Evidence(span_id="response", start=m.start(), end=m.end(),
                                       quote=text[m.start():m.end()])],
                    signature=f"policy:deny:{why[:24]}",
                )
            )
    elapsed = (time.perf_counter() - t0) * 1000
    for f in findings:
        f.latency_ms = elapsed / max(1, len(findings))
    return findings
