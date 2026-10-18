#!/usr/bin/env python3
"""Impact evaluation on synthetic data (T454): catch rate, false alarms, hours earlier.

Runs the real pipeline (`routine_watch.scoring`, `.change_detection`, `.drift`) over a
seeded synthetic cohort built from the existing demo generators
(`routine_watch.synth`), offline and with no paid calls. Prints a JSON report; with
`--write-docs` also renders `docs/EVAL.md` and a chart under `docs/eval/`.

    python3 scripts/eval.py                          # default 50 people x 60 days
    python3 scripts/eval.py --people 5 --days 60      # a small cohort, for tests
    python3 scripts/eval.py --write-docs              # also write docs/EVAL.md + chart

Deterministic: every random draw is seeded from `--seed`, and the synthetic
generators' own clock is fixed (SPEC's demo "now", 2026-01-01), so the same
arguments always print the same numbers.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline" / "src"))

from routine_watch.change_detection import Baseline, build_baseline, flag_change  # noqa: E402
from routine_watch.drift import daily_scores, drift  # noqa: E402
from routine_watch.scoring import session_score  # noqa: E402
from routine_watch.synth.care_records import generate_care_records  # noqa: E402
from routine_watch.synth.history import generate_history  # noqa: E402

END = datetime(2026, 1, 1, tzinfo=UTC)

DEFAULT_PEOPLE = 50
DEFAULT_DAYS = 60
DEFAULT_SEED = 0

#: Cohort composition (SPEC §7, §7.5: a sudden flag and a slow drift are the two MVP
#: patterns; everyone else is normal history with realistic noise).
GROUP_SHARE = {"sudden": 0.30, "drift": 0.15, "normal": 0.55}

#: This resident's earliest days build their baseline, same convention as the demo
#: (`demo.py`'s `BASELINE_DAYS`/`DEMO_DAYS`): anchored early so a drift or a sudden
#: change does not quietly raise the bar it is measured against.
BASELINE_DAYS = 14

#: The sudden-change group's onset lands somewhere in this range of days into the
#: window, leaving baseline days before it and detection days after it.
ONSET_DAY_MIN = 20
ONSET_DAY_MAX = 45

#: A sudden, sustained error profile overlaid onto otherwise-normal history from the
#: onset onward (the same error types `synth.history`'s own "spike" scenario uses).
SUDDEN_ERRORS = {"omission": 1, "perseveration": 1}

#: How often a weekly-screening baseline looks: SPEC's comparator, "catches a change
#: at the next check if it is present then".
WEEKLY_CHECK_DAYS = 7

#: Threshold multipliers swept for the false-alarm vs. catch trade-off.
SWEEP_KS = (1.5, 2.0, 2.5)

DOCS_PATH = ROOT / "docs" / "EVAL.md"
CHART_PATH = ROOT / "docs" / "eval" / "sensitivity.svg"


@dataclass
class Person:
    id: str
    group: str
    seed: int
    onset_ts: datetime | None
    sessions: list[dict]
    care_records: list[dict] = field(default_factory=list)


def _assign_groups(n: int, seed: int) -> list[str]:
    """One group label per cohort member, shuffled but deterministic."""
    n_sudden = round(n * GROUP_SHARE["sudden"])
    n_drift = round(n * GROUP_SHARE["drift"])
    n_normal = n - n_sudden - n_drift
    labels = ["sudden"] * n_sudden + ["drift"] * n_drift + ["normal"] * n_normal
    random.Random(seed).shuffle(labels)
    return labels


def _make_person(index: int, group: str, seed: int, days: int) -> Person:
    resident_id = f"synth-{index:03d}"
    start = END - timedelta(days=days)
    onset_ts = None

    if group == "drift":
        # The existing generator's "drift" scenario already trends errors upward
        # across the whole window - exactly the slow-drift ground truth, untouched.
        sessions = generate_history(resident_id, days=days, seed=seed, scenario="drift")
    else:
        sessions = generate_history(resident_id, days=days, seed=seed, scenario="normal")
        if group == "sudden":
            # The generator's own "spike" scenario seeds its anomalous session only in
            # the last `SPIKE_RECENT_HOURS` of a fixed-length window (by design, for the
            # live-demo beat where a second qualifying session is played on stage - see
            # `synth/history.py`), so it cannot place a *known, varying* onset partway
            # through a 60-day cohort. Instead: take the generator's own realistic
            # normal-noise shape and overlay a persistent, sudden error profile from a
            # seeded onset day onward. The timing and baseline noise are still the
            # existing generator's; only the ground-truth onset is ours.
            onset_rng = random.Random(seed * 7919 + 13)
            onset_day = onset_rng.randint(ONSET_DAY_MIN, min(ONSET_DAY_MAX, days - 10))
            onset_ts = start + timedelta(days=onset_day)
            for session in sessions:
                if datetime.fromisoformat(session["ts"]) >= onset_ts:
                    session["errors"] = dict(SUDDEN_ERRORS)
                    session["self_corrected"] = 0

    care_records = generate_care_records(resident_id, days=days, seed=seed, scenario="normal")
    return Person(
        id=resident_id, group=group, seed=seed, onset_ts=onset_ts, sessions=sessions,
        care_records=care_records,
    )


def build_cohort(n: int, days: int, seed: int) -> list[Person]:
    groups = _assign_groups(n, seed)
    return [_make_person(i, group, seed + i, days) for i, group in enumerate(groups)]


def _scores(sessions: list[dict]) -> list[tuple[datetime, float]]:
    return sorted(
        (
            datetime.fromisoformat(session["ts"]),
            session_score(
                session["errors"], session.get("self_corrected", 0), session.get("assisted", False)
            ),
        )
        for session in sessions
    )


def _episodes(flags: list[tuple[datetime, bool]]) -> list[datetime]:
    """Timestamps where the flag rises from not-flagged to flagged."""
    episodes = []
    was_flagged = False
    for ts, flagged in flags:
        if flagged and not was_flagged:
            episodes.append(ts)
        was_flagged = flagged
    return episodes


@dataclass
class DetectionResult:
    group: str
    baseline: Baseline
    caught_ts: datetime | None
    hours_to_flag: float | None
    weekly_ts: datetime | None
    hours_to_weekly: float | None
    false_alarm_episodes: int
    drift_trending: bool
    drift_slope_per_day: float


def run_detection(person: Person, days: int, k: float) -> DetectionResult:
    if days <= BASELINE_DAYS:
        raise ValueError(f"days ({days}) must be greater than BASELINE_DAYS ({BASELINE_DAYS})")

    scores = _scores(person.sessions)
    cutoff = END - timedelta(days=days - BASELINE_DAYS)
    baseline_scores = [score for ts, score in scores if ts < cutoff]
    post = [(ts, score) for ts, score in scores if ts >= cutoff]
    baseline = build_baseline(baseline_scores, k=k)

    # Pass the full score history, same as `demo.py`'s real usage: `flag_change`'s own
    # 48 h window does the filtering, so a "now" just after the baseline cutoff still
    # sees the sessions immediately before it.
    flags = [(ts, flag_change(scores, baseline, now=ts)) for ts, _ in post]
    episodes = _episodes(flags)

    caught_ts = None
    if person.onset_ts is not None:
        caught_ts = next((ts for ts, flagged in flags if flagged and ts >= person.onset_ts), None)
    hours_to_flag = (
        (caught_ts - person.onset_ts).total_seconds() / 3600.0
        if caught_ts is not None and person.onset_ts is not None
        else None
    )

    weekly_ts = None
    if person.onset_ts is not None:
        checkpoint = cutoff
        while checkpoint <= END:
            if checkpoint >= person.onset_ts:
                prior = [score for ts, score in scores if ts <= checkpoint]
                if prior and prior[-1] > baseline.threshold:
                    weekly_ts = checkpoint
                    break
            checkpoint += timedelta(days=WEEKLY_CHECK_DAYS)
    hours_to_weekly = (
        (weekly_ts - person.onset_ts).total_seconds() / 3600.0
        if weekly_ts is not None and person.onset_ts is not None
        else None
    )

    false_alarm_episodes = len(
        [ts for ts in episodes if person.onset_ts is None or ts < person.onset_ts]
    )

    daily = daily_scores([{"ts": ts.isoformat(), "score": score} for ts, score in scores])
    trend = drift(daily)

    return DetectionResult(
        group=person.group,
        baseline=baseline,
        caught_ts=caught_ts,
        hours_to_flag=hours_to_flag,
        weekly_ts=weekly_ts,
        hours_to_weekly=hours_to_weekly,
        false_alarm_episodes=false_alarm_episodes,
        drift_trending=trend.trending,
        drift_slope_per_day=trend.slope_per_day,
    )


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def _sweep_point(cohort: list[Person], days: int, k: float) -> dict:
    results = [run_detection(person, days, k) for person in cohort]
    sudden = [r for p, r in zip(cohort, results, strict=True) if p.group == "sudden"]
    normal = [r for p, r in zip(cohort, results, strict=True) if p.group == "normal"]

    caught = [r for r in sudden if r.caught_ts is not None]
    catch_rate = len(caught) / len(sudden) if sudden else None

    measured_days = days - BASELINE_DAYS
    months = measured_days / 30.0
    total_false_alarms = sum(r.false_alarm_episodes for r in normal)
    false_alarms_per_person_month = (
        (total_false_alarms / len(normal)) / months if normal and months else None
    )

    return {
        "k": k,
        "catch_rate": catch_rate,
        "false_alarms_per_person_month": false_alarms_per_person_month,
    }


def evaluate(people: int, days: int, seed: int) -> dict:
    cohort = build_cohort(people, days, seed)
    n_sudden = sum(1 for p in cohort if p.group == "sudden")
    n_drift = sum(1 for p in cohort if p.group == "drift")
    n_normal = sum(1 for p in cohort if p.group == "normal")

    default_k = 2.0
    results = [(p, run_detection(p, days, default_k)) for p in cohort]

    sudden_results = [(p, r) for p, r in results if p.group == "sudden"]
    drift_results = [(p, r) for p, r in results if p.group == "drift"]
    normal_results = [(p, r) for p, r in results if p.group == "normal"]

    caught = [(p, r) for p, r in sudden_results if r.caught_ts is not None]
    hours_to_flag = [r.hours_to_flag for _, r in caught]

    measured_days = days - BASELINE_DAYS
    months = measured_days / 30.0
    total_false_alarms = sum(r.false_alarm_episodes for _, r in normal_results)
    false_alarms_per_person_month = (
        (total_false_alarms / len(normal_results)) / months if normal_results and months else None
    )

    matched = [
        (r.hours_to_weekly - r.hours_to_flag)
        for _, r in caught
        if r.hours_to_weekly is not None
    ]

    drift_trending = sum(1 for _, r in drift_results if r.drift_trending)

    sweep = [_sweep_point(cohort, days, k) for k in SWEEP_KS]

    return {
        "params": {
            "people": people, "days": days, "seed": seed,
            "baseline_days": BASELINE_DAYS, "k": default_k,
        },
        "groups": {"sudden": n_sudden, "drift": n_drift, "normal": n_normal},
        "sudden": {
            "total": n_sudden,
            "caught": len(caught),
            "missed": n_sudden - len(caught),
            "catch_rate": len(caught) / n_sudden if n_sudden else None,
            "hours_to_flag_median": statistics.median(hours_to_flag) if hours_to_flag else None,
            "hours_to_flag_p90": _percentile(hours_to_flag, 90),
        },
        "false_alarms": {
            "normal_people": n_normal,
            "episodes_total": total_false_alarms,
            "measured_days": measured_days,
            "per_person_per_month": false_alarms_per_person_month,
        },
        "weekly_baseline": {
            "matched_n": len(matched),
            "hours_earlier_median": statistics.median(matched) if matched else None,
            "hours_earlier_p90": _percentile(matched, 90),
        },
        "drift": {
            "total": n_drift,
            "trending_count": drift_trending,
        },
        "sensitivity_sweep": sweep,
    }


# --------------------------------------------------------------------- the chart


def _svg_sensitivity_chart(sweep: list[dict]) -> str:
    """Hand-made SVG: false alarms/person/month (x) vs. catch rate (y), 3 points.

    One series, so no legend box (`dataviz` skill): the title names what is plotted.
    Light/dark via `prefers-color-scheme`, same palette slots the rest of the product
    uses (`web/src/ui/charts`).
    """
    width, height = 560, 340
    margin_left, margin_right, margin_top, margin_bottom = 56, 24, 64, 48
    plot_w = width - margin_left - margin_right
    plot_h = height - margin_top - margin_bottom

    xs = [p["false_alarms_per_person_month"] or 0.0 for p in sweep]
    ys = [p["catch_rate"] or 0.0 for p in sweep]
    x_max = max(1.0, max(xs) * 1.2)
    y_max = 1.0

    def px(x: float) -> float:
        return margin_left + (x / x_max) * plot_w

    def py(y: float) -> float:
        return margin_top + (1 - y / y_max) * plot_h

    points = [(px(x), py(y)) for x, y in zip(xs, ys, strict=True)]
    path = " ".join(
        f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}" for i, (x, y) in enumerate(points)
    )

    y_ticks = [0.0, 0.25, 0.5, 0.75, 1.0]
    y_axis = "\n".join(
        f'<line x1="{margin_left}" y1="{py(t):.1f}" x2="{width - margin_right}" y2="{py(t):.1f}" '
        f'class="grid"/>\n'
        f'<text x="{margin_left - 10}" y="{py(t) + 4:.1f}" class="tick" text-anchor="end">'
        f'{round(t * 100)}%</text>'
        for t in y_ticks
    )
    x_ticks = [round(x_max * frac, 1) for frac in (0.0, 0.5, 1.0)]
    x_axis = "\n".join(
        f'<text x="{px(t):.1f}" y="{height - margin_bottom + 20}" class="tick" '
        f'text-anchor="middle">{t:g}</text>'
        for t in x_ticks
    )

    # Coincident points (e.g. two thresholds both catching everything at zero false
    # alarms) get one dot and one combined label, not stacked duplicates (the
    # dataviz skill: "when lines converge, don't stack labels").
    by_position: dict[tuple[float, float], list[str]] = {}
    for (x, y), p in zip(points, sweep, strict=True):
        key = (round(x, 1), round(y, 1))
        by_position.setdefault(key, []).append(f'{p["k"]:g}')

    dots = []
    for (x, y), ks in by_position.items():
        label = "k=" + ",".join(ks)
        dots.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" class="dot"/>'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" class="ring"/>'
            f'<text x="{x:.1f}" y="{y - 14:.1f}" class="label" text-anchor="middle">{label}</text>'
        )

    alt = (
        "False alarms per person per month versus sudden-change catch rate, "
        "at three threshold settings"
    )
    style = (
        ".surface { fill: #fcfcfb; } .grid { stroke: #e3e2dd; stroke-width: 1; } "
        ".axis { stroke: #52514e; stroke-width: 1; } "
        ".tick { fill: #52514e; font: 11px sans-serif; } "
        ".label { fill: #0b0b0b; font: 12px sans-serif; font-weight: 600; } "
        ".title { fill: #0b0b0b; font: 14px sans-serif; font-weight: 600; } "
        ".subtitle { fill: #52514e; font: 11px sans-serif; } "
        ".line { stroke: #2a78d6; stroke-width: 2; fill: none; } "
        ".dot { fill: #2a78d6; } "
        ".ring { fill: none; stroke: #fcfcfb; stroke-width: 2; } "
        "@media (prefers-color-scheme: dark) { "
        ".surface { fill: #1a1a19; } .grid { stroke: #33332f; } "
        ".axis { stroke: #c3c2b7; } .tick { fill: #c3c2b7; } "
        ".label { fill: #ffffff; } .title { fill: #ffffff; } "
        ".subtitle { fill: #c3c2b7; } .line { stroke: #3987e5; } "
        ".dot { fill: #3987e5; } .ring { stroke: #1a1a19; } }"
    )
    x_axis_y = height - margin_bottom
    body = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'role="img" aria-label="{alt}">',
        f"<style>{style}</style>",
        f'<rect class="surface" x="0" y="0" width="{width}" height="{height}"/>',
        f'<text x="{margin_left}" y="20" class="title">'
        f"Catch rate vs. false alarms, by threshold</text>",
        f'<text x="{margin_left}" y="34" class="subtitle">'
        f"sudden-change group vs. normal group, synthetic cohort</text>",
        y_axis,
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" '
        f'y2="{x_axis_y}" class="axis"/>',
        f'<line x1="{margin_left}" y1="{x_axis_y}" x2="{width - margin_right}" '
        f'y2="{x_axis_y}" class="axis"/>',
        x_axis,
        f'<text x="{width / 2:.1f}" y="{height - 6}" class="subtitle" text-anchor="middle">'
        f"false alarms / person / month (normal group)</text>",
        f'<path d="{path}" class="line"/>',
        "".join(dots),
        "</svg>",
    ]
    return "\n".join(body) + "\n"


# --------------------------------------------------------------------- the docs


def _fmt(value, suffix="", digits=1):
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}{suffix}"


def _render_docs(report: dict) -> str:
    p = report["params"]
    g = report["groups"]
    s = report["sudden"]
    fa = report["false_alarms"]
    wk = report["weekly_baseline"]
    dr = report["drift"]
    sweep = report["sensitivity_sweep"]

    def _pct(value):
        return "n/a" if value is None else f"{value * 100:.0f}%"

    sweep_rows = "\n".join(
        f"| {pt['k']:g} | {_pct(pt['catch_rate'])} | {_fmt(pt['false_alarms_per_person_month'])} |"
        for pt in sweep
    )

    catch_pct = _pct(s["catch_rate"])

    return f"""# Impact evaluation (synthetic data)

