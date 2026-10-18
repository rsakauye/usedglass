"""Scrape-failure alerting: open, update or close one GitHub issue from data/meta.json.

Usage (GitHub Actions):  python -m scraper.alert
Needs GITHUB_TOKEN (issues: write) and GITHUB_REPOSITORY. Without a token it only prints the report,
so local runs are safe. Exit code is always 0 so a GitHub API hiccup never fails the daily build.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

DATA = Path(os.environ.get("USEDGLASS_DATA", Path(__file__).resolve().parent.parent / "data"))
LABEL = "scrape-alert"
MARKER = "<!-- usedglass-scrape-alert -->"
TITLE = "Scraper alert: dealer feed failing"


def problems(meta: dict) -> list[dict]:
    """Dealers that errored, returned 0 listings, or collapsed vs. the previous run. Skipped feeds are ignored."""
    out = []
    for k, d in (meta.get("dealers") or {}).items():
        status = d.get("status", "")
        if status.startswith("skipped"):
            continue
        if status != "ok":
            out.append({"dealer": k, "problem": (meta.get("errors") or {}).get(k) or status,
                        "detail": status})
        elif d.get("count", 0) == 0:
            out.append({"dealer": k, "problem": "0 listings", "detail": status})
        elif d.get("warning"):
            out.append({"dealer": k, "problem": d["warning"], "detail": "partial result"})
    return out


def report(meta: dict, probs: list[dict]) -> str:
    info = meta.get("dealer_info") or {}
    run = os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/" + os.environ.get("GITHUB_REPOSITORY", "") \
        + "/actions/runs/" + os.environ.get("GITHUB_RUN_ID", "") if os.environ.get("GITHUB_RUN_ID") else ""
    lines = [f"**Run {meta.get('date')}** ({meta.get('run_at')} UTC){f' · [workflow log]({run})' if run else ''}", ""]
    if probs:
        lines += ["| Dealer | Problem |", "|---|---|"]
        for p in probs:
            name = (info.get(p["dealer"]) or {}).get("name", p["dealer"])
            lines.append(f"| {name} (`{p['dealer']}`) | {p['problem'].replace('|', '/')[:300]} |")
        lines += ["", "Errored dealers keep yesterday's listings (marked stale) so the site stays up. "
                      "Check whether the store changed its layout, URL or robots.txt."]
    else:
        lines.append("All dealer feeds are healthy again.")
    ok = sum(1 for d in (meta.get("dealers") or {}).values() if d.get("status") == "ok")
    lines += ["", f"{ok} feeds ok · {meta.get('total', '?')} listings total"]
    return "\n".join(lines)


def _api(method: str, path: str, token: str, body: dict | None = None):
    url = f"{os.environ.get('GITHUB_API_URL', 'https://api.github.com')}{path}"
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "usedglass-alert"})
    with urllib.request.urlopen(req, timeout=30) as r:
        txt = r.read()
    return json.loads(txt) if txt else None


def main() -> int:
    meta = json.loads((DATA / "meta.json").read_text())
    probs = problems(meta)
    if os.environ.get("SCRAPE_OUTCOME") == "failure":
        probs.insert(0, {"dealer": "pipeline", "problem": "scrape step failed (every dealer errored or the run crashed); "
                                                          "see the workflow log", "detail": "failure"})
    text = report(meta, probs)
    print(text)
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        print("(no GITHUB_TOKEN/GITHUB_REPOSITORY: not touching issues)")
        return 0
    try:
        try:
            _api("POST", f"/repos/{repo}/labels", token, {"name": LABEL, "color": "d73a4a",
                                                          "description": "Automatic: a dealer scraper is failing"})
        except urllib.error.HTTPError as e:
            if e.code != 422:  # 422 = label already exists
                raise
        open_issues = _api("GET", f"/repos/{repo}/issues?state=open&labels={LABEL}&per_page=20", token) or []
        issue = next((i for i in open_issues if MARKER in (i.get("body") or "") and "pull_request" not in i), None)
        if probs:
            names = ", ".join(p["dealer"] for p in probs)
            body = f"{MARKER}\n{text}\n\n_This issue updates itself after each daily run and closes when every feed recovers._"
            if issue:
                _api("PATCH", f"/repos/{repo}/issues/{issue['number']}", token, {"body": body, "title": f"{TITLE}: {names}"})
                _api("POST", f"/repos/{repo}/issues/{issue['number']}/comments", token, {"body": text})
                print(f"updated issue #{issue['number']}")
            else:
                new = _api("POST", f"/repos/{repo}/issues", token, {"title": f"{TITLE}: {names}", "body": body, "labels": [LABEL]})
                print(f"opened issue #{new['number']}")
        elif issue:
            _api("POST", f"/repos/{repo}/issues/{issue['number']}/comments", token, {"body": text})
            _api("PATCH", f"/repos/{repo}/issues/{issue['number']}", token, {"state": "closed", "state_reason": "completed"})
            print(f"closed issue #{issue['number']}")
    except Exception as e:  # never fail the build because of the alert itself
        print(f"alert: GitHub API error: {type(e).__name__}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
