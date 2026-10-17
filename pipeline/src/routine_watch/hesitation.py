"""Flag steps or gaps that took much longer than this resident's own average."""

from collections.abc import Mapping, Sequence

from routine_watch.baseline import HESITATION_SIGMA


def hesitations(
    durations: Mapping[str, float],
    history: Mapping[str, Sequence[float]],
    sigma: float = HESITATION_SIGMA,
    min_history: int = 3,
    min_std: float = 1.0,
) -> list[str]:
    flagged = []
    for name, duration in durations.items():
        past = history.get(name, [])
        if len(past) < min_history:
            continue
        mean = sum(past) / len(past)
        variance = sum((x - mean) ** 2 for x in past) / len(past)
        std = variance**0.5
        threshold = mean + sigma * max(std, min_std)
        if duration > threshold:
            flagged.append(name)
    return sorted(flagged)
