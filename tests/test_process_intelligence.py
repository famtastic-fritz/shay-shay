import sqlite3
import unittest

from process_intelligence import ProcessIntelligenceDB, ProcessIntelligenceRecorder
from process_tracker import ProcessTracker, TrackerTransitionError


class ProcessIntelligenceRecorderTest(unittest.TestCase):
    def test_records_run_tool_artifact_and_validation(self):
        with self.subTest("runtime"):
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as tmpdir:
                db_path = Path(tmpdir) / "process_intelligence.db"
                db = ProcessIntelligenceDB(db_path)
                recorder = ProcessIntelligenceRecorder(db, enabled=True)

                run_id = recorder.start_run(
                    session_id="sess-1",
                    parent_session_id="parent-1",
                    task_id="task-1",
                    platform="cli",
                    user_id="user-1",
                    chat_id="chat-1",
                    thread_id="thread-1",
                    model="gpt-test",
                    provider="openai",
                    base_url="https://example.invalid",
                    user_message="Run pytest and update /tmp/out.txt with token sk-secret-123456789012",
                    history_count=2,
                    max_iterations=10,
                )
                self.assertTrue(run_id)

                recorder.record_tool_outcome(
                    tool_name="terminal",
                    args={"command": "pytest tests/test_demo.py", "workdir": "/tmp/demo"},
                    result="1 passed in 0.12s\nreport at /tmp/demo/report.txt",
                    tool_call_id="tool-1",
                    duration_ms=120,
                )
                decision_id = recorder.record_decision(
                    decision_type="architecture",
                    summary="Treat the terminal run as proof for tracker promotion",
                    rationale="pytest passed and report file was written",
                    evidence_refs=["/tmp/demo/report.txt"],
                    artifact_refs=["/tmp/demo/report.txt"],
                    blocker_item_id="MSI-031",
                    lane_id="process-intelligence",
                )
                recorder.record_tool_outcome(
                    tool_name="write_file",
                    args={"path": "/tmp/out.txt", "content": "api_key=shhh"},
                    result="Wrote /tmp/out.txt",
                    tool_call_id="tool-2",
                    duration_ms=20,
                )
                tracker_path = Path(tmpdir) / "tracker.yaml"
                tracker_path.write_text(
                    "items:\n"
                    "  - id: MSI-031\n"
                    "    current_state: pr_ready\n",
                    encoding="utf-8",
                )
                tracker = ProcessTracker(tracker_path, db=db)
                tracker.transition_item(
                    "MSI-031",
                    "live_wired",
                    summary="Promotion backed by test evidence",
                    evidence_refs=["/tmp/demo/report.txt"],
                    run_id=run_id,
                    decision_id=decision_id,
                )
                recorder.persist_snapshot(message_count=4, tool_call_count=2)
                recorder.finish_run(
                    result={
                        "final_response": "done",
                        "api_calls": 3,
                        "completed": True,
                        "interrupted": False,
                        "turn_exit_reason": "assistant_response",
                        "input_tokens": 11,
                        "output_tokens": 22,
                        "total_tokens": 33,
                        "estimated_cost_usd": 0.01,
                        "provider": "openai",
                        "base_url": "https://example.invalid",
                        "response_previewed": False,
                        "partial": False,
                    },
                    message_count=5,
                    tool_call_count=2,
                )

                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row

                run = conn.execute("SELECT * FROM run_ledger WHERE run_id = ?", (run_id,)).fetchone()
                self.assertIsNotNone(run)
                self.assertEqual(run["outcome"], "completed")
                self.assertEqual(run["status"], "finished")
                self.assertEqual(run["tool_call_count"], 2)

                tool_rows = conn.execute(
                    "SELECT * FROM tool_agent_ledger WHERE run_id = ? ORDER BY tool_name", (run_id,)
                ).fetchall()
                self.assertEqual(len(tool_rows), 2)

                artifact_rows = conn.execute(
                    "SELECT * FROM artifact_ledger WHERE run_id = ? ORDER BY path", (run_id,)
                ).fetchall()
                self.assertTrue(any(row["path"] == "/tmp/out.txt" for row in artifact_rows))
                self.assertTrue(any(row["path"] == "/tmp/demo/report.txt" for row in artifact_rows))

                validation_rows = conn.execute(
                    "SELECT * FROM validation_ledger WHERE run_id = ?", (run_id,)
                ).fetchall()
                self.assertEqual(len(validation_rows), 1)
                self.assertEqual(validation_rows[0]["validator"], "terminal")

                decision_rows = conn.execute(
                    "SELECT * FROM decision_ledger WHERE run_id = ? ORDER BY recorded_at ASC", (run_id,)
                ).fetchall()
                self.assertEqual(len(decision_rows), 1)
                self.assertEqual(decision_rows[0]["blocker_item_id"], "MSI-031")

                tracker_rows = conn.execute(
                    "SELECT * FROM tracker_transition_ledger WHERE item_id = ?", ("MSI-031",)
                ).fetchall()
                self.assertEqual(len(tracker_rows), 1)
                self.assertEqual(tracker_rows[0]["to_state"], "live_wired")

                timeline = db.get_run_timeline(run_id)
                self.assertTrue(any(item["kind"] == "tool" for item in timeline))
                self.assertTrue(any(item["kind"] == "artifact" for item in timeline))
                self.assertTrue(any(item["kind"] == "validation" for item in timeline))
                self.assertTrue(any(item["kind"] == "decision" for item in timeline))
                self.assertEqual(db.get_run_decisions(run_id)[0]["decision_id"], decision_id)
                self.assertEqual(db.get_item_blockers("MSI-031")[0]["decision_id"], decision_id)
                self.assertEqual(db.get_tracker_transitions("MSI-031")[0]["decision_id"], decision_id)

                runs = db.list_runs(limit=5)
                self.assertTrue(runs)
                self.assertEqual(runs[0]["run_id"], run_id)

                db.close()

    def test_tracker_rejects_live_promotion_without_evidence(self):
        with self.subTest("tracker"):
            import tempfile
            from pathlib import Path

            with tempfile.TemporaryDirectory() as tmpdir:
                tracker_path = Path(tmpdir) / "tracker.yaml"
                tracker_path.write_text(
                    "items:\n"
                    "  - id: MSI-031\n"
                    "    current_state: pr_ready\n",
                    encoding="utf-8",
                )
                tracker = ProcessTracker(tracker_path)
                with self.assertRaises(TrackerTransitionError):
                    tracker.transition_item(
                        "MSI-031",
                        "live_wired",
                        summary="No proof attached",
                        evidence_refs=[],
                    )


if __name__ == "__main__":
    unittest.main()
