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

    def test_no_manual_review_module(self):
        self.assertFalse(hasattr(update, 'verified_milestones'))

    def test_compacted_api_scans_do_not_duplicate_matrix_data(self):
        rows = [{"repo": "a/b", "api_scan": {
            "status": "ok", "files_scanned": 2,
            "symbols": {"XMemAlloc": {"status": "definition_candidate"}}
        }}]
        update.compact_api_scans(rows)
        self.assertEqual(rows[0]["api_scan"]["symbols_found"], 1)
        self.assertEqual(rows[0]["api_scan"]["files_scanned"], 2)
        self.assertNotIn("symbols", rows[0]["api_scan"])

    def test_readme_table_does_not_infer_progress(self):
        txt = update.render_readme_table([{"repo": "foo/bar", "name": "Foo", "commits_30d": 42}], "2026-11-22T00:00:00Z")
        self.assertIn("not** game compatibility", txt)
        self.assertNotIn("42%", txt)
        self.assertIn("Published metrics", txt)
        self.assertNotIn("Unreviewed", txt)


if __name__ == "__main__":
    unittest.main()
