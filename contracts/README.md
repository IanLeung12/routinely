# contracts/

Schemas shared by `pipeline/` and `web/`. One definition, two consumers: if the
pipeline and the dashboard disagree about a shape, the answer lives here.

## What is here

| File | What it carries |
|---|---|
| `capture_frame.schema.json` | the single per-frame JSONL record: pose skeletons, MediaPipe hand landmarks, object boxes, timestamp (SPEC section 16) |
| `object_detection.schema.json` | one box from the local detector |
| `step_event.schema.json` | a step seen happening, with confidence, `rule` or `verifier`, and the `unclear` flag |
| `task_error.schema.json` | one of the six everyday-action errors, its evidence refs and whether it was self-corrected (SPEC section 7) |
| `session.schema.json` | one attempt at one task: resident, task, start and end, assisted, score |
| `alert.schema.json` | a change flagged for review: sessions, errors, baseline comparison, summary, suggested checks, nurse feedback |
| `live_message.schema.json` | one message on the live WebSocket (`/ws/live`): a `oneOf` keyed on `type` over `session_start`, `step_state`, `frame`, `step`, `error`, `session_end` and `paused` (SPEC section 16, decision B) |
| `resident_summary.schema.json` | one row of the unit overview (`GET /residents`): status chip, the pattern the change is consistent with, sparkline (SPEC section 9, screen 1) |
| `resident.schema.json` | one resident in full (`GET /residents/{id}`): that row plus consent, sessions, care records and baseline (SPEC section 9, screen 2) |
| `handoff.schema.json` | the shift handoff (`GET /handoff`): a row per resident, the rooms whose monitoring is paused, and the window's summary (SPEC section 9) |
| `alert_detail.schema.json` | an alert as a route answers it (`GET /alerts/{id}`, and each row of `GET /alerts`): the `alert` record with `patterns` and `feedback` always sent and the resident's feedback-tuned threshold applied |
| `feedback.schema.json` | the body of `POST /alerts/{id}/feedback`: the nurse's verdict, an optional note, and the optional answer to "what was it?" (SPEC section 5, MVP 7 and 8) |
| `monitoring.schema.json` | every room whose monitoring a nurse has paused (`GET /monitoring`): the state behind the dashboard's pause switches (SPEC section 12) |
| `room_monitoring.schema.json` | one room's switch as the PUT answers it (`PUT /rooms/{room}/monitoring`): the room and whether it is on now |
| `room_monitoring_history.schema.json` | one room's audit trail (`GET /rooms/{room}/monitoring/history`): who paused or resumed it and when, newest first (SPEC section 12) |
| `examples/capture.jsonl` | four sample frames in the capture format; made-up landmark numbers, real shape |

Each schema is standalone (nested types are repeated in its `$defs`), so a validator
needs no registry and no network.

`live_message.schema.json` is the odd one out: a wire protocol rather than a record,
an envelope around the contracts above. The pipeline sends a session's messages
(`pipeline/src/routine_watch/live.py`), the API adds `paused`
(`pipeline/src/routine_watch/api.py`) and the dashboard reads them with its own types
(`web/src/live/useLiveSession.ts`), so nothing is generated for the web side here;
`pipeline/tests/test_live_contract.py` replays a session through `/ws/live`, validates
every message it sends against the schema, and fails if either side knows a message
the other does not.

Everything from `resident_summary.schema.json` down is an HTTP payload rather than
a record: what a route answers with, built by `pipeline/src/routine_watch/demo.py`,
`handoff.py` and `monitoring.py` and served by `api.py`, plus the one body that
travels the other way. The dashboard mirrors them by hand too
(`web/src/overview/types.ts`, `web/src/handoff/types.ts`,
`web/src/about/monitoringApi.ts`, `web/src/alert/api.ts`) or reads them through a
record's own generated type (`alert_detail` through `Alert`), so again nothing is
generated for the web side and the schema is what both sides are held to:
`pipeline/tests/test_api_payload_contracts.py` calls every one of those routes -
every demo resident, one with a live session in their history, a handoff with a room
paused, an alert before and after a nurse answers it, a room paused and resumed -
and validates what comes back.

## Changing them

`pipeline/src/routine_watch/contracts.py` is the source of truth: `CONTRACTS` for the
records, `PROTOCOLS` for the live socket, `PAYLOADS` for what the HTTP routes answer
with, `REQUESTS` for what the dashboard posts back. The schemas, the sample JSONL and
`web/src/contracts.ts` are generated from the pydantic models there:

```sh
cd pipeline
uv run python -m routine_watch.contracts          # rewrite the generated files
uv run python -m routine_watch.contracts --check  # fail if any are stale
```

`pipeline/tests/test_contracts.py` runs that check, round-trips every type through
JSON into its schema, and validates the sample frames, so the three copies cannot
drift. Never hand-edit a generated file.

## Rules

- Only `heavy` tasks may change files here, and the same PR must update every
  consumer (AGENTS.md).
- No raw frames or video in any payload — skeletons, boxes and timestamps only
  (SPEC section 8). Every model forbids unknown fields, so a frame cannot be smuggled
  through a contract; the tests check that too.
- Times inside a session (`t`, `t_start`, `t_end`) are seconds since the session
  started, so a recording replays like the live camera. Wall-clock times
  (`started_at`, `created_at`) are ISO 8601.
