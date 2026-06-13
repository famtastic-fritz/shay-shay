import sqlite3
import unittest

from process_intelligence import ProcessIntelligenceDB, ProcessIntelligenceRecorder


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
                recorder.record_tool_outcome(
                    tool_name="write_file",
                    args={"path": "/tmp/out.txt", "content": "api_key=shhh"},
                    result="Wrote /tmp/out.txt",
                    tool_call_id="tool-2",
                    duration_ms=20,
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

                timeline = db.get_run_timeline(run_id)
                self.assertTrue(any(item["kind"] == "tool" for item in timeline))
                self.assertTrue(any(item["kind"] == "artifact" for item in timeline))
                self.assertTrue(any(item["kind"] == "validation" for item in timeline))

                runs = db.list_runs(limit=5)
                self.assertTrue(runs)
                self.assertEqual(runs[0]["run_id"], run_id)

                db.close()


if __name__ == "__main__":
    unittest.main()
