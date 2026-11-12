"""Keep the scraper's daily output on the `data` branch instead of `main`.

`main` is protected (changes need a pull request), so the daily workflow cannot push there. It restores the
previous run's output from `data` before scraping and publishes the new output to `data` afterwards. The site is
built from the runner's working tree: code and hand-edited data from `main`, scraper output from `data`.

Usage (GitHub Actions):
    python -m scraper.databranch restore    before scraping
    python -m scraper.databranch publish    after scraping

Only the paths in GENERATED live on `data`. Every other file in data/ is edited by hand through pull requests
and always comes from `main`. The copies of GENERATED files on `main` are a seed, used once to start the branch.
"""
from __future__ import annotations

import datetime as dt
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
REMOTE = "origin"
BRANCH = "data"
# Everything scraper/run.py writes, relative to data/. tests/test_databranch.py fails if run.py saves a file
# that is missing here, because a file left out would be thrown away at the end of every run.
GENERATED = [
    "history",
    "changes.json",
    "currency.json",
    "deal-of-the-day.json",
    "deals.json",
    "fx.json",
    "listings.json",
    "meta.json",
    "model-seen.json",
    "models.json",
    "new-prices.json",
    "newsletter.json",
    "rebates.json",
    "state.json",
]
BOT = {"GIT_AUTHOR_NAME": "usedglass-bot", "GIT_COMMITTER_NAME": "usedglass-bot",
       "GIT_AUTHOR_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com",
       "GIT_COMMITTER_EMAIL": "41898282+github-actions[bot]@users.noreply.github.com"}


def git(root: Path, *args: str, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, env={**os.environ, **(env or {})},
                          text=True, capture_output=True, check=check)


def fetch(root: Path) -> str | None:
    """Update the local copy of the data branch. Returns its commit, or None when the branch does not exist yet."""
    ref = f"refs/remotes/{REMOTE}/{BRANCH}"
    found = git(root, "ls-remote", "--exit-code", "--heads", REMOTE, f"refs/heads/{BRANCH}", check=False)
    if found.returncode == 2:  # the remote answered and has no such branch
        return None
    if found.returncode != 0:  # network or auth failure: stop, never mistake it for "no branch yet"
        raise RuntimeError(f"could not reach {REMOTE}: {found.stderr.strip()}")
    git(root, "fetch", "--quiet", REMOTE, f"+refs/heads/{BRANCH}:{ref}")
    return git(root, "rev-parse", ref).stdout.strip()


def restore(root: Path = ROOT) -> bool:
    """Put the last published scraper output into data/. Returns False when there is no data branch yet."""
    tip = fetch(root)
    if tip is None:
        print(f"No '{BRANCH}' branch yet: starting from the seed data on main")
        return False
    for name in GENERATED:
        path = f"data/{name}"
        if git(root, "cat-file", "-e", f"{tip}:{path}", check=False).returncode == 0:
            git(root, "restore", f"--source={tip}", "--worktree", "--", path)
    print(f"Restored scraper output from {BRANCH} @ {tip[:9]}")
    return True


def snapshot(root: Path, parent: str | None, message: str) -> str | None:
    """Commit the GENERATED files in the working tree on top of `parent`. Returns None when nothing changed."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**BOT, "GIT_INDEX_FILE": str(Path(tmp) / "index")}
        present = [f"data/{n}" for n in GENERATED if (root / "data" / n).exists()]
        git(root, "add", "--force", "--", *present, env=env)
        tree = git(root, "write-tree", env=env).stdout.strip()
        if parent and tree == git(root, "rev-parse", f"{parent}^{{tree}}").stdout.strip():
            return None
        args = ["commit-tree", tree, "-m", message] + (["-p", parent] if parent else [])
        return git(root, *args, env=env).stdout.strip()


def publish(root: Path = ROOT, attempts: int = 3) -> str | None:
    """Push the scraper output in data/ to the data branch. Returns the new commit, or None when nothing changed."""
    today = dt.datetime.now(ZoneInfo("America/Edmonton")).date().isoformat()
    err = ""
    for _ in range(attempts):
        parent = fetch(root)
        commit = snapshot(root, parent, f"data: daily update {today}")
        if commit is None:
            print("No data changes")
            return None
        # Fast-forward only. If another run published since the fetch, the push is rejected and we go round
        # again on top of its commit. This run's output is the newest, so its snapshot replaces the older one.
        push = git(root, "push", "--quiet", REMOTE, f"{commit}:refs/heads/{BRANCH}", check=False)
        if push.returncode == 0:
            git(root, "update-ref", f"refs/remotes/{REMOTE}/{BRANCH}", commit)
            print(f"Published scraper output to {BRANCH} @ {commit[:9]}")
            return commit
        err = push.stderr.strip()
        print(f"Push to {BRANCH} rejected, retrying: {err}", file=sys.stderr)
    raise RuntimeError(f"could not push to {BRANCH} after {attempts} attempts: {err}")


def main(argv: list[str]) -> int:
    if argv == ["restore"]:
        restore()
    elif argv == ["publish"]:
        publish()
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
