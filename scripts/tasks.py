#!/usr/bin/env python3
"""Task board CLI. TASKS.md lives on the `tasks` branch, checked out in ./.tasks.

Every write is: reset to origin/tasks -> apply change -> commit -> push.
A rejected push means someone else wrote first; we re-apply on the new tip.
That makes claims atomic: only one agent can flip a task from todo to claimed.

  tasks.py next  --class light              show best claimable task (no write)
  tasks.py auto  --class light --agent max  claim best task, print it
  tasks.py claim T004 --agent max
  tasks.py set   T004 status=in-review pr=#12 [--agent max]
  tasks.py show  T004
  tasks.py list  [--status todo]
  tasks.py stale [--minutes 90]             claimed tasks with no PR for too long
  tasks.py sync                             refresh ./.tasks from origin
  tasks.py commit -m "msg"                  commit+push manual edits in ./.tasks (orchestrator)
  tasks.py reconcile                        mark in-review tasks whose PR merged as done (uses gh)
  tasks.py archive [--keep 10]              move done tasks (except the newest N) to ARCHIVE.md
"""
import argparse, datetime as dt, os, re, subprocess, sys, time

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
WT = os.path.join(ROOT, ".tasks")
FILE = os.path.join(WT, "TASKS.md")
ARCHIVE = os.path.join(WT, "ARCHIVE.md")
CLASSES = ["light", "standard", "heavy"]
STATUSES = ["todo", "claimed", "in-review", "done", "blocked"]
HEAD = re.compile(r"^### (T\d+)\b")
FIELD = re.compile(r"^- (\w[\w-]*): ?(.*)$")


def git(*a, check=True, cwd=WT):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {' '.join(a)} failed:\n{r.stderr.strip()}")
    return r


def sync():
    git("fetch", "-q", "origin", "+tasks:refs/remotes/origin/tasks", cwd=ROOT)
    if not os.path.isdir(WT):
        git("worktree", "prune", cwd=ROOT)
        git("worktree", "add", "-q", "-f", "-B", "tasks", WT, "origin/tasks", cwd=ROOT)
    git("checkout", "-q", "-B", "tasks", "origin/tasks")
    git("reset", "-q", "--hard", "origin/tasks")


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def parse(text):
    """Return (lines, tasks). tasks: id -> {start, end, fields{name: line_idx}, vals}."""
    lines = text.split("\n")
    tasks, cur = {}, None
    for i, ln in enumerate(lines):
        m = HEAD.match(ln)
        if m or ln.startswith("## "):
            if cur:
                cur["end"] = i
            cur = None
        if m:
            cur = tasks[m.group(1)] = {"start": i, "end": len(lines), "fields": {}, "vals": {}}
            continue
        if cur:
            f = FIELD.match(ln)
            if f and f.group(1) not in cur["fields"]:
                cur["fields"][f.group(1)] = i
                cur["vals"][f.group(1)] = f.group(2).strip()
    return lines, tasks


def load():
    with open(FILE) as fh:
        return parse(fh.read())


def archived_ids():
    try:
        with open(ARCHIVE) as fh:
            return set(re.findall(r"^### (T\d+)", fh.read(), re.M))
    except OSError:
        return set()


def deps_of(t):
    d = t["vals"].get("deps", "")
    return re.findall(r"T\d+", d)


def claimable(tasks, cls):
    """Todo tasks whose deps are done and whose class <= cls. Exact class first, then lower."""
    rank = CLASSES.index(cls)
    archived = archived_ids()
    out = []
    for tid, t in tasks.items():
        v = t["vals"]
        if v.get("status") != "todo" or v.get("class") not in CLASSES:
            continue
        if CLASSES.index(v["class"]) > rank:
            continue
        if any(d not in archived and tasks.get(d, {}).get("vals", {}).get("status") != "done" for d in deps_of(t)):
            continue
        try:
            prio = int(v.get("priority", "2") or 2)
        except ValueError:
            prio = 2
        # P0 goes first for any eligible worker; otherwise exact class first, then priority.
        out.append((prio != 0, CLASSES.index(v["class"]) != rank, prio, int(tid[1:]), tid))
    return [x[-1] for x in sorted(out)]


