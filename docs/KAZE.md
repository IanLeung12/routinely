# Project KAZE: safety check-ins

> "Help when someone can't ask for it themselves."

Routine Watch watches an everyday routine and **flags a change for review** when
somebody's own pattern shifts (SPEC §7). KAZE is what happens next: the person is
asked to check in, and if they don't, the people *they* chose are alarmed one after
another until somebody says they're on it.

Where it lives:

| | |
|---|---|
| The rules | `SPEC.md` §18 (and §17 for who the supporters are) |
| The state machine | `pipeline/src/routine_watch/checkin.py` (pure, injected clock) |
| The routes + the countdown | `pipeline/src/routine_watch/api_checkin.py` |
| The screens | `web/src/checkin/` (`AlarmBanner`, `EscalationTimeline`, `SafetySettings`) |
| The scenario runner | `scripts/kaze_demo.py` (this document's `run` column) |
| Tests | `pipeline/tests/test_checkin.py`, `test_api_checkin.py`, `tests/test_kaze_demo.py` |

## The flow

```
                   safety PIN
       ┌──────────────────────────────────────────────▶ ok        (nobody is woken)
       │
  pending ──── duress PIN ───▶ alarm  (silent) ──┐
       │                                          │
       └──── window runs out ──▶ alarm ───────────┼──▶ acknowledged ──▶ resolved
                                   │              │      ("I'm on it")   (false alarm
                       ack window  │              │                       | helped
                       runs out    ▼              │                       | other)
                                escalated ────────┘
                              (supporter #2, #3 …; when the list runs
                               out the alarm stays open and says so)
```

Every transition is appended to the check-in's event log with a timestamp and who it
was by. **The countdown is the server's**: deadlines live server-side and a background
tick advances them once a second, so the alarm still fires when the person's device
drops off the network after the check-in started.

| | Default | The demo people |
|---|---|---|
| Check-in window (the person) | 120 s | 20 s |
| Ack window (each supporter) | 120 s | 15 s |
| Safety PIN / duress PIN | none set | `1234` / `9111` (seeded, changeable) |

Mrs. K's list is Nurse Ana (#1: location, alert details, replays) then the on-call
care line (#2: the alarm and nothing else). Mr. D's is his daughter Lena, then the
same care line. Sam has nobody linked: their alarm stays theirs, and the log says so.

## Run it

```sh
scripts/dev.sh up                         # API on :8000, dashboard on :5173
python3 scripts/kaze_demo.py --list       # the seven scenarios, one line each
python3 scripts/kaze_demo.py duress       # one of them, on the demo's timings
python3 scripts/kaze_demo.py all          # all seven, about 2½ minutes
python3 scripts/kaze_demo.py all --fast   # the same with 5 s windows, about 45 s
scripts/dev.sh down
```

The runner prints every state change with the time it happened and the request that
caused it, and **exits non-zero if the flow does not play out the way SPEC §18 says it
must** — it is a check of the flow, not a narration of it. It talks to nothing but the
check-in API (`POST /checkins/demo`, `GET /checkins/active`,
`POST /checkins/{id}/respond|ack|resolve|simulate`, `GET/PUT /people/{id}/safety`), so
it is also the smallest possible example of driving this feature from the outside.

Two things start a check-in: a session that **flags a change for review** (the API does
it on `session_end`, once per alert), or `POST /checkins/demo` by hand. The runner uses
the second, with a made-up alert id, so a scenario does not need a bad session first.

## The seven scenarios

Each row is one of SPEC §18's scenarios. **Run** is the runner; **click** is the same
thing in the dashboard, which needs a check-in in flight — start one with the runner
(or `curl -X POST localhost:8000/checkins/demo -H 'content-type: application/json' -d
'{"person":"mrs-k"}'`) and watch the supervisor's screen.

| # | Scenario | Run | Click | What it shows |
|---|---|---|---|---|
| 1 | safe | `kaze_demo.py safe` | Supervisor role: the alarm banner stays empty | The person checks in; nobody is woken. A wrong PIN is refused and the countdown carries on |
| 2 | no-response | `kaze_demo.py no-response` | Wait out the 20 s window: the banner appears with "Is everyone okay?", a countdown and the shared location; press **I'm on it** | An unanswered question becomes supporter #1's alarm |
| 3 | duress | `kaze_demo.py duress` | The person's PIN pad is T451 and is not on `main` yet, so run it: the supervisor's banner then says **silent help request**, while the person's own payload reads exactly as `1234` left it | The duress PIN alarms without the person's screen showing anything |
| 4 | disconnect | `kaze_demo.py disconnect` | Start a check-in, close the person's tab, wait: the banner still appears | The countdown is the server's, so a device going quiet does not silence the alarm |
| 5 | unacknowledged | `kaze_demo.py unacknowledged` | Leave the banner alone for the 15 s ack window: the escalation timeline shows it passing to the care line | Nobody answers, so it goes down the list in order |
| 6 | false-alarm | `kaze_demo.py false-alarm` | Pick **False alarm** in *Resolution reason* and press **Resolve** | Either a supporter or the person can close it, with a reason, and it leaves both screens |
| 7 | privacy | `kaze_demo.py privacy` | **Safety settings** → turn *Simulated location* off for a supporter, then look at their banner | Each supporter is told only what that person switched on for *them*: what is off is **absent**, not blanked |

Each scenario also leaves the stack as it found it: windows and sharing it changed go
back, and a check-in it left open is closed.

## What the prototype demonstrates

Real, running code — not a mock, and not a storyboard:

- **The state machine.** `pending → ok | alarm → escalated → acknowledged | resolved`,
  with the escalation order the person chose and an event log of every transition. It
  is pure, takes its clock as an argument, and the seven scenarios are tested against
  a clock the test owns (`pipeline/tests/test_checkin.py`).
- **A server-owned countdown.** Deadlines are stored server-side and advanced by a
  background tick once a second, and every route advances the same way before it
  answers — so an alarm fires with no screen connected at all, and a check-in reads
  right after an API restart.
- **Duress that cannot be read over a shoulder.** The safety PIN and the duress PIN
  answer the person's device with *the same bytes*; the duress one raises a silent
  alarm that nothing on the person's side ever reveals. The runner shows the two
  payloads side by side; `test_api_checkin.py` pins them byte for byte.
- **Per-supporter sharing.** Location, alert details (the alert behind it and the event
  log) and replays are three separate switches, per supporter. A payload carries only
  what is on; what is off is absent from the JSON, not blanked.
- **PINs that are not stored.** Salted PBKDF2-SHA256 hashes, never returned by a route,
  never written to a log, never in a 422 that quotes the value it rejected.
- **The screens.** A supervisor's alarm banner with a countdown, "I'm on it", a
  resolution reason and the escalation timeline; safety settings for windows, the
  ordered supporter list, the three sharing switches and both PINs.

## What is simulated

- **No alarm ever leaves the building.** Nothing calls, texts, pages or push-notifies
  anybody: an alarm is a payload a screen polls for (and a `checkin` message on the
  live socket). There is no provider, no phone number and no delivery receipt.
- **The location is a string the person typed** ("Room 204, care home"), shared or not
  per supporter, and every payload that carries it says `location_simulated: true`.
  Nothing reads a device's location.
- **The supporter list is the demo's.** Mrs. K, Mr. D and Sam are seeded in code, and
  SPEC §17's invite/link flow lives in the frontend's mock (`web/src/people/api.ts`).
- **The demo's timings and PINs are seeded** (20 s / 15 s, `1234` / `9111`) so the flow
  fits on stage. Real windows default to 120 s.
- **Live check-ins are in one process's memory.** Settings persist (one JSON file per
  person under `SAFETY_DIR`); a check-in in flight does not survive a restart.
- **A flagged change is the only trigger.** There is no fall detector, no wearable, no
  inactivity timer and no "help" button wired to this yet.
- **No account behind the PIN.** A 4–12 character PIN with no account, no rate limit and
  no lockout is a demo, not a product.

## Assumptions

- The person **wants** to be asked. A check-in is a question about whether somebody is
  okay, never a judgement about them, and the person sees exactly what their
  supervisors see (SPEC §12, §17).
- Somebody is reachable. The escalation list is only as good as the people on it; with
  nobody linked the alarm has nowhere to go, and when the list runs out the alarm stays
  open and says so rather than quietly closing.
- A short window is kinder than a long one *here*, because the cost of being asked
  twice is far lower than the cost of nobody asking. The windows are the person's to
  set, not ours.
- The person can reach their own device to answer. A duress PIN assumes they can be
  made to answer it — which is the whole reason the answer is indistinguishable.
- Flags are rare enough that a check-in per flag does not become background noise.

## What needs validation

Nothing below is measured yet; each one is a question a pilot would answer.

- **Delivery.** A real push/SMS/call provider (and the retry, receipt and
  do-not-disturb behaviour that comes with it): does supporter #1 actually get it
  inside their ack window, at 3 a.m., on a phone in a drawer? Everything here assumes
  an open screen that polls.
- **Location.** Whether a room, an address or a device location is the right thing to
  share, what the person is willing to share with whom, and what a supporter actually
  needs to act — plus the consent and retention rules that come with a real one.
- **Other signals.** Wearable or ambient input (falls, heart rate, bed/chair sensors,
  inactivity) would change both what starts a check-in and how confident it is. None of
  it is wired in, and each source brings its own false-alarm profile.
- **False-alarm rate.** `docs/EVAL.md` measures the flag rate on synthetic data
  (0 false alarms per person per month on the normal group, synthetic); a check-in per
  flag inherits whatever the real rate is. The number that matters is *alarms a
  supporter is woken by, per month, that turn out to be nothing* — and the rate at
  which people stop answering because of them.
- **The windows.** 120 s / 120 s and 20 s / 15 s are guesses. How long should somebody
  have before their daughter's phone rings?
- **Duress in practice.** Whether people can remember and use a second PIN under
  pressure, and whether "the alarm goes out anyway" is the right behaviour in every
  situation it would fire in.
- **PIN security.** Rate limiting, lockout and an account behind the PIN before this
  goes anywhere near a real person.
- **Whether it helps.** The outcome that matters is somebody getting help sooner than
  they would have. Measuring that needs a pilot with real people, real supporters and
  real response times — see `docs/EVAL.md` for the shape such a study would take.
