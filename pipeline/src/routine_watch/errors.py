"""Error classifier (SPEC section 7).

Turns step events plus the task graph into the six everyday-action error types below.
Valid alternative orders, skipped optional steps, slips the resident fixes straight
away, sessions with staff in frame and `unclear` events are all not errors.
"""

STAGE = "errors"

#: The error types in SPEC section 7. The weights that turn them into a session score
#: are hand-set in a later task.
ERROR_TYPES: tuple[str, ...] = (
    "omission",
    "sequence",
    "perseveration",
    "substitution",
    "hesitation",
    "abandonment",
)
