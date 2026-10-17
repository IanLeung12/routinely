#!/usr/bin/env python3
"""Home-made merge queue (GitHub's merge queue needs an org-owned repo).

`main` requires PR branches to be up to date before merging, so two green PRs can't
combine into a broken `main`. This script, run every ~2 min from cron on the host, keeps
that moving without workers waiting on each other:

  * If any auto-merge PR has CI running, wait (one PR is "in flight" at a time).
  * Otherwise update the oldest auto-merge PR that is BEHIND main (its CI re-runs on
    top of the latest main, then GitHub auto-merges it).
  * A PR that can't be updated because of a conflict goes back to the board:
    its task is set to todo with a note, keeping `pr:`, so the next worker fixes it.

  python3 scripts/mergeq.py          one pass (prints only when it acts)
  python3 scripts/mergeq.py --dry    show what it would do
"""
import json, os, re, subprocess, sys

DRY = "--dry" in sys.argv
ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
STATE = os.path.join(ROOT, ".mergeq-state.json")


def gh(*args):
    r = subprocess.run(["gh", *args], cwd=ROOT, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def checks_state(pr):
    cs = pr.get("statusCheckRollup") or []
    if not cs:
        return "none"
    vals = {(c.get("conclusion") or c.get("status") or "").upper() for c in cs}
    if vals & {"FAILURE", "ERROR", "TIMED_OUT", "STARTUP_FAILURE"}:
        return "failing"
    if vals & {"IN_PROGRESS", "QUEUED", "PENDING", "WAITING", "REQUESTED", ""}:
        return "running"
    return "green"


def task_id(pr):
    m = re.match(r"(T\d+)\b", pr["title"])
    return m.group(1) if m else None


def requeue(pr, why):
    tid = task_id(pr)
    if not tid:
        return
    subprocess.run([sys.executable, "scripts/tasks.py", "set", tid, "status=todo", "owner=—", "claimed=—",
                    f"note={why}", "--agent", "mergeq"], cwd=ROOT, capture_output=True, text=True)


def main():
    rc, out, err = gh("pr", "list", "--state", "open", "-L", "100", "--json",
                      "number,title,mergeStateStatus,autoMergeRequest,statusCheckRollup,isDraft")
    if rc:
        sys.exit("gh pr list failed: " + err.strip())
    prs = [p for p in json.loads(out or "[]") if p.get("autoMergeRequest") and not p.get("isDraft")]
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"conflicts": []}

    for p in prs:
        if p["mergeStateStatus"] == "DIRTY" and p["number"] not in state["conflicts"]:
            msg = f"merge conflict with main on PR #{p['number']}: check out its branch, merge origin/main, fix, push"
            print(f"#{p['number']} has conflicts -> {task_id(p) or '?'} back to todo")
            if not DRY:
                requeue(p, msg)
                gh("pr", "comment", str(p["number"]), "--body", f"mergeq: {msg}.")
                state["conflicts"].append(p["number"])
    state["conflicts"] = [n for n in state["conflicts"] if any(p["number"] == n and p["mergeStateStatus"] == "DIRTY" for p in prs)]

    if any(checks_state(p) == "running" for p in prs):
        pass  # something is in flight; let it finish
    else:
        behind = sorted((p for p in prs if p["mergeStateStatus"] == "BEHIND" and checks_state(p) != "failing"),
                        key=lambda p: p["number"])
        if behind:
            p = behind[0]
            print(f"updating #{p['number']} {p['title']} onto main ({len(behind) - 1} more waiting)")
            if not DRY:
                rc, _, err = gh("pr", "update-branch", str(p["number"]))
                if rc:
                    print(f"  update failed: {err.strip()[:200]}")
    if not DRY:
        with open(STATE, "w") as fh:
            json.dump(state, fh)


if __name__ == "__main__":
    main()
