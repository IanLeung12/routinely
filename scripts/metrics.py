#!/usr/bin/env python3
"""Orchestration metrics: how well is the agent loop working? No LLM.

Reads the board history (tasks branch), the board + archive, PRs and CI runs, and prints
METRICS.md (markdown) to stdout. `--json` prints the raw numbers instead.

  python3 scripts/metrics.py [--hours 6] [--json]

Used by the retro agent (prompts/retro.md) to find and fix systemic problems.
"""
import collections, json, os, re, statistics, subprocess, sys
from datetime import datetime, timedelta, timezone

ROOT = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
NOW = datetime.now(timezone.utc)
SYSTEM = {"ian", "orchestrator", "reviewer", "tester", "mergeq", "integration", "retro", "?"}


def sh(*cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout


def ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def board_fields():
    """id -> fields, from TASKS.md + ARCHIVE.md on origin/tasks."""
    out = {}
    for f in ("TASKS.md", "ARCHIVE.md"):
        text = sh("git", "show", f"origin/tasks:{f}")
        for block in re.split(r"^### ", text, flags=re.M)[1:]:
            m = re.match(r"(T\d+)\s*[—-]\s*(.*)", block)
            if not m:
                continue
            v = dict(re.findall(r"^- ([\w-]+): ?(.*)$", block, re.M))
            v["title"] = m.group(2).strip()
            out[m.group(1)] = v
    return out


def area_key(area):
    for p in (area or "").split(","):
        p = p.strip().split(" ")[0]
        if "/" in p:
            parts = p.split("/")
            return "/".join(parts[:3]) if parts[0] in ("web", "pipeline") else "/".join(parts[:2])
    return "other"


def main():
    hours = 6
    if "--hours" in sys.argv:
        hours = int(sys.argv[sys.argv.index("--hours") + 1])
    since = NOW - timedelta(hours=hours)
    sh("git", "fetch", "-q", "origin")
    fields = board_fields()

    # --- board history
    tasks = collections.defaultdict(lambda: {"claims": [], "releases": 0, "conflicts": 0, "blocked": 0,
                                             "stale": 0, "early_end": 0, "pr": None, "workers": []})
    workers_seen = collections.Counter()
    log = sh("git", "log", "origin/tasks", "--reverse", "--format=%cI\t%s").splitlines()
    for line in log:
        when, _, subj = line.partition("\t")
        t = ts(when)
        m = re.match(r"claim (T\d+) \(([^)]+)\)", subj)
        if m:
            tasks[m.group(1)]["claims"].append(t)
            tasks[m.group(1)]["workers"].append(m.group(2))
            if t and t >= since:
                workers_seen[m.group(2)] += 1
            continue
        m = re.match(r"(T\d+): (.*)", subj)
        if not m:
            continue
        rec, rest = tasks[m.group(1)], m.group(2)
        pr = re.search(r"pr=#(\d+)", rest)
        if pr:
            rec["pr"] = int(pr.group(1))
        if "status=todo" in rest:
            if "merge conflict" in rest:
                rec["conflicts"] += 1
            elif "stale claim" in rest:
                rec["stale"] += 1
            elif "without progress" in rest:
                rec["early_end"] += 1
            rec["releases"] += 1
        if "status=blocked" in rest:
            rec["blocked"] += 1

    # --- PRs and CI
    prs = json.loads(sh("gh", "pr", "list", "--state", "all", "-L", "400", "--json",
                        "number,title,createdAt,mergedAt,state,body,headRefName") or "[]")
    by_pr = {p["number"]: p for p in prs}
    runs = []
    for page in (1, 2, 3):
        r = json.loads(sh("gh", "api", f"repos/{{owner}}/{{repo}}/actions/runs?per_page=100&page={page}") or "{}")
        runs += r.get("workflow_runs", [])
        if len(r.get("workflow_runs", [])) < 100:
            break
    ci_fail = collections.Counter(r["head_branch"] for r in runs if r.get("conclusion") == "failure" and r["event"] == "pull_request")
    main_runs = [r for r in runs if r["head_branch"] == "main" and r["event"] == "push" and ts(r["created_at"]) >= since]
    main_red = sum(1 for r in main_runs if r.get("conclusion") == "failure")
    reverts = [l for l in sh("git", "log", "origin/main", f"--since={since.isoformat()}", "--format=%s").splitlines()
               if l.lower().startswith("revert")]

    # --- per task rows (tasks first claimed in the window)
    rows = []
    for tid, rec in tasks.items():
        first = next((c for c in rec["claims"] if c), None)
        if not first or first < since:
            continue
        f = fields.get(tid, {})
        pr = by_pr.get(rec["pr"]) if rec["pr"] else None
        merged = ts(pr["mergedAt"]) if pr and pr.get("mergedAt") else None
        body = (pr or {}).get("body") or ""
        tok = re.search(r"(?i)tokens?[^0-9\n]{0,25}~?\s*(\d[\d.,]*)\s*([km])?", body)
        tokens = None
        if tok:
            try:
                n = float(tok.group(1).replace(",", "").rstrip("."))
            except ValueError:
                n = 0
            tokens = n * (1000 if (tok.group(2) or "").lower() == "k" else 1_000_000 if (tok.group(2) or "").lower() == "m" else 1)
        fails = ci_fail.get((pr or {}).get("headRefName", ""), 0)
        first_try = bool(merged) and fails == 0 and rec["releases"] == 0
        rate = re.match(r"\s*(\d)", f.get("rating", "") or "")
        rows.append({
            "id": tid, "class": f.get("class", "?"), "kind": f.get("kind", "?"), "area": area_key(f.get("area")),
            "source": f.get("source", "orchestrator"), "worker": rec["workers"][-1] if rec["workers"] else "?",
            "merged": bool(merged), "cycle_min": (merged - first).total_seconds() / 60 if merged else None,
            "ci_fail": fails, "releases": rec["releases"], "conflicts": rec["conflicts"], "stale": rec["stale"],
            "early_end": rec["early_end"], "blocked": rec["blocked"], "first_try": first_try, "tokens": tokens,
            "rating": int(rate.group(1)) if rate else None, "rating_note": f.get("rating", ""),
            "status": f.get("status", "?"), "title": f.get("title", "")[:70],
        })

    def agg(key):
        g = collections.defaultdict(list)
        for r in rows:
            g[r[key]].append(r)
        out = []
        for k, rs in sorted(g.items(), key=lambda kv: -len(kv[1])):
            merged = [r for r in rs if r["merged"]]
            cyc = [r["cycle_min"] for r in merged if r["cycle_min"] is not None]
            tok = [r["tokens"] for r in rs if r["tokens"]]
            out.append({key: k, "tasks": len(rs), "merged": len(merged),
                        "first_try_pct": round(100 * sum(r["first_try"] for r in rs) / len(rs)),
                        "ci_fail": sum(r["ci_fail"] for r in rs), "releases": sum(r["releases"] for r in rs),
                        "median_cycle_min": round(statistics.median(cyc)) if cyc else None,
                        "median_tokens_k": round(statistics.median(tok) / 1000) if tok else None})
        return out

    # local worker idle time (host workers only)
    idle = {}
    for d in sorted(os.listdir(os.path.expanduser("~"))):
        p = os.path.expanduser(f"~/{d}/.worker.out")
        if d.startswith("htv-2026-w") and os.path.exists(p):
            n = 0
            for line in open(p, errors="replace").read().splitlines()[-400:]:
                if "no claimable" in line:
                    n += 1
            idle[d] = n * 3  # IDLE=180s per line

    ratings = [r for r in rows if r["rating"]]
    data = {
        "window_hours": hours, "generated": NOW.strftime("%Y-%m-%d %H:%M UTC"),
        "totals": {
            "tasks_claimed": len(rows), "merged": sum(r["merged"] for r in rows),
            "first_try_pct": round(100 * sum(r["first_try"] for r in rows) / len(rows)) if rows else None,
            "ci_failures_on_prs": sum(r["ci_fail"] for r in rows), "releases": sum(r["releases"] for r in rows),
            "early_session_ends": sum(r["early_end"] for r in rows), "stale_claims": sum(r["stale"] for r in rows),
            "merge_conflicts": sum(r["conflicts"] for r in rows), "blocked": sum(r["blocked"] for r in rows),
            "main_ci_red": main_red, "main_ci_runs": len(main_runs), "reverts": len(reverts),
            "active_workers": len([w for w in workers_seen if w.lower() not in SYSTEM]),
            "avg_task_rating": round(statistics.mean(r["rating"] for r in ratings), 1) if ratings else None,
            "bug_tasks_from_tester_reviewer": sum(1 for f in fields.values()
                                                  if f.get("source") in ("tester", "reviewer", "integration")
                                                  or f.get("title", "").startswith(("Bug:", "Review:"))),
        },
        "by_class": agg("class"), "by_kind": agg("kind"), "by_worker": agg("worker"), "by_area": agg("area")[:8],
        "host_worker_idle_min_recent": idle,
        "problems": [r for r in rows if r["ci_fail"] or r["releases"] or r["blocked"]][:15],
        "low_rated": [{"id": r["id"], "rating": r["rating"], "note": r["rating_note"][:120]} for r in ratings if r["rating"] <= 3][:10],
    }
    if "--json" in sys.argv:
        print(json.dumps(data, indent=1, default=str))
        return

    T = data["totals"]
    out = [f"# METRICS (last {hours} h, generated {data['generated']})", "",
           f"- **Throughput:** {T['merged']}/{T['tasks_claimed']} claimed tasks merged · {T['active_workers']} active workers · "
           f"first-try success {T['first_try_pct']}%",
           f"- **Friction:** {T['ci_failures_on_prs']} PR CI failures · {T['releases']} releases "
           f"({T['early_session_ends']} sessions ended early, {T['stale_claims']} stale, {T['merge_conflicts']} conflicts) · "
           f"{T['blocked']} blocked",
           f"- **Main:** {T['main_ci_red']}/{T['main_ci_runs']} main CI runs red · {T['reverts']} reverts",
           f"- **Quality signals:** avg task rating {T['avg_task_rating']}/5 · {T['bug_tasks_from_tester_reviewer']} bug/review tasks filed (all time)",
           f"- **Host worker idle (recent log):** " + ", ".join(f"{k.replace('htv-2026-', '')} {v}m" for k, v in idle.items()), ""]

    def table(title, rows_, key):
        out.append(f"## {title}")
        out.append(f"| {key} | tasks | merged | first-try % | CI fails | releases | median min | median tokens |")
        out.append("|---|---|---|---|---|---|---|---|")
        for r in rows_:
            out.append(f"| {r[key]} | {r['tasks']} | {r['merged']} | {r['first_try_pct']} | {r['ci_fail']} | "
                       f"{r['releases']} | {r['median_cycle_min'] or '–'} | {str(r['median_tokens_k']) + 'k' if r['median_tokens_k'] else '–'} |")
        out.append("")

    table("By class", data["by_class"], "class")
    table("By kind", data["by_kind"], "kind")
    table("By worker", data["by_worker"], "worker")
    table("By area (top 8)", data["by_area"], "area")
    out.append("## Problem tasks")
    for r in data["problems"]:
        bits = [f"CI×{r['ci_fail']}" if r["ci_fail"] else "", f"released×{r['releases']}" if r["releases"] else "",
                "blocked" if r["blocked"] else ""]
        out.append(f"- {r['id']} ({r['class']}/{r['kind']}, {r['worker']}): {' '.join(b for b in bits if b)} — {r['title']}")
    if data["low_rated"]:
        out += ["", "## Low task ratings (≤3/5)"] + [f"- {r['id']} {r['rating']}/5: {r['note']}" for r in data["low_rated"]]
    print("\n".join(out))


if __name__ == "__main__":
    main()
