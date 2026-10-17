"""Task graphs as data, plus the loader that reads them (SPEC section 7).

A task is a graph of required dependencies, not a fixed sequence: "teabag in cup" has
to happen before "pour", but "fill kettle" and "get cup" may happen in either order.
Each step lists the objects allowed for it ("spoon or teaspoon both count"), whether it
is optional (milk and sugar are) and whether doing it twice is perseveration.

The graphs live next to this module as `<name>.yaml`, so the data a demo depends on can
be read and reviewed without reading any code::

    graph = load_task("tea")
    graph.deps("pour")              # {'boil', 'teabag_in_cup'}
    graph.allowed_objects("stir")   # {'spoon', 'teaspoon', 'cup'}
    graph.is_optional("milk")       # True

The task-graph tracker (`routine_watch.task_graph`) and the error classifier
(`routine_watch.errors`) read a graph; nothing here looks at step events itself.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import NoReturn

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..contracts import ObjectLabel

#: Task files live beside this module: `tasks/<name>.yaml`.
TASKS_DIR = Path(__file__).resolve().parent

#: Task names, step ids and object aliases are snake_case: safe as filenames, as JSON
#: keys and in the dashboard's URLs.
_SNAKE_CASE = re.compile(r"[a-z][a-z0-9_]*")

#: The detector's class names, as plain strings (SPEC section 6.1).
_DETECTOR_CLASSES = frozenset(str(label) for label in ObjectLabel)


class TaskGraphError(ValueError):
    """A task file is missing, unreadable, or not a usable graph."""


# ------------------------------------------------------------------ the file's shape


class _StepSpec(BaseModel):
    """One `steps:` entry of a task file."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str = Field(min_length=1)
    deps: tuple[str, ...] = ()
    objects: tuple[ObjectLabel, ...] = Field(min_length=1)
    optional: bool = False
    once_only: bool = True


class _TaskSpec(BaseModel):
    """A whole task file."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str = Field(min_length=1)
    aliases: dict[str, ObjectLabel] = {}
    steps: tuple[_StepSpec, ...] = Field(min_length=1)


# ------------------------------------------------------------------------ the graph


@dataclass(frozen=True)
class Step:
    """One step of a task, as the rest of the pipeline sees it."""

    #: The step_id carried by step events, e.g. ``teabag_in_cup``.
    id: str
    #: Plain-language name, for the dashboard's task map.
    label: str
    #: Steps that must happen before this one. Direct dependencies only.
    deps: frozenset[str]
    #: Detector classes this step is done with, in the order the task file lists them.
    objects: tuple[ObjectLabel, ...]
    #: Every object name that counts for this step: those classes plus their aliases.
    #: An object outside this set is a substitution error.
    allowed_objects: frozenset[str]
    #: Skipping it is not an error (milk and sugar).
    optional: bool
    #: Doing it again, after other steps, is perseveration.
    once_only: bool


@dataclass(frozen=True)
class TaskGraph:
    """One task as a dependency graph. Immutable; build it with :func:`load_task`."""

    #: The task_id carried by sessions and step events, e.g. ``make_tea``.
    id: str
    title: str
    #: Every step, in the order the task file lists them (the task map's reading order,
    #: not a required sequence).
    steps: tuple[Step, ...]

    _by_id: dict[str, Step] = field(init=False, repr=False, compare=False, default_factory=dict)

    def __post_init__(self) -> None:
        self._by_id.update((step.id, step) for step in self.steps)

    def __len__(self) -> int:
        return len(self.steps)

    @property
    def step_ids(self) -> tuple[str, ...]:
        """Every step id, in the task file's order."""
        return tuple(step.id for step in self.steps)

    @property
    def required_steps(self) -> tuple[str, ...]:
        """The steps that have to happen; leaving one out is an omission."""
        return tuple(step.id for step in self.steps if not step.optional)

    def step(self, step_id: str) -> Step:
        """One step. Raises ``KeyError`` if this task has no such step."""
        try:
            return self._by_id[step_id]
        except KeyError:
            raise KeyError(f"{self.id} has no step {step_id!r}") from None

    def deps(self, step_id: str) -> frozenset[str]:
        """The steps `step_id` directly depends on."""
        return self.step(step_id).deps

    def allowed_objects(self, step_id: str) -> frozenset[str]:
        """Every object name that counts for `step_id`, aliases included."""
        return self.step(step_id).allowed_objects

    def is_optional(self, step_id: str) -> bool:
        """True if skipping `step_id` is not an error."""
        return self.step(step_id).optional

    def is_once_only(self, step_id: str) -> bool:
        """True if repeating `step_id` later in the session is perseveration."""
        return self.step(step_id).once_only

    def prerequisites(self, step_id: str) -> frozenset[str]:
        """Every step that must happen before `step_id`, directly or through another."""
        seen: set[str] = set()
        pending = list(self.deps(step_id))
        while pending:
            dep = pending.pop()
            if dep not in seen:
                seen.add(dep)
                pending.extend(self.deps(dep))
        return frozenset(seen)

    def is_valid_order(self, order: Sequence[str]) -> bool:
        """True if `order` is one complete, correct way of doing the task.

        Every required step is there, each step comes after all of its dependencies,
        and no step appears twice. Skipped optional steps are fine (SPEC section 7); an
        unknown step id, a repeat or a missing required step are not.
        """
        done: set[str] = set()
        for step_id in order:
            if step_id in done or step_id not in self._by_id:
                return False
            if not self.deps(step_id) <= done:
                return False
            done.add(step_id)
        return done.issuperset(self.required_steps)

    def valid_orders(self, steps: Iterable[str] | None = None) -> Iterator[tuple[str, ...]]:
        """Every order in which `steps` can be done, as a generator of tuples.

        `steps` defaults to the required steps, which is the shortest correct run of the
        task; pass ``step_ids`` to include the optional ones. Every dependency of an
        included step must itself be included. Mostly a test helper: use
        :meth:`is_valid_order` to check what somebody actually did.
        """
        chosen = tuple(dict.fromkeys(self.required_steps if steps is None else steps))
        for step_id in chosen:
            self.step(step_id)
        missing = {dep for step_id in chosen for dep in self.deps(step_id)}.difference(chosen)
        if missing:
            raise TaskGraphError(
                f"{self.id}: cannot order {sorted(chosen)} without {sorted(missing)}"
            )
        return self._orders(chosen, ())

    def _orders(
        self, remaining: tuple[str, ...], done: tuple[str, ...]
    ) -> Iterator[tuple[str, ...]]:
        if not remaining:
            yield done
            return
        satisfied = set(done)
        for step_id in remaining:
            if self.deps(step_id) <= satisfied:
                rest = tuple(other for other in remaining if other != step_id)
                yield from self._orders(rest, (*done, step_id))


