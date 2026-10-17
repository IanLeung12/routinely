# Docker host / Vultr deployment

Use a Linux Docker host with Docker Engine and Compose v2.24.4+; no cloud provisioning
is performed here. Run from the repository root (`.env` is optional for offline defaults):

```bash
cp .env.example .env
docker compose -f deploy/docker-compose.yml up -d --build --wait
(cd pipeline && uv sync --frozen --extra dev) # smoke tooling; requires uv on host
bash scripts/smoke.sh
```

Dashboard: http://localhost:5173; landing: http://localhost:5173/landing.html;
API: http://localhost:8000 (health: `/health`, live WebSocket: `/ws/live`).
The smoke script uses `DASHBOARD_PORT` (default 5173) and a positional API URL;
it currently ignores `DASHBOARD_URL` and `API_URL` environment overrides.
Run `bash deploy/check.sh` for container, CORS, routing and smoke checks together.
It creates an offline test env in a temporary directory and removes its containers.

For a remote host, edit `.env`, then use this form for **every** Compose command:

```bash
docker compose --env-file .env -f deploy/docker-compose.yml up -d --build --wait
docker compose --env-file .env -f deploy/docker-compose.yml down
```

`env_file` supplies API runtime settings; `--env-file .env` also supplies Compose
interpolation (including the web build argument). Important production settings:
- `VITE_API_URL`: browser-reachable API URL, e.g. `https://api.example.org`;
  baked into JS at build time; rebuild web after changes. Never use `http://api:8000`.
- `CORS_ORIGINS`: exact dashboard origin, e.g. `https://routine.example.org`.
- `OFFLINE_MODE=true`, `LIVE_API=0`: safe demo defaults; no paid API calls.
  Enable real calls only deliberately with the relevant provider keys and budget.
- `DATABASE_URL`: empty uses memory; a Tiger Data URL uses the optional DB client.
  The current dashboard's demo sessions/feedback remain in memory across neither
  restarts nor replicas; the API routes are not yet wired to TimescaleStore.
- Provider keys belong only in `.env`, never `VITE_*`, images or source control.

Optional local TimescaleDB: set `POSTGRES_PASSWORD` to a strong password and
`DATABASE_URL=postgresql://routine_watch:<URL-encoded-password>@db:5432/routine_watch`
in `.env`, then add `--profile tsdb` before `up`. Wait for `db` to be healthy
before using the store. The schema initializes only on a fresh DB volume.
Without that profile, use a remote database or leave `DATABASE_URL` empty.

Point dashboard and API domain A/AAAA records to the VM. Install Caddy on the
host, reverse-proxy the dashboard domain to localhost:5173 and the API domain to
localhost:8000; Caddy obtains/renews TLS and handles WebSocket upgrades. Allow
public 80/443 and restrict direct 5173/8000 access with the host firewall. Set
the HTTPS URLs above and rebuild before sharing the demo URL.

`down` removes containers/networks; named replay/cache and DB volumes survive.
`down -v` also permanently deletes those volumes. Replay files can live under
`/app/.data/replays`; the API's paid-response cache uses `/app/.data/cache`.
Only skeleton landmarks, object boxes, events and timestamps may be stored.
Never store raw video or frames. Capture runs on the laptop, outside these images.
