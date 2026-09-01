"""Slow Lane: hallucination as an evidence problem, not a truth problem.

We never claim a statement is false. We report that it is unsupported by, or
contradicts, the documents the enterprise has agreed to be bound by -- which
is the only thing that is actually checkable in real time, and the only thing
a reviewer can adjudicate from the evidence shown.
"""
from __future__ import annotations

import time

from controlplane.contract import ResolvedContract
from controlplane.corpus import load_corpus, split_sentences
from controlplane.slowlane.judge import get_judge, numbers
from controlplane.trace import Evidence, Finding, RiskLabel, Severity, Trace

MAX_CLAIMS = 4


def detect(trace: Trace, contract: ResolvedContract) -> list[Finding]:
    if not contract.enabled("hallucination"):
        return []
    t0 = time.perf_counter()
    judge = get_judge()
    corpus = load_corpus(trace.use_case)
    context = [s.content for s in trace.spans if s.kind in ("retrieval", "tool_call") and s.content]
    threshold = contract.threshold("hallucination")

    # Figures the model was legitimately handed: the user's own question and
    # whatever retrieval and tools put in front of it. The judge adds the
    # figures asserted by the source document each claim matches.
    grounded = numbers(trace.user_input) | numbers(" ".join(context))

    findings: list[Finding] = []
    claims = [c for c in split_sentences(trace.response) if judge.is_checkable(c)][:MAX_CLAIMS]

    for claim in claims:
        v = judge.assess(claim, corpus, extra=context, grounded=grounded)
        ungrounded_answer = False

        # A separate control from sensitivity: when the contract requires
        # grounding, an answer with no supporting document is a finding on its
        # own terms, however confident the wording sounds. This is what
        # catches open-ended fabrication -- an invented benefit or programme
        # has no figure to contradict, so no threshold will ever reach it.
        if v.confidence < threshold and contract.grounding_required and v.similarity < judge.TOPICAL:
            v.confidence = 0.80
            v.rationale = (
                "The contract requires every answer to be backed by a governed document, and "
                f"no document supports this claim (best evidence similarity {v.similarity})."
            )
            ungrounded_answer = True
        elif v.confidence < threshold or v.confidence == 0.0:
            continue
        severity = (
            Severity.HIGH if v.contradiction
            else Severity.MEDIUM if v.confidence >= 0.7
            else Severity.LOW
        )
        start = trace.response.find(claim)
        findings.append(
            Finding(
                detector="grounding",
                labels=[RiskLabel.HALLUCINATION],
                severity=severity,
                confidence=v.confidence,
                lane="slow",
                rationale=f"{v.rationale} (evidence similarity {v.similarity}, judge: {judge.name})",
                evidence=[
                    Evidence(
                        span_id="response",
                        start=max(0, start),
                        end=max(0, start) + len(claim),
                        quote=claim,
                        supporting_doc=v.doc_id or None,
                    ),
                    Evidence(span_id=v.doc_id or "corpus", quote=v.evidence,
                             supporting_doc=v.doc_id or None),
                ],
                signature=("hallucination:contradiction" if v.contradiction
                           else "hallucination:ungrounded_answer" if ungrounded_answer
                           else "hallucination:unsupported"),
            )
        )

    elapsed = (time.perf_counter() - t0) * 1000
    for f in findings:
        f.latency_ms = elapsed / max(1, len(findings))
    return findings
