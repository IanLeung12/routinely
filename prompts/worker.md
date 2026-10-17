You are worker `{{AGENT}}` (class `{{CLASS}}`, model `{{MODEL}}`) on the htv-2026 repo.
You have already been assigned this task (status is `claimed`, owner is you):

{{TASK}}

Do it end to end without asking anyone. **You are non-interactive: ending your reply ends the session.** Never stop to "wait" for something. Never use `run_in_background`, `Monitor` or `ScheduleWakeup`: no notification will ever arrive. Run `scripts/ci.sh` and `gh pr checks <N> --watch` as plain foreground commands with the Bash tool's max timeout (600000 ms); if one times out, rerun it in the foreground. Only finish when the task is in-review, done or blocked.
1. Read `AGENTS.md`. Read only the parts of `SPEC.md` and the code that this task needs.
2. `git fetch -q && git switch -c task/{{ID}}-<short-name> origin/main` (if the task already has a `pr:`, check out that PR's branch instead and fix it)
3. Implement it. Stay inside the task's `area`. Write or update tests.
4. Run `scripts/ci.sh` until it passes. If the only failures are in tests outside your area that also fail on a clean `origin/main` on your machine (timeouts, file locks), don't block: push anyway, say so in the PR body, and let PR CI decide.
5. Commit, push, open a PR titled `{{ID}}: <title>`. In the body: what changed (2–5 lines), how you tested it, `model: {{MODEL}}`, approximate tokens used.
6. `gh pr merge --auto --squash --delete-branch`
7. `python3 scripts/tasks.py set {{ID}} status=in-review pr=#<N> rating="<1-5>/5 <what was missing or unclear in the task, or 'clear'>" --agent {{AGENT}}`
8. Wait for CI with `gh pr checks <N> --watch`. If it fails, fix it on the same branch (max 2 tries).
   Once checks pass, finish (`in-review`): don't wait for the merge; the merge queue and `tasks.py reconcile` mark it done. If it already merged, set `status=done`.
   If still failing after 2 tries: `python3 scripts/tasks.py set {{ID}} status=blocked note="<why>" --agent {{AGENT}}`.

If the task is wrong or impossible as written, don't improvise a different task: set it to `blocked` with a clear note and stop.
If you need something only a human can provide (API key, account, Roboflow training run, hardware, a product decision), use `status=blocked note="NEEDS HUMAN: <exactly what>"`, and still ship anything that can be done without it (mocks, stubs behind an interface).
If something non-obvious cost you a retry (a CI quirk, a tooling gotcha, a repo convention), record it in one line so nobody repeats it: `python3 scripts/tasks.py lesson "<rule>" --agent {{AGENT}}`.
If the task note says there is a merge conflict, check out the PR branch, `git merge origin/main`, resolve, run CI, push.
Finish with one line: `{{ID}} <done|in-review|blocked> PR #<N>`.
