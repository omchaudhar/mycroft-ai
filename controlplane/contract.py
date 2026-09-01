"""Evaluation Contracts: governance as configuration, not application logic.

A resolved contract is built from two versioned artifacts:

    Jurisdiction -> Policy Pack -> Use-Case Contract -> Detector configuration

The policy pack can only *raise* strictness, never lower it. That ratchet is
what makes "the same trace behaves differently in India and the EU" a
configuration change rather than a code change.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field

from controlplane.trace import Action, RiskLabel, Severity

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_DIR = ROOT / "contracts"

# Detector sensitivity. A lower threshold fires more often: more false
# positives, fewer false negatives. This is the governance trade-off dial,
# and `metrics.py` measures its cost in both directions.
MODE_THRESHOLDS: dict[str, Optional[float]] = {
    "off": None,
    "permissive": 0.80,
    "standard": 0.60,
    "strict": 0.40,
}
MODE_RANK = {"off": 0, "permissive": 1, "standard": 2, "strict": 3}

DETECTORS = ["pii", "hallucination", "bias", "policy", "behaviour"]


class DetectorConfig(BaseModel):
    mode: str = "standard"
    threshold: Optional[float] = None
    # Where the mode came from, so the UI can show *why* a check is strict.
    source: str = "use_case"

    @property
    def enabled(self) -> bool:
        return self.mode != "off"

    def resolved_threshold(self) -> float:
        if self.threshold is not None:
            return self.threshold
        t = MODE_THRESHOLDS[self.mode]
        return 1.01 if t is None else t


class Economics(BaseModel):
    """Inputs for defect pricing. Every one is an explicit assumption.

    Documented with its source in docs/ASSUMPTIONS.md. Change a number here
    and every rupee figure in the app and the evidence pack changes with it.
    """

    interactions_per_week: int = 12000
    rework_cost_per_incident_inr: float = 0.0
    handoff_rate: float = 0.0
    handoff_cost_inr: float = 0.0
    churn_exposure_per_incident_inr: float = 0.0


class ResolvedContract(BaseModel):
    use_case: str
    description: str = ""
    jurisdiction: str
    jurisdiction_name: str = ""
    risk_level: str = "medium"
    latency_budget_ms: int = 100
    revision: int = 1
    detectors: dict[str, DetectorConfig] = Field(default_factory=dict)
    actions: dict[str, Action] = Field(default_factory=dict)
    force_review_labels: list[RiskLabel] = Field(default_factory=list)
    grounding_required: bool = False
    notes: list[str] = Field(default_factory=list)
    economics: Economics = Field(default_factory=Economics)
    regulatory_references: list[str] = Field(default_factory=list)

    # ------------------------------------------------------------------
    @property
    def version(self) -> str:
        """Content hash. Two contracts with identical behaviour share a
        version; any edit produces a new one, so audit records are exact."""
        payload = json.dumps(
            self.model_dump(mode="json", exclude={"description", "notes", "jurisdiction_name"}),
            sort_keys=True,
        )
        digest = hashlib.sha256(payload.encode()).hexdigest()[:10]
        return f"{self.use_case}@r{self.revision}-{digest}"

    def action_for(self, severity: Severity) -> Action:
        return self.actions.get(severity.value, Action.LOG)

    def threshold(self, detector: str) -> float:
        cfg = self.detectors.get(detector)
        return cfg.resolved_threshold() if cfg else 1.01

    def enabled(self, detector: str) -> bool:
        cfg = self.detectors.get(detector)
        return bool(cfg and cfg.enabled)

    def to_yaml(self) -> str:
        d = self.model_dump(mode="json")
        d["version"] = self.version
        return yaml.safe_dump(d, sort_keys=False, allow_unicode=True)


# ----------------------------------------------------------------------
# Loading and merging
# ----------------------------------------------------------------------


def _read(path: Path) -> dict[str, Any]:
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def list_use_cases() -> list[str]:
    return sorted(p.stem for p in (CONTRACT_DIR / "use_cases").glob("*.yaml"))


def list_jurisdictions() -> list[str]:
    return sorted(p.stem for p in (CONTRACT_DIR / "policy_packs").glob("*.yaml"))


def load_contract(
    use_case: str,
    jurisdiction: str,
    overrides: Optional[dict[str, Any]] = None,
) -> ResolvedContract:
    """Merge a use-case contract with a jurisdiction policy pack.

    `overrides` lets the fix loop (and the app's contract editor) apply a
    patch without editing files on disk.
    """
    uc = _read(CONTRACT_DIR / "use_cases" / f"{use_case}.yaml")
    pack = _read(CONTRACT_DIR / "policy_packs" / f"{jurisdiction}.yaml")
    if overrides:
        uc = _deep_merge(uc, overrides)

    detectors: dict[str, DetectorConfig] = {}
    for name in DETECTORS:
        raw = (uc.get("detectors") or {}).get(name) or {}
        detectors[name] = DetectorConfig(
            mode=raw.get("mode", "off"),
            threshold=raw.get("threshold"),
            source="use_case",
        )

    notes: list[str] = []
    risk_level = uc.get("risk_level", "medium")
    # High risk is decided by the *jurisdiction*, not by the team's own label.
    # Annex III of the EU AI Act names the categories; a support chatbot is not
    # one of them, so it must not silently inherit high-risk obligations.
    is_high_risk = use_case in (pack.get("high_risk_use_cases") or [])

    # The ratchet: a policy pack raises strictness, never lowers it.
    minimums = dict(pack.get("minimum_modes") or {})
    if is_high_risk:
        minimums.update((pack.get("high_risk_minimum_modes") or {}))
    for name, required in minimums.items():
        cfg = detectors.get(name)
        if cfg is None:
            continue
        if MODE_RANK[required] > MODE_RANK[cfg.mode]:
            notes.append(
                f"{pack.get('jurisdiction', jurisdiction)} policy pack raised "
                f"'{name}' from {cfg.mode} to {required}."
            )
            cfg.mode = required
            cfg.threshold = None
            cfg.source = f"policy_pack:{jurisdiction}"

    actions: dict[str, Action] = {}
    for sev in ("high", "medium", "low"):
        raw = (uc.get("actions") or {}).get(sev, "log")
        actions[sev] = Action(raw)
    for sev, floor in (pack.get("minimum_actions") or {}).items():
        if Action(floor).rank > actions.get(sev, Action.LOG).rank:
            notes.append(
                f"{pack.get('jurisdiction', jurisdiction)} policy pack raised the "
                f"'{sev}' severity action from {actions[sev].value} to {floor}."
            )
            actions[sev] = Action(floor)

    force = [RiskLabel(x) for x in (pack.get("force_review_labels") or [])]
    if force:
        notes.append(
            f"{pack.get('jurisdiction', jurisdiction)} requires human review for: "
            + ", ".join(f.value for f in force)
        )

    return ResolvedContract(
        use_case=use_case,
        description=uc.get("description", ""),
        jurisdiction=jurisdiction,
        jurisdiction_name=pack.get("name", jurisdiction),
        risk_level=risk_level,
        latency_budget_ms=uc.get("latency_budget_ms", 100),
        revision=uc.get("revision", 1),
        detectors=detectors,
        actions=actions,
        force_review_labels=force,
        grounding_required=bool((uc.get("requirements") or {}).get("grounding_required", False)),
        notes=notes,
        economics=Economics(**(uc.get("economics") or {})),
        regulatory_references=pack.get("references") or [],
    )


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def save_version(contract: ResolvedContract, label: str) -> Path:
    """Freeze a resolved contract to disk so it can be diffed in git."""
    out = CONTRACT_DIR / "versions" / f"{contract.use_case}.{label}.yaml"
    out.write_text(contract.to_yaml())
    return out
