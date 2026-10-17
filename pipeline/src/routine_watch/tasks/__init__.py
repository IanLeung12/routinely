"""The task graphs, as data: ``load_task("tea")`` is the make-tea graph (SPEC section 7).

Each task is one `<name>.yaml` file in this package, read by `graph.py`.
"""

from .graph import TASKS_DIR, Step, TaskGraph, TaskGraphError, load_task, parse_task

__all__ = [
    "TASKS_DIR",
    "Step",
    "TaskGraph",
    "TaskGraphError",
    "load_task",
    "parse_task",
]
