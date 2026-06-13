import tempfile
import unittest
from pathlib import Path

from life_os_plane import AttentionCandidate, CapabilityClaim, DomainRecord, LifeOSPlane


class LifeOSPlaneTest(unittest.TestCase):
    def test_plane_keeps_open_ended_domains_and_evidence_backed_capabilities(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plane = LifeOSPlane(Path(tmpdir) / "life-os")
            plane.register_domain(
                DomainRecord(
                    key="income-reseller",
                    label="Reseller reactivation",
                    stream="Income",
                    status="active",
                    evidence_refs=["docs/reseller.md"],
                    metadata={"domain_type": "business"},
                )
            )
            plane.register_domain(
                DomainRecord(
                    key="metaphysical-practice",
                    label="Metaphysical practice",
                    stream="Metaphysical",
                    status="active",
                    evidence_refs=["obsidian/metaphysical.md"],
                    metadata={"domain_type": "life"},
                )
            )
            plane.register_capability(
                CapabilityClaim(
                    key="watcher-readonly",
                    label="Read-only watchers",
                    surface="life-os",
                    readiness="healthy",
                    evidence_refs=["life_os_watchers.py", "tests/test_life_os_watchers.py"],
                )
            )
            plane.register_capability(
                CapabilityClaim(
                    key="pattern-scanner",
                    label="Pattern scanner",
                    surface="life-os",
                    readiness="healthy",
                    evidence_refs=["life_os_pattern_scanner.py", "tests/test_life_os_pattern_scanner.py"],
                )
            )

            domains = plane.list_domains(status="active")
            self.assertEqual({domain["stream"] for domain in domains}, {"Income", "Metaphysical"})
            capability = plane.get_capability("watcher-readonly")
            self.assertIsNotNone(capability)
            self.assertTrue(capability["evidence_refs"])
            matrix = plane.capability_matrix()
            self.assertIn("life-os", matrix)
            self.assertEqual(len(matrix["life-os"]), 2)

    def test_attention_router_uses_fritz_specific_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plane = LifeOSPlane(Path(tmpdir) / "life-os")
            candidates = [
                AttentionCandidate(
                    key="reseller",
                    label="Reseller reactivation",
                    stream="Income",
                    revenue_potential=10,
                    automation_potential=7,
                    mental_load_reduction=4,
                    urgency=6,
                    blockers_cleared=8,
                    evidence_refs=["docs/reseller.md"],
                    metadata={"effort": "medium"},
                ),
                AttentionCandidate(
                    key="fritz-reset",
                    label="Fritz recovery block",
                    stream="Fritz",
                    revenue_potential=1,
                    automation_potential=1,
                    mental_load_reduction=10,
                    urgency=8,
                    blockers_cleared=4,
                    evidence_refs=["obsidian/health.md"],
                    metadata={"effort": "low"},
                ),
                AttentionCandidate(
                    key="deep-architecture",
                    label="Deep architecture refactor",
                    stream="Shay+platform",
                    revenue_potential=4,
                    automation_potential=5,
                    mental_load_reduction=1,
                    urgency=3,
                    blockers_cleared=5,
                    evidence_refs=["docs/refactor.md"],
                    metadata={"effort": "high", "mode": "deep-work"},
                ),
            ]
            ranked = plane.route_attention(
                candidates=candidates,
                fritz_state={"overload": 8, "energy": 3, "priority_stream": "Income"},
            )
            self.assertEqual(ranked[0]["key"], "reseller")
            self.assertEqual(ranked[1]["key"], "fritz-reset")
            self.assertIn("Protect the source", " ".join(ranked[1]["why"]))


if __name__ == "__main__":
    unittest.main()
