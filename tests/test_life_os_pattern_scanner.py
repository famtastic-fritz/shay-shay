import json
import tempfile
import unittest
from pathlib import Path

from life_os_pattern_scanner import LifeOSPatternScanner, PatternStateStore
from process_intelligence import ProcessIntelligenceDB


class LifeOSPatternScannerTest(unittest.TestCase):
    def test_scanner_detects_known_pattern_classes_and_dedupes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            tracker_path = root / "tracker.yaml"
            tracker_path.write_text(
                "items:\n"
                "  - id: MSI-001\n"
                "    current_state: live_wired\n"
                "    evidence_refs: []\n"
                "  - id: MSI-002\n"
                "    current_state: blocked\n"
                "    last_transition_at: 1000\n"
                "  - id: MSI-003\n"
                "    current_state: merged_to_main\n",
                encoding="utf-8",
            )

            db_path = root / "process.db"
            db = ProcessIntelligenceDB(db_path)
            db.record_tracker_transition(
                {
                    "transition_id": "tx-1",
                    "item_id": "MSI-003",
                    "from_state": "pr_open",
                    "to_state": "merged_to_main",
                    "summary": "merged",
                    "run_id": None,
                    "decision_id": None,
                    "evidence_refs": ["docs/proof.md"],
                    "recorded_at": 2_000_000,
                    "metadata": {},
                }
            )
            db.close()

            watcher_state = root / "watcher-state"
            review_dir = watcher_state / "review-packets"
            review_dir.mkdir(parents=True)
            for stamp in (1_700_000_000.0, 1_700_000_100.0):
                (review_dir / f"ask-storm-{int(stamp)}.json").write_text(
                    json.dumps(
                        {
                            "watcher": "ask-storm",
                            "status": "storm",
                            "recorded_at": stamp,
                        }
                    ),
                    encoding="utf-8",
                )

            scanner = LifeOSPatternScanner(PatternStateStore(watcher_state))
            findings = scanner.run_all(
                tracker_path=tracker_path,
                process_db_path=db_path,
                watcher_state_dir=watcher_state,
                now=1_700_000_200.0,
                cooldown_seconds=3600,
            )
            self.assertEqual(len(findings), 4)
            by_name = {finding.scanner: finding for finding in findings}
            self.assertEqual(by_name["state-overclaim"].status, "detected")
            self.assertEqual(by_name["stale-gap"].status, "detected")
            self.assertEqual(by_name["ask-storm-pattern"].status, "detected")
            self.assertEqual(by_name["missing-lineage"].status, "detected")
            self.assertTrue(all(finding.emitted for finding in findings))

            findings_again = scanner.run_all(
                tracker_path=tracker_path,
                process_db_path=db_path,
                watcher_state_dir=watcher_state,
                now=1_700_000_260.0,
                cooldown_seconds=3600,
            )
            self.assertTrue(all(not finding.emitted for finding in findings_again))


if __name__ == "__main__":
    unittest.main()
