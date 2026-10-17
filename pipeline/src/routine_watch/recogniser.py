"""Step recogniser (SPEC section 6.2).

State rules over hand-object interactions turn frame records into timestamped step
events with a confidence score. Low-confidence moments go to the Gemini verifier with
a few cropped, low-res frames from the in-memory ring buffer (SPEC section 16,
decision A); whatever it cannot resolve is marked `unclear` and is never counted as an
error.
"""

STAGE = "recogniser"

#: A step event below this confidence needs the verifier (SPEC section 7).
MIN_STEP_CONFIDENCE = 0.6

#: Give up on the verifier after this long and mark the event `unclear`.
VERIFIER_TIMEOUT_S = 3.0
