#!/usr/bin/env python3
"""Capability-aware Life OS plane for Shay Phase 5.

Open-ended registries for life/business domains plus evidence-backed capability
claims and Fritz-specific attention routing inputs.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from shay_constants import get_shay_home


@dataclass
class DomainRecord:
    key: str
    label: str
    stream: str
    status: str
    evidence_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityClaim:
    key: str
    label: str
    surface: str
    readiness: str
    evidence_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AttentionCandidate:
    key: str
    label: str
    stream: str
    revenue_potential: int = 0
    automation_potential: int = 0
    mental_load_reduction: int = 0
    urgency: int = 0
    blockers_cleared: int = 0
    evidence_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class LifeOSPlane:
    def __init__(self, root: str | Path | None = None):
        self.root = Path(root) if root else get_shay_home() / "life-os"
        self.root.mkdir(parents=True, exist_ok=True)
        self.domains_path = self.root / "domains.json"
        self.capabilities_path = self.root / "capabilities.json"

    def register_domain(self, record: DomainRecord) -> None:
        payload = self._load_json(self.domains_path, default={"domains": []})
        domains = [d for d in payload.get("domains", []) if d.get("key") != record.key]
        domains.append(asdict(record))
        payload["domains"] = sorted(domains, key=lambda item: item["key"])
        self._save_json(self.domains_path, payload)

    def register_capability(self, claim: CapabilityClaim) -> None:
        payload = self._load_json(self.capabilities_path, default={"capabilities": []})
        capabilities = [c for c in payload.get("capabilities", []) if c.get("key") != claim.key]
        capabilities.append(asdict(claim))
        payload["capabilities"] = sorted(capabilities, key=lambda item: item["key"])
        self._save_json(self.capabilities_path, payload)

    def list_domains(self, *, status: Optional[str] = None) -> List[Dict[str, Any]]:
        payload = self._load_json(self.domains_path, default={"domains": []})
        domains = payload.get("domains", [])
        if status is not None:
            domains = [domain for domain in domains if domain.get("status") == status]
        return domains

    def get_capability(self, key: str) -> Optional[Dict[str, Any]]:
        payload = self._load_json(self.capabilities_path, default={"capabilities": []})
        for capability in payload.get("capabilities", []):
            if capability.get("key") == key:
                return capability
        return None

    def capability_matrix(self) -> Dict[str, List[Dict[str, Any]]]:
        payload = self._load_json(self.capabilities_path, default={"capabilities": []})
        matrix: Dict[str, List[Dict[str, Any]]] = {}
        for capability in payload.get("capabilities", []):
            surface = capability.get("surface") or "unknown"
            matrix.setdefault(surface, []).append(capability)
        for surface in matrix:
            matrix[surface].sort(key=lambda item: item.get("key") or "")
        return matrix

    def route_attention(
        self,
        *,
        candidates: List[AttentionCandidate],
        fritz_state: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        overload = int(fritz_state.get("overload") or 0)
        energy = int(fritz_state.get("energy") or 0)
        top_stream = str(fritz_state.get("priority_stream") or "")
        scored: List[Dict[str, Any]] = []
        for candidate in candidates:
            score = (
                candidate.revenue_potential * 5
                + candidate.automation_potential * 4
                + candidate.mental_load_reduction * (6 if overload >= 7 else 3)
                + candidate.urgency * 2
                + candidate.blockers_cleared * 3
            )
            if candidate.stream == "Fritz":
                score += 10 if overload >= 6 else 4
            if candidate.stream == "Income":
                score += 8
            if top_stream and candidate.stream == top_stream:
                score += 4
            if energy <= 3 and candidate.metadata.get("effort") == "high":
                score -= 6
            if overload >= 7 and candidate.metadata.get("mode") == "deep-work":
                score -= 5
            scored.append(
                {
                    "key": candidate.key,
                    "label": candidate.label,
                    "stream": candidate.stream,
                    "score": score,
                    "why": self._explain_route(candidate, overload=overload, energy=energy, top_stream=top_stream),
                    "evidence_refs": list(candidate.evidence_refs),
                }
            )
        scored.sort(key=lambda item: (-item["score"], item["label"]))
        return scored

    @staticmethod
    def _explain_route(candidate: AttentionCandidate, *, overload: int, energy: int, top_stream: str) -> List[str]:
        reasons: List[str] = []
        if candidate.stream == "Income":
            reasons.append("Income stream gets structural priority")
        if candidate.stream == "Fritz" and overload >= 6:
            reasons.append("Protect the source: Fritz stream boosted under overload")
        if candidate.mental_load_reduction:
            reasons.append(f"Mental-load reduction={candidate.mental_load_reduction}")
        if candidate.revenue_potential:
            reasons.append(f"Revenue potential={candidate.revenue_potential}")
        if candidate.automation_potential:
            reasons.append(f"Automation potential={candidate.automation_potential}")
        if top_stream and candidate.stream == top_stream:
            reasons.append(f"Matches Fritz priority stream: {top_stream}")
        if energy <= 3 and candidate.metadata.get("effort") == "high":
            reasons.append("Penalized because Fritz energy is low and effort is high")
        return reasons

    @staticmethod
    def _load_json(path: Path, *, default: Dict[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return dict(default)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return dict(default)

    @staticmethod
    def _save_json(path: Path, payload: Dict[str, Any]) -> None:
        data = dict(payload)
        data["updated_at"] = time.time()
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(path)
