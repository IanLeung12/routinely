-- Routine Watch time-series schema (SPEC section 6.3): sessions, step events and task
-- errors, stored in TimescaleDB (Tiger Data) as hypertables on their time column.
--
-- Safe to run against a fresh or existing database: every statement is idempotent.

CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT NOT NULL,
    resident_id TEXT NOT NULL,
    task_id     TEXT NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL,
    ended_at    TIMESTAMPTZ,
    assisted    BOOLEAN NOT NULL DEFAULT FALSE,
    score       DOUBLE PRECISION,
    PRIMARY KEY (session_id, started_at)
);

SELECT create_hypertable('sessions', 'started_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS sessions_resident_task_idx
    ON sessions (resident_id, task_id, started_at DESC);

-- step_events and task_errors carry their own session-relative times (t_start,
-- t_end, seconds since the session started - SPEC section 6, contracts.py), so
-- recorded_at is the wall-clock column the hypertable partitions on.

CREATE TABLE IF NOT EXISTS step_events (
    event_id    TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    step_id     TEXT NOT NULL,
    objects     JSONB NOT NULL,
    t_start     DOUBLE PRECISION NOT NULL,
    t_end       DOUBLE PRECISION NOT NULL,
    confidence  DOUBLE PRECISION NOT NULL,
    source      TEXT NOT NULL,
    unclear     BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (event_id, recorded_at)
);

SELECT create_hypertable('step_events', 'recorded_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS step_events_session_idx
    ON step_events (session_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS task_errors (
    error_id       TEXT NOT NULL,
    session_id     TEXT NOT NULL,
    type           TEXT NOT NULL,
    step_id        TEXT,
    t_start        DOUBLE PRECISION NOT NULL,
    t_end          DOUBLE PRECISION NOT NULL,
    evidence       JSONB NOT NULL,
    self_corrected BOOLEAN NOT NULL DEFAULT FALSE,
    recorded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (error_id, recorded_at)
);

SELECT create_hypertable('task_errors', 'recorded_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS task_errors_session_idx
    ON task_errors (session_id, recorded_at DESC);
