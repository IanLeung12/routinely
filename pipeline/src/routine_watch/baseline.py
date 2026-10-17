"""Personal baseline and change detection (SPEC sections 6.3 and 7).

One baseline per resident per task - error score, step durations, gaps between steps -
and a detector that compares each new session against it.

Two or more sessions above that resident's own threshold within 24-48 h flag a change
for a nurse to review. A single bad session never alerts, and a sustained upward trend
over weeks is reported as a trend rather than as an alert.
"""

STAGE = "baseline"

#: Hesitation threshold, in standard deviations above this resident's own average.
HESITATION_SIGMA = 2.5

#: Sessions above threshold needed inside the window before a change is flagged.
FLAG_MIN_SESSIONS = 2
