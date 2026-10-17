# IMPROVEMENTS

Retro agent's experiments on the agent loop. One line each; judged on later runs.

## Open experiments
_(none)_

## Closed
- E1 (2026-10-17): T071 blocked with finished work stranded locally because local Vitest timed out in unrelated tests (max_API_light 25% first-try, 2 releases, Windows) → worker.md step 4: push when the only failures are outside the area and also fail on clean origin/main; PR CI gates (PR #113). **Kept (10:55):** max_API_light first-try now 90%; T071/T096 later merged; no new blocks for local-only CI failures.
- E2 (2026-10-17): tasks.py parses acceptance bullets (`- x: y`) as fields, so notes land mid-acceptance (T071) and a `- status:` bullet could hijack status → board task T133. **Kept (10:55):** T133 merged first try; no notes inside task bodies since.
