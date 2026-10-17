"""Error classifier (SPEC section 7).

One session's step events plus the task graph in, that session's everyday-action
errors out::

    from routine_watch.tasks import load_task
    errors = classify_errors(events, load_task("tea"), session_id="tea-1")

Five of the six error types in the spec's table are here, because five of them are
rules about the task graph: **omission**, **sequence**, **perseveration**,
**substitution** and **abandonment**. The sixth, **hesitation**, is a step or gap far
longer than *this resident's own* average, so it needs a personal baseline rather than
a graph and lives in `routine_watch.hesitation`.

What is deliberately not an error matters just as much:

* **Valid alternative orders.** The graph's `deps` are the only ordering rules, so
  filling the kettle before fetching the cup and after it are both correct.
* **Skipped optional steps**: milk and sugar.
* **A slip the resident puts right** inside `self_correct_window_s`. That is still
  reported, with `self_corrected=True`: a weaker signal, which the session score
  weighs less.
* **Anything only an `unclear` event points at.** One rule covers every one of them:
  an unclear event can only ever make this classifier quieter, never louder. It is a
  step the verifier could not resolve, so it counts as something that may have
  happened - it satisfies a dependency, keeps a step off the omission list and breaks
  a silence - but it is never itself the subject of an error.

Sessions with a second person in frame are "assisted" and are excluded before this
point (SPEC section 7): this module sees one person's attempt at one task.

Every error carries the step events it was read from as evidence the dashboard can
open (SPEC section 9.4), and an `error_id` built from the session, the error and the
event it is pinned to. Classifying the same session twice - a live session every few
seconds, say - gives the same errors with the same ids, so the dashboard can tell a
new error from one it is already showing.
"""

from __future__ import annotations

from collections.abc import Sequence

from .contracts import ErrorType, EvidenceKind, EvidenceRef, StepEvent, TaskError
from .tasks import Step, TaskGraph

STAGE = "errors"

#: The error types in SPEC section 7, as plain strings in the contract's order. The
#: weights that turn them into a session score are hand-set in `routine_watch.scoring`.
ERROR_TYPES: tuple[str, ...] = tuple(str(error_type) for error_type in ErrorType)

#: No events for this long, with required steps still to do, is abandonment (SPEC
#: section 7: "no events for N minutes"). Hand-set for the MVP.
ABANDON_AFTER_S = 120.0

#: A slip the resident puts right inside this many seconds is a self-corrected slip
#: rather than a full error.
SELF_CORRECT_WINDOW_S = 15.0


