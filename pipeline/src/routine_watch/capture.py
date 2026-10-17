"""Capture, inside the privacy boundary (SPEC sections 6.1 and 16).

MediaPipe pose and hand landmarks plus the local Roboflow object detector turn each
frame into one JSONL record: landmarks, object boxes and a timestamp. The live camera,
the pre-recorded fallback, tests and scenarios all feed the pipeline through this one
format.

Frames are dropped after processing. Raw video is never stored (SPEC section 8), and
the detector only ever runs locally from downloaded weights, never hosted inference.
"""

STAGE = "capture"

#: Bump whenever the per-frame JSONL record changes shape.
FRAME_SCHEMA_VERSION = 1
