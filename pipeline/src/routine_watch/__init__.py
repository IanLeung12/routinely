"""Routine Watch pipeline.

Capture -> step recogniser -> task graph -> errors -> baseline, plus the API that
serves the nurse dashboard. The pipeline runs on the demo laptop and works offline
(SPEC section 16, decision C).

Every stage module here is a placeholder: it states what the stage owns and the few
constants the spec already fixes. Later tasks fill them in.
"""

__version__ = "0.1.0"

#: Stage modules in the order a session flows through them (SPEC section 6).
#: Names only, so importing this package stays cheap.
STAGES: tuple[str, ...] = (
    "capture",
    "recogniser",
    "task_graph",
    "errors",
    "baseline",
)
