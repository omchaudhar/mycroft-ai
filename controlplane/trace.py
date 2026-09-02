"""Core data model for the Mycroft.ai control plane.

A Trace is one AI interaction as an enterprise would capture it at the API
input/output layer -- we never assume access to model internals, which mirrors
the reality that enterprises consume foundation models via API.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# --------------------------------------------------------------------------
# Risk taxonomy
# --------------------------------------------------------------------------


class RiskLabel(str, Enum):
    """The risk families the control plane detects.

    These are deliberately not mutually exclusive: a fabricated personal
    detail is simultaneously HALLUCINATION and PRIVACY. See `risk.py` for how
    overlapping labels are fused into a single action.
    """

    PRIVACY = "privacy"
    HALLUCINATION = "hallucination"
    BIAS = "bias"
    POLICY = "policy"
    BEHAVIOUR = "behaviour"


class Severity(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @property
    def rank(self) -> int:
        return {"none": 0, "low": 1, "medium": 2, "high": 3}[self.value]


class Action(str, Enum):
    """Tiered response. We never silently rewrite a model's output."""

    ALLOW = "allow"
    LOG = "log"
    HUMAN_REVIEW = "human_review"
    BLOCK = "block"

    @property
    def rank(self) -> int:
        return {"allow": 0, "log": 1, "human_review": 2, "block": 3}[self.value]


Lane = Literal["fast", "slow"]


# --------------------------------------------------------------------------
# Trace
# --------------------------------------------------------------------------


class Span(BaseModel):
    """One observable step inside an interaction."""

    span_id: str
    kind: Literal["retrieval", "tool_call", "generation", "user_turn"]
    name: str = ""
    content: str = ""
    tool_args: dict[str, Any] = Field(default_factory=dict)
    doc_id: Optional[str] = None


class Counterfactual(BaseModel):
    """The model's output on the same case with one protected attribute swapped.

    In production these come from a shadow call to the same model. In this
    prototype they are pre-recorded on the trace so the screen is fully
    reproducible offline -- see `slowlane/bias.py` and METHODOLOGY.md.
    """

    attribute: str
    baseline_value: str
    swapped_value: str
    decision: str
    confidence: float
    justification: str = ""


class Trace(BaseModel):
    """One end-to-end AI interaction."""

    trace_id: str
    use_case: str
    user_input: str
    response: str
    spans: list[Span] = Field(default_factory=list)
    # Demographic / contextual attributes, used only by the counterfactual
    # bias screen. Held constant except for the one attribute being swapped.
    subject: dict[str, str] = Field(default_factory=dict)
    # Model-reported decision fields (decision-support use case only).
    decision: Optional[str] = None
    decision_confidence: Optional[float] = None
    justification: str = ""
    counterfactuals: list[Counterfactual] = Field(default_factory=list)
    # Ground truth planted by the generator. Never read by any detector --
    # only by `metrics.py`. See METHODOLOGY.md.
    labels: list[RiskLabel] = Field(default_factory=list)
    label_note: str = ""

    @property
    def retrieved(self) -> list[Span]:
        return [s for s in self.spans if s.kind == "retrieval"]

    @property
    def tool_calls(self) -> list[Span]:
        return [s for s in self.spans if s.kind == "tool_call"]


# --------------------------------------------------------------------------
# Findings and decisions
# --------------------------------------------------------------------------


class Evidence(BaseModel):
    """Every finding is pinned to the exact text that triggered it.

    Without this a reviewer cannot audit the decision, and the finding is not
    defensible to a regulator.
    """

    span_id: str = "response"
    start: int = 0
    end: int = 0
    quote: str = ""
    supporting_doc: Optional[str] = None


class Finding(BaseModel):
    detector: str
    labels: list[RiskLabel]
    severity: Severity
    confidence: float
    lane: Lane
    rationale: str
    evidence: list[Evidence] = Field(default_factory=list)
    latency_ms: float = 0.0
    # Stable key used to cluster many traces into one defect.
    signature: str = ""

    @property
    def primary_label(self) -> RiskLabel:
        return self.labels[0]


class Decision(BaseModel):
    """The control plane's output for one trace."""

    trace_id: str
    use_case: str
    jurisdiction: str
    contract_version: str
    action: Action
    findings: list[Finding] = Field(default_factory=list)
    fast_lane_ms: float = 0.0
    slow_lane_ms: float = 0.0
    reason: str = ""

    @property
    def labels(self) -> list[RiskLabel]:
        seen: list[RiskLabel] = []
        for f in self.findings:
            for lbl in f.labels:
                if lbl not in seen:
                    seen.append(lbl)
        return seen

    @property
    def blocked_or_reviewed(self) -> bool:
        return self.action in (Action.BLOCK, Action.HUMAN_REVIEW)
