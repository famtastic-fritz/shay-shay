#!/usr/bin/env python3
"""Tests for community gap-discovery (D4):

  - SkillNetSource.search() against a mocked hosted API (carries 5-D evaluation)
  - skill_manage(action="discover") is read-only and never installs
  - GapResolver verdicts: ADOPT / REVIEW / BUILD
"""

import json
import unittest
from unittest.mock import patch

from tools.skills_hub import SkillNetSource, SkillMeta


class _MockResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data


_SKILLNET_PAYLOAD = {
    "data": [
        {
            "skill_name": "pdf-extractor",
            "skill_description": "Extract text and tables from PDF files",
            "author": "someuser",
            "stars": 120,
            "skill_url": "https://github.com/someuser/skills/blob/main/pdf-extractor/SKILL.md",
            "category": "documents",
            "evaluation": {
                "safety": {"level": "high", "reason": "no network, no exec"},
                "completeness": {"level": "high", "reason": "covers tables"},
                "executability": {"level": "good", "reason": "runs clean"},
                "maintainability": {"level": "medium", "reason": "single author"},
                "cost": {"level": "high", "reason": "local only"},
            },
        }
    ]
}


class TestSkillNetSource(unittest.TestCase):
    def setUp(self):
        self.src = SkillNetSource()
        self._safe = patch("tools.skills_hub.is_safe_url", return_value=True)
        self._policy = patch("tools.skills_hub.check_website_access", return_value=None)
        self._safe.start()
        self._policy.start()

    def tearDown(self):
        self._policy.stop()
        self._safe.stop()

    def test_blob_url_maps_to_github_identifier(self):
        ident = SkillNetSource._blob_to_identifier(
            "https://github.com/owner/repo/blob/main/skills/foo/SKILL.md"
        )
        self.assertEqual(ident, "owner/repo/skills/foo")

    @patch("tools.skills_hub._write_index_cache")
    @patch("tools.skills_hub._read_index_cache", return_value=None)
    @patch("tools.skills_hub.httpx.get")
    def test_search_parses_results_and_preserves_evaluation(
        self, mock_get, _read, _write
    ):
        mock_get.return_value = _MockResponse(200, _SKILLNET_PAYLOAD)
        results = self.src.search("pdf", limit=5)
        self.assertEqual(len(results), 1)
        meta = results[0]
        self.assertEqual(meta.source, "skillnet")
        self.assertEqual(meta.identifier, "someuser/skills/pdf-extractor")
        self.assertEqual(meta.trust_level, "community")
        # The 5-D evaluation must survive into extra for verdict scoring.
        self.assertIn("evaluation", meta.extra)
        self.assertEqual(meta.extra["evaluation"]["safety"]["level"], "high")

    @patch("tools.skills_hub._read_index_cache", return_value=None)
    @patch("tools.skills_hub.httpx.get")
    def test_search_handles_non_200(self, mock_get, _read):
        mock_get.return_value = _MockResponse(503, None)
        self.assertEqual(self.src.search("pdf", limit=5), [])

    def test_empty_query_returns_empty(self):
        self.assertEqual(self.src.search("   ", limit=5), [])


class TestDiscoverActionReadOnly(unittest.TestCase):
    @patch("tools.gap_resolver.discover")
    def test_skill_manage_discover_is_read_only(self, mock_discover):
        mock_discover.return_value = [
            {"name": "pdf-extractor", "source": "skillnet", "score": 0.9, "verdict": "ADOPT"}
        ]
        from tools.skill_manager_tool import skill_manage

        # No `name` arg — discover must not require it (unlike create/patch/etc).
        out = json.loads(skill_manage(action="discover", query="extract pdf tables"))
        self.assertTrue(out["success"])
        self.assertEqual(out["action"], "discover")
        self.assertEqual(out["count"], 1)
        self.assertIn("No skill was installed", out["note"])
        mock_discover.assert_called_once()

    def test_discover_requires_query(self):
        from tools.skill_manager_tool import skill_manage

        out = json.loads(skill_manage(action="discover"))
        self.assertFalse(out["success"])
        self.assertIn("query is required", out["error"])


class TestGapResolverVerdicts(unittest.TestCase):
    def _meta(self, name, source, evaluation=None, desc=""):
        return SkillMeta(
            name=name,
            description=desc,
            source=source,
            identifier=f"{source}/{name}",
            trust_level="community",
            extra={"evaluation": evaluation} if evaluation else {},
        )

    def test_adopt_for_strong_evaluated_match(self):
        from tools.gap_resolver import GapResolver

        strong_eval = {
            d: {"level": "high"} for d in
            ["safety", "completeness", "executability", "maintainability", "cost"]
        }
        meta = self._meta("pdf-table-extractor", "skillnet", strong_eval,
                          desc="extract pdf table data")
        with patch("tools.gap_resolver.discover") as mock_disc:
            # Use the real scorer to produce the candidate dict.
            from tools.gap_resolver import _candidate_dict
            mock_disc.return_value = [_candidate_dict("pdf table extractor", meta)]
            res = GapResolver().resolve({"capability": "pdf table extractor"})
        self.assertEqual(res["verdict"], "ADOPT")
        self.assertIsNotNone(res["chosen"])

    def test_review_for_plausible_but_weak(self):
        from tools.gap_resolver import GapResolver, _candidate_dict

        # clawhub, no evaluation, partial name overlap -> mid score -> REVIEW
        meta = self._meta("calendar-sync", "clawhub", None,
                          desc="sync calendar events")
        with patch("tools.gap_resolver.discover") as mock_disc:
            mock_disc.return_value = [_candidate_dict("calendar sync tool", meta)]
            res = GapResolver().resolve({"capability": "calendar sync tool"})
        self.assertIn(res["verdict"], ("REVIEW", "ADOPT"))

    def test_build_when_no_candidates(self):
        from tools.gap_resolver import GapResolver

        with patch("tools.gap_resolver.discover", return_value=[]):
            res = GapResolver().resolve({"capability": "totally novel capability xyz"})
        self.assertEqual(res["verdict"], "BUILD")
        self.assertIsNone(res["chosen"])

    def test_build_when_only_irrelevant_candidates(self):
        from tools.gap_resolver import GapResolver, _candidate_dict

        meta = self._meta("unrelated-thing", "clawhub", None, desc="nothing alike")
        with patch("tools.gap_resolver.discover") as mock_disc:
            mock_disc.return_value = [_candidate_dict("pdf table extraction", meta)]
            res = GapResolver().resolve({"capability": "pdf table extraction"})
        self.assertEqual(res["verdict"], "BUILD")


if __name__ == "__main__":
    unittest.main()
