# Infra guide (scripts/, .github/, deploy)
- Scripts are bash with `set -euo pipefail`, idempotent, and print what they did. `scripts/ci.sh` stays the single CI entry point.
- Never break `scripts/tasks.py`, `scripts/worker.sh` or the prompts other agents depend on; run `scripts/ci.sh` and a dry run.
- No secrets in git; new env vars go in `.env.example` with a comment.
