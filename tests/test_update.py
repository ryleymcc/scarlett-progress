import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update


class TrackerTests(unittest.TestCase):
    def test_projects_validate(self):
        projects = update.load_json(update.ROOT / "projects.json")
        update.valid_projects(projects)
        self.assertGreaterEqual(len(projects), 1)
        self.assertTrue(any(p.get("branch") == "xbox-series" for p in projects))

    def test_reject_old_console_only(self):
        with self.assertRaises(ValueError):
            update.valid_projects([{"repo": "foo/bar", "scope": "Xbox 360"}])

    def test_no_unsubstantiated_claims(self):
        evidence = update.load_json(update.ROOT / "data/milestones.json")
        for p in update.load_json(update.ROOT / "projects.json"):
            self.assertEqual(update.verified_milestones(evidence, p["repo"]), [])

    def test_milestone_needs_source(self):
        data = {"milestones": {"foo/bar": [{"milestone": "gta_vi_boot", "status": "claimed"}]}}
        with self.assertRaises(ValueError):
            update.verified_milestones(data, "foo/bar")

    def test_readme_table_does_not_infer_progress(self):
        txt = update.render_readme_table([{"repo": "foo/bar", "name": "Foo", "commits_30d": 42}], "2026-11-22T00:00:00Z")
        self.assertIn("not** game compatibility", txt)
        self.assertNotIn("42%", txt)


if __name__ == "__main__":
    unittest.main()
