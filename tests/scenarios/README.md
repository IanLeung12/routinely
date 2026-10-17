# Scenarios

A scenario is a recorded session plus what the pipeline should make of it. Replaying
one runs capture → steps → task graph → errors → session score → change flag with no
camera, no keys and no network, so it is how the tester checks a change end to end and
how CI keeps `main` honest.

```sh
scripts/e2e.sh                                  # PASS/FAIL every scenario
scripts/e2e.sh tests/scenarios/tea_normal       # just one
cd pipeline && uv run python -m routine_watch.replay ../tests/scenarios/tea_normal
```

The last one prints the full result as JSON: the steps, the errors with their
timestamps, the session score, the baseline and the flag. That is the thing to read
when a scenario fails and the diff alone does not explain why.

The harness is `pipeline/src/routine_watch/replay.py`.

## A scenario directory

```
tests/scenarios/<name>/
  expected.yaml   what the pipeline should make of it
  frames.jsonl    capture records, one per frame      | exactly
  steps.jsonl     step events, written by hand        | one of these
```

### expected.yaml

```yaml
task: tea            # a tasks/<name>.yaml graph; defaults to tea
steps: [get_cup, teabag_in_cup, pour]   # every step event, in order
errors:              # in no particular order; `step` may be left out
  - { type: omission, step: boil }
flag: false          # does this session flag a change for a nurse to review?

score: 6.0           # optional: assert the session score too
assisted: false      # optional: assert whether somebody was helping

history:             # optional: prior sessions of this resident
  - { hours_ago: 48, score: 0.0 }
  - { hours_ago: 30, errors: { omission: 1 } }   # or spell out the errors
```

`steps`, `errors` and `flag` are always checked; `score` and `assisted` only when the
file sets them. An unknown key is an error, so a typo fails the scenario rather than
being quietly ignored.

**History and the flag.** A resident needs at least three prior sessions before they
have a baseline, and two sessions above their own threshold within 48 hours before
anything flags (SPEC §7). A scenario with no `history:` therefore never flags, however
bad the session is. `hours_ago` is measured back from the replayed session, which
happens at a fixed instant (`replay.REPLAY_EPOCH`), so a scenario gives the same answer
today and next month.

### steps.jsonl

One `StepEvent` per line (`contracts/step_event.schema.json`). This is the level to
write a scenario at while the recogniser is still being built, and the level to use
for anything the stub recogniser below cannot express: a low-confidence step, an
`unclear` one, or two steps done with the same objects.

### frames.jsonl

One `CaptureFrame` per line (`contracts/capture_frame.schema.json`): the single
per-frame record every source produces, live camera included (SPEC §16). Steps are
then recognised from the frames. Never a raw frame, an image or a clip — skeletons,
boxes and timestamps only (SPEC §8).

`contracts/examples/capture.jsonl` shows the shape of a record.

## The stubs

Two stages of the pipeline are still placeholders, so the harness stands in for them.
Both are marked `STUB` in `replay.py` and both go away when their task lands. **The
scenarios do not change when that happens** — that is the point of writing them now.

### Stub 1: frames → steps (`steps_from_frames`)

Standing in for `routine_watch.recogniser`. A frame shows a step when the objects a
hand is on are *exactly* that step's objects; a run of consecutive frames showing the
same step is one step event; a frame that touches nothing ends the run. A hand is
either MediaPipe hand landmarks or a box from the detector's `hand` class, so a
synthetic scenario can use whichever is less work.

It is deliberately literal: it never looks at the task's dependencies, so a scenario
can still show steps happening in the wrong order.

What it cannot do, and what to do instead:

| Limit | Why | Work around it |
|---|---|---|
| Two steps with the same objects are indistinguishable (`fill_kettle` and `boil` are both "the kettle") | it reads objects, not state | write the scenario as `steps.jsonl`; the harness fails loudly rather than guessing |
| Every event is a confident rule event | confidence and the Gemini verifier have no frame-level meaning here | write the event, with its `confidence` and `unclear`, in `steps.jsonl` |
| Both hands must be on the objects for a two-object step | "touching" is all it knows | give the frame two `hand` boxes, one per object, as `tea_no_kettle` does while pouring |
| An object inside another (a teabag in the cup) is touched whenever the outer one is | boxes overlap | stop detecting it, which is what a real detector does with a teabag under water |

### Stub 2: steps → errors (`find_errors`)

Standing in for `routine_watch.task_graph` plus `routine_watch.errors`. It walks the
step events against the task graph and finds five of SPEC §7's six error types:
**omission**, **sequence**, **perseveration**, **substitution** and **abandonment**
(no events for five minutes with required steps still to do).

**Hesitation is missing**, because it is a step or gap more than 2.5 standard
deviations above this resident's own average and no scenario carries per-step
baselines yet. A scenario cannot expect one until the baseline stage lands.

Also, as the spec requires: an `unclear` event is never an error, and the step it names
still counts as having happened, so it cannot be reported as an omission either.

Self-corrected slips are not detected yet either, so `self_corrected` is always false.

## The scenarios here

| Scenario | Level | What it is for |
|---|---|---|
| `tea_normal` | steps | A good session. Everything that is *not* an error: either order of filling the kettle and fetching the cup, sugar skipped because it is optional. Catches a classifier that has become too eager. |
| `tea_skip_teabag_pour_twice` | steps | The demo's bad session: the teabag is never put in (omission) and the water is poured twice with a stir in between (perseveration). With one bad session already 30 hours ago, it flags. |
| `tea_no_kettle` | frames | Cold water: the kettle is never filled or boiled, so two omissions. The one scenario that goes through the capture format and the stub recogniser. One bad session on its own never flags. |

## Adding one

1. `mkdir tests/scenarios/<name>` and write `expected.yaml` plus one of the two input
   files. Say in a comment what the scenario is *for*; a scenario nobody understands
   gets deleted the first time it fails.
2. `scripts/e2e.sh tests/scenarios/<name>` until it passes. Read the JSON when the
   diff is not enough.
3. Make sure it would fail for the right reason: change the code it is meant to guard
   and check that it goes red.

Scenarios are cheap and they are the only test that covers the stages together, so a
new error type or a new task graph should arrive with one.