# ----------------------------------------------------------------------- the loader


@lru_cache
def load_task(name: str) -> TaskGraph:
    """The task graph in `tasks/<name>.yaml`, e.g. ``load_task("tea")``.

    Cached, because graphs are immutable and every session loads one.
    """
    if not _SNAKE_CASE.fullmatch(name):
        raise TaskGraphError(f"{name!r} is not a task name")
    path = TASKS_DIR / f"{name}.yaml"
    if not path.is_file():
        raise TaskGraphError(f"no task {name!r} in {TASKS_DIR}")
    return parse_task(path.read_text(encoding="utf-8"), source=str(path))


def parse_task(text: str, *, source: str = "<string>") -> TaskGraph:
    """Build a task graph from the YAML text of one task file."""
    try:
        spec = _TaskSpec.model_validate(yaml.safe_load(text))
    except (ValidationError, yaml.YAMLError) as exc:
        raise TaskGraphError(f"{source}: {exc}") from exc
    return _build(spec, source)


def _build(spec: _TaskSpec, source: str) -> TaskGraph:
    """Turn a validated file into a graph, or say why it is not one."""

    def fail(message: str) -> NoReturn:
        raise TaskGraphError(f"{source}: {message}")

    if not _SNAKE_CASE.fullmatch(spec.id):
        fail(f"task id {spec.id!r} is not snake_case")

    ids = [step.id for step in spec.steps]
    if repeated := sorted({step_id for step_id in ids if ids.count(step_id) > 1}):
        fail(f"step ids are not unique: {repeated}")

    # detector class -> the other names that also mean it.
    also_called: dict[str, list[str]] = {}
    for alias, label in spec.aliases.items():
        if not _SNAKE_CASE.fullmatch(alias):
            fail(f"object alias {alias!r} is not snake_case")
        if alias in _DETECTOR_CLASSES:
            fail(f"object alias {alias!r} is already a detector class")
        also_called.setdefault(str(label), []).append(alias)

    steps = []
    for step in spec.steps:
        if not _SNAKE_CASE.fullmatch(step.id):
            fail(f"step id {step.id!r} is not snake_case")
        if unknown := sorted(set(step.deps).difference(ids)):
            fail(f"step {step.id!r} depends on unknown step(s) {unknown}")
        allowed = {str(label) for label in step.objects}
        allowed.update(
            alias for label in step.objects for alias in also_called.get(str(label), ())
        )
        steps.append(
            Step(
                id=step.id,
                label=step.label,
                deps=frozenset(step.deps),
                objects=tuple(dict.fromkeys(step.objects)),
                allowed_objects=frozenset(allowed),
                optional=step.optional,
                once_only=step.once_only,
            )
        )

    graph = TaskGraph(id=spec.id, title=spec.title, steps=tuple(steps))
    for step in steps:
        # A required step behind an optional one could never be done once the optional
        # step is skipped, which would read as an omission the resident cannot avoid.
        if not step.optional and (skippable := sorted(filter(graph.is_optional, step.deps))):
            fail(f"required step {step.id!r} depends on optional step(s) {skippable}")
    if cycle := _unorderable(graph):
        fail(f"dependencies form a cycle: {cycle}")
    return graph


def _unorderable(graph: TaskGraph) -> list[str]:
    """The steps that can never be reached, i.e. the ones in a dependency cycle."""
    done: set[str] = set()
    pending = set(graph.step_ids)
    while pending:
        ready = {step_id for step_id in pending if graph.deps(step_id) <= done}
        if not ready:
            return sorted(pending)
        done |= ready
        pending -= ready
    return []
