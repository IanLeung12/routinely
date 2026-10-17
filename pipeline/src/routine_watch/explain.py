from typing import Protocol


class Explainer(Protocol):
    def summarise(self, errors: list[dict], baseline: dict, context: list[str]) -> str: ...


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

        if not errors:
            sentence = (
                f"No errors this session vs {baseline_mean} normally over "
                f"{baseline_days} days."
            )
        else:
            details = ", ".join(_format_error(e) for e in errors)
            sentence = (
                f"Flagged for review: {observed} errors this session ({details}) "
                f"vs {baseline_mean} normally over {baseline_days} days."
            )

        if context:
            sentence += " Context: " + "; ".join(context) + "."

        return sentence
