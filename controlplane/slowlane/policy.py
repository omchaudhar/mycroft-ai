"""Slow Lane: semantic policy and explanation-quality checks.

The Fast Lane catches phrases an enterprise can enumerate. This lane catches
the ones it cannot: a justification that leans on a protected attribute, or a
stand-in for one ("profile", "the area they live in"), which the adverse
action rules prohibit just as firmly as naming the attribute outright.
"""
from __future__ import annotations

import re
import time

from controlplane.contract import ResolvedContract
from controlplane.corpus import load_corpus
from controlplane.trace import Evidence, Finding, RiskLabel, Severity, Trace

PROTECTED_TERMS = re.compile(
    r"\b(age band|age group|her |his |she |he |gender|marital status|married|single|"
    r"religion|caste|pregnan\w+|disab\w+|widow\w*)\b",
    re.IGNORECASE,
)
PROXY_TERMS = re.compile(
    r"\b(profile|the area they live|their area|neighbourhood|neighborhood|background|"
    r"people like|typical for this product|less typical)\b",
    re.IGNORECASE,
)
PERMITTED_FACTORS = re.compile(
    r"\b(bureau score|debt-to-income|income history|delinquenc\w+|dti)\b", re.IGNORECASE
)


def detect(trace: Trace, contract: ResolvedContract) -> list[Finding]:
    if not contract.enabled("policy"):
        return []
    t0 = time.perf_counter()
    threshold = contract.threshold("policy")
    text = trace.justification or trace.response
    findings: list[Finding] = []

    if trace.use_case == "decision_support":
        for pattern, kind, conf, sev in (
            (PROTECTED_TERMS, "a protected attribute", 0.86, Severity.HIGH),
            (PROXY_TERMS, "a proxy for a protected attribute", 0.72, Severity.HIGH),
        ):
            m = pattern.search(text)
            if m and conf >= threshold:
                findings.append(
                    Finding(
                        detector="explanation_policy",
                        labels=[RiskLabel.POLICY],
                        severity=sev,
                        confidence=conf,
                        lane="slow",
                        rationale=(
                            f"The recommendation is justified by {kind} ('{m.group(0).strip()}'). "
                            "Adverse action rules require the specific permitted factor, its "
                            "observed value and the threshold."
                        ),
                        evidence=[Evidence(span_id="response", start=m.start(), end=m.end(),
                                           quote=m.group(0).strip())],
                        signature=f"policy:explanation:{kind.split()[-1]}",
                    )
                )
                break

        # An adverse recommendation with no permitted factor cited at all.
        if (trace.decision or "").lower() in ("decline", "refer") and not PERMITTED_FACTORS.search(text):
            conf = 0.68
            if conf >= threshold and not findings:
                findings.append(
                    Finding(
                        detector="explanation_policy",
                        labels=[RiskLabel.POLICY],
                        severity=Severity.MEDIUM,
                        confidence=conf,
                        lane="slow",
                        rationale=(
                            "An adverse recommendation was issued without citing any permitted "
                            "assessment factor."
                        ),
                        evidence=[Evidence(span_id="response", quote=text[:160])],
                        signature="policy:explanation:missing_factor",
                    )
                )

    elapsed = (time.perf_counter() - t0) * 1000
    for f in findings:
        f.latency_ms = elapsed / max(1, len(findings))
    return findings