def block(lines, t):
    return "\n".join(lines[t["start"]:t["end"]]).rstrip()


def write_txn(mutate, msg, tries=8):
    """mutate(lines, tasks) -> lines or raises SystemExit. Retries on push race."""
    for n in range(tries):
        sync()
        lines, tasks = load()
        new = mutate(lines, tasks)
        with open(FILE, "w") as fh:
            fh.write("\n".join(new))
        git("add", "TASKS.md")
        if not git("diff", "--cached", "--quiet", check=False).returncode:
            return
        git("commit", "-q", "-m", msg)
        if git("push", "-q", "origin", "tasks", check=False).returncode == 0:
            return
        time.sleep(1 + n)
    sys.exit("could not push to tasks branch after retries")


def set_fields(lines, t, kv):
    lines = list(lines)
    insert_at = max(t["fields"].values(), default=t["start"]) + 1
    for k, v in kv.items():
        if k in t["fields"]:
            lines[t["fields"][k]] = f"- {k}: {v}"
        else:
            lines.insert(insert_at, f"- {k}: {v}")
            insert_at += 1
    return lines


def do_claim(tid, agent, cls=None):
    def mut(lines, tasks):
        t = tasks.get(tid)
        if not t:
            sys.exit(f"{tid} not found")
        if t["vals"].get("status") != "todo":
            sys.exit(f"LOST: {tid} is {t['vals'].get('status')} ({t['vals'].get('owner')})")
        if cls and tid not in claimable(tasks, cls):
            sys.exit(f"{tid} is not claimable for class {cls}")
        return set_fields(lines, t, {"status": "claimed", "owner": agent, "claimed": now()})
    write_txn(mut, f"claim {tid} ({agent})")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("next", "auto"):
        s = sub.add_parser(name)
        s.add_argument("--class", dest="cls", required=True, choices=CLASSES)
        s.add_argument("--agent", required=(name == "auto"))
    s = sub.add_parser("claim"); s.add_argument("id"); s.add_argument("--agent", required=True)
    s = sub.add_parser("set"); s.add_argument("id"); s.add_argument("kv", nargs="+"); s.add_argument("--agent")
    s = sub.add_parser("show"); s.add_argument("id")
    s = sub.add_parser("list"); s.add_argument("--status"); s.add_argument("--long", action="store_true")
    s = sub.add_parser("stale"); s.add_argument("--minutes", type=int, default=90)
    sub.add_parser("sync")
    sub.add_parser("reconcile")
    s = sub.add_parser("archive"); s.add_argument("--keep", type=int, default=10)
    s = sub.add_parser("commit"); s.add_argument("-m", required=True)
    a = p.parse_args()

    if a.cmd == "commit":
        git("add", "-A")
        if git("diff", "--cached", "--quiet", check=False).returncode:
            git("commit", "-q", "-m", a.m)
        for _ in range(5):
            if git("push", "-q", "origin", "tasks", check=False).returncode == 0:
                return print("pushed")
            if git("pull", "-q", "--rebase", "origin", "tasks", check=False).returncode:
                git("rebase", "--abort", check=False)
                sys.exit("rebase conflict: run `tasks.py sync`, redo your edit, commit again")
        sys.exit("push failed")

    sync()
    lines, tasks = load()

    if a.cmd == "sync":
        return print(f"tasks @ {git('rev-parse', '--short', 'HEAD').stdout.strip()}")
    if a.cmd == "show":
        return print(block(lines, tasks[a.id]) if a.id in tasks else f"{a.id} not found")
    if a.cmd == "list":
        for tid, t in tasks.items():
            v = t["vals"]
            if a.status and v.get("status") != a.status:
                continue
            title = lines[t["start"]].split(" ", 2)[-1]
            if a.long:
                print(f"{tid:5} {v.get('status',''):9} {v.get('class',''):8} {v.get('owner','') or '-':12} "
                      f"P{v.get('priority', '2') or '2'} {v.get('kind', '-') or '-':11} {title}")
            else:
                print(f"{tid:5} {v.get('status',''):9} {v.get('class',''):8} {v.get('owner','') or '-':12} {title}")
        return
    if a.cmd == "stale":
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=a.minutes)
        for tid, t in tasks.items():
            v = t["vals"]
            if v.get("status") != "claimed" or v.get("pr", "-") not in ("", "-", "—"):
                continue
            try:
                c = dt.datetime.strptime(v.get("claimed", ""), "%Y-%m-%dT%H:%MZ").replace(tzinfo=dt.timezone.utc)
            except ValueError:
                c = None
            if c is None or c < cutoff:
                print(f"{tid} {v.get('owner')} claimed {v.get('claimed')}")
        return
    if a.cmd == "next":
        c = claimable(tasks, a.cls)
        return print(block(lines, tasks[c[0]]) if c else "NO_TASK")
    if a.cmd == "auto":
        for _ in range(5):
            lines, tasks = load()
            c = claimable(tasks, a.cls)
            if not c:
                return print("NO_TASK")
            r = subprocess.run([sys.executable, __file__, "claim", c[0], "--agent", a.agent], capture_output=True, text=True)
            sync()
            if r.returncode == 0:
                lines, tasks = load()
                return print(block(lines, tasks[c[0]]))
        return print("NO_TASK")
    if a.cmd == "reconcile":
        import json
        r = subprocess.run(["gh", "pr", "list", "--state", "merged", "-L", "200", "--json", "number"],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            sys.exit("gh pr list failed: " + r.stderr.strip())
        merged = {f"#{p['number']}" for p in json.loads(r.stdout or "[]")}
        fixed = []

        def mut(lines, tasks):
            fixed.clear()
            for tid, t in tasks.items():
                v = t["vals"]
                if v.get("status") == "in-review" and v.get("pr", "").strip() in merged:
                    lines = set_fields(lines, t, {"status": "done"})
                    fixed.append(tid)
            return lines
        write_txn(mut, "reconcile: merged PRs -> done")
        return print("done: " + " ".join(fixed) if fixed else "nothing to reconcile")
    if a.cmd == "archive":
        moved = []

        def mut(lines, tasks):
            moved.clear()
            done = sorted((int(t[1:]), t) for t, v in tasks.items() if v["vals"].get("status") == "done")
            go = [t for _, t in done[:max(0, len(done) - a.keep)]]
            if not go:
                return lines
            drop = set()
            blocks = []
            for t in go:
                b = tasks[t]
                blocks.append("\n".join(lines[b["start"]:b["end"]]).rstrip() + "\n")
                drop.update(range(b["start"], b["end"]))
            old = open(ARCHIVE).read() if os.path.exists(ARCHIVE) else "# ARCHIVE\n\nDone tasks moved off the board by `tasks.py archive`. Read only when needed.\n"
            with open(ARCHIVE, "w") as fh:
                fh.write(old.rstrip() + "\n\n" + "\n".join(blocks))
            git("add", "ARCHIVE.md")
            moved.extend(go)
            return [ln for i, ln in enumerate(lines) if i not in drop]
        write_txn(mut, "archive done tasks")
        return print(f"archived {len(moved)}: {' '.join(moved)}" if moved else "nothing to archive")
    if a.cmd == "claim":
        do_claim(a.id, a.agent)
        return print(f"claimed {a.id}")
    if a.cmd == "set":
        kv = dict(x.split("=", 1) for x in a.kv)
        bad = kv.get("status")
        if bad and bad not in STATUSES:
            sys.exit(f"status must be one of {STATUSES}")
        def mut(lines, tasks):
            if a.id not in tasks:
                sys.exit(f"{a.id} not found")
            return set_fields(lines, tasks[a.id], kv)
        write_txn(mut, f"{a.id}: " + " ".join(a.kv) + (f" ({a.agent})" if a.agent else ""))
        return print(f"updated {a.id}")


if __name__ == "__main__":
    main()
