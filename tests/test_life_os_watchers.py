import json
import tempfile
import unittest
from pathlib import Path

from life_os_watchers import LifeOSWatchers, WatcherStateStore


class LifeOSWatchersTest(unittest.TestCase):
    def test_run_all_emits_review_packets_and_dedupes_with_cooldown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            shay_home = root / ".shay"
            (shay_home / "cron").mkdir(parents=True)
            (shay_home / "cron" / "jobs.json").write_text(
                json.dumps({"jobs": [{"id": "a", "enabled": False}, {"id": "b", "enabled": False}]}),
                encoding="utf-8",
            )
            events_path = shay_home / "events.jsonl"
            now = 1_700_000_000.0
            events = [
                {"kind": "daily_brief", "ts": now - 100},
                {"kind": "daily_brief", "ts": now - 200},
                {"kind": "daily_brief", "ts": now - 300},
            ]
            events_path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

            asks_dir = root / "asks"
            asks_dir.mkdir()
            for i in range(4):
                (asks_dir / f"ask-{i}.json").write_text("{}", encoding="utf-8")

            obsidian_root = root / "obsidian" / "Shay-Memory"
            episodic_dir = obsidian_root / "reflections" / "episodic"
            episodic_dir.mkdir(parents=True)
            episodic = episodic_dir / "today.md"
            episodic.write_text("reflection", encoding="utf-8")
            lessons_dir = obsidian_root / "lessons-mirror"
            lessons_dir.mkdir(parents=True)
            lessons = lessons_dir / "mirror.md"
            lessons.write_text("lesson", encoding="utf-8")

            external_log = root / ".famtastic-intel-loop.log"
            external_log.write_text("ok", encoding="utf-8")

            for path in (episodic, lessons, external_log):
                path.touch()

            store = WatcherStateStore(shay_home / "watcher-state")
            watchers = LifeOSWatchers(store)
            observations = watchers.run_all(
                shay_home=shay_home,
                obsidian_root=obsidian_root,
                asks_dir=asks_dir,
                now=now,
                cooldown_seconds=1800,
            )
            self.assertEqual(len(observations), 5)
            self.assertTrue(all(obs.emitted for obs in observations))
            ask_storm = next(obs for obs in observations if obs.watcher == "ask-storm")
            self.assertEqual(ask_storm.status, "storm")
            packets = list((shay_home / "watcher-state" / "review-packets").glob("*.json"))
            self.assertEqual(len(packets), 5)

            observations_again = watchers.run_all(
                shay_home=shay_home,
                obsidian_root=obsidian_root,
                asks_dir=asks_dir,
                now=now + 60,
                cooldown_seconds=1800,
            )
            self.assertTrue(all(not obs.emitted for obs in observations_again))


if __name__ == "__main__":
    unittest.main()
