"""Slow Lane judge backends.

Two rules govern this file:

1. The evaluator must not be the generator marking its own homework. The
   Anthropic backend is a different model family from the assistant being
   evaluated; the offline backend is not a language model at all.
2. The default path must run with no API key and no network, so the numbers
   in outputs/ are reproducible by anyone who clones the repo.

`OfflineJudge` is a retrieval-and-arithmetic check, not an LLM judge, and is
described that way everywhere it appears.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Optional

from controlplane.corpus import Corpus

# Numbers that carry policy meaning. Long digit strings are identifiers
# (orders, invoices, references), not claims a policy corpus can adjudicate.
_NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")


def numbers(text: str) -> set[float]:
    out = set()
    for m in _NUM.finditer(text):
        raw = m.group(0).replace(",", "").rstrip(".")
        if not raw or len(raw.replace(".", "")) >= 6:
            # Six digits or more is an identifier (order, invoice, reference),
            # not a figure a policy corpus can adjudicate.
            continue
        try:
            out.add(float(raw))
        except ValueError:
            pass
    return out


@dataclass
class ClaimVerdict:
    claim: str
    similarity: float
    evidence: str
    doc_id: str
    contradiction: bool
    unsupported: bool
    confidence: float
    rationale: str
    backend: str


class OfflineJudge:
    """Deterministic grounding check: retrieval similarity + numeric agreement."""

    name = "offline-deterministic"
    describes_itself_as = (
        "retrieval similarity over the governed corpus plus numeric agreement; "
        "not a language model"
    )

    # A claim is only judged if it reads as a general assertion. Account-
    # specific facts ("order 98123 shipped Tuesday") are outside what a policy
    # corpus can verify, and flagging them is noise, not signal.
    MARKERS = re.compile(
        r"\b(takes?|costs?|carr(y|ies|ied)|require[sd]?|must|entitled?|processed|charged|"
        r"cover(s|ed)?|minimum|maximum|within|exceeds?|below|clears?|eligible|allowed|"
        r"accrues?|capped|per day|per year|per night|working days?|days?|months?|"
        r"warranty|refunds?|per-diem|approval|approves?|declines?|fee|discount|returns?|"
        r"allowance|membership|programme|program|tier|credited|reimburs\w+|leave|"
        r"qualif\w+|encash\w+)\b",
        re.IGNORECASE,
    )
    TOPICAL = 0.45   # above this, the claim and the evidence are about the same thing

    def is_checkable(self, claim: str) -> bool:
        return bool(self.MARKERS.search(claim))

    def assess(
        self,
        claim: str,
        corpus: Corpus,
        extra: list[str] | None = None,
        grounded: set[float] | None = None,
    ) -> ClaimVerdict:
        sim, evidence, doc = corpus.best_match(claim)
        # The governed document a claim is closest to defines which figures it
        # is entitled to assert, even when a retrieval snippet happens to match
        # the wording more closely.
        source_doc = doc
        for cand in extra or []:
            s2, _, _ = Corpus(use_case=corpus.use_case, sentences=[cand],
                              sentence_doc=["context"]).build().best_match(claim)
            if s2 > sim:
                sim, evidence, doc = s2, cand, "context"

        claim_nums = numbers(claim)
        # A figure is grounded if the document this claim actually matches
        # asserts it, or if it came from the case data in front of the model.
        grounded_set = set(grounded or set()) | corpus.doc_numbers(source_doc)
        ungrounded = claim_nums - grounded_set
        contradiction = False

        if ungrounded:
            contradiction = sim >= self.TOPICAL
            if contradiction:
                rationale = (
                    f"The response restates {doc} but changes its figures: it asserts "
                    f"{sorted(ungrounded)}, which that source does not state."
                )
                conf = 0.90
            else:
                rationale = (
                    f"The response asserts {sorted(ungrounded)}, which appears neither in the "
                    "governed source it most resembles nor anywhere in this interaction's inputs."
                )
                conf = 0.75
        elif sim < 0.28 and not claim_nums:
            rationale = "No sentence in the governed corpus supports this claim."
            conf = 0.55
        else:
            rationale = "Supported by the governed corpus and the case data."
            conf = 0.0

        return ClaimVerdict(
            claim=claim, similarity=round(sim, 3), evidence=evidence, doc_id=doc,
            contradiction=contradiction, unsupported=conf > 0 and not contradiction,
            confidence=conf, rationale=rationale, backend=self.name,
        )


class AnthropicJudge(OfflineJudge):
    """Optional: uses Claude as an independent evaluator.

    Deliberately a subclass -- the checkability filter and the fallback path
    stay identical, so turning the API on changes the verdict source and
    nothing else about the pipeline.
    """

    name = "anthropic-claude"
    describes_itself_as = "an LLM judge from a different model family than the generator"

    def __init__(self, model: str = "claude-sonnet-5") -> None:
        from anthropic import Anthropic  # imported lazily; optional dependency

        self.client = Anthropic()
        self.model = model

    def assess(
        self,
        claim: str,
        corpus: Corpus,
        extra: list[str] | None = None,
        grounded: set[float] | None = None,
    ) -> ClaimVerdict:
        candidates = corpus.top_matches(claim, k=4)
        evidence_block = "\n".join(f"- {s}" for _, s, _ in candidates) or "(none)"
        prompt = (
            "You verify a claim against governed source documents.\n"
            f"CLAIM: {claim}\n\nSOURCES:\n{evidence_block}\n\n"
            "Answer with exactly one word on the first line -- SUPPORTED, "
            "CONTRADICTED or UNSUPPORTED -- then one sentence of reason."
        )
        try:
            msg = self.client.messages.create(
                model=self.model, max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip()
        except Exception:
            return super().assess(claim, corpus, extra, grounded)   # fail safe, never fail open

        verdict = text.split("\n")[0].strip().upper()
        reason = " ".join(text.split("\n")[1:]).strip()
        sim, evidence, doc = corpus.best_match(claim)
        if verdict.startswith("CONTRAD"):
            return ClaimVerdict(claim, round(sim, 3), evidence, doc, True, False, 0.9,
                                reason or "Contradicted by the governed corpus.", self.name)
        if verdict.startswith("UNSUP"):
            return ClaimVerdict(claim, round(sim, 3), evidence, doc, False, True, 0.7,
                                reason or "Unsupported by the governed corpus.", self.name)
        return ClaimVerdict(claim, round(sim, 3), evidence, doc, False, False, 0.0,
                            reason or "Supported.", self.name)


_JUDGE: Optional[OfflineJudge] = None


def get_judge() -> OfflineJudge:
    """Offline unless MYCROFT_JUDGE=anthropic and a key is present."""
    global _JUDGE
    if _JUDGE is not None:
        return _JUDGE
    if os.getenv("MYCROFT_JUDGE") == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        try:
            _JUDGE = AnthropicJudge()
            return _JUDGE
        except Exception:
            pass
    _JUDGE = OfflineJudge()
    return _JUDGE
