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
top_pattern: sudden_change   # optional: the pattern (SPEC §7.5) the flag should score
                              # highest, or "none" if it should match no pattern

history:             # optional: prior sessions of this resident
  - { hours_ago: 48, score: 0.0 }
  - { hours_ago: 30, errors: { omission: 1 } }   # or spell out the errors
```

`steps`, `errors` and `flag` are always checked; `score`, `assisted` and `top_pattern`
only when the file sets them. An unknown key is an error, so a typo fails the scenario
rather than being quietly ignored. `top_pattern` needs error-breakdown `history:`
entries (not just a bare `score:`) to score anything: the pattern scorer reads a
session's own error types, not an opaque score.

**History and the flag.** A resident needs at least three prior sessions before they
have a baseline, and two sessions above their own threshold within 48 hours before
anything flags (SPEC §7). A scenario with no `history:` therefore never flags, however
bad the session is. `hours_ago` is measured back from the replayed session, which
happens at a fixed instant (`replay.REPLAY_EPOCH`), so a scenario gives the same answer
today and next month.

### Session durations

In `expected.yaml`, set the optional `duration_s` (positive seconds) on the replayed
session and its history sessions to exercise duration-based patterns like `motor_slowing`:

```yaml
duration_s: 450       # replayed session
history:
  - { hours_ago: 72, score: 0.0, duration_s: 300 }
  # Add more history sessions to establish the usual duration.