def classify_errors(
    events: Sequence[StepEvent],
    graph: TaskGraph,
    *,
    session_id: str,
    ended: bool = True,
    abandon_after_s: float = ABANDON_AFTER_S,
    self_correct_window_s: float = SELF_CORRECT_WINDOW_S,
) -> list[TaskError]:
    """The graph-based errors in one session, oldest first.

    `events` is one session's step events in any order: they are read in time order, so
    the same session always gives the same errors however they arrive.

    `ended` is the difference between the two halves of the spec's omission rule. A
    required step that has not happened is an error as soon as something that depends
    on it is done, and otherwise only once the task is over. Pass ``ended=False`` for a
    live session, so the task map can flash red for what is already wrong without
    calling an unfinished task incomplete.

    Raises ``KeyError`` if an event names a step this task graph does not have.
    """
    timeline = sorted(events, key=lambda event: (event.t_start, event.t_end, event.event_id))
    if unknown := sorted({event.step_id for event in timeline}.difference(graph.step_ids)):
        raise KeyError(f"{graph.id} has no step(s) {unknown}")

    found: list[TaskError] = []

    def add(
        error_type: ErrorType,
        step_id: str | None,
        t_start: float,
        t_end: float,
        evidence: list[EvidenceRef],
        *,
        anchor: str,
        self_corrected: bool = False,
    ) -> None:
        """Record one error. `anchor` is what makes its id unique and repeatable: the
        event the error is pinned to, or `end` for a step the session never got to."""
        found.append(
            TaskError(
                error_id=f"{session_id}:{error_type}:{step_id or '-'}:{anchor}",
                session_id=session_id,
                type=error_type,
                step_id=step_id,
                t_start=t_start,
                t_end=t_end,
                evidence=evidence,
                self_corrected=self_corrected,
            )
        )

    #: Steps with an event of any kind. An unclear one may still have happened, so it
    #: counts here: the step is not missing, it is just not certain.
    seen = {event.step_id for event in timeline}
    #: Steps already reported missing, so each is reported once however many steps
    #: depended on it.
    omitted: set[str] = set()
    #: Events that put an earlier slip right. Redoing a step properly is a correction,
    #: not perseveration.
    corrections: set[str] = set()

    done: set[str] = set()  # steps that may have happened by now, unclear ones included
    first_time: dict[str, StepEvent] = {}  # step -> the first confident event for it
    previous: StepEvent | None = None  # the event before this one, unclear ones included
    last_confident: str | None = None  # the step the last confident event showed

    for index, event in enumerate(timeline):
        step = graph.step(event.step_id)
        rest = timeline[index + 1 :]

        # Abandonment: the task started, then nothing happened for long enough, with
        # required steps still to do. The silence is what the error is, so an unclear
        # event at either end still breaks it.
        if (
            previous is not None
            and event.t_start - previous.t_end > abandon_after_s
            and not done.issuperset(graph.required_steps)
        ):
            add(
                ErrorType.ABANDONMENT,
                None,
                previous.t_end,
                event.t_start,
                [_points_at(previous), _points_at(event)],
                anchor=event.event_id,
            )
        previous = event

        if event.unclear:
            done.add(step.id)
            continue

        here = _points_at(event)

        # Substitution: done with an object this step does not allow. Doing it again
        # properly, soon enough, is the resident putting it right.
        if not _allowed(event, step):
            redo = _done_properly(rest, step, after=event, within=self_correct_window_s)
            if redo is not None:
                corrections.add(redo.event_id)
            add(
                ErrorType.SUBSTITUTION,
                step.id,
                event.t_start,
                event.t_end if redo is None else redo.t_end,
                [here] if redo is None else [here, _points_at(redo)],
                anchor=event.event_id,
                self_corrected=redo is not None,
            )

        # One step done before another it depends on. Whether that is a sequence error
        # or an omission is decided by what happens next: a dependency done later is
        # the wrong order, one that never happens at all is a missing step.
        undone = sorted(step.deps - done)
        late = {dep: fix for dep in undone if (fix := _next_confident(rest, dep)) is not None}
        if late:
            fixes = list(late.values())
            put_right = all(fix.t_end - event.t_end <= self_correct_window_s for fix in fixes)
            add(
                ErrorType.SEQUENCE,
                step.id,
                event.t_start,
                max(event.t_end, *(fix.t_end for fix in fixes)),
                [here, *(_points_at(fix) for fix in fixes)],
                anchor=event.event_id,
                self_corrected=put_right,
            )
        for dep in undone:
            if dep not in seen and dep not in omitted and not graph.is_optional(dep):
                omitted.add(dep)
                add(
                    ErrorType.OMISSION,
                    dep,
                    event.t_start,
                    event.t_end,
                    [here],
                    anchor=event.event_id,
                )

        # Perseveration: a once-only step done again with another step in between.
        # Two events in a row for the same step are the recogniser seeing one action
        # twice, not the resident repeating it.
        repeated = step.once_only and step.id in first_time and last_confident != step.id
        if repeated and event.event_id not in corrections:
            add(
                ErrorType.PERSEVERATION,
                step.id,
                event.t_start,
                event.t_end,
                [_points_at(first_time[step.id]), here],
                anchor=event.event_id,
            )

        done.add(step.id)
        first_time.setdefault(step.id, event)
        last_confident = step.id

    # The other half of the omission rule: the task is over and a required step never
    # happened. There is no event to point at, so the evidence is the skeleton replay
    # of the session it is missing from.
    if ended:
        session_end = max((event.t_end for event in timeline), default=0.0)
        for step_id in graph.required_steps:
            if step_id not in seen and step_id not in omitted:
                replay = [_replay_over(0.0, session_end)] if timeline else []
                add(ErrorType.OMISSION, step_id, 0.0, session_end, replay, anchor="end")

    reading_order = {step_id: index for index, step_id in enumerate(graph.step_ids)}
    return sorted(
        found,
        key=lambda error: (
            error.t_start,
            error.t_end,
            reading_order.get(error.step_id or "", -1),
            str(error.type),
        ),
    )


def _allowed(event: StepEvent, step: Step) -> bool:
    """True if every object the step was done with is one the task allows for it."""
    return all(str(label) in step.allowed_objects for label in event.objects)


def _next_confident(events: Sequence[StepEvent], step_id: str) -> StepEvent | None:
    """The first event in `events` that confidently shows `step_id`."""
    return next((e for e in events if e.step_id == step_id and not e.unclear), None)


def _done_properly(
    events: Sequence[StepEvent], step: Step, *, after: StepEvent, within: float
) -> StepEvent | None:
    """The event where the resident does `step` again, properly and soon enough for it
    to count as putting the slip in `after` right (SPEC section 7, self-corrected slip).
    """
    return next(
        (
            event
            for event in events
            if event.step_id == step.id
            and not event.unclear
            and _allowed(event, step)
            and event.t_end - after.t_end <= within
        ),
        None,
    )


def _points_at(event: StepEvent) -> EvidenceRef:
    """Evidence pointing at one step event."""
    return EvidenceRef(
        kind=EvidenceKind.STEP_EVENT,
        t_start=event.t_start,
        t_end=event.t_end,
        event_id=event.event_id,
    )


def _replay_over(t_start: float, t_end: float) -> EvidenceRef:
    """Evidence pointing at the skeleton replay of a span: what a nurse looks at when
    there is no event to point at. Never a video clip (SPEC section 8)."""
    return EvidenceRef(kind=EvidenceKind.SKELETON_REPLAY, t_start=t_start, t_end=t_end)
