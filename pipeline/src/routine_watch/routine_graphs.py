"""Find the task graph for any routine id: a built-in file, a graph id, or a saved routine.

Built-ins come first (`tasks.load_task`, by file name such as ``tea``), then a built-in's
own graph id (``make_tea``), then the routines kept from the builder. One place, so the
live camera and the alert path agree on what a routine id means.
"""

from __future__ import annotations

from .tasks import TASKS_DIR, TaskGraph, TaskGraphError, load_task
from .tasks.graph import parse_task_data


def resolve_task(task: str) -> TaskGraph:
    try:
        return load_task(task)
    except TaskGraphError as first:
        for path in TASKS_DIR.glob("*.yaml"):
            graph = load_task(path.stem)
            if graph.id == task:
                return graph
        from . import routine_builder  # lazy: routine_builder imports tasks

        store = routine_builder.get_routine_store()
        saved = store.get(task)
        if saved is None:
            saved = next((r for r in store.list() if str(r.graph.get("id")) == task), None)
        if saved is not None:
            return parse_task_data(saved.graph, source=f"saved routine {task!r}")
        raise first
