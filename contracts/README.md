# contracts/

Schemas shared by `pipeline/` and `web/`. One definition, two consumers: if the
pipeline and the dashboard disagree about a shape, the answer lives here.

Empty on purpose — nothing is shared yet. The first things expected to land:

- the per-frame capture record (pose and hand landmarks, object boxes, timestamp;
  `routine_watch.capture.FRAME_SCHEMA_VERSION`)
- step events, task-graph definitions and the error types in SPEC section 7
- the session, baseline-comparison and alert payloads the dashboard reads

## Rules

- Only `heavy` tasks may change files here, and the same PR must update every
  consumer (AGENTS.md).
- Generate or mirror both sides from one source rather than hand-maintaining a
  Python copy and a TypeScript copy that can drift.
- No raw frames or video in any payload — skeletons, boxes and timestamps only
  (SPEC section 8).