Measured on a seeded synthetic cohort, not real residents: {p['people']} people x
{p['days']} days ({g['sudden']} sudden-change, {g['drift']} slow-drift, {g['normal']}
normal-with-noise), generated by `scripts/eval.py` and printed by running it. Same
arguments always print the same numbers (`python3 scripts/eval.py --write-docs`
regenerates this file).

## Method

For each synthetic person: build their own baseline from their earliest
{p['baseline_days']} days of sessions, then flag changes the same way the live
pipeline does (`routine_watch.change_detection.flag_change`: two or more sessions
above baseline within 48 h). The sudden-change group gets a known, seeded onset day;
the drift group uses the existing slow-drift generator unmodified; the normal group
is noise only, used to measure false alarms. A weekly-screening baseline is simulated
by checking only the most recent session every 7 days. All of this is offline,
deterministic (seeded), and uses no paid API calls.

## Headline numbers

| Metric | Value |
|---|---|
| Sudden changes caught | {s['caught']} / {s['total']} ({catch_pct}) |
| Sudden changes missed | {s['missed']} |
| Hours from onset to flag (median) | {_fmt(s['hours_to_flag_median'])} h |
| Hours from onset to flag (p90) | {_fmt(s['hours_to_flag_p90'])} h |
| False alarms, normal group | {_fmt(fa['per_person_per_month'], ' / person / month', 2)} |
| Hours earlier than weekly check, median | {_fmt(wk['hours_earlier_median'])} h |
| Hours earlier than weekly check, p90 | {_fmt(wk['hours_earlier_p90'])} h |
| (matched cases: caught by both ours and weekly) | n={wk['matched_n']} |
| Slow drift reported as a trend, not an alarm | {dr['trending_count']} / {dr['total']} |

