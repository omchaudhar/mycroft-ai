"""Fast Lane: deterministic personal-data detection.

Deterministic only. Nothing in the Fast Lane calls a model, because this lane
runs inline on 100% of traffic inside the latency budget and must never add
variance to a user-facing response.

The rule that matters is not "does the response contain a phone number" -- it
is "does the response contain personal data the user did not already have".
Echoing a customer's own details back to them is permitted by the account
handling policy; disclosing somebody else's is the leak.
"""
from __future__ import annotations

import re
import time

from controlplane.contract import ResolvedContract
from controlplane.trace import Evidence, Finding, RiskLabel, Severity, Trace

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from data.idgen import luhn_check, verhoeff_check  # noqa: E402

# (name, pattern, base confidence, severity, validator)
PATTERNS: list[tuple] = [
    ("aadhaar", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"), 0.95, Severity.HIGH,
     lambda m: verhoeff_check(re.sub(r"\D", "", m))),
    ("credit_card", re.compile(r"\b(?:\d[ -]?){13,19}\b"), 0.95, Severity.HIGH,
     lambda m: luhn_check(m)),
    ("pan", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"), 0.90, Severity.HIGH, None),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b"), 0.72, Severity.MEDIUM, None),
    ("phone", re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b"), 0.68, Severity.MEDIUM, None),
    # A capitalised bigram that is not sentence-initial. Deliberately weak:
    # it only fires when the contract is set to 'strict', and it is the main
    # source of this detector's false positives.
    ("person_name", re.compile(r"(?<=[a-z,] )\b[A-Z][a-z]{2,}\s[A-Z][a-z]{2,}\b"), 0.46,
     Severity.LOW, None),
]

LABELS = {
    "aadhaar": "an Aadhaar number",
    "credit_card": "a full card number",
    "pan": "a PAN",
    "email": "an email address",
    "phone": "a mobile number",
    "person_name": "a person's name",
}

_NON_NAME = {
    "Express Delivery", "Working Days", "Gift Card", "Standard Delivery",
    "Expense Policy", "Leave Policy", "Purchase Order",
}


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


def _known_to_user(trace: Trace) -> tuple[set[str], set[str]]:
    """Identifiers the user supplied themselves in this conversation."""
    text = trace.user_input
    nums = {_digits(m) for m in re.findall(r"[\d][\d\s-]{6,}[\d]", text)}
    words = set(re.findall(r"[\w.+-]+@[\w-]+\.[\w.]+", text))
    return {n for n in nums if n}, words


def detect(trace: Trace, contract: ResolvedContract) -> list[Finding]:
    if not contract.enabled("pii"):
        return []
    t0 = time.perf_counter()
    threshold = contract.threshold("pii")
    known_nums, known_words = _known_to_user(trace)
    text = trace.response
    findings: list[Finding] = []
    claimed: list[tuple[int, int]] = []

    for name, pattern, conf, severity, validator in PATTERNS:
        if conf < threshold:
            continue
        for m in pattern.finditer(text):
            raw = m.group(0).strip()
            if validator is not None and not validator(raw):
                continue
            # Longer, higher-confidence matches win overlapping spans.
            if any(m.start() < e and m.end() > s for s, e in claimed):
                continue
            if name == "person_name" and raw in _NON_NAME:
                continue
            d = _digits(raw)
            # Formatting differs between what a user types and what a model
            # writes back ("98214 32210" vs "+91 98214 32210"), so compare on
            # containment rather than equality.
            if d and any(d in k or k in d for k in known_nums):
                continue          # the user's own number, echoed back
            if raw in known_words:
                continue          # the user's own email, echoed back
            claimed.append((m.start(), m.end()))
            findings.append(
                Finding(
                    detector="pii",
                    labels=[RiskLabel.PRIVACY],
                    severity=severity,
                    confidence=conf,
                    lane="fast",
                    rationale=(
                        f"The response contains {LABELS[name]} that the user did not supply "
                        "in this conversation."
                    ),
                    evidence=[Evidence(span_id="response", start=m.start(), end=m.end(), quote=raw)],
                    signature=f"pii:{name}",
                )
            )

    elapsed = (time.perf_counter() - t0) * 1000
    for f in findings:
        f.latency_ms = elapsed / max(1, len(findings))
    return findings
