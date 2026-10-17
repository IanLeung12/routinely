from typing import Protocol


class Explainer(Protocol):
    def summarise(self, errors: list[dict], baseline: dict, context: list[str]) -> str: ...


def scope_phrase(sessions: int) -> str:
    """What the summary's error count is counted over: one session, or several.

    A change flag rests on two bad sessions inside 48 h (SPEC section 7), so an
    alert's errors are often spread over more than one session and "this session"
    would be a wrong fact in the nurse's first sentence (T155). Callers that really
    are summarising one session (the shift handoff) pass nothing and keep the
    singular. Public because `explain_claude` states the same scope in its prompt.
    """
    return "this session" if sessions <= 1 else f"across {sessions} sessions"


def _format_timestamp(t_start: float) -> str:
    minutes = int(t_start // 60)
    seconds = int(t_start % 60)
    return f"{minutes}:{seconds:02d}"


_PHRASES = {
    "omission": "skipped {step}",
    "perseveration": "repeated {step}",
    "sequence": "{step} out of order",
    "substitution": "wrong object for {step}",
    "hesitation": "long pause at {step}",
    "abandonment": "stopped before {step}",
}


def _format_error(error: dict) -> str:
    step = error["step_id"].replace("_", " ")
    template = _PHRASES.get(error["type"])
    if template is None:
        error_type = error["type"].replace("_", " ")
        phrase = f"{error_type} at {step}"
    else:
        phrase = template.format(step=step)
    return f"{phrase} at {_format_timestamp(error['t_start'])}"


class TemplateExplainer:
    def summarise(self, errors: list[dict], baseline: dict, context: list[str]) -> str:
        observed = baseline["observed"]
        baseline_mean = baseline["baseline_mean"]
        baseline_days = baseline["baseline_days"]
        scope = scope_phrase(baseline.get("sessions", 1))

        if not errors:
            sentence = (
                f"No errors {scope} vs {baseline_mean} normally over "
                f"{baseline_days} days."
            )
        else:
            details = ", ".join(_format_error(e) for e in errors)
            sentence = (
                f"Flagged for review: {observed} errors {scope} ({details}) "
                f"vs {baseline_mean} normally over {baseline_days} days."
            )

        if context:
            sentence += " Context: " + "; ".join(context) + "."

        return sentence