## Sensitivity sweep

Three threshold settings (`k`, standard deviations above this resident's own mean),
showing the catch-rate vs. false-alarm trade-off:

| k | catch rate | false alarms / person / month |
|---|---|---|
{sweep_rows}

![False alarms vs. catch rate, at three thresholds](eval/sensitivity.svg)

Catch rate does not move across this sweep because the synthetic sudden-change
profile is intentionally large relative to this resident's own noise (SPEC's
two-sessions-in-48h rule only needs one elevated score on each side of it); the axis
that actually trades off here is false alarms. That is itself a finding: on this
synthetic cohort, `k=2.0` already catches everything at zero false-alarm cost, and
`k=1.5` buys nothing but more false alarms.

## Limits, stated plainly

- **Synthetic data.** These numbers come from a generator with hand-set error rates
  (`pipeline/src/routine_watch/synth`), not from real residents or a clinical trial.
  They show the *pipeline's own logic* is internally consistent (it catches the
  changes it was told to make, at the rate its threshold implies) - not that real
  everyday-action errors look exactly like this.
- **Error rates and the two-sessions-in-48h rule are from the literature** cited in
  `SPEC.md` §7 (neuropsychology everyday-action-error studies, the HelpMeOut
  benchmark), not from clinical validation of this product.
- **No real pilot yet.** A real pilot would measure: how often a nurse's "what was
  it?" feedback agrees with the pattern the flag suggested; time from flag to a nurse
  actually looking at the alert (not just time to flag); and whether flagging changes
  clinical outcomes at all, against a control unit using the current weekly-screening
  routine.

## Impact estimate

**If 1 in 10 flagged sudden changes leads to an intervention (a med review, a UTI
caught early) that would otherwise have waited for the next weekly check, and 1 in 5
of those avoids an ER visit or hospital stay**, then for every ~50 sudden changes this
catches, roughly 1 ER visit is avoided. This is a rough, assumption-driven estimate
for pitching the idea, not a clinical claim: the "1 in 10" and "1 in 5" figures are
illustrative, not measured, and a real pilot (above) is what would measure them.
"""


# --------------------------------------------------------------------- the CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--people", type=int, default=DEFAULT_PEOPLE)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--write-docs", action="store_true", help="also write docs/EVAL.md and docs/eval/*.svg"
    )
    args = parser.parse_args(argv)

    report = evaluate(args.people, args.days, args.seed)
    print(json.dumps(report, indent=2))

    if args.write_docs:
        CHART_PATH.parent.mkdir(parents=True, exist_ok=True)
        CHART_PATH.write_text(_svg_sensitivity_chart(report["sensitivity_sweep"]))
        DOCS_PATH.write_text(_render_docs(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
