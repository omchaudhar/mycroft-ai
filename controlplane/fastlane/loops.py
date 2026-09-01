"""Fast Lane: loop, budget and behavioural-signal breakers.

Multi-turn agents compound risk: one questionable step shapes several
downstream ones. These checks are cheap, deterministic circuit breakers on
that compounding, plus the revealed-preference signals a user leaves behind
when the assistant is not helping.
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter

from controlplane.contract import ResolvedContract
from controlplane.trace import Evidence, Finding, RiskLabel, Severity, Trace

MAX_IDENTICAL_CALLS = 3
MAX_TOOL_CALLS = 8

FRUSTRATION = re.compile(
    r"\b(no,? not that|i said|as i (already )?said|that's not what|again,|still wrong)\b",
    re.IGNORECASE,
)


def detect(trace: Trace, contract: ResolvedContract) -> list[Finding]:
    if not contract.enabled("behaviour"):
        return []
    t0 = time.perf_counter()
    findings: list[Finding] = []
    calls = trace.tool_calls

    sigs = Counter(f"{s.name}:{json.dumps(s.tool_args, sort_keys=True)}" for s in calls)
    for sig, n in sigs.items():
        if n > MAX_IDENTICAL_CALLS:
            findings.append(
                Finding(
                    detector="loop_breaker",
                    labels=[RiskLabel.BEHAVIOUR],
                    severity=Severity.MEDIUM,
                    confidence=0.9,
                    lane="fast",
                    rationale=f"The same tool call was issued {n} times in one run.",
                    evidence=[Evidence(span_id="tool", quote=sig.split(":", 1)[0])],
                    signature=f"behaviour:loop:{sig.split(':', 1)[0]}",
                )
            )

    if len(calls) > MAX_TOOL_CALLS:
        findings.append(
            Finding(
                detector="budget_breaker",
                labels=[RiskLabel.BEHAVIOUR],
                severity=Severity.LOW,
                confidence=0.8,
                lane="fast",
                rationale=f"{len(calls)} tool calls in one run exceeds the budget of {MAX_TOOL_CALLS}.",
                evidence=[Evidence(span_id="tool", quote=f"{len(calls)} calls")],
                signature="behaviour:budget",
            )
        )

    m = FRUSTRATION.search(trace.user_input)
    if m:
        findings.append(
            Finding(
                detector="revealed_signal",
                labels=[RiskLabel.BEHAVIOUR],
                severity=Severity.LOW,
                confidence=0.75,
                lane="fast",
                rationale="The user restated a constraint the assistant had already been given.",
                evidence=[Evidence(span_id="user", start=m.start(), end=m.end(), quote=m.group(0))],
                signature="behaviour:instruction_decay",
            )
        )

    findings = [f for f in findings if f.confidence >= contract.threshold("behaviour")]
    elapsed = (time.perf_counter() - t0) * 1000
    for f in findings:
        f.latency_ms = elapsed / max(1, len(findings))
    return findings