```

Leaving durations unset keeps `duration_ratio` unset.

### steps.jsonl

One `StepEvent` per line (`contracts/step_event.schema.json`). This is the level to
write a scenario at for anything the recogniser's state rules cannot express from
object boxes alone: a low-confidence step, an `unclear` one, or a moment the Gemini
verifier would need to resolve.

### frames.jsonl

One `CaptureFrame` per line (`contracts/capture_frame.schema.json`): the single
per-frame record every source produces, live camera included (SPEC §16). Steps are
recognised from the frames by the real `routine_watch.recogniser.recognise`: state
rules over hand-object contacts (how far an object travelled while held, whether it
changed direction, how long it sat still, whether it went over the cup), not just
which objects a hand is on at a given instant — see `recogniser.py`'s docstring for
the rules themselves. Never a raw frame, an image or a clip — skeletons, boxes and
timestamps only (SPEC §8).

`contracts/examples/capture.jsonl` shows the shape of a record.

Errors come from the real `routine_watch.errors.classify_errors`, which finds five of
SPEC §7's six error types: **omission**, **sequence**, **perseveration**,
**substitution** and **abandonment** (no events for more than two minutes with required
steps still to do). The separate `routine_watch.hesitation` stage flags steps or gaps
that took much longer than this resident's own average. These scenarios do not yet
carry the per-step history needed to exercise it.

## The scenarios here

| Scenario | Level | What it is for |
|---|---|---|
| `tea_normal` | frames | A good session. Everything that is *not* an error: either order of filling the kettle and fetching the cup, sugar skipped because it is optional. Catches a classifier that has become too eager; also `routine_watch.evidence`'s normal-session replay, distinct from `tea_no_kettle`'s. |
| `tea_abandoned` | steps | A 131-second silence after starting tea, followed by one last step and an unfinished routine. Abandonment and remaining omissions flag with another recent bad session. |
| `tea_skip_teabag_pour_twice` | steps | The demo's bad session: the teabag is never put in (omission) and the water is poured twice with a stir in between (perseveration). With one bad session already 30 hours ago, it flags. |
| `tea_no_kettle` | frames | Cold water: the kettle is never filled or boiled, so two omissions. One bad session on its own never flags. Also `routine_watch.evidence`'s alert-session replay. |
| `tea_sequence_error` | steps | Pouring before adding the teabag produces exactly one sequence error. |
| `tea_single_bad_no_flag` | steps | One bad session after quiet history produces errors without flagging a change. |
| `tea_substitution` | steps | Stirring with milk instead of a spoon produces exactly one substitution error. |
| `tea_unclear_not_error` | steps | An unclear, low-confidence teabag observation must not produce an error. |
| `tea_session_unclear_no_flag` | steps | Bad lighting: over 40% of the session's events are unclear/low-confidence, so the whole session is too unclear to score, even against a history that would otherwise flag a change. |
| `meds_normal` | steps | The second task (`meds`), done right: the pill branch and the glass branch interleaved, and the optional `close_organiser` skipped. Nothing here may ever be an error. |
| `meds_skip_water` | steps | The dry swallow: the water is poured and never drunk, so `drink_water` is an omission. Shows graph, errors, score and flag running off a task file alone. |
| `meds_abandoned` | steps | The pill comes out but the water steps never happen after a 131-second silence: abandonment plus the remaining omissions, mirroring `tea_abandoned`. |
| `meds_pill_twice` | steps | A double dose: the pill is taken out of the organiser a second time with `drink_water` in between, a perseveration error. Flags with another recent bad session. |
| `meds_session_unclear_no_flag` | steps | The meds counterpart of `tea_session_unclear_no_flag`: bad lighting makes over 40% of the session's events unclear, so the whole session is too unclear to score, even against a history that would otherwise flag the same double-dose session. |
| `pattern_sudden_change` | steps | The demo's bad session on a resident whose own history has only scattered single-type slips: `top_pattern` checks the flag is consistent with `sudden_change` (SPEC §7.5). |
| `pattern_slow_drift` | steps | Cold water, no stir, after three weeks of hesitation climbing night after night: `top_pattern` checks `slow_drift` (SPEC §7.5). |
| `pattern_executive` | steps | The teabag goes in three times (perseveration) with the order otherwise intact, building over about a week: `top_pattern` checks `executive_pattern` (SPEC §7.5). |
| `pattern_evening_worsening` | steps | A clean session, but six straight evenings of long pauses with mornings staying clean: `top_pattern` checks `evening_worsening` (SPEC §7.5). |
| `pattern_none` | steps | A substitution error against a resident with one earlier substitution: flags a change, but `top_pattern` checks it matches no pattern in the library. |
| `pattern_motor_slowing` | steps | A clean session, but it and two recent sessions run 450s against this resident's usual 300s with a touch of hesitation: `top_pattern` checks `motor_slowing` (SPEC §7.5). |
| `meds_pill_before_water` | steps | Taking the pill before filling the glass is fine, but drinking before filling is a sequence error; does not flag. |
| `meds_unclear_not_error` | steps | An unclear, low-confidence pill observation must not produce an error. |
| `meds_bad_sessions_far_apart` | steps | Two bad meds sessions more than 48 hours apart must not flag; guards the 48h window. |
| `meds_single_bad_no_flag` | steps | The meds counterpart of `tea_single_bad_no_flag`: one bad session after quiet history produces errors without flagging a change. |
| `meds_pill_three_times` | steps | The meds counterpart of `tea_teabag_three_times`: the pill comes out of the organiser three times, two perseveration errors on the once-only step. |
| `tea_bad_sessions_far_apart` | steps | Two bad sessions more than 48 hours apart must not flag; guards the 48h window. |
| `tea_kettle_twice` | steps | Boiling the kettle again after getting a cup is perseveration on a once-only step; flags with another recent bad session. |
| `tea_milk_sugar` | steps | A clean tea routine with both optional steps, milk and sugar, taken; never flags. |
| `tea_self_corrected` | steps | A sequence slip corrected within 15 seconds counts at reduced weight, so the session stays under the flag threshold despite one earlier bad session. |
| `tea_teabag_three_times` | steps | Putting the teabag in three times produces two perseveration errors on the once-only step; does not flag. |
| `meds_self_corrected` | steps | The meds counterpart of `tea_self_corrected`: a sequence slip on `take_pill` corrected within 15 seconds pins the reduced weight for the second task too. |
| `meds_two_errors_one_session` | steps | Two different error types in one session: the pill comes out of the organiser twice (perseveration) and the water is never drunk (omission) - a double dose and a dry swallow together. |
| `meds_pill_substitution` | steps | The meds counterpart of `tea_substitution`: drinking straight from the water jug instead of the glass it was poured into is exactly one substitution error on `drink_water`. |
| `tea_two_errors_one_session` | steps | Two different error types in one session: pouring before the teabag goes in (sequence) and stirring with the milk carton instead of a spoon (substitution). |
| `tea_long_pause_not_error` | steps | An otherwise-correct session with a 100s gap between `teabag_in_cup` and `pour`, under the 120s abandonment threshold: a long pause alone must never surface as a task error or flag a change. |
| `tea_late_start_normal` | steps | A resident who sits for 200s before touching the kettle at all, then makes tea correctly: the long idle before the *first* step must not start the abandonment timer or surface as any error. |
| `meds_long_pause_not_error` | steps | The meds counterpart of `tea_long_pause_not_error`: a 100s gap between `take_pill` and `fill_glass`, under the 120s abandonment threshold, must never surface as a task error or flag a change. |
| `meds_late_start_normal` | steps | The meds counterpart of `tea_late_start_normal`: a resident who sits for 200s before touching the pill organiser or glass at all, then takes the medication correctly: the long idle before the *first* step must not start the abandonment timer or surface as any error. |
| `protein_shake_normal` | steps | The third task's version of `tea_normal` and `meds_normal` (Ian's own routine): powder scooped before the liquid is added, and both optional steps - closing the tub, drinking - skipped. Nothing here may ever be an error. |
| `protein_shake_omit_powder` | steps | The shaker is filled and shaken with no powder ever scooped in: `scoop_powder` is required and never happens, so exactly one omission. |
| `protein_shake_lid_open_shake` | steps | The shaker is shaken before the lid is closed, and the lid is only closed well after the self-correction window: `shake` depends on `close_lid`, done later, so exactly one sequence error. |
| `protein_shake_double_pour` | steps | The liquid is added twice with `scoop_powder` in between, not two events back to back: a perseveration error on `add_liquid`, the protein-shake counterpart of `meds_pill_twice`. |
| `protein_shake_abandoned` | steps | The resident gets the shaker and opens the tub, then leaves a 131-second silence before one last step - scooping the powder in - with the liquid, lid and shake left undone: three omissions plus abandonment, flagging with another recent bad session. |

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
