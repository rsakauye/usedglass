import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from scraper import databranch

ROOT = Path(__file__).resolve().parent.parent


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True).stdout.strip()


class GeneratedListTests(unittest.TestCase):
    def test_every_scraper_output_is_listed(self):
        src = (ROOT / "scraper" / "run.py").read_text()
        saved = set(re.findall(r'save\(DATA / "([^"]+)"', src))
        self.assertGreater(len(saved), 10)
        self.assertEqual(saved - set(databranch.GENERATED), set())

    def test_hand_edited_files_are_not_listed(self):
        for name in ("events.json", "model-meta.json", "listing-overrides.json", "us-offers.json", "firmware.json"):
            self.assertNotIn(name, databranch.GENERATED)


class DataBranchTests(unittest.TestCase):
    """Runs restore/publish against a throwaway origin, the way two daily runs in a row would."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.origin = base / "origin.git"
        git(base, "init", "--quiet", "--bare", "--initial-branch=main", str(self.origin))
        seed = self.clone("seed")
        (seed / "data" / "history").mkdir(parents=True)
        self.write(seed, "listings.json", ["seed"])
        self.write(seed, "state.json", {"a": 1})
        self.write(seed, "history/2026-11-08.json", {"date": "2026-11-08"})
        self.write(seed, "events.json", ["by hand v1"])
        (seed / "README.md").write_text("code\n")
        self.commit_main(seed, "seed")

    def tearDown(self):
        self.tmp.cleanup()

    def clone(self, name):
        path = Path(self.tmp.name) / name
        git(self.tmp.name, "clone", "--quiet", str(self.origin), str(path))
        git(path, "config", "user.name", "t")
        git(path, "config", "user.email", "t@example.invalid")
        return path

    def write(self, repo, name, obj):
        (repo / "data" / name).write_text(json.dumps(obj) + "\n")

    def read(self, repo, name):
        return json.loads((repo / "data" / name).read_text())

    def commit_main(self, repo, msg):
        git(repo, "add", "-A")
        git(repo, "commit", "--quiet", "-m", msg)
        git(repo, "push", "--quiet", "origin", "HEAD:main")

    def test_first_run_creates_branch_and_second_run_restores_it(self):
        main_before = git(self.origin, "rev-parse", "main")

        # Run 1: no data branch yet.
        run1 = self.clone("run1")
        self.assertFalse(databranch.restore(run1))
        self.assertEqual(self.read(run1, "listings.json"), ["seed"])
        self.write(run1, "listings.json", ["day 1"])
        self.write(run1, "history/2026-11-12.json", {"date": "2026-11-12"})
        first = databranch.publish(run1)
        self.assertEqual(git(self.origin, "rev-parse", "data"), first)
        files = set(git(self.origin, "ls-tree", "-r", "--name-only", "data").splitlines())
        self.assertEqual(files, {"data/listings.json", "data/state.json",
                                 "data/history/2026-11-08.json", "data/history/2026-11-12.json"})

        # A hand-edited file changes on main between runs.
        edit = self.clone("edit")
        self.write(edit, "events.json", ["by hand v2"])
        self.commit_main(edit, "events")
        main_after_edit = git(self.origin, "rev-parse", "main")

        # Run 2: a fresh checkout of main gets yesterday's output back, and main's hand-edited file wins.
        run2 = self.clone("run2")
        self.assertEqual(self.read(run2, "listings.json"), ["seed"])
        self.assertTrue(databranch.restore(run2))
        self.assertEqual(self.read(run2, "listings.json"), ["day 1"])
        self.assertTrue((run2 / "data" / "history" / "2026-11-12.json").exists())
        self.assertEqual(self.read(run2, "events.json"), ["by hand v2"])

        # Nothing new scraped: no commit.
        self.assertIsNone(databranch.publish(run2))
        self.assertEqual(git(self.origin, "rev-parse", "data"), first)

        # New output: one commit on top of the first.
        self.write(run2, "listings.json", ["day 2"])
        second = databranch.publish(run2)
        self.assertEqual(git(self.origin, "rev-parse", "data^"), first)
        self.assertEqual(git(self.origin, "rev-parse", "data"), second)
        self.assertEqual(git(run2, "rev-parse", "origin/data"), second)

        # main is never written, and the working checkout stays on main.
        self.assertNotEqual(main_before, main_after_edit)
        self.assertEqual(git(self.origin, "rev-parse", "main"), main_after_edit)
        self.assertEqual(git(run2, "rev-parse", "--abbrev-ref", "HEAD"), "main")

    def test_newer_run_wins_when_another_run_published_first(self):
        a, b = self.clone("a"), self.clone("b")
        databranch.restore(a)
        databranch.restore(b)
        self.write(a, "listings.json", ["older run"])
        older = databranch.publish(a)
        self.write(b, "listings.json", ["newer run"])
        newer = databranch.publish(b)
        self.assertEqual(git(self.origin, "rev-parse", "data^"), older)
        self.assertEqual(git(self.origin, "show", "data:data/listings.json"), '["newer run"]')
        self.assertEqual(git(self.origin, "rev-parse", "data"), newer)

    def test_unreachable_remote_is_an_error_not_a_first_run(self):
        run = self.clone("run")
        git(run, "remote", "set-url", "origin", str(Path(self.tmp.name) / "missing.git"))
        with self.assertRaises(RuntimeError):
            databranch.restore(run)


if __name__ == "__main__":
    unittest.main()
